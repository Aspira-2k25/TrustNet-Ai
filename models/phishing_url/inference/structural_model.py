"""Calibrated, domain-independent structural model. No domain exceptions."""
import time
from .model_loader import checked_path
from models.phishing_url.preprocessing.structural_features import extract, NAMES, VERSION

class StructuralModel:
    def __init__(self, root, manifest):
        import joblib
        if manifest['structural_features'] != list(NAMES) or manifest['structural_preprocessing'] != VERSION:
            raise ValueError('Structural model feature schema mismatch')
        self.model = joblib.load(checked_path(root, manifest['artifact'], manifest['sha256']))
        self.calibrator = joblib.load(checked_path(root, manifest['calibrator'], manifest['calibrator_sha256']))
        self.manifest = manifest

    def predict_url(self, url, unused_features):
        import numpy as np
        start = time.monotonic()
        features = extract(url)
        row = np.asarray([list(features.values())], dtype=np.float32)
        p = float(self.calibrator.predict(self.model.predict_proba(row)[:, 1])[0])
        values = self.model.booster_.predict(row, pred_contrib=True)[0][:-1]
        top = sorted(zip(NAMES, values), key=lambda x: abs(x[1]), reverse=True)[:5]
        evidence = [{'feature_or_region': name, 'contribution': float(value),
                     'human_readable_note': f'Structural model association: {name}={features[name]:g}, contribution {value:+.3f} before calibration; not independent proof.'}
                    for name, value in top]
        return p, self.manifest['threshold'], {'configuration': 'structural_v3', 'calibrated': True,
                    'confidence_definition': 'Probability calibrated on domain-disjoint development data; live reliability remains subject to evaluation.',
                    'analyzers': [{'name': 'Structural URL model', 'status': 'APPLIED', 'category': 'primary_ml'}],
                    'evidence': evidence, 'structural_features': features,
                    'inference_ms': round((time.monotonic()-start)*1000)}
