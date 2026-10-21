import base64
import hashlib
import io
import cv2
import numpy as np
from PIL import Image
from models.image_deepfake.forensics.supporting_signals import analyze
import pytest


def encoded(pixels,format='PNG'):
    stream=io.BytesIO();Image.fromarray(pixels).save(stream,format);return stream.getvalue()


def test_lossless_input_does_not_invent_a_jpeg_history_or_edit_mask():
    data=encoded(np.random.default_rng(42).integers(0,256,(128,160,3),dtype=np.uint8))
    sha=hashlib.sha256(data).hexdigest();result=analyze(data)
    assert result['ela']['status']=='NOT_APPLICABLE'
    assert result['assets']=={}
    assert result['affects_verdict'] is False
    assert not {'probability','regions','mask'} & result.keys()
    assert hashlib.sha256(data).hexdigest()==sha


def test_ela_native_window_is_explicit_and_not_stretched_to_original():
    data=encoded(np.full((820,1000,3),128,np.uint8),'JPEG')
    result=analyze(data);scope=result['scope']
    assert scope==dict(x=116,y=26,width=768,height=768,native_pixels=True,whole_image=False)
    layer=cv2.imdecode(np.frombuffer(base64.b64decode(result['assets']['ela']),np.uint8),cv2.IMREAD_COLOR)
    assert layer.shape==(768,768,3)
    assert result['ela']['fixed_display_gain']==8
    assert 'not a localized edit mask' in result['ela']['note']


def test_copy_move_reports_geometric_candidates_without_asserting_manipulation():
    pixels=np.random.default_rng(19).integers(0,256,(384,384,3),dtype=np.uint8)
    pixels[224:352,224:352]=pixels[32:160,32:160]
    result=analyze(encoded(pixels))
    assert result['copy_move']['geometric_inliers']>=6
    assert result['affects_verdict'] is False
    assert 'No edit regions are asserted' in result['copy_move']['note']


@pytest.mark.parametrize('failure',[RuntimeError,cv2.error])
def test_diagnostic_failure_cannot_change_the_real_verdict_path(monkeypatch,failure):
    import importlib
    import json
    from pathlib import Path
    from types import SimpleNamespace
    module=importlib.import_module('models.image_deepfake.inference.forensic_detector')
    supporting=importlib.import_module('models.image_deepfake.forensics.supporting_signals')
    detector=module.ForensicDetector.__new__(module.ForensicDetector)
    detector.config=json.loads((Path(module.__file__).resolve().parents[1]/'calibration/evidence-v2.json').read_text())
    detector.global_model=SimpleNamespace(predict=lambda *a,**k:{'ai_score':.01,'model_view_shape':[1,3,384,384]})
    detector.modern_head=None;detector.localizer=None;detector.localizer_error='Disabled for this behavior test.'
    monkeypatch.setattr(module,'inspect_c2pa',lambda *args:{})
    data=encoded(np.full((256,256,3),110,np.uint8),'JPEG')
    reference=detector.predict(data)
    def unavailable(*args):raise failure('diagnostic failure')
    monkeypatch.setattr(supporting,'analyze',unavailable)
    result=detector.predict(data)
    assert (result.verdict,result.explanation,result.native_score)==(reference.verdict,reference.explanation,reference.native_score)
    assert result.metadata['image_analysis']['supporting_forensics']['affects_verdict'] is False
