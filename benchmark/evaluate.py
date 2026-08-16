"""
TrustNet AI — Forensic Benchmark & Model Evaluation Engine.

Evaluates multi-signal detector performance against labelled real and synthetic/deepfake datasets.
Computes standard statistical metrics:
- Accuracy, Precision, Recall (Sensitivity), Specificity, F1-Score
- False Positive Rate (FPR), False Negative Rate (FNR)
- ROC-AUC and PR-AUC
- Confusion Matrix [[TN, FP], [FN, TP]]

Usage:
    python benchmark/evaluate.py --dataset-dir /path/to/dataset
    python benchmark/evaluate.py --manifest /path/to/manifest.json
"""

import os
import sys
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np

# Ensure workspace root is in python path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from models.image_deepfake.evaluation.metrics import (
    compute_confusion_matrix,
    compute_roc_auc,
    compute_pr_auc
)

def evaluate_dataset(dataset_dir: str, threshold: float = 50.0) -> Dict[str, Any]:
    dataset_path = Path(dataset_dir)
    real_dir = dataset_path / "real"
    fake_dir = dataset_path / "fake"

    if not real_dir.exists() or not fake_dir.exists():
        return {
            "status": "PENDING",
            "message": f"Benchmark pending — labelled evaluation dataset not currently available at '{dataset_dir}'. Expected 'real/' and 'fake/' subdirectories."
        }

    supported_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    real_files = [f for f in real_dir.iterdir() if f.suffix.lower() in supported_exts]
    fake_files = [f for f in fake_dir.iterdir() if f.suffix.lower() in supported_exts]

    if not real_files and not fake_files:
        return {
            "status": "PENDING",
            "message": "Benchmark pending — labelled evaluation dataset contains 0 supported images."
        }

    print(f"Loading TrustNet EfficientNetDetector...")
    detector = EfficientNetDetector(enable_explainability=False)

    y_true: List[int] = []
    y_pred: List[int] = []
    y_scores: List[float] = []
    records: List[Dict[str, Any]] = []

    start_eval_time = time.time()

    # Process REAL images (Ground truth label = 0)
    for file_path in real_files:
        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            res = detector.predict(img_bytes)
            risk = res.risk_score
            pred = 1 if risk >= threshold else 0

            y_true.append(0)
            y_pred.append(pred)
            y_scores.append(risk / 100.0)
            records.append({
                "file": file_path.name,
                "ground_truth": "REAL",
                "predicted_label": res.label,
                "risk_score": res.risk_score,
                "confidence": res.confidence,
                "verdict": res.verdict
            })
        except Exception as e:
            print(f"Error processing real image {file_path.name}: {e}")

    # Process FAKE / SYNTHETIC images (Ground truth label = 1)
    for file_path in fake_files:
        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            res = detector.predict(img_bytes)
            risk = res.risk_score
            pred = 1 if risk >= threshold else 0

            y_true.append(1)
            y_pred.append(pred)
            y_scores.append(risk / 100.0)
            records.append({
                "file": file_path.name,
                "ground_truth": "FAKE",
                "predicted_label": res.label,
                "risk_score": res.risk_score,
                "confidence": res.confidence,
                "verdict": res.verdict
            })
        except Exception as e:
            print(f"Error processing fake image {file_path.name}: {e}")

    total_time = time.time() - start_eval_time
    total_samples = len(y_true)

    # Compute Confusion Matrix
    cm = compute_confusion_matrix(y_true, y_pred)
    tn = cm["true_negatives"]
    fp = cm["false_positives"]
    fn = cm["false_negatives"]
    tp = cm["true_positives"]

    # Compute Statistical Metrics
    accuracy = (tp + tn) / max(1, total_samples)
    precision = tp / max(1, (tp + fp))
    recall = tp / max(1, (tp + fn))
    specificity = tn / max(1, (tn + fp))
    f1 = (2 * precision * recall) / max(1e-6, (precision + recall))
    fpr = fp / max(1, (fp + tn))
    fnr = fn / max(1, (fn + tp))

    roc_auc = compute_roc_auc(y_true, y_scores)
    pr_auc = compute_pr_auc(y_true, y_scores)

    report = {
        "status": "COMPLETED",
        "dataset_path": str(dataset_path),
        "total_samples": total_samples,
        "real_count": len(real_files),
        "fake_count": len(fake_files),
        "processing_time_sec": round(total_time, 2),
        "avg_time_per_image_ms": round((total_time / max(1, total_samples)) * 1000, 2),
        "metrics": {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall_sensitivity": round(recall, 4),
            "specificity": round(specificity, 4),
            "f1_score": round(f1, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4)
        },
        "confusion_matrix": {
            "true_negatives_real_correct": tn,
            "false_positives_real_as_fake": fp,
            "false_negatives_fake_as_real": fn,
            "true_positives_fake_correct": tp
        }
    }

    return report

def main():
    parser = argparse.ArgumentParser(description="TrustNet Model Evaluation & Benchmark CLI")
    parser.add_argument("--dataset-dir", type=str, default="dataset", help="Path to evaluation dataset root folder")
    parser.add_argument("--threshold", type=float, default=50.0, help="Risk score decision threshold (0-100)")
    args = parser.parse_args()

    print("=" * 70)
    print("TRUSTNET AI FORENSIC BENCHMARK EVALUATION ENGINE")
    print("=" * 70)

    report = evaluate_dataset(args.dataset_dir, threshold=args.threshold)

    if report["status"] == "PENDING":
        print(f"\nSTATUS: {report['message']}")
        print("\nTo benchmark on an external labelled evaluation set:")
        print("1. Organize your evaluation dataset with subdirectories: '<dataset_dir>/real/' and '<dataset_dir>/fake/'")
        print("2. Run: python benchmark/evaluate.py --dataset-dir <path_to_dataset>")
    else:
        print(f"\nDataset: {report['dataset_path']} ({report['total_samples']} images)")
        print(f"Time: {report['processing_time_sec']}s ({report['avg_time_per_image_ms']}ms / image)")
        print("\n--- METRICS ---")
        for k, v in report["metrics"].items():
            print(f"  {k:<22}: {v}")
        print("\n--- CONFUSION MATRIX ---")
        for k, v in report["confusion_matrix"].items():
            print(f"  {k:<30}: {v}")

        # Save detailed per-image report
        import json
        out_json = Path("benchmark_results.json")
        with open(out_json, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed evaluation results saved to: {out_json.resolve()}")

if __name__ == "__main__":
    main()
