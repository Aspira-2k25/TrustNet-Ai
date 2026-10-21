import numpy as np
import pytest
from benchmark.coverage_train import select_threshold, score, PROTOCOL
from models.image_deepfake.inference.decision import decide


def test_feature_view_overrides_the_processor_center_crop():
    from pathlib import Path
    from PIL import Image
    from transformers import AutoImageProcessor
    from benchmark.coverage_train import feature_batch
    location=Path(__file__).resolve().parents[1]/'models/image_deepfake/artifacts/global'
    processor=AutoImageProcessor.from_pretrained(location,local_files_only=True)
    batch=feature_batch(processor,[Image.new('RGB',(512,400))])
    assert tuple(batch['pixel_values'].shape)==(1,3,224,224)


def test_operating_point_does_not_split_tied_real_scores():
    labels=[False]*100+[True]*20
    scores=[.1]*98+[.8,.8]+[.9]*20
    threshold=select_threshold(labels,scores)
    assert sum(np.asarray(scores[:100])>=threshold)==0
    assert sum(np.asarray(scores[100:])>=threshold)==20


def test_one_percent_boundary_uses_real_denominator():
    scores=np.arange(200)/200
    labels=np.r_[np.zeros(100,dtype=bool),np.ones(100,dtype=bool)]
    threshold=select_threshold(labels,scores)
    assert np.mean(scores[~labels]>=threshold)<=.01
    with pytest.raises(ValueError):select_threshold([True,True],[.3,.5])


def test_isotonic_serving_clips_outside_reference_range():
    head=dict(mean=[0],scale=[1],coef=[1],intercept=0,isotonic_x=[.2,.8],isotonic_y=[.1,.9])
    assert np.allclose(score(head,[{'embedding':[-100]},{'embedding':[100]}]),[.1,.9])


@pytest.mark.parametrize('changed',[
    {'ai':None},{'ai':.5},{'manipulation':None},{'manipulation':.5},
    {'quality':{'adequate':False}},{'provenance':{'ai_markers':[{'marker':'generative tool'}]}},
    {'provenance':{'asserts_generative_edit':True,'signature_trusted':False}},
])
def test_authentic_requires_every_evidence_gate(changed):
    inputs=dict(ai=.01,manipulation=.01,provenance={},quality={'adequate':True},regions=[],
        config=dict(calibration_ready=True,authenticity_enabled=True,ai_alert=.95,ai_authentic=.05,manipulation_alert=.95,manipulation_authentic=.05))
    assert decide(**inputs)[0]=='LIKELY_AUTHENTIC'
    assert decide(**(inputs|changed))[0]=='INCONCLUSIVE'
    assert PROTOCOL['authenticity'].startswith('Disabled')
