import numpy as np
from models.image_deepfake.evaluation.metrics import compute_evaluation_metrics, compute_eer

def test_evaluation_metrics_computation():
    y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1])
    y_pred_prob = np.array([0.1, 0.2, 0.85, 0.9, 0.3, 0.75, 0.4, 0.95])
    
    metrics = compute_evaluation_metrics(y_true, y_pred_prob)
    
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert "auc_roc" in metrics
    assert "equal_error_rate" in metrics
    assert metrics["accuracy"] == 1.0
    assert metrics["auc_roc"] == 1.0
    assert metrics["equal_error_rate"] == 0.0
