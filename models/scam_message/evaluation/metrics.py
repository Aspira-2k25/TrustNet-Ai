"""Shared offline evaluation; abstentions remain in the measured population."""
import math
import numpy as np
from sklearn.metrics import (accuracy_score, average_precision_score,
                             brier_score_loss, classification_report,
                             confusion_matrix, f1_score, log_loss)

LABELS = ['ham', 'smishing', 'spam']


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - radius), min(1, center + radius)]


def evaluate(y, probabilities, threshold, abstained=None, promotional=None, outside=None):
    y = np.asarray(y, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    if p.shape != (len(y), 3) or not np.isfinite(p).all() or not np.allclose(p.sum(1), 1, atol=1e-5):
        raise ValueError('Expected finite normalized three-class probabilities')
    if (p < 0).any() or (p > 1).any() or not np.isin(y, [0, 1, 2]).all() or not 0 < threshold < 1:
        raise ValueError('Invalid labels, probabilities or threshold')
    absent = np.zeros(len(y), dtype=bool) if abstained is None else np.asarray(abstained, dtype=bool)
    if absent.shape != y.shape:
        raise ValueError('Abstention mask must match the population')
    outside = np.zeros(len(y), dtype=bool) if outside is None else np.asarray(outside, dtype=bool)
    if outside.shape != y.shape:
        raise ValueError('Domain mask must match the population')
    predicted = p.argmax(1)
    fraud = y == 1
    alert = p[:, 1] >= threshold
    absent = absent | (outside & ~alert)
    suspicious = ~absent & (outside | (p.max(1) < .65) | (alert & (p[:, 1] < .5)))
    likely = ~absent & ~suspicious & (p[:, 1] >= max(.5, threshold))
    low_signal = ~absent & ~suspicious & ~likely
    def rate(mask, outcome):
        total = int(mask.sum())
        successes = int(outcome[mask].sum())
        return {'value': successes / total if total else None, 'n': total,
                'successes': successes, 'wilson_95': wilson(successes, total)}
    bins = np.minimum((p[:, 1] * 10).astype(int), 9)
    ece = sum(np.mean(bins == b) * abs(np.mean(p[bins == b, 1]) - np.mean(fraud[bins == b]))
              for b in range(10) if (bins == b).any())
    promotion = np.zeros(len(y), dtype=bool) if promotional is None else np.asarray(promotional, dtype=bool)
    if promotion.shape != y.shape or (promotion & (y != 0)).any():
        raise ValueError('Promotional false positives require annotated legitimate promotion')
    return {
        'n': len(y), 'labels': LABELS, 'class_counts': np.bincount(y, minlength=3).tolist(),
        'scope': 'Fraud-only populations establish positive recall, not precision, false-positive rates or overall reliability' if len(set(y)) == 1 else 'All labelled examples retained, including abstentions',
        'accuracy': float(accuracy_score(y, predicted)),
        'macro_f1': float(f1_score(y, predicted, labels=[0, 1, 2], average='macro', zero_division=0)) if len(set(y)) > 1 else None,
        'per_class': classification_report(y, predicted, labels=[0, 1, 2], target_names=LABELS, output_dict=True, zero_division=0),
        'confusion_matrix': confusion_matrix(y, predicted, labels=[0, 1, 2]).tolist(),
        'fraud_argmax_recall': rate(fraud, predicted == 1),
        'fraud_alert_recall': rate(fraud, alert),
        'fraud_high_probability_recall': rate(fraud, p[:, 1] >= max(.5, threshold)),
        'fraud_false_negative_rate': rate(fraud, ~alert),
        'legitimate_fpr': rate(y == 0, alert), 'spam_fpr': rate(y == 2, alert),
        'promotional_fpr': rate(promotion, alert),
        'fraud_pr_auc': float(average_precision_score(fraud, p[:, 1])) if len(set(fraud)) == 2 else None,
        'fraud_brier': float(brier_score_loss(fraud, p[:, 1])),
        'log_loss': float(log_loss(y, p, labels=[0, 1, 2])), 'fraud_ece_10_bins': float(ece),
        'threshold': threshold, 'abstained': int(absent.sum()), 'coverage': float(1 - absent.mean()),
        'operational_fraud_alert_recall': rate(fraud, alert & ~absent),
        'presentation': {'definition': 'Actual enrichment policy: unsupported/insufficient or low out-of-domain probability abstains; confidence below .65 reviews; likely requires positive probability >=max(.5,threshold) and remaining confidence/domain checks. Uncertainty-only reviews are not counted as detected fraud.',
                         'counts': {'LIKELY_SCAM': int(likely.sum()), 'SUSPICIOUS': int(suspicious.sum()),
                                    'UNABLE_TO_ASSESS': int(absent.sum()), 'NO_STRONG_INDICATORS': int(low_signal.sum())},
                         'fraud_likely_scam_recall': rate(fraud, likely),
                         'fraud_threshold_qualified_suspicious_recall': rate(fraud, suspicious & alert),
                         'fraud_uncertainty_only_reviews': rate(fraud, suspicious & ~alert)},
    }
