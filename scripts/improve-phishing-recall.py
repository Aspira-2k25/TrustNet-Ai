"""Tune monotone rescue on development data; never reads an independent test."""
import importlib.util
from itertools import product
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('targeted_base',ROOT/'scripts/train-targeted-phishing.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
from models.phishing_url.inference.regional_model import RegionalModel,region
OUT=ROOT/'models/phishing_url/checkpoints/research_recall_v1'
REPORT=ROOT/'models/phishing_url/research/recall_improvement_20261018.json'
CACHE=ROOT/'models/phishing_url/data/recall_development_20261018'
ACTIVE=ROOT/'models/phishing_url/checkpoints/regional_v1'


def main():
    if OUT.exists() or REPORT.exists():raise SystemExit('Completed recall experiment is immutable')
    OUT.mkdir(parents=True);CACHE.mkdir(parents=True,exist_ok=True)
    manifest=t.json.loads((ACTIVE/'manifest.json').read_text());model=RegionalModel(ACTIVE,manifest)
    protocol={'active_manifest_sha256':t.r.digest(ACTIVE/'manifest.json'),
              'dataset_manifest_sha256':t.r.digest(t.DATA/'dataset_manifest.json'),
              'policy':'Preserve every primary alert. Rescue primary negatives only with a different expert.',
              'rescue_probability_floor':.9,'known_negative_score_margin':.01,
              'additional_validation_fpr_budget':.001,'targeted_additional_false_positives':0,
              'selection':'Maximum additional validation TP subject to added FP budget and positive accuracy gain; tie prefer fewer FP.',
              'independent_test_read':False,'forensic_rules_changed':False}
    t.r.dump(OUT/'protocol.json',protocol)
    def predictions(urls):
        pred,_,_,_=model.expert_predictions(urls)
        g=t.np.asarray([region(u) for u in urls]);p=t.np.zeros(len(urls));th=t.np.zeros(len(urls))
        for shape,route in manifest['routing'].items():
            s=g==shape;p[s]=pred[route['expert']][s];th[s]=route['threshold']
        return {'experts':pred,'regions':g,'primary':p,'thresholds':th}
    def split(name):
        path=t.DATA/(name+'.csv');stamp={'input_sha256':t.r.digest(path),'model_sha256':protocol['active_manifest_sha256']}
        cache=CACHE/(name+'.joblib')
        if cache.exists():
            result=t.joblib.load(cache)
            if result['stamp']!=stamp:raise ValueError('Development cache no longer matches frozen inputs')
            return result
        rows=list(t.development_rows(t.DATA,name)) if name=='validation' else [(r['url'],int(r['label'])) for r in t.r.readrows(path)]
        urls=[u for u,_ in rows];result={'stamp':stamp,'urls':urls,'y':t.np.asarray([y for _,y in rows]),**predictions(urls)}
        t.joblib.dump(result,cache);return result
    t.r.log('recall_prepare_validation')
    val=split('validation');y=val['y'];primary=val['primary']>=val['thresholds'];base=t.r.metrics(y,val['primary'],val['thresholds'])
    target_path=t.DATA/'targeted_validation.csv';dm=t.json.loads((t.DATA/'dataset_manifest.json').read_text())
    if t.r.digest(target_path)!=dm['files'][target_path.name]:raise ValueError('Targeted cohort changed')
    target_urls={r['url'] for r in t.r.readrows(target_path)};target=t.np.asarray([u in target_urls for u in val['urls']])
    old=t.json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text())
    homes=sorted(set(['https://'+d+'/' for d in old['challenge_domains_excluded_from_fit']]+['https://docs.python.org/3/','https://www.google.com/','https://paypal.com/']))
    hp=predictions(homes);reference=split('regression_reference');options={}
    for shape,route in manifest['routing'].items():
        other='correction' if route['expert']=='baseline' else 'baseline';p=val['experts'][other];s=(val['regions']==shape)&~primary
        h=(hp['regions']==shape)&(hp['primary']<hp['thresholds'])
        floor=max(.9,float(hp['experts'][other][h].max())+.01 if h.any() else .9)
        options[shape]=[{'rule':None,'tp':0,'fp':0}]
        thresholds=sorted(set([floor,.95,.97,.99]+list(t.np.unique(p[s & (y==1)]))))
        for threshold in thresholds:
            if not floor<=threshold<1:continue
            added=s&(p>=threshold);tp=int(sum(added&(y==1)));fp=int(sum(added&(y==0)))
            if tp==0 or sum(added&target&(y==0)):continue
            # Previously used reference negatives are development guards too.
            r=(reference['regions']==shape)&(reference['primary']<reference['thresholds'])&(reference['y']==0)
            if t.np.any(r&(reference['experts'][other]>=threshold)):continue
            options[shape].append({'rule':{'expert':other,'threshold':float(threshold)},'tp':tp,'fp':fp})
    max_fp=int(.001*sum(y==0));candidates=[]
    for combo in product(*(options[s] for s in ('root','query','path'))):
        tp=sum(r['tp'] for r in combo);fp=sum(r['fp'] for r in combo)
        if fp<=max_fp and tp>fp:candidates.append((tp,-fp,combo))
    if not candidates:
        t.r.dump(REPORT,{'protocol':protocol,'baseline_validation':base,'eligible':False,'promoted':False,'reason':'No accuracy/recall improvement within false-positive controls','independent_test_read':False})
        t.r.log('recall_rejected_no_development_gain');return
    tp,minus_fp,chosen=max(candidates,key=lambda c:c[:2]);rescue={s:r['rule'] for s,r in zip(('root','query','path'),chosen)}
    def apply(data):
        p=data['primary'].copy();thresholds=data['thresholds'].copy();negative=p<thresholds
        for shape,rule in rescue.items():
            if rule is None:continue
            use=(data['regions']==shape)&negative&(data['experts'][rule['expert']]>=rule['threshold'])
            p[use]=data['experts'][rule['expert']][use];thresholds[use]=rule['threshold']
        return p,thresholds
    manifest.update(kind='regional_recall_v1',model_version='regional-recall-v1',detector_id='phishing.regional.recall.v1',rescue=rescue,
                    source_report=str(REPORT.relative_to(ROOT)).replace('\\','/'))
    for e in manifest['components'].values():shutil.copyfile(ACTIVE/e['artifact'],OUT/e['artifact'])
    t.r.dump(OUT/'manifest.json',manifest)
    p,th=apply(val);candidate=t.r.metrics(y,p,th)
    selection={'rescue':rescue,'baseline_validation':base,'candidate_validation':candidate,'added_validation_tp':tp,'added_validation_fp':-minus_fp,
               'frozen_before_regression':True,'manifest_sha256':t.r.digest(OUT/'manifest.json')}
    t.r.dump(OUT/'selection.json',selection);t.r.log('recall_selection',**selection)
    regression={}
    for name in ('historical_regression','regression_reference'):
        t.r.log('recall_regression',split=name);data=split(name);p,th=apply(data)
        before=t.r.metrics(data['y'],data['primary'],data['thresholds']);after=t.r.metrics(data['y'],p,th)
        regression[name]={'baseline':before,'candidate':after}
    p,th=apply(hp)
    home_alerts=int(sum(p>=th));history=regression['historical_regression']
    gates={'accuracy_improved':history['candidate']['accuracy']>history['baseline']['accuracy'],
           'recall_improved':history['candidate']['recall']>history['baseline']['recall'],
           'historical_fpr_increase_bounded':history['candidate']['fpr']<=history['baseline']['fpr']+.001,
           'homepages_no_alerts':home_alerts==0,'primary_alerts_preserved':bool(t.np.all((p>=th)|(hp['primary']<hp['thresholds'])))}
    t.r.dump(REPORT,{'protocol':protocol,'selection':selection,'regression':regression,'home_alerts':home_alerts,'gates':gates,
        'eligible':all(gates.values()),'promoted':False,'independent_test_read':False,
        'active_model_unchanged':t.r.digest(ACTIVE/'manifest.json')==protocol['active_manifest_sha256']})
    t.r.log('recall_development_complete',gates=gates)


if __name__=='__main__':main()
