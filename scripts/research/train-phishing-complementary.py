"""Second research experiment: domain-text signal + existing masked/structure branches.

No runtime changes. The fresh challenge is now explicitly a reused regression set.
All fitting and threshold selection still exclude its domains and labels.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import time
import warnings

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('phishing_improvement',ROOT/'scripts/research/improve-phishing-model.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.exceptions import ConvergenceWarning
from models.phishing_url.inference.url_text_model import canonical_text
from models.phishing_url.inference.modern_model import ModernModel,meta_features

OUT=ROOT/'models/phishing_url/checkpoints/research_v7'
REPORT=ROOT/'models/phishing_url/research/complementary_20261018.json'
SEED=20261019


def main():
    if REPORT.exists():raise SystemExit('Completed experiment is immutable; create a new version.')
    start=time.monotonic();data=r.prepare();g,X,y=data['groups'],data['X'],data['y']
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((r.BASE/'manifest.json').read_text());base=ModernModel(r.BASE,manifest)
    protocol={'seed':SEED,'fpr_budget':.0075,'selection':'Validation only, maximum recall at FPR <= 0.75%.',
              'architecture':'Existing masked text and structural branches, complementary regularized unmasked text, HGB fusion on all 30 structure features.',
              'challenge_role':'Reused convenience regression challenge after v6; no longer an untouched acceptance test.',
              'no_fresh_training':True,'no_per_domain_rules':True,'baseline_hashes':{name:r.digest(r.BASE/e['artifact']) for name,e in manifest['components'].items()}}
    r.dump(OUT/'protocol.json',protocol)
    rng=random.Random(SEED);indices=[]
    for source in ('primary','phiusiil'):
        for label in (0,1):
            pool=[i for i,row in enumerate(g['train']) if row[3]==source and row[1]==label]
            indices.extend(rng.sample(pool,min(40000,len(pool))))
    rng.shuffle(indices)
    lexical=Pipeline([('tfidf',TfidfVectorizer(analyzer='char',ngram_range=(3,5),preprocessor=canonical_text,lowercase=False,
                                             min_df=5,max_features=40000,sublinear_tf=True,dtype=np.float32)),
                      ('classifier',SGDClassifier(loss='log_loss',alpha=1e-5,max_iter=200,tol=1e-4,average=True,random_state=SEED))])
    r.log('complementary_text_fit',rows=len(indices))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning)
        lexical.fit([g['train'][i][0] for i in indices],y['train'][indices])
    convergence=[str(w.message) for w in caught if issubclass(w.category,ConvergenceWarning)]
    r.log('complementary_text_fitted',iterations=int(lexical.named_steps['classifier'].n_iter_))
    def features(rows,matrix):
        sp=base.models['structural'].predict_proba(matrix)[:,1]
        mp=base.models['text'].predict_proba([row[0] for row in rows])[:,1]
        lp=lexical.predict_proba([row[0] for row in rows])[:,1]
        return np.column_stack([sp,mp,lp,matrix])
    def baseline(matrix):
        return base.models['calibrator'].predict(base.models['fusion'].predict_proba(meta_features(matrix[:,3:],matrix[:,1],matrix[:,0]))[:,1])
    cm=features(g['calibration'],X['calibration'])
    part=np.array([int(hashlib.sha256(row[2].encode()).hexdigest()[:8],16)%2 for row in g['calibration']])
    fusion=HistGradientBoostingClassifier(max_iter=200,max_leaf_nodes=15,max_depth=4,min_samples_leaf=100,l2_regularization=10,random_state=SEED)
    fusion.fit(cm[part==0],y['calibration'][part==0])
    calibrator=IsotonicRegression(out_of_bounds='clip').fit(fusion.predict_proba(cm[part==1])[:,1],y['calibration'][part==1])
    vm=features(g['validation'],X['validation']);vp=calibrator.predict(fusion.predict_proba(vm)[:,1])
    threshold=r.select_threshold(y['validation'],vp,.0075)
    validation=r.metrics(y['validation'],vp,threshold)
    r.dump(OUT/'selection.json',{'threshold':threshold,'validation':validation,'frozen_before_regression':True})
    for name,value in [('lexical',lexical),('fusion',fusion),('calibrator',calibrator)]:joblib.dump(value,OUT/(name+'.joblib'))
    r.log('complementary_selection_frozen',threshold=threshold,validation=validation)
    report={'protocol':protocol,'validation':validation,'threshold':threshold,'convergence_warnings':convergence,'results':{}}
    for split,rows in [('test',g['test']),('fresh',data['fresh'])]:
        r.log('complementary_evaluation',split=split)
        fm=features(rows,X[split]);bp=baseline(fm);cp=calibrator.predict(fusion.predict_proba(fm)[:,1])
        entry={'baseline':r.metrics(y[split],bp,.7),'candidate':r.metrics(y[split],cp,threshold),
               'candidate_slices':r.slices(rows,X[split],y[split],cp,threshold)}
        if split=='fresh':
            strict=np.array([row[4] and row[5] for row in rows])
            entry['strict_legacy_unseen_domains']={'rows':int(sum(strict)),'baseline':r.evaluate_slice(y[split][strict],bp[strict],.7),
                                                  'candidate':r.evaluate_slice(y[split][strict],cp[strict],threshold)}
        np.savez_compressed(r.DATA/(split+'_v7_predictions.npz'),y=y[split],baseline=bp,candidate=cp)
        report['results'][split]=entry
        r.log('complementary_comparison',split=split,baseline=entry['baseline'],candidate=entry['candidate'])
    improvements={split:all(report['results'][split]['candidate'][m]<report['results'][split]['baseline'][m] for m in ('fpr','fnr')) for split in ('test','fresh')}
    report['promotion']={'promoted':False,'both_error_rates_improved':improvements,'eligible_for_local_integration':all(improvements.values()) and not convergence,
                         'independent_acceptance_complete':False,'baseline_unchanged':all(r.digest(r.BASE/e['artifact'])==protocol['baseline_hashes'][name] for name,e in manifest['components'].items())}
    report['elapsed_seconds']=time.monotonic()-start
    r.dump(REPORT,report)
    r.log('complementary_complete',promotion=report['promotion'])

if __name__=='__main__':main()
