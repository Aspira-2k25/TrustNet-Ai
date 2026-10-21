"""Explicit high-risk requests. Observations never masquerade as probabilities."""
import re

RULE_POLICY_VERSION='secret-negation-v2'

SECRET=re.compile(r'\b(?:otp|one[ -]?time (?:password|code)|password|cvv|upi\s*pin|atm\s*pin)\b|पासवर्ड|ओटीपी|यूपीआई\s*पिन',re.I)
SEND=re.compile(r'\b(?:share|send|tell|provide|forward|reveal|bhej\w*|bata\w*|de\s*do|do\s*abhi)\b|भेज\w*|बताइ?\w*|बताएं|साझा\s*कर\w*|दे\s*द[ोें]',re.I)
NEGATION=re.compile(r"\b(?:never|don.t|do not|must not|should not|no need to|mat|nahi|nahin)\b|कभी.*नहीं|मत\s|न\s*भेज|नहीं",re.I)
PRIZE=re.compile(r'\b(?:won|winner|lottery|prize|inaam|inam|jeet\w*)\b|लॉटरी|इनाम|जीत',re.I)
FEE=re.compile(r'\b(?:pay|payment|fee|deposit|bhej\w*|jama|processing)\b|शुल्क|जमा|भुगतान',re.I)
RETURNS=re.compile(r'\b(?:guaranteed|double|risk.free|100\s*%)\b|गारंटी|दोगुन',re.I)
INVEST=re.compile(r'\b(?:invest\w*|crypto|bitcoin|trading|return\w*|munafa|paisa)\b|निवेश|मुनाफा|पैसा',re.I)

# Negation must apply to the sharing action, not to an unrelated pretext such
# as "KYC nahi hua". Keep offsets on the original Unicode text.
BEFORE_ACTION_NEGATION=re.compile(r"(?:\b(?:never|don.t|do not|must not|should not|no need to|mat|nahi|nahin)|मत|नहीं|न)\s+(?:(?:ever|please|kabhi|कभी)\s+)?(?:(?:ask|asks)(?:\s+you)?\s+to\s+)?$",re.I)
AFTER_ACTION_NEGATION=re.compile(r"^\s*(?:(?:it|this|these|them|your|otp|password|pin|kabhi|bhi|ओटीपी|पासवर्ड|कभी|भी)\s+){0,5}(?:mat|nahi|nahin|not|मत|नहीं)(?:\W|$)",re.I)


def secret_request(value):
    if not SECRET.search(value):return False
    return any(not BEFORE_ACTION_NEGATION.search(value[:action.start()]) and
               not AFTER_ACTION_NEGATION.search(value[action.end():]) for action in SEND.finditer(value))


def analyze(text):
    findings=[]
    # Clause boundaries preserve Unicode offsets. Negated safety advice does not
    # suppress a different clause that actually requests secrets.
    for clause in re.finditer(r'[^.!?;\n।]+',text):
        value=clause.group()
        code,reason=None,None
        if secret_request(value):
            code='SECRET_REQUEST'
            reason='This clause asks you to disclose a password, OTP or payment PIN. Do not share these secrets with a person or message sender.'
        elif NEGATION.search(value):
            continue
        elif PRIZE.search(value) and FEE.search(value):
            code='PRIZE_ADVANCE_FEE'
            reason='The message connects a prize or lottery to an upfront payment, a common advance-fee scam pattern.'
        elif RETURNS.search(value) and INVEST.search(value):
            code='GUARANTEED_INVESTMENT'
            reason='The message advertises guaranteed or doubled investment returns. Treat this as a fraud warning and verify independently.'
        if code:
            findings.append(dict(code=code,start=clause.start(),end=clause.end(),reason=reason,severity='high',
                observed_text=value.strip(),score_semantics='rule warning, not probability'))
    return findings
