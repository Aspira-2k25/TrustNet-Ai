"""Frozen hybrid test evaluation and branch/fallback ablation; no test tuning."""
import argparse
import csv
import json
from pathlib import Path
import time
import numpy as np
from models.phishing_url.inference.phishing_detector import PhishingDetector
from models.phishing_url.preprocessing.extract_features import extract_features
from models.phishing_url.evaluation.metrics import metrics

def evaluate(dataset, manifest, output):
    detector=PhishingDetector(manifest)
    if not hasattr(detector.model,"predict_url"):
        raise ValueError("Hybrid bundle required")
    with open(dataset,encoding="utf-8") as source:
        rows=[row for row in csv.DictReader(source) if row["split"]=="test"]
    labels, probs, lgbm, bert, durations=[],[],[],[],[]
    for index,row in enumerate(rows):
        start=time.monotonic()
        p,threshold,observation=detector.model.predict_url(row["url"],extract_features(row["url"]))
        if observation["configuration"]!="lightgbm_bert":
            raise RuntimeError("Both branches required for final evaluation")
        labels.append(int(row["label"]));probs.append(p)
        lgbm.append(observation["branch_probabilities"]["lightgbm"]);bert.append(observation["branch_probabilities"]["bert"])
        durations.append(1000*(time.monotonic()-start))
        if index%1000==0: print(json.dumps({"test_processed":index,"total":len(rows)}),flush=True)
    fusion=detector.model.fusion
    report={"test_rows":len(rows),"hybrid":metrics(labels,probs,threshold),"branches":{},"inference_ms":{"p50":float(np.percentile(durations,50)),"p95":float(np.percentile(durations,95))},"collection":"disabled; not included in latency","threshold_selected_on_test":False,"model_version":detector.manifest["model_version"]}
    for name,p in (("lightgbm",lgbm),("bert",bert)):
        calibrated=detector.model.fallbacks[name].predict(p)
        report["branches"][name]=metrics(labels,calibrated,fusion["fallbacks"][name]["threshold"])
    Path(output).write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
if __name__=="__main__":
    parser=argparse.ArgumentParser();[parser.add_argument(name) for name in ("dataset","manifest","output")];a=parser.parse_args();evaluate(a.dataset,a.manifest,a.output)
