import shutil
import pytest
from models.scam_message.multilingual import MultilingualHead
from models.scam_message.detector import ScamDetector
from models.scam_message.presentation import enrich
from shared.schemas.message_input import MessageInput
from shared.utils.message_normalization import normalize_message, message_language


def test_real_selected_artifacts_load_without_transformer_or_external_cache(monkeypatch):
    monkeypatch.setenv('SCAM_TEXT_POLICY','multilingual')
    detector=ScamDetector()
    assert detector.semantic is None
    request=MessageInput(text='Reply with your password and one-time code to restore access.')
    result=enrich(detector.predict(request.text,'selected-head'),request)
    assert result.verdict=='LIKELY_SCAM'
    assert result.presentation.verdict_key=='scam'
    assert result.model_version=='message-multilingual-lexical-v1'
    assert result.metadata['confidence_available'] is False


def test_research_language_annotation_is_never_a_routing_input():
    assert message_language('Your account balance is Rs 420. Thank you for banking with us.')=='English'
    assert message_language('Aapka parcel kal aayega aur paise nahi dene hain.')=='Hinglish'
    assert message_language('आपका पार्सल कल आएगा।')=='Hindi'
    assert normalize_message('OTP １２３ https://example.com/ABC')=='otp number link'


def test_hindi_failed_release_gate_cannot_trigger_standalone_model():
    head=MultilingualHead()
    assert not head.supports('आपका OTP है इसे किसी को ना बताएं')
    with pytest.raises(ValueError,match='Unsupported language'):
        head.predict('आपका OTP है इसे किसी को ना बताएं','hindi-gate')


@pytest.mark.parametrize('text',[
    'Your OTP is 483920 for signing in. Do not share it with anyone.',
    'Your parcel will arrive tomorrow. No payment is needed.',
    'Never send money to claim a lottery prize. This is a scam warning.',
    'Aapka OTP 123456 hai. Kisi ko mat batana.',
    'Aapka parcel kal aayega. Koi paise dene ki zaroorat nahi hai.',
    'KYC ke naam par OTP mat bhejo. Official app use karo.',
    'आपका OTP है इसे किसी को ना बताएं',
    'आपका पार्सल कल पहुँचेगा। कोई भुगतान नहीं चाहिए।',
])
def test_normal_otp_delivery_and_security_advice_not_a_scam_warning(text):
    detector=ScamDetector();request=MessageInput(text=text)
    result=enrich(detector.predict(text,'hard-negative'),request)
    assert result.verdict!='LIKELY_SCAM'


def test_long_text_cannot_silently_pass_unchecked_tail():
    request=MessageInput(text='This is a normal appointment reminder. '*70)
    result=enrich(ScamDetector().predict(request.text,'truncated'),request)
    assert result.metadata['coverage']['truncated'] is True
    assert result.presentation.verdict_key=='incomplete'


def test_tampered_selected_artifact_rejected(tmp_path):
    head=MultilingualHead()
    for name in ('manifest.json','config.json','weights.npz'):shutil.copy2(head.path/name,tmp_path/name)
    (tmp_path/'weights.npz').write_bytes(b'not valid weights')
    with pytest.raises(ValueError,match='checksum'):MultilingualHead(tmp_path)


def test_unsupported_script_returns_limited_result_instead_of_loading_legacy_weights():
    detector=ScamDetector();text='هذه رسالة عادية بخصوص موعد الغد'
    result=detector.predict(text,'unsupported-script')
    assert result.verdict=='UNABLE_TO_ASSESS'
    assert result.metadata['language_coverage_limited'] is True
