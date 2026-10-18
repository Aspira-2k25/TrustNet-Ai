"""LightGBM native TreeSHAP in log-odds space before fusion/calibration."""
import numpy as np
from shared.schemas.evidence import EvidenceItem
from models.phishing_url.preprocessing.extract_features import FEATURE_NAMES

def explain(model, features, top_k=5):
    contributions = np.asarray(model.booster_.predict([list(features.values())], pred_contrib=True))[0][:-1]
    return [EvidenceItem(feature_or_region=FEATURE_NAMES[i], contribution=float(contributions[i]), human_readable_note=f"TreeSHAP log-odds contribution {contributions[i]:+.3f} from {FEATURE_NAMES[i]}={features[FEATURE_NAMES[i]]:g}; before calibration/voting") for i in np.argsort(np.abs(contributions))[-top_k:][::-1]]
