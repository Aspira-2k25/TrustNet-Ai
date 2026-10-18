"""Reproducible offline candidate development; never changes the deployed bundle.

Historical test is a regression set (already seen during previous development).
Fresh challenge is frozen before fitting, never used for model/threshold selection.
Only aggregate research reports leave ignored data/; URLs remain inert local data.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import random
import sys
import time
import warnings
import zipfile
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('MKL_NUM_THREADS','2')
import joblib
import lightgbm as lgb
import numpy as np
import tldextract
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.isotonic import IsotonicRegression
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
from models.phishing_url.inference.modern_model import masked_url_text,meta_features,ModernModel
from models.phishing_url.preprocessing.structural_features import extract,NAMES
from models.phishing_url.evaluation.metrics import metrics

DATA=ROOT/'models/phishing_url/data/improvement_20261018'
FRESH=DATA/'fresh_holdout_v2'
OUT=ROOT/'models/phishing_url/checkpoints/research_v6'
REPORT=ROOT/'models/phishing_url/research/improvement_20261018.json'
BASE=ROOT/'models/phishing_url/checkpoints/modern_v5'
suffix=tldextract.TLDExtract(suffix_list_urls=(),cache_dir=None,include_psl_private_domains=True)
SEED=20261018
threadpool_limits(limits=2)

def log(stage,**values): print(json.dumps({'stage':stage,**values}),flush=True)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2),encoding='utf-8')
@lru_cache(maxsize=300000)
def domain(host):return suffix(host).top_domain_under_public_suffix or host
def identity(url):
    p=urlsplit(url)
    host=(p.hostname or '').rstrip('.').encode('idna').decode('ascii').lower()
    if not host or p.scheme not in {'http','https'}:raise ValueError('Invalid URL')
    return (p.netloc.lower()+(p.path or '/')+('?' + p.query if p.query else ''))[:2048],domain(host)

def readrows(path):
    with path.open(encoding='utf-8') as f:return list(csv.DictReader(f))

def prepare():
    cache=DATA/'prepared.joblib'
    if cache.exists():
        log('loading_cached_research_features')
        cached=joblib.load(cache)
        if digest(FRESH/'holdout.csv')!=cached['audit']['fresh_snapshot_sha256']:
            raise ValueError('Frozen holdout changed since feature preparation')
        for relative,expected in cached['audit']['source_hashes'].items():
            if digest(ROOT/relative)!=expected:raise ValueError('Training source changed since feature preparation')
        return cached
    fresh_manifest=json.loads((FRESH/'manifest.json').read_text())
    if digest(FRESH/'holdout.csv')!=fresh_manifest['sha256']:raise ValueError('Frozen holdout changed')
    fresh=readrows(FRESH/'holdout.csv')
    if {int(row['label']) for row in fresh}!={0,1}:
        raise ValueError('Fresh challenge must contain both classes; incomplete collection is not a benchmark')
    reserve={identity(r['url'])[1] for r in fresh}
    records,conflicts={},set()
    def add(url,label,source):
        try:key,group=identity(url)
        except (ValueError,UnicodeError,AttributeError):return
        if key in records and records[key][1]!=label:conflicts.add(key)
        elif key not in records:records[key]=(url,label,group,source)
    with (ROOT/'models/phishing_url/data/primary/prepared/prepared.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):add(r['url'],int(r['label']),'primary')
    with zipfile.ZipFile(ROOT/'models/phishing_url/data/phiusiil/source.zip') as z:
        with io.TextIOWrapper(z.open('PhiUSIIL_Phishing_URL_Dataset.csv'),encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):add(r['URL'],1-int(r['label']),'phiusiil')
    for key in conflicts:records.pop(key,None)
    challenges=set(json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text())['challenge_domains_excluded_from_fit'])
    groups={s:[] for s in ('train','calibration','validation','test')}
    legacy_fit=set();excluded=Counter()
    for row in records.values():
        h=int(hashlib.sha256(('structural-v3-42:'+row[2]).encode()).hexdigest()[:8],16)%100
        split='test' if row[2] in challenges or h>=85 else 'validation' if h>=78 else 'calibration' if h>=70 else 'train'
        if split!='test':legacy_fit.add(row[2])
        if row[2] in reserve and split!='test':excluded[split]+=1;continue
        groups[split].append(row)
    fresh_records=[]; overlap=Counter()
    for r in fresh:
        key,group=identity(r['url'])
        if key in records:overlap['historical_url']+=1
        if group in legacy_fit:overlap['legacy_fit_domain']+=1
        fresh_records.append((r['url'],int(r['label']),group,r['source'],group not in legacy_fit,key not in records))
    del records
    domain_sets={s:{r[2] for r in rows} for s,rows in groups.items()}
    for a in groups:
        for b in groups:
            if a!=b and domain_sets[a]&domain_sets[b]:raise ValueError('Domain leakage')
    assert not reserve & set.union(*(domain_sets[s] for s in ('train','calibration','validation')))
    arrays={};labels={}
    for split,rows in {**groups,'fresh':fresh_records}.items():
        log('extracting_features',split=split,rows=len(rows))
        arrays[split]=np.asarray([list(extract(r[0]).values()) for r in rows],dtype=np.float32)
        labels[split]=np.asarray([r[1] for r in rows],dtype=np.int8)
    audit={'created_at':datetime.now(timezone.utc).isoformat(),'rows':{s:len(r) for s,r in groups.items()},
           'sources_labels':{s:dict(Counter(f'{r[3]}:{r[1]}' for r in rows)) for s,rows in groups.items()},
           'label_mapping':{'primary':{'good':0,'bad':1},'phiusiil':{'original_1':0,'original_0':1}},
           'conflicting_urls_removed':len(conflicts),'domain_overlap':0,'fresh_domains_excluded_from_candidate_fit':dict(excluded),
           'fresh_snapshot_sha256':fresh_manifest['sha256'],'fresh_rows':len(fresh_records),'fresh_overlap':dict(overlap),
           'source_hashes':{str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'models/phishing_url/data/primary/prepared/prepared.csv',ROOT/'models/phishing_url/data/phiusiil/source.zip']},
           'limitations':['Historical test was already inspected in earlier development; it is a regression set.','Fresh collection is a small convenience challenge with provider-reported positives and official-page reference negatives.','Reserved fresh domains are removed from all candidate fitting and threshold selection; legacy model may have seen some domains.','No temporal/campaign generalization or globally representative accuracy claim.']}
    data={'groups':groups,'fresh':fresh_records,'X':arrays,'y':labels,'audit':audit}
    joblib.dump(data,cache,compress=0);dump(DATA/'dataset_manifest.json',audit)
    log('prepared',**audit['rows']);return data

def balanced_weights(rows):
    counts=Counter((r[3],r[1]) for r in rows)
    return np.asarray([len(rows)/(len(counts)*counts[r[3],r[1]]) for r in rows],dtype=np.float32)

def select_threshold(y,p,max_fpr=.01):
    # Exact validation-only operating points; choose maximum recall within FPR budget.
    order=np.argsort(-p,kind='stable'); sorted_p=p[order]; sorted_y=y[order]
    tp=np.cumsum(sorted_y);fp=np.cumsum(1-sorted_y)
    ends=np.r_[np.flatnonzero(sorted_p[:-1]!=sorted_p[1:]),len(p)-1]
    eligible=ends[fp[ends]/max(1,int(sum(y==0)))<=max_fpr]
    if not len(eligible):return float(np.nextafter(max(p),np.inf))
    best=max(eligible,key=lambda i:(int(tp[i]),-int(fp[i]),float(sorted_p[i])))
    return float(sorted_p[best])

def evaluate_slice(y,p,threshold):
    return metrics(y,p,threshold) if len(y) and len(np.unique(y))==2 else {'rows':len(y),'positive_rows':int(sum(y==1)),
        'alert_rate':float(np.mean(p>=threshold)) if len(y) else None,'note':'Single-class slice; no overall accuracy/AUC claim.'}

def slices(rows,X,y,p,threshold):
    masks={f'source:{s}':np.array([r[3]==s for r in rows]) for s in sorted({r[3] for r in rows})}
    for name,condition in [('root_path',X[:,NAMES.index('path_length')]<=1),('long_path',X[:,NAMES.index('path_length')]>=30),
                           ('has_query',X[:,NAMES.index('query_length')]>0),('digit_hostname',X[:,NAMES.index('host_digits')]>0),
                           ('credential_terms',X[:,NAMES.index('credential_terms')]>0),('https',np.array([r[0].startswith('https://') for r in rows]))]:masks[name]=condition
    return {name:{'rows':int(mask.sum()),**evaluate_slice(y[mask],p[mask],threshold)} for name,mask in masks.items() if mask.any()}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    started=time.monotonic();DATA.mkdir(parents=True,exist_ok=True)
    data=prepare()
    if args.prepare_only:return
    if REPORT.exists():raise SystemExit('Evaluation report is frozen; use a new experiment version rather than tuning on its results.')
    OUT.mkdir(parents=True,exist_ok=True)
    groups,X,y=data['groups'],data['X'],data['y']
    manifest=json.loads((BASE/'manifest.json').read_text());base=ModernModel(BASE,manifest)
    base_hashes={name:digest(BASE/item['artifact']) for name,item in manifest['components'].items()}
    def baseline(rows,matrix):
        structural=base.models['structural'].predict_proba(matrix)[:,1]
        text=base.models['text'].predict_proba([r[0] for r in rows])[:,1]
        return base.models['calibrator'].predict(base.models['fusion'].predict_proba(meta_features(matrix,text,structural))[:,1])
    log('baseline_validation')
    bvp=baseline(groups['validation'],X['validation'])
    baseline_threshold=manifest['threshold']
    baseline_validation=metrics(y['validation'],bvp,baseline_threshold)
    # All experiment settings are fixed and written BEFORE any test/challenge prediction.
    protocol={'seed':SEED,'fpr_budget':.01,'selection':'Maximum validation recall subject to FPR <= 1%; no fallback to unconstrained threshold.',
              'candidates':['retuned_v5','balanced_structural','balanced_text_structure_fusion'],
              'promotion_gate':'Both FPR and FNR must decrease on historical regression AND frozen fresh challenge; no model promotion from source-only improvement.',
              'runtime_change':'None until all gates and integration tests pass.','baseline_hashes':base_hashes,
              'fresh_snapshot_sha256':data['audit']['fresh_snapshot_sha256']}
    dump(OUT/'protocol.json',protocol)
    # Separate train-domain tuning subset for early stopping; threshold validation stays separate.
    tuning=np.array([int(hashlib.sha256(('earlystop:'+r[2]).encode()).hexdigest()[:8],16)%10==0 for r in groups['train']])
    weights=balanced_weights(groups['train'])
    structural=lgb.LGBMClassifier(n_estimators=1600,learning_rate=.035,num_leaves=63,max_depth=-1,min_child_samples=60,
                                  reg_lambda=5,colsample_bytree=.9,random_state=SEED,n_jobs=2,verbosity=-1)
    log('training_balanced_structure',rows=int(sum(~tuning)))
    structural.fit(X['train'][~tuning],y['train'][~tuning],sample_weight=weights[~tuning],
                   eval_set=[(X['train'][tuning],y['train'][tuning])],eval_sample_weight=[weights[tuning]],callbacks=[lgb.early_stopping(60,verbose=False)])
    log('structural_fitted',best_iteration=int(structural.best_iteration_))
    # Text sample balanced by source/class, all from train; no synthetic URLs or label changes.
    rng=random.Random(SEED);indices=[]
    for source in ('primary','phiusiil'):
        for label in (0,1):
            candidates=[i for i,r in enumerate(groups['train']) if r[3]==source and r[1]==label]
            indices.extend(rng.sample(candidates,min(40000,len(candidates))))
    rng.shuffle(indices)
    text=Pipeline([('tfidf',TfidfVectorizer(analyzer='char',ngram_range=(3,5),preprocessor=masked_url_text,lowercase=False,
                                           min_df=5,max_features=40000,sublinear_tf=True,dtype=np.float32)),
                   ('classifier',SGDClassifier(loss='log_loss',alpha=1e-5,max_iter=200,tol=1e-4,average=True,random_state=SEED))])
    log('training_balanced_text',rows=len(indices))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning)
        text.fit([groups['train'][i][0] for i in indices],y['train'][indices])
    convergence=[str(w.message) for w in caught if issubclass(w.category,ConvergenceWarning)]
    log('text_fitted',iterations=int(text.named_steps['classifier'].n_iter_),convergence_warnings=convergence)
    def raw_features(rows,matrix):
        sp=structural.predict_proba(matrix)[:,1];tp=text.predict_proba([r[0] for r in rows])[:,1]
        return np.column_stack([sp,tp,matrix])
    cm=raw_features(groups['calibration'],X['calibration'])
    part=np.array([int(hashlib.sha256(r[2].encode()).hexdigest()[:8],16)%2 for r in groups['calibration']])
    fusion=lgb.LGBMClassifier(n_estimators=250,learning_rate=.035,num_leaves=15,max_depth=5,min_child_samples=100,
                              reg_lambda=10,random_state=SEED,n_jobs=2,verbosity=-1)
    fusion.fit(cm[part==0],y['calibration'][part==0])
    calibrator=IsotonicRegression(out_of_bounds='clip').fit(fusion.predict_proba(cm[part==1])[:,1],y['calibration'][part==1])
    structural_cal=IsotonicRegression(out_of_bounds='clip').fit(cm[part==1,0],y['calibration'][part==1])
    vm=raw_features(groups['validation'],X['validation'])
    validation_probabilities={'retuned_v5':bvp,'balanced_structural':structural_cal.predict(vm[:,0]),
                               'balanced_text_structure_fusion':calibrator.predict(fusion.predict_proba(vm)[:,1])}
    thresholds={name:select_threshold(y['validation'],p) for name,p in validation_probabilities.items()}
    validation={name:metrics(y['validation'],p,thresholds[name]) for name,p in validation_probabilities.items()}
    selected=max(validation,key=lambda name:(validation[name]['recall'],-validation[name]['fpr'],validation[name]['f1']))
    dump(OUT/'selection.json',{'thresholds':thresholds,'validation':validation,'selected':selected,'frozen_before_test':True})
    for name,model in [('structural',structural),('text',text),('fusion',fusion),('calibrator',calibrator),('structural_calibrator',structural_cal)]:joblib.dump(model,OUT/(name+'.joblib'))
    log('selection_frozen',selected=selected,threshold=thresholds[selected],validation=validation[selected])
    report={'protocol':protocol,'data':data['audit'],'baseline_validation':baseline_validation,'candidate_validation':validation,
            'selected':selected,'selected_threshold':thresholds[selected],'convergence_warnings':convergence,
            'text_iterations':int(text.named_steps['classifier'].n_iter_),'structural_best_iteration':int(structural.best_iteration_),
            'results':{},'promotion':{'promoted':False,'reason':'Pending completed evaluation.'}}
    for split,rows in [('test',groups['test']),('fresh',data['fresh'])]:
        log('evaluating_locked_candidate',split=split,rows=len(rows))
        bp=baseline(rows,X[split]); fm=raw_features(rows,X[split])
        cp=bp if selected=='retuned_v5' else structural_cal.predict(fm[:,0]) if selected=='balanced_structural' else calibrator.predict(fusion.predict_proba(fm)[:,1])
        entry={'baseline':metrics(y[split],bp,baseline_threshold),'candidate':metrics(y[split],cp,thresholds[selected]),
               'baseline_slices':slices(rows,X[split],y[split],bp,baseline_threshold),
               'candidate_slices':slices(rows,X[split],y[split],cp,thresholds[selected])}
        if split=='fresh':
            strict=np.array([r[4] and r[5] for r in rows])
            entry['strict_unseen_legacy_fit_domains']={'rows':int(strict.sum()),'baseline':evaluate_slice(y[split][strict],bp[strict],baseline_threshold),
                                                    'candidate':evaluate_slice(y[split][strict],cp[strict],thresholds[selected])}
            entry['label_caveat']='Provider reports and official-page reference labels; small convenience challenge, not independent adjudicated deployment accuracy.'
        np.savez_compressed(DATA/(split+'_predictions.npz'),y=y[split],baseline=bp,candidate=cp)
        with (DATA/(split+'_errors.csv')).open('w',newline='',encoding='utf-8') as f:
            writer=csv.writer(f);writer.writerow(['url','label','source','baseline_probability','candidate_probability','baseline_error','candidate_error'])
            for r,label,b,c in zip(rows,y[split],bp,cp):
                be=int((b>=baseline_threshold)!=label);ce=int((c>=thresholds[selected])!=label)
                if be or ce:writer.writerow([r[0],int(label),r[3],float(b),float(c),be,ce])
        report['results'][split]=entry
        log('comparison',split=split,baseline=entry['baseline'],candidate=entry['candidate'])
    checks={split:all(report['results'][split]['candidate'][metric]<report['results'][split]['baseline'][metric] for metric in ('fpr','fnr')) for split in ('test','fresh')}
    unchanged=all(digest(BASE/item['artifact'])==base_hashes[name] for name,item in manifest['components'].items())
    report['promotion']={'promoted':False,'both_error_rates_improved':checks,'eligible_for_integration':all(checks.values()) and not convergence,
                         'baseline_artifacts_unchanged':unchanged,
                         'reason':'Candidate requires runtime integration and regression tests before activation.' if all(checks.values()) else 'Promotion rejected: both FPR and FNR did not improve on both the historical regression and fresh challenge.'}
    report['elapsed_seconds']=time.monotonic()-started
    dump(REPORT,report)
    dump(OUT/'bundle.json',{'experimental_only':True,'selection':selected,'threshold':thresholds[selected],
         'fusion_inputs':['structural_probability','text_probability',*NAMES],
         'artifacts':{p.name:digest(p) for p in OUT.glob('*.joblib')},'report':str(REPORT.relative_to(ROOT))})
    log('complete',promotion=report['promotion'],report=str(REPORT.relative_to(ROOT)))

if __name__=='__main__':main()
