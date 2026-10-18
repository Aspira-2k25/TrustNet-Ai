"""Fixed familiar-homepage regression; no tuning or deployment side effects."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import joblib
import numpy as np
from threadpoolctl import threadpool_limits
from models.phishing_url.inference.modern_model import ModernModel,meta_features
from models.phishing_url.preprocessing.structural_features import extract
from models.phishing_url.inference.forensics import analyze
threadpool_limits(limits=2)


def main():
    out=ROOT/'models/phishing_url/checkpoints/research_v7'
    report=json.loads((ROOT/'models/phishing_url/research/complementary_20261018.json').read_text())
    basepath=ROOT/'models/phishing_url/checkpoints/modern_v5'
    manifest=json.loads((basepath/'manifest.json').read_text());base=ModernModel(basepath,manifest)
    models={name:joblib.load(out/(name+'.joblib')) for name in ('lexical','fusion','calibrator')}
    old=json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text())
    urls=['https://'+domain+'/' for domain in old['challenge_domains_excluded_from_fit']]
    urls+=['https://docs.python.org/3/','https://www.google.com/','https://paypal.com/','https://paypaI.com/']
    X=np.asarray([list(extract(url).values()) for url in urls],dtype=np.float32)
    sp=base.models['structural'].predict_proba(X)[:,1];mp=base.models['text'].predict_proba(urls)[:,1]
    lp=models['lexical'].predict_proba(urls)[:,1]
    bp=base.models['calibrator'].predict(base.models['fusion'].predict_proba(meta_features(X,mp,sp))[:,1])
    cp=models['calibrator'].predict(models['fusion'].predict_proba(np.column_stack([sp,mp,lp,X]))[:,1])
    rows=[{'url':url,'baseline_probability':float(b),'candidate_probability':float(c),
           'candidate_model_alert':bool(c>=report['threshold']),'offline_forensic_outcome':analyze(url)['outcome']} for url,b,c in zip(urls,bp,cp)]
    result={'role':'Previously used familiar-homepage regression, not new independently labeled accuracy data.',
            'threshold':report['threshold'],'rows':rows,'official_homepage_alerts':sum(r['candidate_model_alert'] for r in rows[:19]),
            'illustrative_lookalike_note':'The paypaI input is a visual-domain test, not an independently verified live phishing label.',
            'artifact_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.joblib')}}
    path=ROOT/'models/phishing_url/research/complementary_homepages_20261018.json'
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
