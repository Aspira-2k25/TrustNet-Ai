"""Single, evidence-backed public view. Recomputed after fusion on serialization.

Legacy detector records remain available for experts, not client-side verdict logic.
Evidence IDs are JSON pointers into the serialized detection result.
"""
import json
import math
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def translations():
    return json.loads(Path(__file__).with_name('translations.json').read_text(encoding='utf-8'))


def image_assessment(record, image, words):
    score=image.get('ai_policy_score')
    usable=record.get('status') in ('SUCCESS','PARTIAL_SUCCESS') and (image.get('quality') or {}).get('adequate') is True and not image.get('ai_checks_disagree')
    valid=lambda v:isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and 0<=v<=1
    boundary=image.get('ai_decision_boundary')
    signed=record.get('status') in ('SUCCESS','PARTIAL_SUCCESS') and (image.get('provenance') or {}).get('signature_trusted') and (image.get('provenance') or {}).get('asserts_ai_generation')
    has_markers=bool((image.get('provenance') or {}).get('ai_markers'))
    category='ai_generated' if signed else 'likely_ai' if (usable and record.get('verdict')=='LIKELY_AI_GENERATED') or has_markers else 'uncertain'
    readings=[]
    if record.get('status') in ('SUCCESS','PARTIAL_SUCCESS'):
        for field,name,note in [('ai_raw_score','Primary image model','Primary reading note'),('modern_generator_raw_score','Experimental image head','Experimental reading note')]:
            value=image.get(field)
            if valid(value):readings.append({'name':words[name],'value':round(value*100,2),'note':words[note],'evidence_id':'/metadata/image_analysis/'+field})
    provenance=image.get('provenance') or {}
    origin={'status':provenance.get('c2pa_status','not_checked'),'signer':provenance.get('signer'),
        'trusted':bool(provenance.get('signature_trusted')),'declares_ai':bool(provenance.get('asserts_ai_generation')),
        'declares_ai_edit':bool(provenance.get('asserts_generative_edit')),
        'evidence_id':'/metadata/image_analysis/provenance'}
    return {'file_origin':origin,'model_readings':readings,'category':category,'score':round(score*100,1) if usable and valid(score) else None,
        'alert_boundary':round(boundary*100,1) if valid(boundary) else None,
        'model':image.get('ai_model_id') or record.get('model_version') or words['Model unavailable'],
        'score_label':words['AI evidence score'], 'score_notice':words['Score interpretation'],
        'bands':[{'key':key,'label':words[label],'rule':words[rule],'enabled':enabled}
            for key,label,rule,enabled in [
                ('authentic','Authentic','Authentic rule',False),
                ('likely_authentic','Likely authentic','Likely authentic rule',False),
                ('uncertain','Uncertain','Uncertain rule',True),
                ('likely_ai','Likely AI-generated','Likely AI rule',True),
                ('ai_generated','AI-generated','AI generated rule',True)]]}


def public_result(record):
    meta = record.get('metadata') or {}
    image = meta.get('image_analysis') or {}
    is_image = record.get('module') == 'image_deepfake'
    verdict = record.get('verdict')
    status = record.get('status')
    if hasattr(status, 'value'):
        status = status.value
    reason_keys = []
    custom = []
    limits = ['edit_scope', 'edit_license'] if is_image else ['link_scope', 'language_scope']
    key = 'not_sure'
    levels = {}
    checks = []

    def reason(code, pointer):
        reason_keys.append((code, pointer))

    def band(value):
        return ('high' if value >= .7 else 'medium' if value >= .3 else 'low') if isinstance(value, (int, float)) and math.isfinite(value) else None

    if status not in ('SUCCESS', 'PARTIAL_SUCCESS'):
        key = 'incomplete'
        reason('failed', '/status')
    elif is_image:
        incomplete = image.get('analysis_complete') is not True or image.get('manipulation_prob') is None
        verified_ai=(image.get('provenance') or {}).get('signature_trusted') and (image.get('provenance') or {}).get('asserts_ai_generation')
        verified_edit=(image.get('provenance') or {}).get('signature_trusted') and (image.get('provenance') or {}).get('asserts_generative_edit') and not verified_ai
        ai_markers = (image.get('provenance') or {}).get('ai_markers') or []
        if verified_ai:
            key='looks_ai'
            reason('verified_ai_origin','/metadata/image_analysis/provenance')
        elif verified_edit:
            key='looks_edited'
            reason('verified_ai_edit','/metadata/image_analysis/provenance')
        if incomplete:
            if not (verified_ai or verified_edit):key = 'incomplete'
            reason('edit_incomplete', '/metadata/image_analysis/analysis_complete' if 'analysis_complete' in image else '/metadata/image_analysis' if 'image_analysis' in meta else '/metadata')
        elif not (verified_ai or verified_edit) and verdict == 'LIKELY_AI_GENERATED':
            key = 'looks_ai'
        elif not (verified_ai or verified_edit) and verdict == 'LIKELY_MANIPULATED':
            key = 'looks_edited'
        elif not (verified_ai or verified_edit) and ai_markers:
            key = 'looks_ai'
        elif not (verified_ai or verified_edit) and verdict == 'NO_STRONG_INDICATORS':
            key = 'no_clear_signs'
            reason('image_no_warning', '/verdict')
        # Authenticity is disabled until independently validated. Never upgrade old labels.
        if image.get('quality', {}).get('adequate') is False:
            reason('quality', '/metadata/image_analysis/quality/adequate')
        origin=image.get('provenance') or {}
        if ai_markers:
            reason('ai_metadata_detected', '/metadata/image_analysis/provenance')
            tools_found = sorted({c.get('tool') for c in ai_markers if c.get('tool')})
            if tools_found:
                custom.append({'text': f"Metadata inspection identified AI tool signatures: {', '.join(tools_found[:4])}.", 'evidence_id': '/metadata/image_analysis/provenance'})
        if (origin.get('asserts_ai_generation') or origin.get('asserts_generative_edit')) and not origin.get('signature_trusted'):
            reason('unverified_ai_origin','/metadata/image_analysis/provenance')
        if image.get('ai_checks_disagree') and not (verified_ai or verified_edit):
            reason('conflict', '/metadata/image_analysis/ai_checks_disagree')
        if verdict in ('LIKELY_AI_GENERATED', 'LIKELY_MANIPULATED') and not (verified_ai or verified_edit):
            reason('model_warning', '/verdict')
        # Mapped reference readings are not decision probabilities. In particular,
        # a reading above 80% can still be BELOW the selected raw alert boundary.
        # Never apply generic .3/.7 display cutoffs to these image readings.
        usable = image.get('quality', {}).get('adequate') is not False and not image.get('ai_checks_disagree')
        ai_warning = bool(verified_ai) or bool(ai_markers) or (usable and verdict == 'LIKELY_AI_GENERATED')
        edit_warning = bool(verified_edit) or usable and verdict == 'LIKELY_MANIPULATED'
        if ai_warning:
            levels['ai'] = 'high'
        if edit_warning:
            levels['editing'] = 'high'
        checks = [
            ('ai_check', 'warning' if ai_warning else 'uncertain', 'verified_ai_origin' if verified_ai else 'ai_metadata_detected' if ai_markers else 'ai_warning' if ai_warning else 'image_no_warning' if key == 'no_clear_signs' else 'ai_uncertain', '/metadata/image_analysis'),
            ('edit_check', 'incomplete' if incomplete else 'warning' if edit_warning else 'uncertain',
             'verified_ai_edit' if verified_edit else 'edit_incomplete' if incomplete else 'edit_warning' if edit_warning else 'edit_uncertain', '/metadata/image_analysis'),
        ]
    else:
        links = meta.get('links') or []
        missing = [i for i, link in enumerate(links) if link.get('status') not in ('SUCCESS', 'PARTIAL_SUCCESS') or link.get('risk_score') is None]
        # Missing live checks are explicit, including offline-only URL results.
        if meta.get('coverage', {}).get('truncated'):
            key = 'incomplete'
            reason('failed', '/metadata/coverage/truncated')
        elif missing:
            key = 'incomplete'
            reason('links_incomplete', '/metadata/links')
        elif verdict in ('LIKELY_SCAM', 'SMISHING_RISK'):
            key = 'scam'
        elif verdict == 'SUSPICIOUS':
            key = 'risky'
        elif verdict in ('NO_STRONG_INDICATORS', 'LEGITIMATE') and status in ('SUCCESS', 'PARTIAL_SUCCESS'):
            key = 'no_clear_signs'
            reason('no_warning', '/verdict')
        for i, finding in enumerate(meta.get('rule_findings') or []):
            if finding.get('code') in translations()['en']:
                reason(finding['code'], f'/metadata/rule_findings/{i}')
        for i, link in enumerate(links):
            if link.get('verdict') == 'SUSPICIOUS':
                reason('link_warning', f'/metadata/links/{i}')
        if verdict in ('LIKELY_SCAM', 'SMISHING_RISK', 'SUSPICIOUS') and not meta.get('rule_findings'):
            reason('model_warning', '/verdict')
        for i, finding in enumerate((meta.get('forensics') or {}).get('findings') or []):
            if finding.get('severity') in ('high', 'medium') and finding.get('reason'):
                custom.append({'text': finding['reason'], 'evidence_id': f'/metadata/forensics/findings/{i}'})
        value = band(record.get('risk_score', 0) / 100)
        if value and key != 'incomplete':
            levels['warning'] = value
    if record.get('module') not in ('image_deepfake', 'scam_message', 'phishing'):
        key = 'incomplete'
    if not reason_keys and not custom:
        reason('uncertain', '/verdict' if 'verdict' in record else '/status')
    result = {}
    for language, words in translations().items():
        if is_image:
            headline = words['image_partial_ai' if levels.get('ai') == 'high' else 'image_partial'] if key == 'incomplete' and status in ('SUCCESS','PARTIAL_SUCCESS') else words[key]
        else:
            has_alert = verdict in ('LIKELY_SCAM', 'SMISHING_RISK', 'SUSPICIOUS') or bool(levels.get('warning')) or any(f.get('code') in ('SECRET_REQUEST','PRIZE_ADVANCE_FEE','GUARANTEED_INVESTMENT') for f in (meta.get('rule_findings') or [])) or any(link.get('verdict') == 'SUSPICIOUS' for link in meta.get('links') or [])
            headline = words['text_partial_warning'] if key == 'incomplete' and status in ('SUCCESS','PARTIAL_SUCCESS') and has_alert else words[key]
        result[language] = {
            'verdict_key': key, 'headline': headline,
            'reasons': [{'text': words[code], 'evidence_id': pointer} for code, pointer in reason_keys] + custom,
            'next_steps': [words['next_image' if is_image else 'next_text']],
            'level': levels, 'limits': [words[code] for code in limits],
            'checks': [{'name':words[name], 'state':state, 'text':words[code], 'evidence_id':pointer} for name,state,code,pointer in checks],
        }
    if is_image:
        for language,view in result.items():
            view['image_assessment']=image_assessment(record,image,translations()[language])
            if key=='looks_ai' and (image.get('provenance') or {}).get('signature_trusted') and (image.get('provenance') or {}).get('asserts_ai_generation'):
                view['headline']=translations()[language]['Verified AI-generated']
            elif key=='looks_edited' and (image.get('provenance') or {}).get('signature_trusted') and (image.get('provenance') or {}).get('asserts_generative_edit'):
                view['headline']=translations()[language]['Verified AI edits']
    # Only factual existing measurements here, never invented confidence.
    details = {k: record[k] for k in ('risk_score', 'native_score', 'confidence', 'model_version', 'processing_time_ms') if k in record}
    if meta.get('confidence_available') is False or is_image:
        details.pop('confidence', None)
    if is_image:
        details.pop('risk_score', None)
    if status not in ('SUCCESS','PARTIAL_SUCCESS'):
        for name in ('risk_score','native_score','confidence'):
            details.pop(name, None)
    details['score_notice'] = 'Detector readings are not guarantees. A combined warning index is not a calibrated probability.'
    intel = meta.get('domain_intel') or {}
    if intel:
        if intel.get('domain'):
            details['domain_name'] = intel['domain']
        age = intel.get('domain_age_days')
        if age is not None:
            if age < 30:
                details['domain_age'] = f"{age} days old (⚠️ Brand New Domain - High Risk)"
            elif age < 365:
                details['domain_age'] = f"{age // 30} months old ({age} days)"
            else:
                years = round(age / 365, 1)
                details['domain_age'] = f"{years} years old ({age} days)"
        if intel.get('registration_date'):
            details['registered_on'] = str(intel['registration_date'])[:10]
        if intel.get('ssl_status'):
            details['ssl_status'] = intel['ssl_status']
        if intel.get('ssl_issuer'):
            details['ssl_issuer'] = intel['ssl_issuer']
    return {**result['en'], 'details': details, 'locales': result, 'contract_version': '1'}


def normalize_results(value):
    """Also upgrade historical dictionaries at the authenticated API boundary."""
    if isinstance(value, dict):
        output = {k: (v if k == 'presentation' else normalize_results(v)) for k, v in value.items()}
        if all(k in output for k in ('module', 'detector_id', 'status', 'risk_score')):
            output['presentation'] = public_result(output)
        return output
    if isinstance(value, list):
        return [normalize_results(item) for item in value]
    return value
