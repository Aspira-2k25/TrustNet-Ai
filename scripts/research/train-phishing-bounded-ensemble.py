"""Validate bounded complementary influence without domain-specific decisions."""
import importlib.util
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('targeted_base',ROOT/'scripts/research/train-targeted-phishing.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
OUT=ROOT/'models/phishing_url/checkpoints/research_v11'
REPORT=ROOT/'models/phishing_url/research/bounded_ensemble_20261018.json'


def main():
    if OUT.exists() or REPORT.exists():raise SystemExit('Completed experiment is immutable')
    OUT.mkdir(parents=True)
    manifest=t.json.loads((t.r.BASE/'manifest.json').read_text());base=t.ModernModel(t.r.BASE,manifest)
    v9=ROOT/'models/phishing_url/checkpoints/research_v9'
    selected=t.json.loads((v9/'selection.json').read_text())
    for n,digest in selected['artifact_hashes'].items():
        if t.r.digest(v9/n)!=digest:raise ValueError('Changed frozen complementary model')
    lexical=t.joblib.load(v9/'lexical.joblib');fusion=t.joblib.load(v9/'fusion.joblib')
    protocol={'architecture':'Convex blend of frozen identity-neutral v5 probability and raw complementary fusion; held-out-domain isotonic calibration.',
              'weights':[.25,.5,.75],'fpr_budget':.009,'dataset_manifest_sha256':t.r.digest(t.DATA/'dataset_manifest.json'),
              'selection':'Lowest validation FNR among weights with no targeted validation FPR/FNR regression; otherwise reject.',
              'no_domain_overrides':True,'independent_test_read':False,
              'baseline_hashes':{n:t.r.digest(t.r.BASE/e['artifact']) for n,e in manifest['components'].items()},
              'complementary_hashes':selected['artifact_hashes']}
    t.r.dump(OUT/'protocol.json',protocol)
    def inputs(urls):
        x=t.np.asarray([list(t.extract(u).values()) for u in urls],dtype=t.np.float32)
        sp=base.models['structural'].predict_proba(x)[:,1];mp=base.models['text'].predict_proba(urls)[:,1]
        bp=base.models['calibrator'].predict(base.models['fusion'].predict_proba(t.meta_features(x,mp,sp))[:,1])
        lp=lexical.predict_proba(urls)[:,1]
        raw=fusion.predict_proba(t.np.column_stack([sp,mp,lp,x]))[:,1]
        return bp,raw
    cal=list(t.development_rows(t.DATA,'calibration'));val=list(t.development_rows(t.DATA,'validation'))
    t.r.log('bounded_prepare',calibration=len(cal),validation=len(val))
    cb,cr=inputs([u for u,_ in cal]);vb,vr=inputs([u for u,_ in val])
    cy=t.np.asarray([y for _,y in cal]);vy=t.np.asarray([y for _,y in val])
    part=t.np.asarray([int(t.hashlib.sha256(t.registered_domain(urlsplit(u).hostname).encode()).hexdigest()[:8],16)%2 for u,_ in cal])
    dm=t.json.loads((t.DATA/'dataset_manifest.json').read_text());path=t.DATA/'targeted_validation.csv'
    if t.r.digest(path)!=dm['files'][path.name]:raise ValueError('Changed cohort')
    new={v['url'] for v in t.r.readrows(path)};sel=t.np.asarray([u in new for u,_ in val])
    targetbase=t.r.metrics(vy[sel],vb[sel],.7);candidates=[];results=[]
    for weight in protocol['weights']:
        calibrator=t.IsotonicRegression(out_of_bounds='clip').fit(((1-weight)*cb+weight*cr)[part==1],cy[part==1])
        p=calibrator.predict((1-weight)*vb+weight*vr)
        threshold=t.r.select_threshold(vy,p,.009);score=t.r.metrics(vy,p,threshold);target=t.r.metrics(vy[sel],p[sel],threshold)
        eligible=all(target[m]<=targetbase[m] for m in ('fpr','fnr'))
        candidates.append((not eligible,score['fnr'],score['fpr'],weight,calibrator,threshold,score,target))
        result={'weight':weight,'validation':score,'targeted_validation':target,'development_eligible':eligible};results.append(result)
        t.r.log('bounded_validation',**result)
    _,_,_,weight,calibrator,threshold,score,target=min(candidates,key=lambda c:c[:4])
    t.joblib.dump(calibrator,OUT/'calibrator.joblib')
    selection={'weight':weight,'threshold':threshold,'validation':score,'frozen_before_regression':True,
               'artifact_hashes':{'calibrator.joblib':t.r.digest(OUT/'calibrator.joblib')}}
    t.r.dump(OUT/'selection.json',selection)
    def predictions(urls):
        bp,raw=inputs(urls)
        return bp,calibrator.predict((1-weight)*bp+weight*raw)
    regression={}
    for split in ('historical_regression','regression_reference'):
        t.r.log('bounded_regression',split=split)
        rows=t.r.readrows(t.DATA/(split+'.csv'));y=t.np.asarray([int(v['label']) for v in rows])
        bp,p=predictions([v['url'] for v in rows]);regression[split]={'baseline':t.r.metrics(y,bp,.7),'candidate':t.r.metrics(y,p,threshold)}
    old=t.json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text())
    urls=sorted(set(['https://'+d+'/' for d in old['challenge_domains_excluded_from_fit']]+['https://docs.python.org/3/','https://www.google.com/','https://paypal.com/']))
    bp,p=predictions(urls);homepages=[{'url':u,'baseline_probability':float(b),'candidate_probability':float(c),'candidate_alert':bool(c>=threshold)} for u,b,c in zip(urls,bp,p)]
    gates={'homepages_no_alerts':not any(v['candidate_alert'] for v in homepages),
           'historical_both_error_rates_improved':all(regression['historical_regression']['candidate'][m]<regression['historical_regression']['baseline'][m] for m in ('fpr','fnr')),
           'reference_no_error_rate_regression':all(regression['regression_reference']['candidate'][m]<=regression['regression_reference']['baseline'][m] for m in ('fpr','fnr')),
           'targeted_no_error_rate_regression':all(target[m]<=targetbase[m] for m in ('fpr','fnr'))}
    t.r.dump(REPORT,{'protocol':protocol,'selection':selection,'validation_candidates':results,'regression':regression,
        'targeted_validation':{'baseline':targetbase,'candidate':target},'homepages':homepages,'gates':gates,
        'eligible_for_independent_evaluation':all(gates.values()),'independent_test_read':False,'promoted':False,
        'baseline_unchanged':all(t.r.digest(t.r.BASE/e['artifact'])==protocol['baseline_hashes'][n] for n,e in manifest['components'].items())})
    t.r.log('bounded_complete',gates=gates,promoted=False)


if __name__=='__main__':main()
