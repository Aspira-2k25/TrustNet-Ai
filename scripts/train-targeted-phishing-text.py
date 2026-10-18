"""Complementary targeted text experiment, isolated from active inference/test."""
import importlib.util
from pathlib import Path
import random
import warnings

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('targeted_base', ROOT/'scripts/train-targeted-phishing.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.exceptions import ConvergenceWarning
from models.phishing_url.inference.url_text_model import canonical_text
from urllib.parse import urlsplit

OUT = ROOT/'models/phishing_url/checkpoints/research_v9'
REPORT = ROOT/'models/phishing_url/research/targeted_text_training_20261018.json'


def main():
    if OUT.exists() or REPORT.exists():
        raise SystemExit('Completed experiment is immutable')
    start = t.time.monotonic(); OUT.mkdir(parents=True)
    manifest = t.json.loads((t.r.BASE/'manifest.json').read_text())
    base = t.ModernModel(t.r.BASE,manifest)
    protocol = {'seed':t.SEED,'dataset_manifest_sha256':t.r.digest(t.DATA/'dataset_manifest.json'),
                'baseline_hashes':{n:t.r.digest(t.r.BASE/e['artifact']) for n,e in manifest['components'].items()},
                'architecture':'Frozen v5 structural/masked text, targeted unmasked text, 33-input fusion and isotonic calibration.',
                'training_weight_targeted':20,'fusion_weight_targeted':20,'calibration_reweighted':False,
                'validation_fpr_budget':.0075,'independent_test_read':False,'promoted':False}
    t.r.dump(OUT/'protocol.json',protocol)
    dataset_manifest = t.json.loads((t.DATA/'dataset_manifest.json').read_text())
    def cohort(split):
        path=t.DATA/('targeted_'+split+'.csv')
        if t.r.digest(path)!=dataset_manifest['files'][path.name]:raise ValueError('Changed targeted cohort')
        return {v['url'] for v in t.r.readrows(path)}
    rows=list(t.development_rows(t.DATA,'train')); new=cohort('train')
    rng=random.Random(t.SEED); ids=[]
    for label in (0,1):
        pool=[i for i,(_,y) in enumerate(rows) if y==label]
        ids.extend(rng.sample(pool,min(80000,len(pool))))
    ids=sorted(set(ids)|{i for i,(u,_) in enumerate(rows) if u in new});rng.shuffle(ids)
    urls=[rows[i][0] for i in ids];y=t.np.asarray([rows[i][1] for i in ids])
    weights=t.np.asarray([20. if u in new else 1. for u in urls])
    lexical=Pipeline([('tfidf',TfidfVectorizer(analyzer='char',ngram_range=(3,5),preprocessor=canonical_text,lowercase=False,
        min_df=5,max_features=40000,sublinear_tf=True,dtype=t.np.float32)),
        ('classifier',SGDClassifier(loss='log_loss',alpha=1e-5,max_iter=200,tol=1e-4,average=True,random_state=t.SEED))])
    t.r.log('targeted_text_fit',rows=len(ids),targeted_rows=sum(u in new for u in urls))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning)
        lexical.fit(urls,y,classifier__sample_weight=weights)
    convergence=[str(w.message) for w in caught if issubclass(w.category,ConvergenceWarning)]
    del rows, urls, ids, weights
    t.joblib.dump(lexical,OUT/'lexical.joblib')
    def features(urls):
        x=t.np.asarray([list(t.extract(u).values()) for u in urls],dtype=t.np.float32)
        sp=base.models['structural'].predict_proba(x)[:,1];mp=base.models['text'].predict_proba(urls)[:,1]
        lp=lexical.predict_proba(urls)[:,1]
        bp=base.models['calibrator'].predict(base.models['fusion'].predict_proba(t.meta_features(x,mp,sp))[:,1])
        return t.np.column_stack([sp,mp,lp,x]),bp
    cal=list(t.development_rows(t.DATA,'calibration'));val=list(t.development_rows(t.DATA,'validation'))
    cm,_=features([u for u,_ in cal]);vm,vb=features([u for u,_ in val])
    cy=t.np.asarray([y for _,y in cal]);vy=t.np.asarray([y for _,y in val])
    part=t.np.asarray([int(t.hashlib.sha256(t.registered_domain(urlsplit(u).hostname).encode()).hexdigest()[:8],16)%2 for u,_ in cal])
    newcal=cohort('calibration');cw=t.np.asarray([20. if u in newcal else 1. for u,_ in cal])
    candidates=[]
    for leaves in (7,15):
        fusion=t.HistGradientBoostingClassifier(max_iter=200,max_leaf_nodes=leaves,max_depth=4,min_samples_leaf=100,l2_regularization=10,random_state=t.SEED)
        fusion.fit(cm[part==0],cy[part==0],sample_weight=cw[part==0])
        calibrator=t.IsotonicRegression(out_of_bounds='clip').fit(fusion.predict_proba(cm[part==1])[:,1],cy[part==1])
        p=calibrator.predict(fusion.predict_proba(vm)[:,1]);threshold=t.r.select_threshold(vy,p,.0075)
        score=t.r.metrics(vy,p,threshold);candidates.append((score['fnr'],score['fpr'],leaves,fusion,calibrator,threshold,score,p))
        t.r.log('targeted_text_validation',leaves=leaves,metrics=score)
    _,_,leaves,fusion,calibrator,threshold,score,vp=min(candidates,key=lambda c:c[:3])
    for n,m in [('fusion',fusion),('calibrator',calibrator)]:t.joblib.dump(m,OUT/(n+'.joblib'))
    selection={'threshold':threshold,'leaves':leaves,'validation':score,'frozen_before_regression':True,
               'artifact_hashes':{p.name:t.r.digest(p) for p in OUT.glob('*.joblib')}}
    t.r.dump(OUT/'selection.json',selection)
    regression={}
    for split in ('historical_regression','regression_reference'):
        t.r.log('targeted_text_regression',split=split)
        rows=t.r.readrows(t.DATA/(split+'.csv'));sy=t.np.asarray([int(v['label']) for v in rows])
        fm,bp=features([v['url'] for v in rows]);cp=calibrator.predict(fusion.predict_proba(fm)[:,1])
        regression[split]={'baseline':t.r.metrics(sy,bp,.7),'candidate':t.r.metrics(sy,cp,threshold)}
    old=t.json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text())
    urls=['https://'+d+'/' for d in old['challenge_domains_excluded_from_fit']]+['https://docs.python.org/3/','https://www.google.com/','https://paypal.com/']
    fm,bp=features(urls);cp=calibrator.predict(fusion.predict_proba(fm)[:,1])
    homepages=[{'url':u,'baseline_probability':float(b),'candidate_probability':float(c),'candidate_alert':bool(c>=threshold)} for u,b,c in zip(urls,bp,cp)]
    newval=cohort('validation');sel=t.np.asarray([u in newval for u,_ in val])
    targeted={'rows':int(sum(sel)),'baseline':t.r.metrics(vy[sel],vb[sel],.7),'candidate':t.r.metrics(vy[sel],vp[sel],threshold)}
    gates={'homepages_no_alerts':not any(v['candidate_alert'] for v in homepages),
           'historical_both_error_rates_improved':all(regression['historical_regression']['candidate'][m]<regression['historical_regression']['baseline'][m] for m in ('fpr','fnr')),
           'reference_no_error_rate_regression':all(regression['regression_reference']['candidate'][m]<=regression['regression_reference']['baseline'][m] for m in ('fpr','fnr')),
           'targeted_no_error_rate_regression':all(targeted['candidate'][m]<=targeted['baseline'][m] for m in ('fpr','fnr')),
           'converged':not convergence}
    t.r.dump(REPORT,{'protocol':protocol,'selection':selection,'regression':regression,'targeted_validation':targeted,
        'validation_baseline':t.r.metrics(vy,vb,.7),'candidate_validation_results':[{'leaves':c[2],'metrics':c[6]} for c in candidates],
        'homepages':homepages,'gates':gates,'convergence_warnings':convergence,
        'eligible_for_independent_evaluation':all(gates.values()),'independent_test_read':False,'promoted':False,
        'baseline_unchanged':all(t.r.digest(t.r.BASE/e['artifact'])==protocol['baseline_hashes'][n] for n,e in manifest['components'].items()),
        'elapsed_seconds':t.time.monotonic()-start})
    t.r.log('targeted_text_complete',gates=gates,promoted=False)


if __name__=='__main__':main()
