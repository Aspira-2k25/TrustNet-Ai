"""Train raw-URL LR/RF baselines on explicitly domain-grouped CSV partitions.

CSV columns: url,label,domain_group,split; label is 0=legitimate/1=phishing;
split is train/validation/test. domain_group must be computed with a pinned PSL.
Usage: python -m models.phishing_url.training.train_baselines data.csv output
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from models.phishing_url.preprocessing.extract_features import FEATURE_NAMES, extract_features
from models.phishing_url.preprocessing.url_parser import PREPROCESSING_VERSION

def load_rows(path):
    with open(path, encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    groups, urls = {}, set()
    for row in rows:
        if row.get("label") not in {"0", "1"} or row.get("split") not in {"train", "validation", "test"}:
            raise ValueError("Explicit binary labels and train/validation/test splits required")
        group = row.get("domain_group", "").strip()
        if not group or groups.setdefault(group, row["split"]) != row["split"]:
            raise ValueError("Missing domain group or domain leakage between partitions")
        if row["url"] in urls:
            raise ValueError("Duplicate URL; reconcile duplicates and conflicting labels first")
        urls.add(row["url"])
        extract_features(row["url"])
    for split in ("train", "validation", "test"):
        if {r["label"] for r in rows if r["split"] == split} != {"0", "1"}:
            raise ValueError(f"{split} must contain both classes")
    return rows

def train(path, output):
    import joblib
    import numpy as np
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, brier_score_loss, confusion_matrix
    rows = load_rows(path)
    partitions = {}
    for split in ("train", "validation", "test"):
        selected = [r for r in rows if r["split"] == split]
        partitions[split] = (np.array([list(extract_features(r["url"]).values()) for r in selected]), np.array([int(r["label"]) for r in selected]))
    models = {"lr": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42)),
              "rf": RandomForestClassifier(n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=-1)}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, model in models.items():
        model.fit(*partitions["train"])
        x, y = partitions["validation"]
        probabilities = model.predict_proba(x)[:, list(model.classes_).index(1)]
        threshold = max(np.linspace(.05, .95, 91), key=lambda t: f1_score(y, probabilities >= t))
        metrics = {}
        for split in ("validation", "test"):
            x, y = partitions[split]
            p = model.predict_proba(x)[:, list(model.classes_).index(1)]
            predictions = p >= threshold
            metrics[split] = dict(accuracy=accuracy_score(y, predictions), precision=precision_score(y, predictions, zero_division=0), recall=recall_score(y, predictions), f1=f1_score(y, predictions), roc_auc=roc_auc_score(y, p), pr_auc=average_precision_score(y, p), brier=brier_score_loss(y, p), confusion_matrix=confusion_matrix(y, predictions).tolist())
        artifact = output / f"{name}.joblib"
        joblib.dump(model, artifact)
        manifest = dict(detector_id=f"phishing.{name}.lexical.v1", model_version="baseline-v1", preprocessing_version=PREPROCESSING_VERSION, feature_names=list(FEATURE_NAMES), threshold=float(threshold), artifact=artifact.name, sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(), dataset_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(), calibrated=False, metrics=metrics)
        (output / f"{name}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        report[name] = metrics
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(train(args.dataset, args.output), indent=2))
