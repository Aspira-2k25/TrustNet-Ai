"""URL-shape expert routing. No domain lists or caller-supplied verdicts."""
from urllib.parse import urlsplit
import time
import numpy as np
from .modern_model import meta_features
from .model_loader import checked_path
from models.phishing_url.preprocessing.structural_features import extract,NAMES,VERSION


def region(url):
    p=urlsplit(url)
    return 'query' if p.query else 'root' if p.path in ('','/') else 'path'


class RegionalModel:
    def __init__(self,root,manifest,allow_unselected=False):
        import joblib
        if manifest['structural_features']!=list(NAMES) or manifest['structural_preprocessing']!=VERSION:
            raise ValueError('Regional feature schema mismatch')
        if not allow_unselected and set(manifest.get('routing',{}))!={'root','query','path'}:
            raise ValueError('Regional routing must cover every URL shape')
        self.manifest=manifest
        self.models={n:joblib.load(checked_path(root,e['artifact'],e['sha256'])) for n,e in manifest['components'].items()}
        for name,route in manifest.get('routing',{}).items():
            if name not in {'root','query','path'} or route['expert'] not in {'baseline','correction'} or not 0<route['threshold']<1:
                raise ValueError('Invalid regional routing')

    def expert_predictions(self,urls):
        m=self.models
        x=np.asarray([list(extract(u).values()) for u in urls],dtype=np.float32)
        sp=m['structural'].predict_proba(x)[:,1];mp=m['text'].predict_proba(urls)[:,1]
        raw5=m['base_fusion'].predict_proba(meta_features(x,mp,sp))[:,1]
        bp=m['base_calibrator'].predict(raw5)
        lp=m['complementary_text'].predict_proba(urls)[:,1]
        raw9=m['complementary_fusion'].predict_proba(np.column_stack([sp,mp,lp,x]))[:,1]
        raw12=m['correction_fusion'].predict_proba(np.column_stack([raw5,raw9,x]))[:,1]
        cp=m['correction_calibrator'].predict(raw12)
        return {'baseline':bp,'correction':cp},x,sp,mp

    def predict_url(self,url,unused_features):
        start=time.monotonic();pred,x,sp,mp=self.expert_predictions([url]);shape=region(url)
        route=self.manifest['routing'][shape];p=float(pred[route['expert']][0])
        return p,route['threshold'],{'configuration':'regional_v1','calibrated':False,
            'confidence_definition':'Individual experts were calibrated on development data. Calibration of conditional routing is not established; this is not a live safety guarantee.',
            'analyzers':[{'name':'URL structure and text experts','status':'APPLIED','category':'primary_ml'}],
            'structural_features':dict(zip(NAMES,map(float,x[0]))),
            'branch_probabilities':{'structural':float(sp[0]),'url_text':float(mp[0])},
            'selected_expert':route['expert'],'url_region':shape,
            'expert_estimates':{n:float(v[0]) for n,v in pred.items()},
            'evidence':[],'inference_ms':round((time.monotonic()-start)*1000)}
