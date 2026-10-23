from shared.schemas.detection_result import DetectionResult
from services.trust_engine.app.services.fusion_engine import FusionEngine

def test_partial_image_stays_partial_and_confidence_unavailable():
    result=DetectionResult(scan_id='fixture',module='image_deepfake',detector_id='fixture',model_version='v2',
        preprocessing_version='v2',native_score=.91,native_score_semantics='anomaly_score',risk_score=91,
        confidence=0,status='PARTIAL_SUCCESS',label='uncertain',verdict='UNCERTAIN',timestamp='2026-10-20T00:00:00Z',
        metadata={'assessment_policy':'image-screening-v2','confidence_available':False,'is_contradiction':True})
    fused=FusionEngine().fuse([result])
    assert fused.status=='PARTIAL_SUCCESS'
    assert fused.trust_risk_score==91
    assert fused.contradiction_flag is True
    assert fused.risk_level.value == 'UNKNOWN'
    assert fused.metadata['confidence_available'] is False
    assert 'confidence: 0%' not in fused.explanation


def test_vit_unsupported_has_no_numeric_trust_score():
    result=DetectionResult(scan_id='fixture',module='image_deepfake',detector_id='vit',model_version='v3',
        preprocessing_version='v3',native_score=0,native_score_semantics='anomaly_score',risk_score=0,
        confidence=0,status='PARTIAL_SUCCESS',label='unknown',verdict='UNSUPPORTED',timestamp='2026-10-20T00:00:00Z',
        explanation='No assessable face.', metadata={'assessment_policy':'image-vit-v3','score_available':False})
    fused=FusionEngine().fuse([result])
    assert fused.trust_risk_score is None
    assert fused.status=='PARTIAL_SUCCESS' and fused.risk_level.value=='UNKNOWN'
