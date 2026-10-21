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
