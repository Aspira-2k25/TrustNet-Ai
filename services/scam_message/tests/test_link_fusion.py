import asyncio
from datetime import datetime, timezone
from unittest.mock import patch
import httpx
from shared.schemas.message_input import MessageInput
from shared.schemas.detection_result import DetectionResult
from models.scam_message.presentation import enrich
from services.scam_message.app.link_fusion import combine, extract_urls, assess_links

def result(score=10, verdict='NO_STRONG_INDICATORS'):
    r = DetectionResult(scan_id='fixture', module='scam_message', detector_id='fixture', model_version='fixture',
        preprocessing_version='fixture', native_score=score/100, native_score_semantics='probability_of_positive_class',
        risk_score=score, confidence=.9, label='ham', status='SUCCESS', verdict=verdict,
        timestamp=datetime.now(timezone.utc).isoformat(), metadata={'coverage':{}, 'limitations':[]})
    return enrich(r, MessageInput(text='Your appointment is confirmed tomorrow morning.'))

def test_extract_hidden_html_destinations_and_no_email_address():
    req=MessageInput(message_type='email', text_format='html', text='<p>Contact x@example.org. See example.com.</p><a href="https://hidden.invalid/path">Receipt</a>', displayed_links=[{'text':'Receipt','href':'https://hidden.invalid/path'}])
    assert extract_urls(req)==['https://hidden.invalid/path','example.com']


def test_deceptive_url_userinfo_is_not_removed_as_an_email_address():
    url = 'https://paypal.com@account.example/login'
    req = MessageInput(text=f'Contact support@example.com or verify your account at {url}.')
    assert extract_urls(req) == [url]

def test_fusion_preserves_primary_probabilities_and_escalates_link_warning():
    r=result(); r.metadata['probabilities']={'ham':.9,'smishing':.1,'spam':0}
    combined=combine(r,[dict(url='https://fixture.invalid',status='PARTIAL_SUCCESS',risk_score=91,label='phishing')])
    assert combined.risk_score==91 and combined.native_score==.1
    assert combined.verdict=='LIKELY_SCAM'
    assert combined.metadata['message_model']['risk_score']==10
    assert combined.metadata['probabilities']['ham']==.9
    assert combined.metadata['fusion']['calibrated'] is False

def test_missing_url_is_not_a_safe_result_and_never_lowers_message_risk():
    r=combine(result(),[dict(url='https://fixture.invalid',status='UNAVAILABLE',reason='offline')])
    assert r.verdict=='SUSPICIOUS' and r.risk_score==10
    assert r.metadata['fusion']['url_score'] is None
    assert r.metadata['fusion']['status']=='PARTIAL'
    high=combine(result(95),[dict(url='https://fixture.invalid',status='PARTIAL_SUCCESS',risk_score=2,label='legitimate')])
    assert high.risk_score==95 and high.verdict=='LIKELY_SCAM'

def test_no_links_keeps_message_assessment():
    r=combine(result(),[])
    assert r.risk_score==10 and r.verdict=='NO_STRONG_INDICATORS'
    assert r.metadata['fusion']['status']=='NO_LINKS'

def test_service_failure_is_recorded_not_raised():
    class FailingClient:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kwargs): raise httpx.ConnectError('offline')
    with patch('services.scam_message.app.link_fusion.httpx.AsyncClient',return_value=FailingClient()):
        links=asyncio.run(assess_links(['https://fixture.invalid'],'fixture','http://127.0.0.1:8007'))
    assert links[0]['status']=='UNAVAILABLE' and links[0].get('risk_score') is None

def test_url_limit_is_explicit_and_corrupt_response_rejected():
    class BadClient:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kwargs):
            return httpx.Response(200,json={'data':{'scan_id':'wrong'}},request=httpx.Request('POST','http://fixture'))
    with patch('services.scam_message.app.link_fusion.httpx.AsyncClient',return_value=BadClient()):
        links=asyncio.run(assess_links([f'https://fixture{i}.invalid' for i in range(10)],'fixture','http://127.0.0.1:8007'))
    assert len(links)==10 and all(link.get('risk_score') is None for link in links)
    assert links[-1]['reason']=='URL assessment limit reached; not analysed'

def test_genuine_academic_announcement_and_offer_not_flagged_as_scam():
    req_academic = MessageInput(
        message_type='email',
        text='ConfAI 2026 Academic Conference Announcement at Plaksha University. Registrations are officially open.',
        displayed_links=[{'text':'ConfAI','href':'https://www.conf-ai.in/'}]
    )
    raw_academic = DetectionResult(
        scan_id='f1', module='scam_message', detector_id='f', model_version='f', preprocessing_version='f',
        native_score=0.92, native_score_semantics='probability_of_positive_class', risk_score=92.0,
        confidence=0.9, label='smishing', status='SUCCESS', verdict='SMISHING_RISK',
        timestamp=datetime.now(timezone.utc).isoformat(), metadata={'coverage':{}, 'limitations':[], 'evaluated_domains':['English SMS', 'English email']}
    )
    res_academic = enrich(raw_academic, req_academic)
    fused_academic = combine(res_academic, [{'url':'https://www.conf-ai.in/','status':'PARTIAL_SUCCESS','risk_score':38.0,'verdict':'REVIEW_RECOMMENDED'}])
    assert fused_academic.verdict == 'NO_STRONG_INDICATORS'
    assert fused_academic.risk_score <= 40

    req_offer = MessageInput(
        message_type='email',
        text='We are pleased to offer you the full-time position of Engineer. Your annual compensation is $90,000.',
        displayed_links=[{'text':'Onboarding','href':'https://careers.example.com/'}]
    )
    raw_offer = DetectionResult(
        scan_id='f2', module='scam_message', detector_id='f', model_version='f', preprocessing_version='f',
        native_score=0.75, native_score_semantics='probability_of_positive_class', risk_score=75.0,
        confidence=0.9, label='smishing', status='SUCCESS', verdict='SMISHING_RISK',
        timestamp=datetime.now(timezone.utc).isoformat(), metadata={'coverage':{}, 'limitations':[], 'evaluated_domains':['English SMS', 'English email']}
    )
    res_offer = enrich(raw_offer, req_offer)
    fused_offer = combine(res_offer, [{'url':'https://careers.example.com/','status':'PARTIAL_SUCCESS','risk_score':25.0,'verdict':'REVIEW_RECOMMENDED'}])
    assert fused_offer.verdict == 'NO_STRONG_INDICATORS'
    assert fused_offer.risk_score <= 40

def test_real_recruitment_scam_with_advance_fee_still_flagged():
    req_scam = MessageInput(
        message_type='email',
        text='Job offer! Earn $500 daily part-time job. Just pay registration fee of $50 via Telegram @recruiter.',
        displayed_links=[]
    )
    raw_scam = DetectionResult(
        scan_id='f3', module='scam_message', detector_id='f', model_version='f', preprocessing_version='f',
        native_score=0.95, native_score_semantics='probability_of_positive_class', risk_score=95.0,
        confidence=0.95, label='smishing', status='SUCCESS', verdict='SMISHING_RISK',
        timestamp=datetime.now(timezone.utc).isoformat(), metadata={'coverage':{}, 'limitations':[], 'evaluated_domains':['English SMS', 'English email']}
    )
    res_scam = enrich(raw_scam, req_scam)
    assert res_scam.verdict == 'LIKELY_SCAM'
    assert res_scam.risk_score >= 80

