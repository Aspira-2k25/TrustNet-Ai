"""Out-of-fit disagreement correction; all model selection is development-only."""
import importlib.util
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('targeted_base',ROOT/'scripts/train-targeted-phishing.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
OUT=ROOT/'models/phishing_url/checkpoints/research_v12'
REPORT=ROOT/'models/phishing_url/research/residual_20261018.json'


def main():
    if OUT.exists() or REPORT.exists():raise SystemExit('Completed experiment is immutable')
    OUT.mkdir(parents=True)
    manifest=t.json.loads((t.r.BASE/'manifest.json').read_text());base=t.ModernModel(t.r.BASE,manifest)
    v9=ROOT/'models/phishing_url/checkpoints/research_v9';selection9=t.json.loads((v9/'selection.json').read_text())
    for n,d in selection9['artifact_hashes'].items():
        if t.r.digest(v9/n)!=d:raise ValueError('Complementary model changed')
    lexical=t.joblib.load(v9/'lexical.joblib');fusion9=t.joblib.load(v9/'fusion.joblib')
    protocol={'architecture':'Out-of-fit disagreement correction: v5 score, raw complementary fusion, 30 URL measurements.',
              'fitting':'Use only original calibration half 1 (underlying fusion models fit half 0); divide its domains again for correction/calibration.',
              'dataset_manifest_sha256':t.r.digest(t.DATA/'dataset_manifest.json'),'independent_test_read':False,
              'selection':'Validation FNR then FPR, subject to FPR <=0.9% and no targeted FPR/FNR regression.',
              'baseline_hashes':{n:t.r.digest(t.r.BASE/e['artifact']) for n,e in manifest['components'].items()},
              'complementary_hashes':selection9['artifact_hashes']}
    t.r.dump(OUT/'protocol.json',protocol)
    def inputs(urls):
        x=t.np.asarray([list(t.extract(u).values()) for u in urls],dtype=t.np.float32)
        sp=base.models['structural'].predict_proba(x)[:,1];mp=base.models['text'].predict_proba(urls)[:,1]
        # Use the raw v5 fusion too: its isotonic layer was fitted on half 1.
        raw5=base.models['fusion'].predict_proba(t.meta_features(x,mp,sp))[:,1]
        bp=base.models['calibrator'].predict(raw5)
        lp=lexical.predict_proba(urls)[:,1]
        raw9=fusion9.predict_proba(t.np.column_stack([sp,mp,lp,x]))[:,1]
        return t.np.column_stack([raw5,raw9,x]),bp
    dm=t.json.loads((t.DATA/'dataset_manifest.json').read_text())
    def cohort(split):
        path=t.DATA/('targeted_'+split+'.csv')
        if t.r.digest(path)!=dm['files'][path.name]:raise ValueError('Changed cohort')
        return {v['url'] for v in t.r.readrows(path)}
    cal=list(t.development_rows(t.DATA,'calibration'));val=list(t.development_rows(t.DATA,'validation'))
    def partition(u):
        domain=t.registered_domain(urlsplit(u).hostname)
        outer=int(t.hashlib.sha256(domain.encode()).hexdigest()[:8],16)%2
        inner=int(t.hashlib.sha256(('correction:'+domain).encode()).hexdigest()[:8],16)%2
        return outer,inner
    cal=[row for row in cal if partition(row[0])[0]==1]
    part=t.np.asarray([partition(u)[1] for u,_ in cal]);cy=t.np.asarray([y for _,y in cal]);vy=t.np.asarray([y for _,y in val])
    t.r.log('residual_prepare',out_of_fit_calibration=len(cal),validation=len(val))
    cm,_=inputs([u for u,_ in cal]);vm,bp=inputs([u for u,_ in val])
    newcal=cohort('calibration');newval=cohort('validation');sel=t.np.asarray([u in newval for u,_ in val])
    targetbase=t.r.metrics(vy[sel],bp[sel],.7);candidates=[];results=[]
    for weight in (1,20,50):
        weights=t.np.asarray([float(weight) if u in newcal else 1. for u,_ in cal])
        for leaves in (7,15):
            fusion=t.HistGradientBoostingClassifier(max_iter=150,max_leaf_nodes=leaves,max_depth=4,min_samples_leaf=100,l2_regularization=20,random_state=t.SEED)
            fusion.fit(cm[part==0],cy[part==0],sample_weight=weights[part==0])
            calibrator=t.IsotonicRegression(out_of_bounds='clip').fit(fusion.predict_proba(cm[part==1])[:,1],cy[part==1])
            p=calibrator.predict(fusion.predict_proba(vm)[:,1]);threshold=t.r.select_threshold(vy,p,.009)
            score=t.r.metrics(vy,p,threshold);target=t.r.metrics(vy[sel],p[sel],threshold)
            eligible=all(target[m]<=targetbase[m] for m in ('fpr','fnr'))
            candidates.append((not eligible,score['fnr'],score['fpr'],weight,leaves,fusion,calibrator,threshold,score,target))
            result={'weight':weight,'leaves':leaves,'validation':score,'targeted_validation':target,'development_eligible':eligible};results.append(result)
            t.r.log('residual_validation',**result)
    _,_,_,weight,leaves,fusion,calibrator,threshold,score,target=min(candidates,key=lambda c:c[:5])
    for n,m in [('fusion',fusion),('calibrator',calibrator)]:t.joblib.dump(m,OUT/(n+'.joblib'))
    selection={'weight':weight,'leaves':leaves,'threshold':threshold,'validation':score,'frozen_before_regression':True,
               'artifact_hashes':{p.name:t.r.digest(p) for p in OUT.glob('*.joblib')}}
    t.r.dump(OUT/'selection.json',selection);regression={}
    def predict(urls):
        fm,bp=inputs(urls)
        return bp,calibrator.predict(fusion.predict_proba(fm)[:,1])
    for split in ('historical_regression','regression_reference'):
        t.r.log('residual_regression',split=split)
        rows=t.r.readrows(t.DATA/(split+'.csv'));y=t.np.asarray([int(v['label']) for v in rows]);bp,p=predict([v['url'] for v in rows])
        regression[split]={'baseline':t.r.metrics(y,bp,.7),'candidate':t.r.metrics(y,p,threshold)}
    old=t.json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text())
    urls=sorted(set(['https://'+d+'/' for d in old['challenge_domains_excluded_from_fit']]+['https://docs.python.org/3/','https://www.google.com/','https://paypal.com/']))
    bp,p=predict(urls);homepages=[{'url':u,'baseline_probability':float(b),'candidate_probability':float(c),'candidate_alert':bool(c>=threshold)} for u,b,c in zip(urls,bp,p)]
    gates={'homepages_no_alerts':not any(v['candidate_alert'] for v in homepages),
           'historical_both_error_rates_improved':all(regression['historical_regression']['candidate'][m]<regression['historical_regression']['baseline'][m] for m in ('fpr','fnr')),
           'reference_no_error_rate_regression':all(regression['regression_reference']['candidate'][m]<=regression['regression_reference']['baseline'][m] for m in ('fpr','fnr')),
           'targeted_no_error_rate_regression':all(target[m]<=targetbase[m] for m in ('fpr','fnr'))}
    t.r.dump(REPORT,{'protocol':protocol,'selection':selection,'validation_candidates':results,'regression':regression,
        'targeted_validation':{'baseline':targetbase,'candidate':target},'homepages':homepages,'gates':gates,
        'eligible_for_independent_evaluation':all(gates.values()),'independent_test_read':False,'promoted':False,
        'baseline_unchanged':all(t.r.digest(t.r.BASE/e['artifact'])==protocol['baseline_hashes'][n] for n,e in manifest['components'].items())})
    t.r.log('residual_complete',gates=gates,promoted=False)


if __name__=='__main__':main()
