"""Calibrated URL text + structure ensemble with no per-domain verdicts."""
import time
from urllib.parse import urlsplit
from functools import lru_cache
from models.phishing_url.preprocessing.structural_features import extract, NAMES, VERSION


@lru_cache(maxsize=100000)
def domain_boundary(host):
    from .forensics import suffix_parser
    return suffix_parser()(host).top_domain_under_public_suffix or host

def masked_url_text(url):
    """Validated inputs: remove registered-name identity, retain structural context."""
    p = urlsplit(url)
    host = (p.hostname or '').lower().rstrip('.')
    domain = domain_boundary(host)
    subdomain = host[:-len(domain)].rstrip('.') if host != domain else ''
    authority = (subdomain+'.' if subdomain else '')+'[DOMAIN]'
    if p.username is not None: authority = '[USERINFO]@'+authority
    if p.port is not None: authority += ':[PORT]'
    return (authority+(p.path or '/')+('?'+p.query if p.query else '')+('#'+p.fragment if p.fragment else ''))[:2048]

def meta_features(structural, text_p, structural_p):
    import numpy as np
    indexes = [NAMES.index(k) for k in ('host_length','path_length','host_labels','query_length','ip_destination')]
    return np.column_stack([structural_p, text_p, structural[:, indexes]])

class ModernModel:
    def __init__(self, root, manifest):
        import joblib
        from .model_loader import checked_path
        if manifest['structural_features'] != list(NAMES) or manifest['structural_preprocessing'] != VERSION:
            raise ValueError('Modern feature schema mismatch')
        self.models = {name: joblib.load(checked_path(root, item['artifact'], item['sha256'])) for name,item in manifest['components'].items()}
        self.manifest = manifest

    def predict_url(self, url, unused_features):
        import numpy as np
        start = time.monotonic()
        features = extract(url)
        row = np.asarray([list(features.values())], dtype=np.float32)
        structural = self.models['structural'].predict_proba(row)[:,1]
        text = self.models['text'].predict_proba([url])[:,1]
        raw = self.models['fusion'].predict_proba(meta_features(row, text, structural))[:,1]
        p = float(self.models['calibrator'].predict(raw)[0])
        return p, self.manifest['threshold'], {'configuration':self.manifest['kind'],'calibrated':True,
                 'confidence_definition':'Domain-disjoint development calibration of the model, not a guarantee of live safety.',
                 'analyzers':[{'name':'URL text + structure ensemble','status':'APPLIED','category':'primary_ml'}],
                 'structural_features':features, 'branch_probabilities':{'structural':float(structural[0]),'url_text':float(text[0])},
                 'evidence':[], 'inference_ms':round((time.monotonic()-start)*1000)}
