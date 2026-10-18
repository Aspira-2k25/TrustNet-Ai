"""Train the lexical LightGBM branch on the frozen primary partitions."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
from lightgbm import LGBMClassifier, early_stopping
from models.phishing_url.preprocessing.extract_features import FEATURE_NAMES, extract_features
from models.phishing_url.preprocessing.url_parser import PREPROCESSING_VERSION
from models.phishing_url.evaluation.metrics import metrics

def train(dataset, output):
    from models.phishing_url.training.train_baselines import load_rows
    rows = load_rows(dataset)
    data = {}
    for split in ("train", "validation", "test"):
        selected = [r for r in rows if r["split"] == split]
        data[split] = (np.asarray([list(extract_features(r["url"]).values()) for r in selected], dtype=np.float32), np.asarray([int(r["label"]) for r in selected]))
    model = LGBMClassifier(n_estimators=1000, learning_rate=.05, num_leaves=31, min_child_samples=30, reg_lambda=1, random_state=42, n_jobs=4, verbosity=-1)
    validation_rows = [r for r in rows if r["split"] == "validation"]
    selection = np.array([int(hashlib.sha256(r["domain_group"].encode()).hexdigest()[:8],16)%3 == 0 for r in validation_rows])
    vx, vy = data["validation"]
    if set(vy[selection]) != {0,1}:
        raise ValueError("Selection validation must contain both classes")
    model.fit(*data["train"], eval_set=[(vx[selection],vy[selection])], callbacks=[early_stopping(30, verbose=False)])
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    artifact = out / "lightgbm.joblib"
    joblib.dump(model, artifact)
    manifest = dict(detector_id="phishing.lightgbm.lexical.v1", model_version="lightgbm-v1", preprocessing_version=PREPROCESSING_VERSION, feature_names=list(FEATURE_NAMES), threshold=.5, artifact=artifact.name, sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(), dataset_sha256=hashlib.sha256(Path(dataset).read_bytes()).hexdigest(), calibrated=False, metadata_features_used=False, best_iteration=model.best_iteration_, metrics={})
    # Do not use test predictions until fusion/calibration are frozen.
    for split in ("validation",):
        x, y = data[split]
        p = model.predict_proba(x)[:, 1]
        manifest["metrics"][split] = metrics(y, p)
        selected = [r for r in rows if r["split"] == split]
        with (out / f"{split}_predictions.csv").open("w", newline="", encoding="utf-8") as target:
            writer = csv.writer(target)
            writer.writerow(["url", "domain_group", "label", "probability"])
            writer.writerows((r["url"], r["domain_group"], r["label"], float(prob)) for r, prob in zip(selected, p))
    (out / "lightgbm.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(train(args.dataset, args.output), indent=2))
