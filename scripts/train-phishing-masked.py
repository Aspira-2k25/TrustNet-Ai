"""Evaluate URL text + structural fusion on the same auditable domain partitions."""
import csv, hashlib, io, json, sys, time, zipfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root))
import joblib, numpy as np, tldextract
from urllib.parse import urlsplit
from functools import lru_cache
from threadpoolctl import threadpool_limits
threadpool_limits(limits=2)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from models.phishing_url.inference.modern_model import masked_url_text, meta_features
from models.phishing_url.preprocessing.structural_features import extract, NAMES, VERSION
from models.phishing_url.preprocessing.url_parser import parse_url, PREPROCESSING_VERSION
from models.phishing_url.preprocessing.extract_features import FEATURE_NAMES
from models.phishing_url.evaluation.metrics import metrics

started=time.monotonic(); out=root/'models/phishing_url/checkpoints/modern_v5';out.mkdir(parents=True,exist_ok=True)
report3=json.loads((root/'models/phishing_url/research/structural_candidate.json').read_text())
challenge=set(report3['challenge_excluded_from_train_calibration_validation'])
suffix=tldextract.TLDExtract(suffix_list_urls=(),cache_dir=None,include_psl_private_domains=True)
rows,conflicts={},set()
@lru_cache(maxsize=300000)
def domain_for(host):
    return suffix(host).top_domain_under_public_suffix or host

def add(url,label,source):
    # These exact files were already audited for valid URLs. Fast source loading
    # preserves the previous canonical key and split; inference validates separately.
    try:
        p=urlsplit(url)
        key=(p.netloc.lower()+(p.path or '/')+('?' + p.query if p.query else ''))[:2048]
        host=p.hostname.rstrip('.').encode('idna').decode('ascii').lower()
    except (ValueError,UnicodeError,AttributeError):return
    if key in rows and rows[key][1]!=label:conflicts.add(key)
    elif key not in rows:rows[key]=(url,label,domain_for(host),source)
print('Loading approved source records',flush=True)
with (root/'models/phishing_url/data/primary/prepared/prepared.csv').open(encoding='utf-8') as f:
    for r in csv.DictReader(f):add(r['url'],int(r['label']),'primary')
with zipfile.ZipFile(root/'models/phishing_url/data/phiusiil/source.zip') as z:
    with io.TextIOWrapper(z.open('PhiUSIIL_Phishing_URL_Dataset.csv'),encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):add(r['URL'],1-int(r['label']),'phiusiil')
for key in conflicts:rows.pop(key,None)
groups={k:[] for k in ('train','calibration','validation','test')}
for row in rows.values():
    h=int(hashlib.sha256(('structural-v3-42:'+row[2]).encode()).hexdigest()[:8],16)%100
    split='test' if row[2] in challenge or h>=85 else 'validation' if h>=78 else 'calibration' if h>=70 else 'train'
    groups[split].append(row)
del rows
assert {s:len(v) for s,v in groups.items()}==report3['rows']
domain_sets={s:{r[2] for r in rows} for s,rows in groups.items()}
assert not any(domain_sets[a]&domain_sets[b] for a in groups for b in groups if a!=b)
model=Pipeline([('tfidf',TfidfVectorizer(analyzer='char',ngram_range=(3,5),preprocessor=masked_url_text,lowercase=False,
                                      min_df=5,max_features=40000,sublinear_tf=True,dtype=np.float32)),
                ('classifier',SGDClassifier(loss='log_loss',alpha=1e-6,max_iter=25,tol=1e-4,average=True,random_state=42))])
import random
rng=random.Random(42)
train=[]
for source_name in ('primary','phiusiil'):
    for label in (0,1):
        candidates=[r for r in groups['train'] if r[3]==source_name and r[1]==label]
        train.extend(rng.sample(candidates,min(50000,len(candidates))))
rng.shuffle(train)
print('Fitting masked text classifier: '+str(len(train)),flush=True)
model.fit([r[0] for r in train],[r[1] for r in train],classifier__sample_weight=np.array([2. if r[3]=='phiusiil' else .5 for r in train],dtype=np.float32))
structural=joblib.load(root/'models/phishing_url/checkpoints/structural_v3/model.joblib')
def probabilities(rows):
    X=np.asarray([list(extract(r[0]).values()) for r in rows],dtype=np.float32)
    tp=model.predict_proba([r[0] for r in rows])[:,1]
    sp=structural.predict_proba(X)[:,1]
    return meta_features(X,tp,sp)
calrows=groups['calibration']; cm=probabilities(calrows); cy=np.array([r[1] for r in calrows])
part=np.array([int(hashlib.sha256(r[2].encode()).hexdigest()[:8],16)%2 for r in calrows])
fusion=HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=15,max_depth=4,min_samples_leaf=100,l2_regularization=10,random_state=42)
fusion.fit(cm[part==0],cy[part==0])
cal=IsotonicRegression(out_of_bounds='clip').fit(fusion.predict_proba(cm[part==1])[:,1],cy[part==1])
print('Evaluating validation partition',flush=True)
val=groups['validation'];vp=cal.predict(fusion.predict_proba(probabilities(val))[:,1]);vy=np.array([r[1] for r in val])
options=[(float(t),metrics(vy,vp,float(t))) for t in np.linspace(.05,.95,91)]
eligible=[(t,m) for t,m in options if m['fpr']<=.02]
threshold,validation=max(eligible or options,key=lambda x:x[1]['f1'])
test=groups['test'];prob=cal.predict(fusion.predict_proba(probabilities(test))[:,1]);y=np.array([r[1] for r in test])
checks=['https://'+d+'/' for d in sorted(challenge)]
cp=cal.predict(fusion.predict_proba(probabilities([(u,0,'challenge','challenge') for u in checks]))[:,1])
report={'rows':{s:len(v) for s,v in groups.items()},'domain_overlap':0,'calibration_meta_partition_sizes':{str(i):int(sum(part==i)) for i in (0,1)},
        'text_training_rows':len(train),'registered_domain_identity_masked':True,'threshold':threshold,'validation':validation,'test':metrics(y,prob,threshold),
        'test_by_source':{},'challenge':[{'url':u,'probability':float(p),'alert':bool(p>=threshold)} for u,p in zip(checks,cp)],
        'challenge_domains_excluded_from_fit':sorted(challenge),'elapsed_seconds':time.monotonic()-started,
        'limitations':['Source/domain-held-out benchmark, not a temporal deployment guarantee.','Structural-only and unmasked-text candidates were rejected; this development reused their evaluation partition. Fresh web comparisons are separate.'],
        'https_rows_by_label':report3['https_rows_by_label']}
for source in ('primary','phiusiil'):
    mask=np.array([r[3]==source for r in test]);report['test_by_source'][source]=metrics(y[mask],prob[mask],threshold)
components={}
for name,value in [('text',model),('structural',structural),('fusion',fusion),('calibrator',cal)]:
    path=out/(name+'.joblib');joblib.dump(value,path)
    components[name]={'artifact':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
manifest={'kind':'modern_v5','model_version':'modern-v5','detector_id':'phishing.modern.v5','preprocessing_version':PREPROCESSING_VERSION,
          'feature_names':list(FEATURE_NAMES),'structural_features':list(NAMES),'structural_preprocessing':VERSION,
          'threshold':threshold,'components':components,'source_report':'models/phishing_url/research/masked_candidate.json'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
(root/'models/phishing_url/research/masked_candidate.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
