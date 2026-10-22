import copy
import pytest
from shared.presentation.result import public_result, normalize_results, translations
from shared.schemas.api_response import APIResponse, ResponseMeta


def record(**changes):
    return {'scan_id':'contract-unit','module':'scam_message','detector_id':'unit',
            'status':'SUCCESS','risk_score':90,'verdict':'LIKELY_SCAM', 'metadata':{},**changes}


def resolve(record, pointer):
    value=record
    for part in pointer.lstrip('/').split('/'):
        value=value[int(part)] if isinstance(value,list) else value[part]
    return value


@pytest.mark.parametrize('status',['FAILED','TIMEOUT','UNAVAILABLE','QUEUED','PROCESSING'])
def test_unfinished_never_becomes_low_or_warning(status):
    assert public_result(record(status=status))['verdict_key']=='incomplete'


def test_failed_link_keeps_warning_evidence_but_incomplete_headline():
    item=record(metadata={'rule_findings':[{'code':'SECRET_REQUEST'}], 'links':[{'status':'UNAVAILABLE'}]})
    view=public_result(item)
    assert view['verdict_key']=='incomplete'
    assert 'OTP' in ' '.join(r['text'] for r in view['reasons'])
    assert all(resolve(item,r['evidence_id']) is not None for r in view['reasons'])


def test_image_missing_edit_check_is_incomplete_even_with_high_ai_score():
    item=record(module='image_deepfake', verdict='LIKELY_AI_GENERATED',metadata={'image_analysis':{'analysis_complete':False,'ai_generated_prob':.99}})
    assert public_result(item)['verdict_key']=='incomplete'


def test_old_authentic_label_does_not_enable_unvalidated_authenticity():
    item=record(module='image_deepfake',verdict='LIKELY_AUTHENTIC',metadata={'image_analysis':{'analysis_complete':True,'manipulation_prob':.1}})
    assert public_result(item)['verdict_key']=='not_sure'


def test_history_dict_recomputed_and_input_unchanged():
    item=record(presentation={'verdict_key':'no_clear_signs'})
    original=copy.deepcopy(item)
    response=APIResponse(data={'result':item},meta=ResponseMeta(request_id='unit')).model_dump(mode='json')
    assert response['data']['result']['presentation']['verdict_key']=='scam'
    assert item==original


def test_recompute_after_late_fusion_and_preserve_link_view():
    item=record(verdict='NO_STRONG_INDICATORS')
    first=normalize_results(item)
    assert first['presentation']['verdict_key']=='no_clear_signs'
    first['metadata']['links']=[{'status':'UNAVAILABLE','presentation':{'verdict_key':'incomplete'}}]
    second=normalize_results(first)
    assert second['presentation']['verdict_key']=='incomplete'
    assert second['metadata']['links'][0]['presentation']['verdict_key']=='incomplete'


def test_catalogue_keys_and_evidence_ids():
    assert translations()['en'].keys()==translations()['hi'].keys()
    for item in [record(),record(verdict='UNKNOWN'),record(module='phishing',metadata={'missing_signals':['tls']})]:
        view=public_result(item)
        for locale in view['locales'].values():
            assert locale['headline']
            for reason in locale['reasons']:resolve(item,reason['evidence_id'])


def test_reference_mapped_reading_does_not_define_image_warning_level():
    item=record(module='image_deepfake',verdict='INCONCLUSIVE',metadata={'image_analysis':{
        'analysis_complete':True,'ai_generated_prob':.8153,'manipulation_prob':.1,'quality':{'adequate':True}}})
    view=public_result(item)
    assert view['level']=={}
    assert view['checks'][0]['state']=='uncertain'
    assert 'risk_score' not in view['details']
    for check in view['checks']:resolve(item,check['evidence_id'])


def test_ai_warning_and_edit_timeout_have_independent_visible_states():
    item=record(module='image_deepfake',verdict='LIKELY_AI_GENERATED',status='PARTIAL_SUCCESS',metadata={'image_analysis':{
        'analysis_complete':False,'ai_generated_prob':.99,'manipulation_prob':None,'quality':{'adequate':True}}})
    view=public_result(item)
    assert view['verdict_key']=='incomplete'
    assert view['headline']=='AI warning found. Edit check incomplete.'
    assert [c['state'] for c in view['checks']]==['warning','incomplete']


def test_image_scale_exposes_real_boundary_and_never_guesses_authenticity():
    item=record(module='image_deepfake',verdict='NO_STRONG_INDICATORS')
    item['metadata']={'image_analysis':{'ai_policy_score':.12,'ai_decision_boundary':.5,'quality':{'adequate':True},'analysis_complete':True,'manipulation_prob':.01}}
    scale=public_result(item)['image_assessment']
    assert scale['score']==12 and scale['alert_boundary']==50
    assert scale['category']=='uncertain'
    assert [band['enabled'] for band in scale['bands']]==[False,False,True,True,True]
    item['metadata']['image_analysis']['ai_checks_disagree']=True
    assert public_result(item)['image_assessment']['score'] is None
    item['status']='FAILED'
    assert public_result(item)['image_assessment']['score'] is None


def test_conflicting_model_readings_are_available_but_not_a_reliable_combined_score():
    item=record(module='image_deepfake',verdict='INCONCLUSIVE',status='PARTIAL_SUCCESS',metadata={'image_analysis':{
        'ai_raw_score':.2197122,'modern_generator_raw_score':.942399,'ai_policy_score':.74167,
        'ai_checks_disagree':True,'quality':{'adequate':True},'analysis_complete':False,'manipulation_prob':None}})
    view=public_result(item);scale=view['image_assessment']
    assert view['verdict_key']=='incomplete' and scale['score'] is None
    assert [reading['value'] for reading in scale['model_readings']]==[21.97,94.24]
    for reading in scale['model_readings']:assert resolve(item,reading['evidence_id']) is not None
    assert scale['category']=='uncertain'


def test_verified_ai_origin_remains_visible_when_editing_is_incomplete():
    item=record(module='image_deepfake',verdict='LIKELY_AI_GENERATED',status='PARTIAL_SUCCESS',metadata={'image_analysis':{
        'analysis_complete':False,'manipulation_prob':None,'ai_checks_disagree':True,
        'provenance':{'signature_trusted':True,'asserts_ai_generation':True,'signer':'OpenAI OpCo, LLC','c2pa_status':'present'}}})
    view=public_result(item)
    assert view['verdict_key']=='looks_ai'
    assert view['headline']=='This is AI-generated'
    assert view['image_assessment']['category']=='ai_generated'
    assert view['checks'][1]['state']=='incomplete'
    assert any(reason['evidence_id'].endswith('/provenance') for reason in view['reasons'])
    item['metadata']['image_analysis']['provenance']['signature_trusted']=False
    assert public_result(item)['verdict_key']=='incomplete'


@pytest.mark.parametrize('signer',['OpenAI OpCo, LLC','Google LLC','Adobe Inc.','Example compliant provider'])
def test_any_trusted_standard_ai_declaration_has_the_same_clear_verdict(signer):
    item=record(module='image_deepfake',verdict='INCONCLUSIVE',status='PARTIAL_SUCCESS',metadata={'image_analysis':{
        'analysis_complete':False,'manipulation_prob':None,
        'provenance':{'signature_trusted':True,'asserts_ai_generation':True,'signer':signer,'c2pa_status':'present'}}})
    view=public_result(item)
    assert view['headline']=='This is AI-generated'
    assert not any(reason['evidence_id']=='/verdict' for reason in view['reasons'])
    assert view['image_assessment']['file_origin']['signer']==signer


def test_signed_ai_edit_is_not_claimed_to_be_a_fully_generated_image():
    item=record(module='image_deepfake',verdict='LIKELY_MANIPULATED',status='PARTIAL_SUCCESS',metadata={'image_analysis':{
        'analysis_complete':False,'manipulation_prob':None,
        'provenance':{'signature_trusted':True,'asserts_generative_edit':True,'asserts_ai_generation':False}}})
    view=public_result(item)
    assert view['headline']=='Contains AI edits' and view['verdict_key']=='looks_edited'
    assert view['checks'][1]['state']=='incomplete'
    item['metadata']['image_analysis']['provenance']['signature_trusted']=False
    assert public_result(item)['verdict_key']=='incomplete'


def test_ai_metadata_clues_conclude_looks_ai():
    item=record(module='image_deepfake',verdict='INCONCLUSIVE',status='SUCCESS',metadata={'image_analysis':{
        'analysis_complete':True,'manipulation_prob':0.01,'ai_generated_prob':0.02,
        'provenance':{'ai_markers':[{'field':'Software','marker':'Midjourney','tool':'Midjourney'}]}}})
    view=public_result(item)
    assert view['verdict_key']=='looks_ai'
    assert view['level']['ai']=='high'
    assert view['checks'][0]['state']=='warning'
    assert any('Midjourney' in r['text'] for r in view['reasons'])

