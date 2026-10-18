"""Train a separately versioned CPU candidate; never overwrite the BERT bundle.

Official UCI PhiUSIIL labels: 1 legitimate, 0 phishing. Only URL and label
are used. Existing approved source is retained; canonical conflicts excluded.
"""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
import csv,hashlib,io,json,time,zipfile
from collections import Counter
import joblib
import numpy as np
import tldextract
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.isotonic import IsotonicRegression
from models.phishing_url.inference.url_text_model import canonical_text
from models.phishing_url.preprocessing.url_parser import parse_url,PREPROCESSING_VERSION
from models.phishing_url.preprocessing.extract_features import FEATURE_NAMES
from models.phishing_url.evaluation.metrics import metrics

started=time.monotonic();out=root/'models/phishing_url/checkpoints/url_text_v2';out.mkdir(parents=True,exist_ok=True)
extract=tldextract.TLDExtract(suffix_list_urls=(),cache_dir=None,include_psl_private_domains=True)
records={};conflicts=set();counts=Counter()
def add(url,label,source):
    try:
        key=canonical_text(url);parsed=parse_url(url)
        domain=extract(parsed.hostname).top_domain_under_public_suffix or parsed.hostname
    except ValueError: counts['invalid']+=1;return
    if key in records and records[key]['label']!=label: conflicts.add(key);return
    if key not in records: records[key]=dict(url=url,label=label,domain=domain,source=source)

with (root/'models/phishing_url/data/primary/prepared/prepared.csv').open(encoding='utf-8') as f:
    for r in csv.DictReader(f): add(r['url'],int(r['label']),'primary')
source=root/'models/phishing_url/data/phiusiil/source.zip'
with zipfile.ZipFile(source) as z:
    with io.TextIOWrapper(z.open('PhiUSIIL_Phishing_URL_Dataset.csv'),encoding='utf-8-sig') as f:
        for r in csv.DictReader(f): add(r['URL'],1-int(r['label']),'phiusiil')
for key in conflicts: records.pop(key,None)
challenge={'google.com','wikipedia.org','github.com','microsoft.com','amazon.in','python.org','bbc.com','example.com','paypal.com'}
rows=list(records.values()); del records
for r in rows:
    h=int(hashlib.sha256(('url-v2-42:'+r['domain']).encode()).hexdigest()[:8],16)%100
    r['split']='test' if r['domain'] in challenge or h>=85 else 'validation' if h>=70 else 'train'
splits={s:[r for r in rows if r['split']==s] for s in ('train','validation','test')}
print(json.dumps({'rows':{s:len(v) for s,v in splits.items()},'conflicting_urls_removed':len(conflicts),'stage':'fit'}),flush=True)
model=Pipeline([('tfidf',TfidfVectorizer(analyzer='char',ngram_range=(3,5),preprocessor=canonical_text,lowercase=False,min_df=3,max_features=120000,sublinear_tf=True,dtype=np.float32)),
                ('classifier',SGDClassifier(loss='log_loss',alpha=1e-6,max_iter=15,tol=1e-4,random_state=42))])
model.fit([r['url'] for r in splits['train']],[r['label'] for r in splits['train']])
v=splits['validation'];vp=model.predict_proba([r['url'] for r in v])[:,1];vy=np.array([r['label'] for r in v])
parts=np.array([int(hashlib.sha256(r['domain'].encode()).hexdigest()[:8],16)%2 for r in v])
cal=IsotonicRegression(out_of_bounds='clip').fit(vp[parts==0],vy[parts==0])
cp=cal.predict(vp[parts==1]);cy=vy[parts==1]
options=[(float(t),metrics(cy,cp,float(t))) for t in np.linspace(.01,.99,99)]
eligible=[(t,m) for t,m in options if m['fpr']<=.01]
threshold,validation=max(eligible or options,key=lambda item:item[1]['f1'])
artifact=out/'model.joblib';joblib.dump(model,artifact)
calpath=out/'calibrator.joblib';joblib.dump(cal,calpath)
test=splits['test'];prob=cal.predict(model.predict_proba([r['url'] for r in test])[:,1]);y=np.array([r['label'] for r in test])
groups={s:{r['domain'] for r in values} for s,values in splits.items()}
assert not (groups['train']&groups['validation'] or groups['train']&groups['test'] or groups['validation']&groups['test'])
report={'rows':{s:len(v) for s,v in splits.items()},'label_counts':{s:dict(Counter(r['label'] for r in v)) for s,v in splits.items()},
        'canonical_conflicts_removed':len(conflicts),'invalid_urls':counts['invalid'],'domain_overlap':0,
        'challenge_domains_excluded_from_training_and_calibration':sorted(challenge),'validation':validation,'test':metrics(y,prob,threshold),
        'test_by_source':{},'threshold':threshold,'elapsed_seconds':time.monotonic()-started,
        'primary_reused':True,'temporal_generalization_measured':False,'source':'https://archive.ics.uci.edu/dataset/967/phiusil-phishing-url-dataset',
        'license':'CC BY 4.0; Prasad & Chandra (2024), PhiUSIIL, UCI','phiusiil_zip_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
for name in ('primary','phiusiil'):
    mask=np.array([r['source']==name for r in test]);report['test_by_source'][name]=metrics(y[mask],prob[mask],threshold)
manifest={'kind':'url_text','detector_id':'phishing.url_text.v2','model_version':'url-text-v2','preprocessing_version':PREPROCESSING_VERSION,
          'representation':'scheme-neutral host/path/query char 3-5 TF-IDF','feature_names':list(FEATURE_NAMES),'threshold':threshold,'calibrated':True,
          'artifact':artifact.name,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'calibrator':calpath.name,'calibrator_sha256':hashlib.sha256(calpath.read_bytes()).hexdigest(),
          'source_report':'models/phishing_url/research/accuracy_candidate.json'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
(root/'models/phishing_url/research/accuracy_candidate.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
