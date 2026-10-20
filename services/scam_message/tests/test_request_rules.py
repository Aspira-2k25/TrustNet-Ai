import pytest
from models.scam_message.rules import analyze


@pytest.mark.parametrize('text',[
    'Your account will close. Send your OTP and UPI PIN to our agent now.',
    'Aapka KYC band ho jayega. OTP aur UPI PIN abhi bhejo.',
    'आपका खाता बंद होगा। अपना OTP और UPI PIN अभी भेजें।',
    'University account verification: share your OTP and password with our helpdesk to avoid suspension.',
    'Never share your password. Send your OTP to our verification agent.',
    'You won the lottery, pay the processing fee to receive your prize.',
])
def test_explicit_dangerous_requests_are_detected(text):
    findings=analyze(text)
    assert findings
    assert all(text[f['start']:f['end']].strip()==f['observed_text'] for f in findings)


@pytest.mark.parametrize('text',[
    'Never share your OTP or password. Your bank will never ask for it.',
    'Apna OTP kisi ko mat bhejo.',
    'अपना OTP कभी नहीं भेजें।',
    'Your OTP is 123456. Use it in the app to sign in.',
    'Conference registration is open. The registration fee covers meals.',
    'Can you send the lecture notes after class?',
])
def test_safety_advice_and_routine_requests_do_not_trigger_secret_rules(text):
    assert analyze(text)==[]
