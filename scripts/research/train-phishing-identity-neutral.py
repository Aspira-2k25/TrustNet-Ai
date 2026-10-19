"""Identity-neutral fusion correction; no domain allowlist or independent-test access."""
import importlib.util
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('targeted_base',ROOT/'scripts/research/train-targeted-phishing.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
OUT=ROOT/'models/phishing_url/checkpoints/research_v10'
REPORT=ROOT/'models/phishing_url/research/identity_neutral_20261018.json'


def main():
    if OUT.exists() or REPORT.exists():raise SystemExit('Completed experiment is immutable')
    OUT.mkdir(parents=True)
    manifest=t.json.loads((t.r.BASE/'manifest.json').read_text());base=t.ModernModel(t.r.BASE,manifest)
    protocol={'architecture':'Masked text and structural probabilities plus all 30 structural measurements; no raw hostname text.',
              'dataset_manifest_sha256':t.r.digest(t.DATA/'dataset_manifest.json'),'seed':t.SEED,
              'validation_fpr_budget':.009,'targeted_fusion_weight':20,
              'selection':'Validation-only lowest FNR then FPR among candidates with no targeted validation FPR/FNR regression.',
              'independent_test_read':False,'promoted':False,
              'baseline_hashes':{n:t.r.digest(t.r.BASE/e['artifact']) for n,e in manifest['components'].items()}}
    t.r.dump(OUT/'protocol.json',protocol)
    dm=t.json.loads((t.DATA/'dataset_manifest.json').read_text())
    def cohort(split):
        path=t.DATA/('targeted_'+split+'.csv')
        if t.r.digest(path)!=dm['files'][path.name]:raise ValueError('Changed cohort')
        return {v['url'] for v in t.r.readrows(path)}
    structures={'baseline':base.models['structural'],'targeted':t.joblib.load(t.OUT/'structural.joblib')}
    def inputs(urls):
        x=t.np.asarray([list(t.extract(u).values()) for u in urls],dtype=t.np.float32)
        mp=base.models['text'].predict_proba(urls)[:,1]
        sp={n:m.predict_proba(x)[:,1] for n,m in structures.items()}
        bp=base.models['calibrator'].predict(base.models['fusion'].predict_proba(t.meta_features(x,mp,sp['baseline']))[:,1])
        return {n:t.np.column_stack([p,mp,x]) for n,p in sp.items()},bp
    cal=list(t.development_rows(t.DATA,'calibration'));val=list(t.development_rows(t.DATA,'validation'))
    t.r.log('identity_neutral_prepare',calibration=len(cal),validation=len(val))
    cm,_=inputs([u for u,_ in cal]);vm,bp=inputs([u for u,_ in val])
    cy=t.np.asarray([y for _,y in cal]);vy=t.np.asarray([y for _,y in val])
    part=t.np.asarray([int(t.hashlib.sha256(t.registered_domain(urlsplit(u).hostname).encode()).hexdigest()[:8],16)%2 for u,_ in cal])
    newcal=cohort('calibration');weights=t.np.asarray([20. if u in newcal else 1. for u,_ in cal])
    newval=cohort('validation');sel=t.np.asarray([u in newval for u,_ in val]);targetbase=t.r.metrics(vy[sel],bp[sel],.7)
    candidates=[];results=[]
    for structure in structures:
        for leaves in (7,15,31):
            fusion=t.HistGradientBoostingClassifier(max_iter=200,max_leaf_nodes=leaves,max_depth=5,min_samples_leaf=100,l2_regularization=10,random_state=t.SEED)
            fusion.fit(cm[structure][part==0],cy[part==0],sample_weight=weights[part==0])
            calibrator=t.IsotonicRegression(out_of_bounds='clip').fit(fusion.predict_proba(cm[structure][part==1])[:,1],cy[part==1])
            p=calibrator.predict(fusion.predict_proba(vm[structure])[:,1]);threshold=t.r.select_threshold(vy,p,.009)
            score=t.r.metrics(vy,p,threshold);target=t.r.metrics(vy[sel],p[sel],threshold)
            eligible=all(target[m]<=targetbase[m] for m in ('fpr','fnr'))
            result={'structure':structure,'leaves':leaves,'threshold':threshold,'validation':score,'targeted_validation':target,'development_eligible':eligible}
            results.append(result);candidates.append((not eligible,score['fnr'],score['fpr'],structure,leaves,fusion,calibrator,threshold,score,target))
            t.r.log('identity_neutral_validation',**result)
    _,_,_,structure,leaves,fusion,calibrator,threshold,score,target=min(candidates,key=lambda c:c[:5])
    for n,m in [('structural',structures[structure]),('fusion',fusion),('calibrator',calibrator)]:t.joblib.dump(m,OUT/(n+'.joblib'))
    selection={'structure':structure,'leaves':leaves,'threshold':threshold,'validation':score,'frozen_before_regression':True,
               'artifact_hashes':{p.name:t.r.digest(p) for p in OUT.glob('*.joblib')}}
    t.r.dump(OUT/'selection.json',selection)
    regression={}
    for split in ('historical_regression','regression_reference'):
        t.r.log('identity_neutral_regression',split=split)
        rows=t.r.readrows(t.DATA/(split+'.csv'));y=t.np.asarray([int(v['label']) for v in rows])
        fm,bp=inputs([v['url'] for v in rows]);p=calibrator.predict(fusion.predict_proba(fm[structure])[:,1])
        regression[split]={'baseline':t.r.metrics(y,bp,.7),'candidate':t.r.metrics(y,p,threshold)}
    old=t.json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text())
    urls=sorted(set(['https://'+d+'/' for d in old['challenge_domains_excluded_from_fit']]+['https://docs.python.org/3/','https://www.google.com/','https://paypal.com/']))
    fm,bp=inputs(urls);p=calibrator.predict(fusion.predict_proba(fm[structure])[:,1])
    homepages=[{'url':u,'baseline_probability':float(b),'candidate_probability':float(c),'candidate_alert':bool(c>=threshold)} for u,b,c in zip(urls,bp,p)]
    gates={'homepages_no_alerts':not any(v['candidate_alert'] for v in homepages),
           'historical_both_error_rates_improved':all(regression['historical_regression']['candidate'][m]<regression['historical_regression']['baseline'][m] for m in ('fpr','fnr')),
           'reference_no_error_rate_regression':all(regression['regression_reference']['candidate'][m]<=regression['regression_reference']['baseline'][m] for m in ('fpr','fnr')),
           'targeted_no_error_rate_regression':all(target[m]<=targetbase[m] for m in ('fpr','fnr'))}
    t.r.dump(REPORT,{'protocol':protocol,'selection':selection,'validation_candidates':results,'regression':regression,
        'targeted_validation':{'baseline':targetbase,'candidate':target},'homepages':homepages,'gates':gates,
        'eligible_for_independent_evaluation':all(gates.values()),'independent_test_read':False,'promoted':False,
        'baseline_unchanged':all(t.r.digest(t.r.BASE/e['artifact'])==protocol['baseline_hashes'][n] for n,e in manifest['components'].items())})
    t.r.log('identity_neutral_complete',gates=gates,promoted=False)


if __name__=='__main__':main()
