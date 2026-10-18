"""Calibrated consensus using domains out of fit for every underlying fusion."""
import importlib.util
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('targeted_base',ROOT/'scripts/train-targeted-phishing.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
OUT=ROOT/'models/phishing_url/checkpoints/research_v13'
REPORT=ROOT/'models/phishing_url/research/consensus_20261018.json'


def main():
    if OUT.exists() or REPORT.exists():raise SystemExit('Completed experiment is immutable')
    OUT.mkdir(parents=True)
    manifest=t.json.loads((t.r.BASE/'manifest.json').read_text());base=t.ModernModel(t.r.BASE,manifest)
    def frozen(version):
        path=ROOT/('models/phishing_url/checkpoints/research_v'+str(version));s=t.json.loads((path/'selection.json').read_text())
        for n,d in s['artifact_hashes'].items():
            if t.r.digest(path/n)!=d:raise ValueError('Changed frozen component')
        return path,s
    v9,s9=frozen(9);v12,s12=frozen(12)
    lexical=t.joblib.load(v9/'lexical.joblib');fusion9=t.joblib.load(v9/'fusion.joblib');fusion12=t.joblib.load(v12/'fusion.joblib')
    protocol={'architecture':'Convex or geometric consensus of raw v5 and raw out-of-fit disagreement correction; independent-domain isotonic calibration.',
              'calibration':'Only outer half 1 / correction inner half 1; excluded from fitting all three underlying fusion models.',
              'fpr_budget':.0125,'selection':'Validation FNR then FPR with no targeted validation FPR/FNR regression; no homepage labels used for selection.',
              'dataset_manifest_sha256':t.r.digest(t.DATA/'dataset_manifest.json'),'independent_test_read':False,
              'baseline_hashes':{n:t.r.digest(t.r.BASE/e['artifact']) for n,e in manifest['components'].items()},
              'v9_hashes':s9['artifact_hashes'],'v12_hashes':s12['artifact_hashes']}
    t.r.dump(OUT/'protocol.json',protocol)
    def inputs(urls):
        x=t.np.asarray([list(t.extract(u).values()) for u in urls],dtype=t.np.float32)
        sp=base.models['structural'].predict_proba(x)[:,1];mp=base.models['text'].predict_proba(urls)[:,1]
        raw5=base.models['fusion'].predict_proba(t.meta_features(x,mp,sp))[:,1]
        lp=lexical.predict_proba(urls)[:,1];raw9=fusion9.predict_proba(t.np.column_stack([sp,mp,lp,x]))[:,1]
        raw12=fusion12.predict_proba(t.np.column_stack([raw5,raw9,x]))[:,1]
        return raw5,raw12,base.models['calibrator'].predict(raw5)
    def heldout(u):
        d=t.registered_domain(urlsplit(u).hostname)
        return int(t.hashlib.sha256(d.encode()).hexdigest()[:8],16)%2==1 and int(t.hashlib.sha256(('correction:'+d).encode()).hexdigest()[:8],16)%2==1
    cal=[r for r in t.development_rows(t.DATA,'calibration') if heldout(r[0])];val=list(t.development_rows(t.DATA,'validation'))
    t.r.log('consensus_prepare',calibration=len(cal),validation=len(val))
    cb,cr,_=inputs([u for u,_ in cal]);vb,vr,bp=inputs([u for u,_ in val]);cy=t.np.asarray([y for _,y in cal]);vy=t.np.asarray([y for _,y in val])
    path=t.DATA/'targeted_validation.csv';dm=t.json.loads((t.DATA/'dataset_manifest.json').read_text())
    if t.r.digest(path)!=dm['files'][path.name]:raise ValueError('Changed cohort')
    new={r['url'] for r in t.r.readrows(path)};sel=t.np.asarray([u in new for u,_ in val]);targetbase=t.r.metrics(vy[sel],bp[sel],.7)
    def combine(b,r,w):return t.np.sqrt(b*r) if w=='geometric' else (1-w)*b+w*r
    candidates=[];results=[]
    for weight in (.25,.5,.75,'geometric'):
        calibrator=t.IsotonicRegression(out_of_bounds='clip').fit(combine(cb,cr,weight),cy)
        p=calibrator.predict(combine(vb,vr,weight));threshold=t.r.select_threshold(vy,p,.0125)
        score=t.r.metrics(vy,p,threshold);target=t.r.metrics(vy[sel],p[sel],threshold);eligible=all(target[m]<=targetbase[m] for m in ('fpr','fnr'))
        candidates.append((not eligible,score['fnr'],score['fpr'],str(weight),weight,calibrator,threshold,score,target))
        result={'weight':weight,'validation':score,'targeted_validation':target,'development_eligible':eligible};results.append(result);t.r.log('consensus_validation',**result)
    _,_,_,_,weight,calibrator,threshold,score,target=min(candidates,key=lambda c:c[:4])
    t.joblib.dump(calibrator,OUT/'calibrator.joblib')
    selection={'weight':weight,'threshold':threshold,'validation':score,'frozen_before_regression':True,'artifact_hashes':{'calibrator.joblib':t.r.digest(OUT/'calibrator.joblib')}}
    t.r.dump(OUT/'selection.json',selection)
    def predict(urls):
        b,r,bp=inputs(urls)
        return bp,calibrator.predict(combine(b,r,weight))
    regression={}
    for split in ('historical_regression','regression_reference'):
        t.r.log('consensus_regression',split=split)
        rows=t.r.readrows(t.DATA/(split+'.csv'));y=t.np.asarray([int(v['label']) for v in rows]);bp,p=predict([v['url'] for v in rows])
        regression[split]={'baseline':t.r.metrics(y,bp,.7),'candidate':t.r.metrics(y,p,threshold)}
    old=t.json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text());urls=sorted(set(['https://'+d+'/' for d in old['challenge_domains_excluded_from_fit']]+['https://docs.python.org/3/','https://www.google.com/','https://paypal.com/']))
    bp,p=predict(urls);homepages=[{'url':u,'baseline_probability':float(b),'candidate_probability':float(c),'candidate_alert':bool(c>=threshold)} for u,b,c in zip(urls,bp,p)]
    gates={'homepages_no_alerts':not any(v['candidate_alert'] for v in homepages),
           'historical_both_error_rates_improved':all(regression['historical_regression']['candidate'][m]<regression['historical_regression']['baseline'][m] for m in ('fpr','fnr')),
           'reference_no_error_rate_regression':all(regression['regression_reference']['candidate'][m]<=regression['regression_reference']['baseline'][m] for m in ('fpr','fnr')),
           'targeted_no_error_rate_regression':all(target[m]<=targetbase[m] for m in ('fpr','fnr'))}
    t.r.dump(REPORT,{'protocol':protocol,'selection':selection,'validation_candidates':results,'regression':regression,'targeted_validation':{'baseline':targetbase,'candidate':target},
        'homepages':homepages,'gates':gates,'eligible_for_independent_evaluation':all(gates.values()),'independent_test_read':False,'promoted':False,
        'baseline_unchanged':all(t.r.digest(t.r.BASE/e['artifact'])==protocol['baseline_hashes'][n] for n,e in manifest['components'].items())})
    t.r.log('consensus_complete',gates=gates,promoted=False)


if __name__=='__main__':main()
