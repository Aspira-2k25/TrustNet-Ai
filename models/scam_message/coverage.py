"""Coverage-aware warnings; rules never become calibrated class probabilities."""
import re
from datetime import datetime,timezone
from shared.schemas.detection_result import DetectionResult
from models.scam_message.rules import analyze, RULE_POLICY_VERSION

HINGLISH=re.compile(r'\b(?:aap(?:ka|ki|ko)?|tum(?:hara)?|hai|hain|karo|karna|paisa|paise|bhej\w*|turant|abhi|jayega|nahi|nahin|mat|mera|mujhe)\b',re.I)


def limited_language(text):
    return bool(re.search('[\u0900-\u097f]',text)) or len({m.group().casefold() for m in HINGLISH.finditer(text)})>=2


def predict_with_coverage(predictor,text,scan_id,model_version):
    if not text.strip() or len(text)>10000 or '\x00' in text:
        raise ValueError('Message must contain 1–10000 characters and no NUL bytes')
    findings=analyze(text)
    unsupported=limited_language(text)
    result=None
    if not unsupported:
        try:result=predictor(text,scan_id)
        except ValueError as exc:
            if not any(word in str(exc).lower() for word in ['language','script','hinglish','no features']):raise
            unsupported=True
    if result is None:
        result=DetectionResult(scan_id=scan_id,module='scam_message',detector_id='scam_message.coverage_rules.v1',
            model_version=model_version,preprocessing_version='unicode-rules-v1',native_score=0,
            native_score_semantics='anomaly_score',risk_score=0,confidence=0,label='not_assessed',
            status='SUCCESS',verdict='UNABLE_TO_ASSESS',timestamp=datetime.now(timezone.utc).isoformat(),
            explanation='This language is outside validated classifier coverage. Explicit secret-request, advance-fee and investment-warning rules were checked; their absence does not establish safety.',
            metadata={'probabilities':{},'spans':[],'links':[],'coverage':{},'limitations':[],
                'threshold':.4,'confidence_available':False,'evaluated_domains':[],
                'confidence_definition':'No calibrated classifier probability is available for this language.'})
    meta=result.metadata
    meta.setdefault('coverage',{}).update(characters_processed=len(text),truncated=False)
    meta['rule_findings']=findings
    meta['rule_policy_version']=RULE_POLICY_VERSION
    meta['language_coverage_limited']=unsupported
    meta['model_risk_score']=None if unsupported else result.risk_score
    meta['model_confidence']=None if unsupported else result.confidence
    meta['model_verdict']=None if unsupported else result.verdict
    meta['score_semantics']='Maximum of model reading and explicit rule warning index, not a calibrated combined fraud probability.'
    meta['limitations']=meta.get('limitations',[])+[
        'Hindi/Hinglish support is limited to explicit warning patterns. Broad multilingual classifier performance is not validated.'
    ]
    for f in findings:
        meta.setdefault('spans',[]).append({**f,'kind':'rule','direction':'support','contribution':0,'note':f['reason']})
    if findings:
        result.risk_score=max(result.risk_score,90.)
        result.confidence=0.
        meta['confidence_available']=False
        result.explanation=' '.join(f['reason'] for f in findings)+' Rule warning index: 90/100, not a probability. '+(result.explanation or '')
    return result
