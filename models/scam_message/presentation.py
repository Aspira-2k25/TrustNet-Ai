"""Separate text risk, category, unverified sender and unassessed authorship."""
from email.utils import parseaddr
from urllib.parse import urlsplit
import re

VERDICTS={
 'NO_STRONG_INDICATORS':'No strong scam indicators detected',
 'SUSPICIOUS':'Suspicious — review carefully',
 'LIKELY_SCAM':'Likely scam/phishing',
 'UNABLE_TO_ASSESS':'Unable to assess reliably',
}


def hostname(value):
    try:
        return (urlsplit(value if '://' in value else 'https://'+value).hostname or '').lower()
    except ValueError:
        return ''

def enrich(result, request):
    meta=result.metadata
    threshold=float(meta.get('threshold', .4))
    score=result.risk_score/100
    canonical_text = request.canonical_text()
    insufficient=len(re.findall(r'\b\w+\b',canonical_text))<4
    evaluated = meta.get('evaluated_domains', ['English SMS'])
    email_evaluated = 'English email' in evaluated
    # Collection-specific evaluation never establishes universal email reliability.
    outside=(request.message_type=='email' or len(canonical_text)>1600) and not email_evaluated

    likely_threshold = 0.50 if request.message_type != 'email' else 0.78
    verdict=('UNABLE_TO_ASSESS' if insufficient or (outside and score<threshold)
             else 'SUSPICIOUS' if outside or result.confidence<.65 or threshold<=score<likely_threshold
             else 'LIKELY_SCAM' if score>=likely_threshold else 'NO_STRONG_INDICATORS')
    category='phishing/fraud' if verdict=='LIKELY_SCAM' else 'spam' if result.label=='spam' and not outside else 'unknown'
    # Ham annotations cannot distinguish personal, transactional and promotional.
    result.verdict=verdict
    meta['display_verdict']=VERDICTS[verdict]
    meta['threshold']=threshold
    meta['threshold_definition']='Validation-selected alert threshold; a probability above this threshold warrants review, not certainty of fraud'
    meta['assessment_dimensions']={
        'scam_risk':{'score':result.risk_score,'status':'OUT_OF_DOMAIN' if outside else 'LIMITED_COVERAGE' if email_evaluated else 'ASSESSED',
                     'definition':'SMS-model smishing estimate; not a guarantee of safety; email calibration unavailable' if outside else 'Calibrated message-model fraud-class probability × 100; limited labelled collections, not proof of safety' if email_evaluated else 'Calibrated SMS-model positive-class probability × 100'},
        'message_category':{'value':category,'status':'MODEL_ESTIMATE' if category!='unknown' else 'NOT_ESTABLISHED',
                            'reason':'Training labels do not distinguish personal, transactional and legitimate promotion; none are inferred from keywords'},
        'sender_verification':{'status':'NOT_VERIFIED','reason':'No SPF, DKIM, DMARC, ownership or reputation verification is implemented'},
        'ai_authorship':{'status':'NOT_ASSESSED','reason':'No separately validated authorship model; scam risk does not establish AI authorship'},
    }
    sender=parseaddr(request.claimed_sender)[1].rsplit('@',1)
    reply=parseaddr(request.reply_to)[1].rsplit('@',1)
    observations=[]
    if request.claimed_sender: observations.append({'kind':'claimed_sender','value':request.claimed_sender,'status':'UNVERIFIED'})
    if request.reply_to: observations.append({'kind':'reply_to','value':request.reply_to,'status':'UNVERIFIED'})
    if len(sender)==2 and len(reply)==2 and sender[-1].lower()!=reply[-1].lower():
        observations.append({'kind':'different_reply_domain','value':'Claimed sender and reply-to domains differ; forwarding/services can also cause this. This observation does not change model risk.','status':'OBSERVATION'})
    for link in request.displayed_links:
        dest=hostname(link.href) if link.href.lower().startswith(('https://','http://')) else ''
        display=hostname(link.text.strip()) if re.match(r'^(?:https?://|www\.)',link.text.strip(),re.I) else ''
        observations.append({'kind':'displayed_link','text':link.text,'destination_hostname':dest or 'Unavailable / non-HTTP link',
                            'displayed_hostname':display or None,'hostnames_differ':bool(display and dest and display!=dest),
                            'status':'NOT_OPENED','reason':'Literal hostnames only; tracking/redirect destinations, reputation, ownership and domain age not checked'})
    meta['sender_link_observations']=observations
    meta['message_type']=request.message_type
    meta['assessed_text']=request.canonical_text()
    meta['span_offset_unit']='Unicode code points in assessed_text (decoded plain text, including subject prefix); not original HTML source'
    meta['input_context']={'subject':request.subject,'claimed_sender':request.claimed_sender,'reply_to':request.reply_to,'text_format':request.text_format}
    meta['coverage']['validated_domain']=not outside
    meta['coverage']['evaluation_scope']='Limited labelled SMS/email collections; deployment reliability not established' if email_evaluated else 'English SMS; email outside validated coverage'
    meta['coverage']['abstained']=verdict=='UNABLE_TO_ASSESS'
    meta['next_steps']=['Use the organisation’s independently known app or contact details to verify requests.','Do not send passwords, OTPs or money based only on this assessment.']
    if not email_evaluated:
        meta['limitations'].append('Previously inspected source benchmark is diagnostic; it is no longer an untouched final test.')
    return result
