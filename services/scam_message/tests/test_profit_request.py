import pytest
from models.scam_message.rules import analyze
from models.scam_message.detector import ScamDetector
from models.scam_message.presentation import enrich
from shared.schemas.message_input import MessageInput

EXAMPLE = (
    "Bro, I have a 100% sure-shot trick for today's match! "
    "Deposit Rs 500 and I'll help you turn it into Rs 5,000 within 30 minutes. "
    "Guaranteed profit, no risk! I have an insider connection, so the match result "
    "is already known. Send the money to this UPI ID and share the payment "
    "screenshot to activate your VIP account. Hurry, only 3 slots left!"
)


def test_actual_scam_pipeline_warns_on_guaranteed_match_profit(monkeypatch):
    monkeypatch.setenv('SCAM_TEXT_POLICY','multilingual')
    request=MessageInput(text=EXAMPLE)
    result=enrich(ScamDetector().predict(request.text,'profit-regression'),request)
    assert result.verdict=='LIKELY_SCAM'
    assert result.presentation.verdict_key=='scam'
    assert any(f['code']=='GUARANTEED_INVESTMENT' for f in result.metadata['rule_findings'])
    assert result.risk_score>=90
    for finding in result.metadata['rule_findings']:
        assert request.text[finding['start']:finding['end']].strip()==finding['observed_text']


@pytest.mark.parametrize('text',[
    'Guaranteed profit is a misleading claim. Verify investments independently.',
    'Never deposit Rs 500 for guaranteed profit. This is a scam warning.',
    'Do not send money for guaranteed profit.',
    'Your payment of Rs 500 was received. Your monthly profit statement is ready.',
    'Profit is not guaranteed. Never send money to strangers.',
])
def test_normal_notices_and_safety_advice_do_not_trigger_new_profit_rule(text):
    assert analyze(text)==[]
