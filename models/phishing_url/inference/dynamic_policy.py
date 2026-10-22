"""Combine measured model output with current observations, with explicit provenance."""
import json
from functools import lru_cache
from pathlib import Path
from shared.constants.status import StatusEnum
from shared.constants.native_score_semantics import NativeScoreSemanticsEnum
from shared.schemas.evidence import EvidenceItem
from .forensics import analyze, POLICY_VERSION

@lru_cache(maxsize=1)
def evidence_policy():
    value = json.loads((Path(__file__).resolve().parents[1]/'configs/evidence_policy.json').read_text())
    if any(not 0 <= w <= 1 for w in value['weights'].values()):
        raise ValueError('Invalid evidence policy weight')
    return value

def apply(result, url, threshold=None, observations=None):
    report = analyze(url, observations)
    link=report.get('input',{})
    meta = result.metadata
    diagnostic = meta.setdefault('diagnostic_model', {'probability': result.native_score,
                    'risk_score': result.risk_score, 'label': result.label, 'status': result.status.value,
                    'error_code': result.error_code})
    trusted = result.model_version in {'modern-v5','regional-v1','regional-recall-v1'} and diagnostic['status'] in {'SUCCESS', 'PARTIAL_SUCCESS'}
    model_calibrated=trusted and result.model_version=='modern-v5'
    model_p = float(diagnostic['probability']) if trusted else None
    strong = report['outcome'] == 'SUSPICIOUS'
    medium = any(f.get('severity') == 'medium' for f in report.get('findings', []))

    # A popular/accredited hostname or an unsubscribe path is not safety evidence.
    # Never overwrite the selected model reading with an unmeasured allowlist clamp.
    meta['decision_policy_revision']='no-allowlist-score-clamp-v1'

    policy = evidence_policy()
    residual = 1 - model_p if trusted else 1.
    updates, used = [], set()
    for finding in report['findings']:
        code = finding['code']
        if code not in used and code in policy['weights']:
            weight = policy['weights'][code]
            residual *= 1 - weight
            updates.append({'code': code, 'policy_weight': weight})
            used.add(code)
    assessed = trusted or strong
    score = round(100 * (1-residual), 1) if assessed else None
    signals = report['network'].get('signals', {})
    observed = lambda name: str(signals.get(name, {}).get('status', '')).lower() == 'observed'
    meta.update(assessment_policy=POLICY_VERSION, link_analysis_version='links-v1', assessed_url=link.get('normalized',url), original_input=url, input_handling=link, forensics=report,
                confidence_available=False, calibrated=False, model_calibrated=model_calibrated,
                score_basis='model_and_live_evidence' if trusted and updates else ('calibrated_url_model' if model_calibrated else 'regional_url_model') if trusted else 'live_evidence' if assessed else 'withheld',
                score_definition='Risk index from the selected URL model and recorded forensic evidence. Higher means more risk; this combined index is not a probability or safety guarantee.',
                score_components={'model_probability': model_p, 'evidence_updates': updates, 'policy_version': policy['version'],
                                  'formula': '100 * (1 - (1 - model_probability) * product(1 - evidence_weight))',
                                  'combined_calibration_validated': False},
                threshold=threshold,
                threshold_definition=('Development-selected threshold for the selected URL expert and URL shape. Strong current forensic findings can also trigger an alert.' if result.model_version in {'regional-v1','regional-recall-v1'} else 'Validation-selected model alert threshold. Strong current forensic findings can also trigger an alert.'),
                coverage={'status': 'LIVE_CHECKS_APPLIED' if observed('http') else 'URL_ANALYSIS_ONLY',
                          'website_fetched': observed('http'),
                          'reason': 'Live checks supplement the URL model. Unavailable checks are listed in the report.'},
                missing_signals=[name for name in ('dns','tls','http','html','registration','reputation') if not observed(name)])
    result.confidence = 0
    result.native_score_semantics = NativeScoreSemanticsEnum.anomaly_score
    result.evidence = [e for e in result.evidence if not e.feature_or_region.startswith('forensic:')]
    result.evidence.extend(EvidenceItem(feature_or_region='forensic:'+f['code'], contribution=0,
                                       human_readable_note=f['reason']) for f in report['findings'])
    result.analyzers = [a for a in result.analyzers if a.get('category') not in {'forensics','live_collection'}]
    result.analyzers += [{'name': 'URL forensics', 'status': 'APPLIED', 'category': 'forensics', 'finding': report['outcome']},
                         {'name': 'Live website checks', 'status': 'APPLIED' if observed('http') else 'UNAVAILABLE', 'category': 'live_collection',
                          'finding': 'Public DNS, TLS, redirects and static page evidence are recorded individually.'},
                         {'name': 'PhishStats reputation', 'status': 'APPLIED' if observed('reputation') else 'UNAVAILABLE', 'category': 'live_collection',
                          'finding': 'Exact URL report match.' if signals.get('reputation',{}).get('matched') else 'No exact match or provider unavailable; neither establishes safety.'}]
    reasons = [f['reason'] for f in sorted(report['findings'], key=lambda f: {'high':0,'medium':1,'info':2}[f['severity']]) if f['severity'] != 'info']
    if trusted:
        flagged = strong or model_p >= float(threshold)
        reasons.append('The address pattern resembles phishing URLs learned by the model.' if model_p >= float(threshold)
                       else 'The address pattern did not trigger the URL model’s phishing checks.')
    else:
        flagged = strong
    if observed('tls') and signals['tls'].get('certificate') and signals['tls'].get('validated') is not False:
        reasons.append('The HTTPS certificate was validated for the destination hostname. This protects transport; it does not establish website safety.')
    if observed('http'):
        reasons.append(f'The live request returned HTTP {signals["http"].get("status_code")} after {signals["http"].get("redirects",0)} redirects.')
    if not reasons:
        reasons = [f'The destination hostname is {report["hostname"]}. Not enough reliable evidence was available for a result.']
    meta['reasons'] = reasons
    if assessed:
        result.status = StatusEnum.PARTIAL_SUCCESS
        result.error_code = result.error_message = None
        is_established = False
        reg_dom = str(report.get('registered_domain', '')).lower()
        obs_age = signals.get('registration', {}).get('domain_age_days') or (observations or {}).get('domain_age_days')
        if (obs_age is not None and obs_age >= 365) or reg_dom.endswith(('.edu', '.edu.in', '.ac.in', '.gov', '.gov.in')):
            if not strong and not medium and not report.get('visual_domain_match'):
                is_established = True
        if is_established and not flagged:
            score = min(score, 10.0)
            review = False
        else:
            review = not flagged and (report['outcome'] == 'REVIEW' or score >= 25)
        result.risk_score = score
        result.native_score = score/100
        result.label = 'phishing' if flagged else 'unknown' if review else 'legitimate'
        result.verdict = 'SUSPICIOUS' if flagged else 'REVIEW_RECOMMENDED' if review else 'NO_STRONG_INDICATORS'
        meta['display_verdict'] = 'Phishing risk detected' if flagged else 'Some URL details need review' if review else 'Low phishing risk'
        result.explanation = ' '.join(reasons[:2])
    else:
        result.status = StatusEnum.UNAVAILABLE
        result.risk_score = result.native_score = 0
        result.label, result.verdict = 'unknown', 'UNCERTAIN'
        result.error_code = diagnostic.get('error_code') or 'INSUFFICIENT_EVIDENCE'
        result.error_message = 'We could not complete enough checks for this URL. Please try again shortly.'
        result.explanation = result.error_message
        meta['display_verdict'] = 'Check incomplete'
        if link.get('kind')=='non_web':
            result.error_code='NON_WEB_LINK'
            result.error_message=f"This {link['scheme']} link was inspected without opening it. The website model cannot assign a reliable score to this link type."
            result.explanation=result.error_message
            meta['display_verdict']='Link inspected — limited coverage'
    if report.get('visual_domain_match'):
        meta['display_verdict']='Lookalike domain risk detected'
    meta['assessment_dimensions'] = {'phishing_risk': {'status':'ASSESSED' if assessed else 'UNAVAILABLE', 'score':score},
                                    'website_verification': {'status':'NOT_VERIFIED'}, 'ai_authorship': {'status':'NOT_ASSESSED'}}
    meta['limitations'] = ['A low score does not guarantee safety or verify ownership.',
                          'The combined evidence index is not empirically calibrated as a probability.',
                          'Static page checks do not execute JavaScript; cloaking and new campaigns may be missed.',
                          'Threat provider coverage, availability and rate limits affect reputation checks.']
    meta['next_steps'] = ['Check the actual hostname and verify unexpected credential/payment requests independently.']
    return result
