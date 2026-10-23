"""Regression contracts for degraded localization and conflicting model views."""
import io
from unittest.mock import patch

from PIL import Image
import pytest

from models.image_deepfake.forensics.face_analyzer import FaceAnalyzer
from models.image_deepfake.inference.local_vit_detector import LocalViTDeepfakeDetector


def image_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (400, 500), (180, 130, 90)).save(buffer, format='PNG')
    return buffer.getvalue()


def fake_result(score):
    return {'is_hf_applied': True, 'hf_risk_score': score,
            'hf_label': 'fake' if score >= 50 else 'real',
            'hf_confidence': 0.99, 'model_name': 'test-model'}


def test_missing_cascades_never_turns_skin_regions_into_faces():
    analyzer = FaceAnalyzer()
    analyzer.cascades = []
    result = analyzer.analyze(image_bytes())
    assert result['status'] == 'UNAVAILABLE'
    assert result['has_face'] is False
    assert result['bounding_boxes'] == []
    assert result['localization_available'] is False


def test_conflicting_face_and_frame_predictions_are_preserved():
    detector = LocalViTDeepfakeDetector()
    full = fake_result(0.1)
    with patch.object(detector, 'predict', return_value=fake_result(95)) as predict:
        result = detector.predict_views(image_bytes(), [(100, 100, 160, 180)], full)
    assert result['hf_risk_score'] == 95
    assert result['model_view_disagreement'] is True
    assert result['full_frame_prediction']['risk_score'] == 0.1
    assert result['face_predictions'][0]['risk_score'] == 95
    assert result['face_predictions'][0]['box'] == [100, 100, 160, 180]
    assert predict.call_count == 1
    assert Image.open(io.BytesIO(predict.call_args.args[0])).size == (160, 180)


def test_consistently_low_views_do_not_create_synthetic_alert():
    detector = LocalViTDeepfakeDetector()
    with patch.object(detector, 'predict', return_value=fake_result(2)):
        result = detector.predict_views(image_bytes(), [(100, 100, 160, 180)], fake_result(3))
    assert result['hf_risk_score'] == 3
    assert result['model_view_disagreement'] is False


def test_unavailable_face_classifier_is_not_a_zero_risk_vote():
    detector = LocalViTDeepfakeDetector()
    with patch.object(detector, 'predict', return_value={'is_hf_applied': False, 'note': 'missing model'}):
        result = detector.predict_views(image_bytes(), [(100, 100, 160, 180)], fake_result(2))
    assert result['view_coverage_complete'] is False
    assert result['face_predictions'][0]['risk_score'] is None
    assert result['hf_risk_score'] == 2


@pytest.mark.parametrize('boxes', [[(-1, 0, 100, 100)], [(0, 0, 1000, 1000)], [(0, 0, 0, 100)]])
def test_invalid_boxes_are_rejected_without_cropping(boxes):
    detector = LocalViTDeepfakeDetector()
    with patch.object(detector, 'predict') as predict:
        result = detector.predict_views(image_bytes(), boxes, fake_result(2))
    assert not predict.called
    assert result['view_coverage_complete'] is False


def test_face_inference_is_bounded_and_prioritizes_largest_regions():
    detector = LocalViTDeepfakeDetector()
    boxes = [(i * 10, i * 10, 60 + i, 60 + i) for i in range(8)]
    with patch.object(detector, 'predict', return_value=fake_result(3)) as predict:
        result = detector.predict_views(image_bytes(), boxes, fake_result(2))
    assert predict.call_count == 4
    assert result['face_predictions'][0]['box'] == list(boxes[-1])
    assert result['view_coverage_complete'] is False


@pytest.mark.parametrize('score', [float('nan'), float('inf'), -1, 101, None])
def test_invalid_face_scores_are_unavailable(score):
    detector = LocalViTDeepfakeDetector()
    with patch.object(detector, 'predict', return_value={'is_hf_applied': True, 'hf_risk_score': score}):
        result = detector.predict_views(image_bytes(), [(100, 100, 160, 180)], fake_result(2))
    assert result['face_predictions'][0]['risk_score'] is None
    assert result['view_coverage_complete'] is False


def test_missing_detected_boxes_cannot_claim_complete_face_coverage():
    result = LocalViTDeepfakeDetector().predict_views(image_bytes(), [], fake_result(2))
    assert result['view_coverage_complete'] is False
