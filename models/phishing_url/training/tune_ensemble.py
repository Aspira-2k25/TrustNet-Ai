"""Validation-only weighted voting, disjoint calibration and threshold fitting."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import log_loss, f1_score
from models.phishing_url.evaluation.metrics import metrics

def read(path):
    with open(path, encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    indexed = {r["url"]: r for r in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate predictions")
    return indexed

def tune(lightgbm_predictions, bert_predictions, output):
    left, right = read(lightgbm_predictions), read(bert_predictions)
    if set(left) != set(right):
        raise ValueError("Branch predictions must use identical validation URLs")
    urls = sorted(left)
    for url in urls:
        if any(left[url][key] != right[url][key] for key in ("domain_group", "label")):
            raise ValueError("Branch row mismatch")
    # Split by domain hashes; neither branch trained these validation domains.
    parts = np.array([int(hashlib.sha256(left[u]["domain_group"].encode()).hexdigest()[:8], 16) % 3 for u in urls])
    y = np.array([int(left[u]["label"]) for u in urls])
    lp, bp = (np.array([float(branch[u]["probability"]) for u in urls]) for branch in (left, right))
    for part in range(3):
        if set(y[parts == part]) != {0, 1}:
            raise ValueError("Fusion/calibration/threshold partition lacks both classes")
    if not all(np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all() for p in (lp, bp)):
        raise ValueError("Invalid branch probabilities")
    weight = float(min(np.linspace(0, 1, 21), key=lambda w: log_loss(y[parts == 0], (w * lp + (1-w) * bp)[parts == 0], labels=[0,1])))
    vote = weight * lp + (1-weight) * bp
    calibrator = IsotonicRegression(out_of_bounds="clip").fit(vote[parts == 1], y[parts == 1])
    calibrated = calibrator.predict(vote[parts == 2])
    threshold = float(max(np.linspace(.01, .99, 99), key=lambda t: f1_score(y[parts == 2], calibrated >= t)))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    artifact = output / "calibrator.joblib"; joblib.dump(calibrator, artifact)
    manifest = dict(lightgbm_weight=weight, threshold=threshold, calibration="isotonic", calibrator=artifact.name, calibrator_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(), objective="validation log loss for voting, independent threshold F1", partition_policy="domain sha256 mod 3: vote/calibrate/threshold", partition_counts={str(part): int((parts==part).sum()) for part in range(3)}, validation_metrics=metrics(y[parts == 2], calibrated, threshold), lightgbm_predictions_sha256=hashlib.sha256(Path(lightgbm_predictions).read_bytes()).hexdigest(), bert_predictions_sha256=hashlib.sha256(Path(bert_predictions).read_bytes()).hexdigest())
    manifest["fallbacks"] = {}
    for name, probabilities in (("lightgbm", lp), ("bert", bp)):
        fallback = IsotonicRegression(out_of_bounds="clip").fit(probabilities[parts == 1], y[parts == 1])
        fallback_p = fallback.predict(probabilities[parts == 2])
        fallback_threshold = float(max(np.linspace(.01, .99, 99), key=lambda t: f1_score(y[parts == 2], fallback_p >= t)))
        fallback_artifact = output / f"{name}_calibrator.joblib"
        joblib.dump(fallback, fallback_artifact)
        manifest["fallbacks"][name] = {"threshold": fallback_threshold, "artifact": fallback_artifact.name, "sha256": hashlib.sha256(fallback_artifact.read_bytes()).hexdigest(), "validation_metrics": metrics(y[parts == 2], fallback_p, fallback_threshold)}
    (output / "fusion.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("lightgbm_predictions"); parser.add_argument("bert_predictions"); parser.add_argument("output")
    args=parser.parse_args(); print(json.dumps(tune(args.lightgbm_predictions,args.bert_predictions,args.output),indent=2))
