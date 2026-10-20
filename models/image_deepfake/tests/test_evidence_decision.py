import pytest
from models.image_deepfake.inference.decision import decide


CONFIG={'calibration_ready':True,'ai_alert':.97,'ai_authentic':.03,
        'manipulation_alert':.95,'manipulation_authentic':.05}


@pytest.mark.parametrize('ai,manipulation',[(None,0.01),(0.01,None),(float('nan'),.01),(.3,.01),(.01,.3)])
def test_missing_or_intermediate_evidence_never_becomes_authentic(ai,manipulation):
    assert decide(ai,manipulation,{}, {'adequate':True},[],CONFIG)[0]=='INCONCLUSIVE'


def test_low_generation_and_low_localization_are_both_required():
    assert decide(.01,.01,{}, {'adequate':True},[],CONFIG)[0]=='LIKELY_AUTHENTIC'
    assert decide(.01,.01,{'ai_markers':[{'marker':'chatgpt'}]}, {'adequate':True},[],CONFIG)[0]=='INCONCLUSIVE'


def test_compression_limits_and_missing_calibration_prevent_confident_verdicts():
    assert decide(.99,.01,{}, {'adequate':False,'limits':['heavy compression']},[],CONFIG)[0]=='INCONCLUSIVE'
    assert decide(.99,.01,{}, {'adequate':True},[],{**CONFIG,'calibration_ready':False})[0]=='INCONCLUSIVE'


def test_manipulation_alert_requires_a_pixel_region():
    assert decide(.1,.99,{}, {'adequate':True},[],CONFIG)[0]=='INCONCLUSIVE'
    assert decide(.1,.99,{}, {'adequate':True},[{'area':200}],CONFIG)[0]=='LIKELY_MANIPULATED'


def test_unsigned_generator_text_is_not_a_trusted_credential():
    assert decide(None,None,{'asserts_ai_generation':True,'signature_trusted':False}, {'adequate':True},[],CONFIG)[0]=='INCONCLUSIVE'


def test_failed_unseen_generator_diagnostic_disables_pixel_authenticity():
    config={**CONFIG,'authenticity_enabled':False,'authenticity_limit':'Unseen generator coverage is not established.'}
    assert decide(.0001,.0001,{}, {'adequate':True},[],config)[0]=='INCONCLUSIVE'


def test_failed_real_photo_guard_requires_primary_corroboration():
    config={**CONFIG,'ai_alert_corroboration_required':True,'ai_alert_corroborated':False}
    assert decide(.999,.01,{}, {'adequate':True},[],config)[0]=='INCONCLUSIVE'
    assert decide(.999,.01,{}, {'adequate':True},[],{**config,'ai_alert_corroborated':True})[0]=='LIKELY_AI_GENERATED'


def test_shipped_profile_disables_authenticity_for_unvalidated_edit_types():
    import json
    from pathlib import Path
    cfg=json.loads((Path(__file__).resolve().parents[1]/'calibration/evidence-v2.json').read_text())
    assert cfg['authenticity_enabled'] is False
    assert decide(0,0,{}, {'adequate':True},[],cfg)[0]=='INCONCLUSIVE'


def test_research_localizer_can_be_disabled_without_importing_vendor():
    from models.image_deepfake.inference.localizer_backend import create_localizer
    assert create_localizer('none') is None
    with pytest.raises(ValueError):create_localizer('unknown')
