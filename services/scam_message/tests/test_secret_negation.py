import pytest
from models.scam_message.rules import analyze


@pytest.mark.parametrize('message',[
    'Aapka KYC nahi hua, apna OTP bhejo abhi',
    'Aapka KYC nahi hua apna OTP bhejo abhi',
    'आपका केवाईसी पूरा नहीं हुआ, अपना ओटीपी भेजें',
    'Never delay, send your OTP to me',
    'Never share your OTP with strangers, but send your OTP to our agent',
])
def test_an_unrelated_negation_cannot_suppress_a_secret_request(message):
    result=analyze(message)
    assert any(r['code']=='SECRET_REQUEST' for r in result)
    for item in result:assert message[item['start']:item['end']].strip()==item['observed_text']


@pytest.mark.parametrize('message',[
    'Do not share your OTP with anyone',
    'Never ever share your password',
    'Our bank will never ask you to share your OTP',
    'Apna OTP kisi ko mat bhejo',
    'OTP kabhi share mat karna',
    'OTP share kabhi nahi karna',
    'किसी को ओटीपी मत भेजें',
    'ओटीपी साझा नहीं करें',
    'Your OTP is 123456. It expires in five minutes.',
])
def test_safety_advice_and_legitimate_otp_notifications_are_not_secret_requests(message):
    assert not any(r['code']=='SECRET_REQUEST' for r in analyze(message))


def test_hinglish_coverage_flow_records_the_rule_version_and_warns_without_fake_confidence():
    from models.scam_message.coverage import predict_with_coverage
    from models.scam_message.presentation import enrich
    from models.scam_message.rules import RULE_POLICY_VERSION
    from shared.schemas.message_input import MessageInput
    request=MessageInput(text='Aapka KYC nahi hua, apna OTP bhejo abhi')
    def unsupported_predictor(*args):raise AssertionError('The English-only classifier must not assess this Hinglish fixture')
    result=enrich(predict_with_coverage(unsupported_predictor,request.text,'unit-hinglish','fixture'),request)
    assert result.verdict=='LIKELY_SCAM' and result.confidence==0
    assert result.metadata['rule_policy_version']==RULE_POLICY_VERSION
    assert result.metadata['language_coverage_limited'] is True
