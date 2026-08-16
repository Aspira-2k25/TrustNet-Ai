from typing import Dict, Any, List, Union
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    precision_recall_curve,
    auc as sklearn_auc,
    confusion_matrix as sklearn_confusion_matrix,
    log_loss,
    roc_curve
)

def compute_eer(y_true: Union[List[int], np.ndarray], y_pred_prob: Union[List[float], np.ndarray]) -> float:
    """Computes Equal Error Rate (EER) where FPR == FNR."""
    try:
        fpr, tpr, thresholds = roc_curve(y_true, y_pred_prob, pos_label=1)
        fnr = 1 - tpr
        eer_idx = np.nanargmin(np.absolute((fnr - fpr)))
        return float((fpr[eer_idx] + fnr[eer_idx]) / 2.0)
    except Exception:
        return 0.0

def compute_confusion_matrix(y_true: Union[List[int], np.ndarray], y_pred: Union[List[int], np.ndarray]) -> Dict[str, int]:
    """Computes standard binary confusion matrix breakdown."""
    try:
        cm = sklearn_confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        return {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        }
    except Exception:
        return {
            "true_negatives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "true_positives": 0
        }

def compute_roc_auc(y_true: Union[List[int], np.ndarray], y_scores: Union[List[float], np.ndarray]) -> float:
    """Computes ROC-AUC score with safety fallbacks."""
    try:
        return float(roc_auc_score(y_true, y_scores))
    except Exception:
        return 0.5

def compute_pr_auc(y_true: Union[List[int], np.ndarray], y_scores: Union[List[float], np.ndarray]) -> float:
    """Computes Precision-Recall AUC score."""
    try:
        precision, recall, _ = precision_recall_curve(y_true, y_scores)
        return float(sklearn_auc(recall, precision))
    except Exception:
        return 0.5

def compute_evaluation_metrics(y_true: np.ndarray, y_pred_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    """
    Computes standard computer vision forensics evaluation metrics.
    
    Args:
        y_true: Array of ground truth labels (0 for Real, 1 for Fake).
        y_pred_prob: Array of predicted probabilities for the positive/fake class.
        threshold: Decision threshold for discrete classification.
        
    Returns:
        Dict[str, float] with accuracy, precision, recall, f1, auc_roc, log_loss, eer.
    """
    y_true = np.array(y_true)
    y_pred_prob = np.array(y_pred_prob)
    y_pred = (y_pred_prob >= threshold).astype(int)

    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    auc = compute_roc_auc(y_true, y_pred_prob)

    try:
        loss = float(log_loss(y_true, y_pred_prob, eps=1e-7))
    except Exception:
        loss = 0.0

    eer = compute_eer(y_true, y_pred_prob)

    cm = compute_confusion_matrix(y_true, y_pred)
    tn = cm["true_negatives"]
    fp = cm["false_positives"]
    fn = cm["false_negatives"]
    tp = cm["true_positives"]

    spec = tn / max(1, (tn + fp))
    fpr = fp / max(1, (fp + tn))
    fnr = fn / max(1, (fn + tp))
    pr_auc = compute_pr_auc(y_true, y_pred_prob)

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "recall_sensitivity": round(rec, 4),
        "specificity": round(spec, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "auc_roc": round(auc, 4),
        "auc": round(auc, 4),
        "pr_auc": round(pr_auc, 4),
        "log_loss": round(loss, 4),
        "equal_error_rate": round(eer, 4)
    }

calculate_metrics = compute_evaluation_metrics
