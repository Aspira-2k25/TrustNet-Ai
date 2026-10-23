"""Optional generated explanations must not become classifier votes."""
import io
from unittest.mock import patch
from PIL import Image
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector

def create_dummy_jpeg():
    stream=io.BytesIO();Image.new('RGB',(128,128),(30,60,180)).save(stream,format='JPEG')
    return stream.getvalue()

def test_lm_studio_observation_is_advisory():
    detector=EfficientNetDetector(enable_explainability=False, policy='image-screening-v2')
    vote={'is_hf_applied':True,'hf_risk_score':5,'model_name':'test-vote'}
    vision={'status':'APPLIED','model_name':'fixture-vision','visual_verdict':'suspicious',
            'confidence':.99,'simple_explanation':'Unverified visual suspicion.'}
    with patch.object(detector.hf_client,'predict',return_value=vote):
        baseline=detector.predict(create_dummy_jpeg())
        with patch.object(detector.lm_studio_client,'analyze',return_value=vision):
            explained=detector.predict(create_dummy_jpeg(),enable_explanation=True)
    assert baseline.risk_score==explained.risk_score==5
    assert explained.status.value=='PARTIAL_SUCCESS'
    assert explained.metadata['lm_studio_status']=='APPLIED'
    assert explained.metadata['lm_studio_model']=='fixture-vision'
    assert explained.evidence==[]
    assert any('advisory' in reason for reason in explained.metadata['why_reasons'])

def test_lm_studio_unavailability_is_reported_without_fabricated_vote():
    detector=EfficientNetDetector(enable_explainability=False, policy='image-screening-v2')
    with patch.object(detector.hf_client,'predict',return_value={'is_hf_applied':True,'hf_risk_score':5}), patch.object(
        detector.lm_studio_client,'analyze',return_value={'status':'UNAVAILABLE','reason':'Vision unavailable'}):
        result=detector.predict(create_dummy_jpeg(),enable_explanation=True)
    item=next(a for a in result.analyzers if a['category']=='local_vision_reasoning')
    assert item['status']=='UNAVAILABLE' and item['reason']=='Vision unavailable'
    assert result.risk_score==5
