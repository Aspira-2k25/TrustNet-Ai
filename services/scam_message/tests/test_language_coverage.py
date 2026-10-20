import pytest
from models.scam_message.coverage import predict_with_coverage
from models.scam_message.presentation import enrich
from shared.schemas.message_input import MessageInput


@pytest.mark.parametrize('text,expected',[
    ('Aapka KYC band ho jayega. OTP aur UPI PIN abhi bhejo.','LIKELY_SCAM'),
    ('आपका खाता बंद होगा। अपना OTP अभी भेजें।','LIKELY_SCAM'),
    ('Apna OTP kisi ko mat bhejo.','UNABLE_TO_ASSESS'),
    ('कल शाम छह बजे मिलते हैं।','UNABLE_TO_ASSESS'),
])
def test_limited_languages_keep_warnings_and_never_invent_class_probabilities(text,expected):
    def no_model(*args):raise AssertionError('English classifier must not assess unsupported text')
    result=predict_with_coverage(no_model,text,'language-test','fixture')
    result=enrich(result,MessageInput(text=text))
    assert result.verdict==expected
    assert result.metadata['probabilities']=={}
    assert result.metadata['model_risk_score'] is None
    assert result.confidence==0
    assert result.metadata['coverage']['validated_domain'] is False
    assert result.metadata['coverage']['characters_processed']==len(text)
    assert result.metadata['coverage']['truncated'] is False
