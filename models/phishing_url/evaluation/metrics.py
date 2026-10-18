"""Binary probability metrics with explicit calibration and latency conventions."""
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, brier_score_loss, confusion_matrix

def metrics(y, p, threshold=.5):
    y, p = np.asarray(y), np.asarray(p)
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Probabilities must be finite and bounded")
    tn, fp, fn, tp = confusion_matrix(y, p >= threshold, labels=[0, 1]).ravel()
    ece = 0.
    for lo, hi in zip(np.linspace(0, 1, 11)[:-1], np.linspace(0, 1, 11)[1:]):
        selected = (p >= lo) & ((p < hi) if hi < 1 else (p <= hi))
        if selected.any():
            ece += selected.mean() * abs(p[selected].mean() - y[selected].mean())
    return dict(accuracy=float(accuracy_score(y, p >= threshold)), precision=float(precision_score(y, p >= threshold, zero_division=0)), recall=float(recall_score(y, p >= threshold, zero_division=0)), f1=float(f1_score(y, p >= threshold, zero_division=0)), roc_auc=float(roc_auc_score(y, p)), pr_auc=float(average_precision_score(y, p)), brier=float(brier_score_loss(y, p)), ece=float(ece), fpr=float(fp / (fp + tn)) if fp + tn else None, fnr=float(fn / (fn + tp)) if fn + tp else None, specificity=float(tn / (tn + fp)) if tn + fp else None, confusion_matrix=[[int(tn), int(fp)], [int(fn), int(tp)]])
