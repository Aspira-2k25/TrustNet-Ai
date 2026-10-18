"""Development-only regional expert/threshold selection with fixed regression constraints."""
import importlib.util
from itertools import product
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('targeted_base',ROOT/'scripts/research/train-targeted-phishing.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
from models.phishing_url.inference.regional_model import RegionalModel,region
OUT=ROOT/'models/phishing_url/checkpoints/research_v16'
REPORT=ROOT/'models/phishing_url/research/regional_20261018.json'


def main(expanded_budgets=False):
    global OUT,REPORT
    if expanded_budgets:
        OUT=ROOT/'models/phishing_url/checkpoints/research_v17'
        REPORT=ROOT/'models/phishing_url/research/regional_expanded_20261018.json'
    if OUT.exists() or REPORT.exists():raise SystemExit('Completed experiment is immutable')
    OUT.mkdir(parents=True)
    bm=t.json.loads((t.r.BASE/'manifest.json').read_text())
    sources={n:(t.r.BASE/e['artifact'],e['sha256']) for n,e in bm['components'].items()}
    sources['base_fusion']=sources.pop('fusion');sources['base_calibrator']=sources.pop('calibrator')
    for version,mapping in [(9,{'lexical':'complementary_text','fusion':'complementary_fusion'}),(12,{'fusion':'correction_fusion','calibrator':'correction_calibrator'})]:
        p=ROOT/('models/phishing_url/checkpoints/research_v'+str(version));s=t.json.loads((p/'selection.json').read_text())
        for old,new in mapping.items():sources[new]=(p/(old+'.joblib'),s['artifact_hashes'][old+'.joblib'])
    components={}
    for n,(path,digest) in sources.items():
        if t.r.digest(path)!=digest:raise ValueError('Changed frozen expert')
        shutil.copyfile(path,OUT/(n+'.joblib'));components[n]={'artifact':n+'.joblib','sha256':digest}
    manifest={**bm,'kind':'regional_v1','model_version':'regional-v1','detector_id':'phishing.regional.v1','components':components,'routing':{}}
    model=RegionalModel(OUT,manifest,allow_unselected=True)
    protocol={'selection':'Validation-only regional expert/threshold choice with reused familiar-site development constraints; untouched independent test required.',
              'regions':['root','query','path'],'regional_fpr_budgets':[.005,.01,.015,.02]+([.05,.1] if expanded_budgets else []),
              'global_validation_fpr_budget':.015,'targeted_errors_must_not_increase':True,
              'dataset_manifest_sha256':t.r.digest(t.DATA/'dataset_manifest.json'),'independent_test_read':False,
              'components':components,'no_domain_rules':True,'homepage_role':'Reused labeled development constraints, not independent evidence.'}
    t.r.dump(OUT/'protocol.json',protocol)
    rows=list(t.development_rows(t.DATA,'validation'));urls=[u for u,_ in rows];y=t.np.asarray([v for _,v in rows]);g=t.np.asarray([region(u) for u in urls])
    t.r.log('regional_prepare',validation=len(rows))
    predictions,_,_,_=model.expert_predictions(urls)
    dm=t.json.loads((t.DATA/'dataset_manifest.json').read_text());path=t.DATA/'targeted_validation.csv'
    if t.r.digest(path)!=dm['files'][path.name]:raise ValueError('Changed cohort')
    new={v['url'] for v in t.r.readrows(path)};target=t.np.asarray([u in new for u in urls])
    baseline_target=t.r.metrics(y[target],predictions['baseline'][target],.7)
    old=t.json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text());homes=sorted(set(['https://'+d+'/' for d in old['challenge_domains_excluded_from_fit']]+['https://docs.python.org/3/','https://www.google.com/','https://paypal.com/']))
    hp,_,_,_=model.expert_predictions(homes);hg=t.np.asarray([region(u) for u in homes]);options={}
    for shape in protocol['regions']:
        selected=g==shape;ht=hg==shape;options[shape]=[]
        for expert in predictions:
            thresholds=[t.r.select_threshold(y[selected],predictions[expert][selected],budget) for budget in protocol['regional_fpr_budgets']]
            if expanded_budgets and expert=='baseline':thresholds.append(.7)
            for threshold in sorted(set(thresholds)):
                if ht.any():threshold=max(threshold,float(t.np.nextafter(hp[expert][ht].max(),1.)))
                if threshold>=1:continue
                positive=predictions[expert]>=threshold
                counts={'fp':int(sum(selected & (y==0) & positive)),'fn':int(sum(selected & (y==1) & ~positive)),
                        'target_fp':int(sum(selected & target & (y==0) & positive)),
                        'target_fn':int(sum(selected & target & (y==1) & ~positive))}
                options[shape].append({'expert':expert,'threshold':threshold,'counts':counts})
    combinations=[]
    for routes in product(*(options[s] for s in protocol['regions'])):
        counts={key:sum(route['counts'][key] for route in routes) for key in ('fp','fn','target_fp','target_fn')}
        fpr=counts['fp']/sum(y==0);fnr=counts['fn']/sum(y==1)
        eligible=fpr<=.015 and counts['target_fp']<=baseline_target['confusion_matrix'][0][1] and counts['target_fn']<=baseline_target['confusion_matrix'][1][0]
        combinations.append((not eligible,fnr,fpr,routes))
    if not combinations:raise ValueError('No admissible expert configurations')
    _,_,_,routes=min(combinations,key=lambda c:c[:3])
    manifest['routing']={shape:{k:v for k,v in route.items() if k!='counts'} for shape,route in zip(protocol['regions'],routes)}
    p=t.np.zeros(len(y));thresholds=t.np.zeros(len(y))
    for shape,route in manifest['routing'].items():
        chosen=g==shape;p[chosen]=predictions[route['expert']][chosen];thresholds[chosen]=route['threshold']
    score=t.r.metrics(y,p,thresholds);ts=t.r.metrics(y[target],p[target],thresholds[target])
    manifest['threshold']=.7  # Runtime always uses the selected region threshold.
    manifest['source_report']=str(REPORT.relative_to(ROOT)).replace('\\','/')
    t.r.dump(OUT/'manifest.json',manifest)
    selection={'routing':manifest['routing'],'validation':score,'targeted_validation':ts,'frozen_before_regression':True,
               'manifest_sha256':t.r.digest(OUT/'manifest.json'),'eligible_configurations':sum(not c[0] for c in combinations)}
    t.r.dump(OUT/'selection.json',selection);t.r.log('regional_selection',selection=selection)
    def predict(urls):
        pred,_,_,_=model.expert_predictions(urls);p=[];thresholds=[]
        for i,u in enumerate(urls):
            route=manifest['routing'][region(u)];p.append(pred[route['expert']][i]);thresholds.append(route['threshold'])
        return pred['baseline'],t.np.asarray(p),t.np.asarray(thresholds)
    regression={}
    for split in ('historical_regression','regression_reference'):
        t.r.log('regional_regression',split=split);rs=t.r.readrows(t.DATA/(split+'.csv'));sy=t.np.asarray([int(v['label']) for v in rs]);bp,p,thresholds=predict([v['url'] for v in rs])
        regression[split]={'baseline':t.r.metrics(sy,bp,.7),'candidate':t.r.metrics(sy,p,thresholds)}
    bp,p,thresholds=predict(homes);homepages=[{'url':u,'baseline_probability':float(b),'candidate_probability':float(c),'candidate_alert':bool(c>=th)} for u,b,c,th in zip(homes,bp,p,thresholds)]
    gates={'homepages_no_alerts':not any(v['candidate_alert'] for v in homepages),
           'historical_both_error_rates_improved':all(regression['historical_regression']['candidate'][m]<regression['historical_regression']['baseline'][m] for m in ('fpr','fnr')),
           'reference_no_error_rate_regression':all(regression['regression_reference']['candidate'][m]<=regression['regression_reference']['baseline'][m] for m in ('fpr','fnr')),
           'targeted_no_error_rate_regression':all(ts[m]<=baseline_target[m] for m in ('fpr','fnr')),
           'validation_constraints':selection['eligible_configurations']>0}
    t.r.dump(REPORT,{'protocol':protocol,'selection':selection,'regression':regression,'targeted_validation':{'baseline':baseline_target,'candidate':ts},
        'homepages':homepages,'gates':gates,'eligible_for_independent_evaluation':all(gates.values()),'independent_test_read':False,'promoted':False,
        'baseline_unchanged':all(t.r.digest(t.r.BASE/e['artifact'])==e['sha256'] for e in bm['components'].values())})
    t.r.log('regional_complete',gates=gates,promoted=False)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--expanded-budgets',action='store_true')
    main(parser.parse_args().expanded_budgets)
