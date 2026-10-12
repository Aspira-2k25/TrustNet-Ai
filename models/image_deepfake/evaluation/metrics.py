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
    if len(set(y_true)) < 2:
        return None
    try:
        fpr, tpr, thresholds = roc_curve(y_true, y_pred_prob, pos_label=1)
        fnr = 1 - tpr
        eer_idx = np.nanargmin(np.absolute((fnr - fpr)))
        return float((fpr[eer_idx] + fnr[eer_idx]) / 2.0)
    except Exception:
        return None

def compute_confusion_matrix(y_true: Union[List[int], np.ndarray], y_pred: Union[List[int], np.ndarray]) -> Dict[str, int]:
    """Computes standard binary confusion matrix breakdown."""
    actual, predicted = np.asarray(y_true), np.asarray(y_pred)
    if actual.ndim != 1 or predicted.ndim != 1 or not len(actual) or actual.shape != predicted.shape or not set(actual).issubset({0, 1}) or not set(predicted).issubset({0, 1}):
        raise ValueError("Invalid binary confusion matrix inputs")
    try:
        cm = sklearn_confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        return {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        }
    except Exception as exc:
        raise ValueError("Confusion matrix unavailable: invalid inputs") from exc


def compute_roc_auc(y_true: Union[List[int], np.ndarray], y_scores: Union[List[float], np.ndarray]) -> float:
    """Computes ROC-AUC score with safety fallbacks."""
    if len(set(y_true)) < 2:
        return None
    try:
        return float(roc_auc_score(y_true, y_scores))
    except Exception:
        return None

def compute_pr_auc(y_true: Union[List[int], np.ndarray], y_scores: Union[List[float], np.ndarray]) -> float:
    """Computes Precision-Recall AUC score."""
    if not np.any(np.asarray(y_true) == 1):
        return None
    try:
        precision, recall, _ = precision_recall_curve(y_true, y_scores)
        return float(sklearn_auc(recall, precision))
    except Exception:
        return None

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
    if y_true.ndim != 1 or not 0 <= threshold <= 1 or not len(y_true) or y_true.shape != y_pred_prob.shape or not np.isfinite(y_pred_prob).all() or np.any((y_pred_prob < 0) | (y_pred_prob > 1)) or not set(y_true).issubset({0, 1}):
        raise ValueError("Invalid binary evaluation inputs")
    y_pred = (y_pred_prob >= threshold).astype(int)

    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    auc = compute_roc_auc(y_true, y_pred_prob)

    try:
        loss = float(log_loss(y_true, y_pred_prob, labels=[0, 1]))
    except Exception:
        loss = None

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
        "precision": round(prec, 4) if np.any(y_pred == 1) else None,
        "recall": round(rec, 4) if np.any(y_true == 1) else None,
        "recall_sensitivity": round(rec, 4) if np.any(y_true == 1) else None,
        "specificity": round(spec, 4) if tn + fp else None,
        "f1_score": round(f1, 4) if tp + fp + fn else None,
        "false_positive_rate": round(fpr, 4) if tn + fp else None,
        "false_negative_rate": round(fnr, 4) if fn + tp else None,
        "auc_roc": round(auc, 4) if auc is not None and np.isfinite(auc) else None,
        "auc": round(auc, 4) if auc is not None and np.isfinite(auc) else None,
        "pr_auc": round(pr_auc, 4) if pr_auc is not None and np.isfinite(pr_auc) else None,
        "log_loss": round(loss, 4) if loss is not None and np.isfinite(loss) else None,
        "equal_error_rate": round(eer, 4) if eer is not None and np.isfinite(eer) else None
    }

calculate_metrics = compute_evaluation_metrics
