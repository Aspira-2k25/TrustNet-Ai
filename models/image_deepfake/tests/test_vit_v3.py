import io
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from PIL import Image
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from models.image_deepfake.inference.vit_policy import load_policy


def blob():
    stream = io.BytesIO(); Image.new('RGB', (160, 160), 'blue').save(stream, format='PNG')
    return stream.getvalue()


@pytest.fixture
def detector(monkeypatch):
    value = EfficientNetDetector(policy='image-vit-v3')
    monkeypatch.setattr(value.local_vit, '_get_pipeline', lambda: object())
    monkeypatch.setattr(value.face_analyzer, 'analyze', lambda _: {
        'status': 'APPLIED', 'localization_available': True, 'has_face': True,
        'face_count': 1, 'bounding_boxes': [[20, 20, 100, 100]], 'boundary_anomaly_score': .1})
    monkeypatch.setattr(value.local_vit, 'predict', lambda _: {'is_hf_applied': True, 'hf_risk_score': 95., 'model_name': 'fixture'})
    monkeypatch.setattr(value.local_vit, 'predict_views', lambda *args: {
        'face_predictions': [{'status': 'APPLIED', 'risk_score': 90.}],
        'full_frame_prediction': {'status': 'APPLIED', 'risk_score': .09},
        'view_coverage_complete': True})
    return value


def test_default_policy_uses_vit_not_cnn():
    value = EfficientNetDetector()
    assert value.policy == 'image-vit-v3' and value.cnn.model is None


def test_cnn_absence_is_not_missing_required_check(detector):
    result = detector.predict(blob())
    assert result.status.value == 'SUCCESS'
    assert result.risk_score == 90
    assert result.metadata['missing_required_checks'] == []
    assert result.verdict == 'UNCERTAIN'  # No fabricated validated operating point.
    assert result.metadata['decision_policy_validated'] is False
    assert result.metadata['model_views']['full_frame']['risk_score'] == .09


def test_out_of_scope_does_not_run_any_classifier(detector, monkeypatch):
    monkeypatch.setattr(detector.face_analyzer, 'analyze', lambda _: {
        'status': 'SKIPPED', 'localization_available': True, 'has_face': False,
        'bounding_boxes': [], 'boundary_anomaly_score': 0})
    predict = Mock(side_effect=AssertionError('must not run'))
    monkeypatch.setattr(detector.local_vit, 'predict', predict)
    result = detector.predict(blob())
    assert result.verdict == 'UNSUPPORTED'
    assert result.metadata['score_available'] is False
    assert result.metadata['hf_risk_score'] is None
    predict.assert_not_called()


def test_advisory_failure_does_not_gate_vit_coverage(detector, monkeypatch):
    monkeypatch.setattr(detector.ela_analyzer, 'analyze', lambda _: {'status': 'FAILED', 'ela_anomaly_score': 0})
    result = detector.predict(blob())
    assert result.status.value == 'SUCCESS'
    assert result.metadata['model_views']['coverage_complete'] is True
    assert 'ela' in result.metadata['advisory_unavailable']


def test_runtime_readiness_does_not_claim_decision_validation(detector, monkeypatch):
    monkeypatch.setattr(detector.local_vit, '_get_pipeline', lambda: object())
    state = detector.readiness()
    assert state['ready'] and not state['decision_policy_validated']
    assert 'trained_cnn' not in state


def test_bad_policy_is_explicitly_unvalidated(tmp_path):
    path = tmp_path/'policy.json'; path.write_text('{}')
    result = load_policy(path)
    assert not result['validated'] and 'unavailable' in result['reason']


def test_validated_face_policy_does_not_let_low_frame_cancel_face(detector, monkeypatch):
    import models.image_deepfake.inference.vit_policy as module
    detector.local_vit.processor_identity = {'sha256': 'fixture'}
    monkeypatch.setattr(module, 'load_policy', lambda **kwargs: {
        'validated': True, 'processor_sha256': 'fixture', 'low': 20, 'high': 80, 'reason': 'fixture'})
    result = detector.predict(blob())
    assert result.verdict == 'LIKELY_AI_MANIPULATED'
    assert result.risk_score == 90 and result.metadata['model_views']['full_frame']['risk_score'] == .09


def test_missing_diagnostic_frame_does_not_hide_complete_face_assessment(detector, monkeypatch):
    monkeypatch.setattr(detector.local_vit, 'predict_views', lambda *args: {
        'face_predictions': [{'status': 'APPLIED', 'risk_score': 90.}],
        'full_frame_prediction': {'status': 'UNAVAILABLE', 'risk_score': None}, 'view_coverage_complete': False})
    result = detector.predict(blob())
    assert result.status.value == 'SUCCESS'
    assert result.metadata['model_views']['coverage_complete'] is True
