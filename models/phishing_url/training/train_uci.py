"""Offline UCI LR/RF experiment; never promoted as raw-URL inference."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from models.phishing_url.evaluation.metrics import metrics

def train(archive, output, phishing_label):
    with zipfile.ZipFile(archive) as source:
        raw = source.read("Training Dataset.arff")
    data = re.split(r"(?im)^@data\s*$", raw.decode(), maxsplit=1)[1]
    records = [tuple(map(int, line.split(","))) for line in data.splitlines() if line.strip()]
    grouped = defaultdict(set)
    for record in records:
        grouped[record[:-1]].add(record[-1])
    clean = [(features, next(iter(labels))) for features, labels in sorted(grouped.items()) if len(labels) == 1]
    x = np.array([row[0] for row in clean]); y = np.array([int(row[1] == phishing_label) for row in clean])
    development, test = train_test_split(np.arange(len(clean)), test_size=.2, random_state=42, stratify=y)
    report = {"dataset": "uci-327", "archive_sha256": hashlib.sha256(Path(archive).read_bytes()).hexdigest(), "label_mapping": {str(phishing_label): "phishing", str(-phishing_label): "legitimate"}, "label_mapping_evidence": "Explicit caller argument; compare dataset author dictionary or research source before interpretation", "original_rows": len(records), "unique_unambiguous_vectors": len(clean), "conflicting_vectors_excluded": sum(len(labels)>1 for labels in grouped.values()), "seed": 42, "split_sha256": hashlib.sha256(json.dumps({"development":development.tolist(),"test":test.tolist()}).encode()).hexdigest(), "limitation": "No URL/domain/timestamps; feature-disjoint evaluation cannot establish domain or temporal generalization", "models": {}}
    models = {"lr": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42)), "rf": RandomForestClassifier(n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=4)}
    for name, model in models.items():
        cv = cross_validate(model, x[development], y[development], cv=StratifiedKFold(n_splits=10, shuffle=True, random_state=43), scoring=["accuracy", "precision", "recall", "f1", "roc_auc"], n_jobs=1)
        model.fit(x[development], y[development])
        p = model.predict_proba(x[test])[:, 1]
        report["models"][name] = {"development_10fold": {key:{"mean":float(values.mean()),"std":float(values.std())} for key,values in cv.items() if key.startswith("test_")}, "test":metrics(y[test],p), "threshold":.5}
    output = Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("archive"); p.add_argument("output"); p.add_argument("--phishing-label",type=int,required=True,choices=[-1,1]); a=p.parse_args(); print(json.dumps(train(a.archive,a.output,a.phishing_label),indent=2))
