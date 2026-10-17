"""Assemble only trained, matching-split branches into a checked hybrid bundle."""
import argparse
import json
from pathlib import Path
import shutil
import hashlib
from models.phishing_url.preprocessing.extract_features import FEATURE_NAMES
from models.phishing_url.preprocessing.url_parser import PREPROCESSING_VERSION

def build(lightgbm, bert, fusion, output):
    lightgbm, bert, fusion, output = map(Path, (lightgbm, bert, fusion, output))
    left = json.loads((lightgbm / "lightgbm.json").read_text())
    right = json.loads((bert / "bert_manifest.json").read_text())
    vote = json.loads((fusion / "fusion.json").read_text())
    if left["dataset_sha256"] != right["dataset_sha256"] or not right["full_training_partition"]:
        raise ValueError("Hybrid requires matching full training partitions")
    if vote["lightgbm_predictions_sha256"] != hashlib.sha256((lightgbm/"validation_predictions.csv").read_bytes()).hexdigest() or vote["bert_predictions_sha256"] != hashlib.sha256((bert/"validation_predictions.csv").read_bytes()).hexdigest():
        raise ValueError("Fusion does not match the branch prediction files")
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(lightgbm / left["artifact"], output / left["artifact"])
    shutil.copytree(bert / "bert", output / "bert", dirs_exist_ok=True)
    for entry in [vote["calibrator"]] + [item["artifact"] for item in vote["fallbacks"].values()]:
        shutil.copy2(fusion / entry, output / entry)
    manifest = dict(kind="lightgbm_bert", detector_id="phishing.lgbm_bert.v1", model_version="hybrid-v1", preprocessing_version=PREPROCESSING_VERSION, feature_names=list(FEATURE_NAMES), threshold=vote["threshold"], calibrated=True, lightgbm=left, bert=right, fusion=vote)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

if __name__ == "__main__":
    p=argparse.ArgumentParser(); [p.add_argument(name) for name in ("lightgbm","bert","fusion","output")]; a=p.parse_args(); build(a.lightgbm,a.bert,a.fusion,a.output)
