"""Failure and contract tests. Mocked votes are not detection accuracy evidence."""
import io
import hashlib
from types import SimpleNamespace
from unittest.mock import patch
import pytest
import torch
from PIL import Image
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from models.image_deepfake.inference.classifier_contract import parse_binary_predictions
from models.image_deepfake.preprocessing.transforms import process_image_bytes
from models.image_deepfake.preprocessing.validator import ImageValidator

def blob():
    stream = io.BytesIO()
    Image.new('RGB', (128,128), (30,60,180)).save(stream, format='JPEG')
    return stream.getvalue()

@pytest.fixture
def detector():
    value = EfficientNetDetector(enable_explainability=False, policy='image-screening-v2')
    value.cnn = SimpleNamespace(ready=True, error=None, manifest={'scope':'general_image'},
        predict=lambda data:{'status':'APPLIED','risk_score':5.0})
    value.hf_client = SimpleNamespace(predict=lambda *args,**kwargs:{'is_hf_applied':True,'hf_risk_score':5.,'model_name':'fixture'})
    return value

def test_failed_forensics_never_claim_complete_authenticity(detector):
    failed = detector.ela_analyzer.analyze(b'bad')
    with patch.object(detector.ela_analyzer,'analyze',return_value=failed):
        result=detector.predict(blob())
    assert result.status.value=='PARTIAL_SUCCESS'
    assert result.verdict=='UNCERTAIN'
    assert 'ela' in result.metadata['missing_required_checks']
    assert result.metadata['observations']['ela']['ela_anomaly_score'] is None
    assert next(a for a in result.analyzers if a['category']=='ela')['status']=='UNAVAILABLE'

def test_file_payload_does_not_change_authorship_score(detector):
    original=detector.predict(blob())
    appended=detector.predict(blob()+b'PK\x03\x04'+b'HARMLESS_TRAILER_'*8)
    assert appended.metadata['file_safety']['payload_detected'] is True
    assert appended.risk_score==original.risk_score==5
    assert appended.verdict==original.verdict=='LOW_MANIPULATION_SIGNAL'

def test_input_hash_and_trace_are_real(detector):
    result=detector.predict(blob())
    assert result.metadata['input_sha256']==hashlib.sha256(blob()).hexdigest()
    assert result.metadata['decision_trace'][0]['rule']=='primary_cnn'
    assert result.metadata['cross_domain_consistency'] is None
    assert result.evidence==[]

def test_missing_checkpoint_is_not_imagenet_fallback():
    value=EfficientNetDetector(policy='image-screening-v2')
    with patch.object(value.hf_client,'predict',return_value={'is_hf_applied':True,'hf_risk_score':3,'model_name':'fixture'}):
        result=value.predict(blob())
    assert value.model is None
    assert value.readiness()['ready'] is False
    assert result.status.value=='PARTIAL_SUCCESS' and result.verdict=='UNCERTAIN'
    assert result.metadata['cnn_status']=='UNAVAILABLE'

def test_busy_worker_rejects_instead_of_queueing(detector):
    detector._lock.acquire()
    try: result=detector.predict(blob())
    finally: detector._lock.release()
    assert result.error_code=='INFERENCE_BUSY'

@pytest.mark.parametrize('predictions',[[],[{'label':'UNKNOWN','score':1}],
    [{'label':'PAINTING','score':1}], [{'label':'real','score':float('nan')},{'label':'fake','score':.2}],
    [{'label':'real','score':.9},{'label':'fake','score':.9}]])
def test_invalid_classifier_output_is_rejected(predictions):
    with pytest.raises(ValueError):parse_binary_predictions(predictions)

def test_complete_binary_mapping():
    assert parse_binary_predictions([{'label':'Real','score':.8},{'label':'Fake','score':.2}])==20

def test_unimplemented_general_model_is_not_silently_ignored():
    from models.image_deepfake.inference.local_vit_detector import LocalViTDeepfakeDetector
    with pytest.raises(ValueError,match='general_image'):
        LocalViTDeepfakeDetector(general_model_name='unimplemented')

def test_orientation_is_applied_consistently():
    image=Image.new('RGB',(80,40));image.paste((255,0,0),(0,0,40,40))
    a,b=io.BytesIO(),io.BytesIO();image.save(a,format='JPEG')
    exif=Image.Exif();exif[274]=6;image.save(b,format='JPEG',exif=exif)
    assert not torch.equal(process_image_bytes(a.getvalue()),process_image_bytes(b.getvalue()))

def test_pixel_budget_and_animation_are_rejected(monkeypatch):
    import models.image_deepfake.preprocessing.validator as module
    monkeypatch.setattr(module,'MAX_PIXELS',100)
    assert ImageValidator().validate(blob())[0] is False
    monkeypatch.setattr(module,'MAX_PIXELS',4000000)
    data=io.BytesIO()
    Image.new('RGB',(20,20),'red').save(data,format='GIF',save_all=True,append_images=[Image.new('RGB',(20,20),'blue')])
    assert ImageValidator().validate(data.getvalue())[0] is False
