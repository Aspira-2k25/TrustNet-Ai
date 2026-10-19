"""Offline checked hybrid loading and explicit calibrated branch fallback."""
import hashlib
import time
import joblib
import numpy as np

def checked_path(root, relative, digest):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Bundle path/checksum mismatch")
    return path

class HybridModel:
    classes_ = np.array([0, 1])
    def __init__(self, root, manifest):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.manifest = manifest
        self.fusion = manifest["fusion"]
        self.lightgbm = joblib.load(checked_path(root, manifest["lightgbm"]["artifact"], manifest["lightgbm"]["sha256"]))
        self.calibrator = joblib.load(checked_path(root, self.fusion["calibrator"], self.fusion["calibrator_sha256"]))
        self.fallbacks = {name: joblib.load(checked_path(root, entry["artifact"], entry["sha256"])) for name, entry in self.fusion["fallbacks"].items()}
        for relative, digest in manifest["bert"]["files"].items():
            checked_path(root, relative, digest)
        self.tokenizer = AutoTokenizer.from_pretrained(root / "bert", local_files_only=True)
        self.bert = AutoModelForSequenceClassification.from_pretrained(root / "bert", local_files_only=True).eval()
        torch.set_num_threads(4)

    def predict_url(self, url, features):
        import torch
        from models.phishing_url.preprocessing.bert_tokenizer import serialize_url
        observed, probabilities = [], {}
        start = time.monotonic()
        try:
            probabilities["lightgbm"] = float(self.lightgbm.predict_proba([list(features.values())])[0][1])
            observed.append({"name": "LightGBM lexical branch", "status": "APPLIED"})
        except (RuntimeError, ValueError):
            observed.append({"name": "LightGBM lexical branch", "status": "UNAVAILABLE"})
        try:
            tokens = self.tokenizer(serialize_url(url), return_tensors="pt", truncation=True, max_length=self.manifest["bert"]["max_length"])
            with torch.no_grad():
                probabilities["bert"] = float(torch.softmax(self.bert(**tokens).logits, dim=1)[0, 1])
            observed.append({"name": "BERT URL branch", "status": "APPLIED"})
        except (RuntimeError, ValueError):
            observed.append({"name": "BERT URL branch", "status": "UNAVAILABLE"})
        if len(probabilities) == 2:
            w = self.fusion["lightgbm_weight"]
            p = float(self.calibrator.predict([w * probabilities["lightgbm"] + (1-w) * probabilities["bert"]])[0])
            threshold = self.fusion["threshold"]
            mode = "lightgbm_bert"
        elif len(probabilities) == 1:
            mode = next(iter(probabilities))
            p = float(self.fallbacks[mode].predict([probabilities[mode]])[0])
            threshold = self.fusion["fallbacks"][mode]["threshold"]
        else:
            raise RuntimeError("No phishing branch available")
        evidence = []
        if "lightgbm" in probabilities:
            from models.phishing_url.explainability.shap_explainer import explain
            evidence = [item.model_dump() for item in explain(self.lightgbm, features)]
        decisions = {name: bool(float(self.fallbacks[name].predict([value])[0]) >= self.fusion['fallbacks'][name]['threshold']) for name,value in probabilities.items()}
        return p, threshold, {"configuration": mode, "branch_probabilities": probabilities, "branch_decisions": decisions, "model_disagreement": len(set(decisions.values())) > 1, "calibrated": True, "confidence_definition": "calibrated probability of predicted label; calibration measured on held-out development domains", "evidence": evidence, "analyzers": observed, "inference_ms": int(1000*(time.monotonic()-start))}
