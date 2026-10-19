"""Scheme-neutral URL text classifier with locally checked calibration."""
import time
from .model_loader import checked_path
from models.phishing_url.preprocessing.url_parser import parse_url

def canonical_text(url):
    p=parse_url(url)
    # Transport is not a phishing label; preserve hostname, path and query.
    authority=p.parts.netloc.lower()
    return (authority+(p.parts.path or '/')+('?' + p.parts.query if p.parts.query else ''))[:2048]

class URLTextModel:
    def __init__(self,root,manifest):
        import joblib
        self.manifest=manifest
        self.pipeline=joblib.load(checked_path(root,manifest['artifact'],manifest['sha256']))
        self.calibrator=joblib.load(checked_path(root,manifest['calibrator'],manifest['calibrator_sha256']))
        self.names=self.pipeline.named_steps['tfidf'].get_feature_names_out()

    def predict_url(self,url,features):
        start=time.monotonic()
        raw=float(self.pipeline.predict_proba([url])[0,1])
        p=float(self.calibrator.predict([raw])[0])
        vector=self.pipeline.named_steps['tfidf'].transform([url])
        weights=self.pipeline.named_steps['classifier'].coef_[0]
        contributions=sorted(((int(i),float(v*weights[i])) for i,v in zip(vector.indices,vector.data)),key=lambda x:abs(x[1]),reverse=True)[:5]
        evidence=[{'feature_or_region':'URL text: '+str(self.names[i]),'contribution':v,
                   'human_readable_note':f"URL text fragment {str(self.names[i])!r} {'increased' if v>0 else 'reduced'} the URL classifier's estimate (before calibration)."} for i,v in contributions]
        return p,self.manifest['threshold'],{'configuration':'url_text_v2','calibrated':True,
            'confidence_definition':'Prediction probability calibrated on disjoint development domains; not a guarantee of website safety.',
            'analyzers':[{'name':'Scheme-neutral URL text model','status':'APPLIED'}],
            'evidence':evidence,'inference_ms':int(1000*(time.monotonic()-start))}
