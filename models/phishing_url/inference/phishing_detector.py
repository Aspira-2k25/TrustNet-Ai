"""Phishing inference with checked model loading and current forensic policy."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from shared.interfaces.detector_base import BaseDetector
from shared.schemas.detection_result import DetectionResult
from shared.schemas.evidence import EvidenceItem
from models.phishing_url.preprocessing.extract_features import FEATURE_NAMES, extract_features
from models.phishing_url.preprocessing.url_parser import PREPROCESSING_VERSION
from .presentation import present
from .forensics import apply_policy, canonical_url

class PhishingDetector(BaseDetector):
    def __init__(self, manifest_path=None):
        self.model = None
        self.manifest = {}
        if manifest_path:
            import joblib
            path = Path(manifest_path)
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if manifest["feature_names"] != list(FEATURE_NAMES) or manifest["preprocessing_version"] != PREPROCESSING_VERSION:
                raise ValueError("Artifact feature schema mismatch")
            if manifest.get('kind') == 'structural_v3':
                from .structural_model import StructuralModel
                self.model = StructuralModel(path.parent, manifest)
                self.manifest = manifest
                return
            if manifest.get('kind') == 'modern_v5':
                from .modern_model import ModernModel
                self.model = ModernModel(path.parent, manifest)
                self.manifest = manifest
                return
            if manifest.get('kind') == 'regional_v1':
                from .regional_model import RegionalModel
                self.model = RegionalModel(path.parent, manifest)
                self.manifest = manifest
                return
            if manifest.get('kind') == 'regional_recall_v1':
                from .recall_model import RecallModel
                self.model = RecallModel(path.parent, manifest)
                self.manifest = manifest
                return
            if manifest.get("kind") == "lightgbm_bert":
                from .model_loader import HybridModel
                self.model = HybridModel(path.parent, manifest)
                self.manifest = manifest
                return
            if manifest.get('kind') == 'url_text':
                from .url_text_model import URLTextModel
                self.model = URLTextModel(path.parent, manifest)
                self.manifest = manifest
                return
            artifact = path.parent / manifest["artifact"]
            if artifact.resolve().parent != path.parent.resolve():
                raise ValueError("Artifact must be inside bundle directory")
            if hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest["sha256"]:
                raise ValueError("Artifact checksum mismatch")
            if not 0 < manifest["threshold"] < 1:
                raise ValueError("Invalid threshold")
            self.model = joblib.load(artifact)
            if set(self.model.classes_) != {0, 1}:
                raise ValueError("Artifact requires binary classes 0 and 1")
            self.manifest = manifest

    def predict(self, input_data):
        scan_id = input_data["scan_id"]
        base = dict(scan_id=scan_id, module="phishing", detector_id=self.manifest.get("detector_id", "phishing.lexical.unavailable"), model_version=self.manifest.get("model_version", "none"), preprocessing_version=self.manifest.get('structural_preprocessing',PREPROCESSING_VERSION), native_score_semantics="probability_of_positive_class", timestamp=datetime.now(timezone.utc).isoformat())
        try:
            from models.phishing_url.preprocessing.link_input import inspect_input
            link=inspect_input(input_data.get('url'))
            if link['kind']!='web':
                return apply_policy(DetectionResult(**{**base,'model_version':'link-forensics-v1'},native_score=0,risk_score=0,confidence=0,label='unknown',status='UNAVAILABLE',error_code='NON_WEB_LINK',error_message='Offline inspection only: the website model does not apply to this link type.'),input_data['url'])
            inference_url = canonical_url(input_data.get("url"))
            features = extract_features(inference_url)
        except ValueError as exc:
            return present(DetectionResult(**base, native_score=0, risk_score=0, confidence=0, label="unknown", status="FAILED", error_code="INVALID_URL", error_message=str(exc)), input_data.get('url'), None)
        if self.model is None:
            return apply_policy(DetectionResult(**base, native_score=0, risk_score=0, confidence=0, label="unknown", status="UNAVAILABLE", error_code="MODEL_NOT_CONFIGURED", error_message="Train and configure a trusted phishing model bundle before inference"), input_data['url'])
        if hasattr(self.model, "predict_url"):
            p, threshold, hybrid = self.model.predict_url(inference_url, features)
        else:
            p = float(self.model.predict_proba([list(features.values())])[0][list(self.model.classes_).index(1)])
            threshold, hybrid = self.manifest["threshold"], None
        if not 0 <= p <= 1:
            raise ValueError("Invalid model probability")
        evidence = [EvidenceItem(feature_or_region=name, contribution=0, human_readable_note=f"Observed {name}: {value:g}; observation only, not a model attribution") for name, value in features.items() if name in {"has_userinfo", "is_ip", "is_idn", "sensitive_tokens"} and value]
        label = "phishing" if p >= threshold else "legitimate"
        metadata = {"configuration": "lexical_baseline", "calibrated": False, "confidence_available": False, "missing_signals": ["whois", "tls", "dns", "html", "bert"], "features": features}
        if hybrid:
            metadata['assessment_policy'] = 'url-text-v2' if self.manifest.get('kind') == 'url_text' else 'branch-agreement-v1'
            metadata.update({key: value for key, value in hybrid.items() if key not in {"analyzers", "evidence"}})
            evidence.extend(EvidenceItem.model_validate(item) for item in hybrid.get("evidence", []))
            metadata["missing_signals"] = ["whois", "tls", "dns", "html"]
            if hybrid['configuration'] == 'url_text_v2':
                metadata['missing_signals'].extend(['bert', 'lightgbm'])
            elif hybrid['configuration'] in {'structural_v3','modern_v5','regional_v1'}:
                metadata['missing_signals'].extend(['bert'])
            elif hybrid["configuration"] != "lightgbm_bert":
                metadata["missing_signals"].append("bert" if hybrid["configuration"] == "lightgbm" else "lightgbm")
            metadata["confidence_available"] = True
        result = DetectionResult(**base, native_score=p, risk_score=round(p * 100), confidence=(p if label == "phishing" else 1-p) if hybrid else 0, label=label, status="PARTIAL_SUCCESS", evidence=evidence, metadata=metadata, analyzers=hybrid["analyzers"] if hybrid else [], processing_time_ms=hybrid["inference_ms"] if hybrid else 0)
        if hybrid and hybrid.get('model_disagreement'):
            result.metadata['diagnostic_phishing_probability'] = p
            result.metadata['confidence_available'] = False
            result.status = type(result.status).UNAVAILABLE
            result.label = 'unknown'
            result.confidence = 0
            result.error_code = 'MODEL_DISAGREEMENT'
            result.error_message = 'The two URL models disagree. A reliable trust score cannot be assigned; this is not a confirmed phishing result.'
        result.metadata['inference_url'] = inference_url
        return apply_policy(result, input_data['url'], threshold)
