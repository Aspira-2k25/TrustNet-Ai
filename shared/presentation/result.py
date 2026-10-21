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
        if incomplete:
            key = 'incomplete'
            reason('edit_incomplete', '/metadata/image_analysis/analysis_complete' if 'analysis_complete' in image else '/metadata/image_analysis' if 'image_analysis' in meta else '/metadata')
        elif verdict == 'LIKELY_AI_GENERATED':
            key = 'looks_ai'
        elif verdict == 'LIKELY_MANIPULATED':
            key = 'looks_edited'
        elif verdict == 'NO_STRONG_INDICATORS':
            key = 'no_clear_signs'
            reason('image_no_warning', '/verdict')
        # Authenticity is disabled until independently validated. Never upgrade old labels.
        if image.get('quality', {}).get('adequate') is False:
            reason('quality', '/metadata/image_analysis/quality/adequate')
        if image.get('ai_checks_disagree'):
            reason('conflict', '/metadata/image_analysis/ai_checks_disagree')
        if verdict in ('LIKELY_AI_GENERATED', 'LIKELY_MANIPULATED'):
            reason('model_warning', '/verdict')
        # Mapped reference readings are not decision probabilities. In particular,
        # a reading above 80% can still be BELOW the selected raw alert boundary.
        # Never apply generic .3/.7 display cutoffs to these image readings.
        usable = image.get('quality', {}).get('adequate') is not False and not image.get('ai_checks_disagree')
        ai_warning = usable and verdict == 'LIKELY_AI_GENERATED'
        edit_warning = usable and verdict == 'LIKELY_MANIPULATED'
        if ai_warning:
            levels['ai'] = 'high'
        if edit_warning:
            levels['editing'] = 'high'
        checks = [
            ('ai_check', 'warning' if ai_warning else 'uncertain', 'ai_warning' if ai_warning else 'image_no_warning' if key == 'no_clear_signs' else 'ai_uncertain', '/metadata/image_analysis'),
            ('edit_check', 'incomplete' if incomplete else 'warning' if edit_warning else 'uncertain',
             'edit_incomplete' if incomplete else 'edit_warning' if edit_warning else 'edit_uncertain', '/metadata/image_analysis'),
        ]
    else:
        links = meta.get('links') or []
        missing = [i for i, link in enumerate(links) if link.get('status') not in ('SUCCESS', 'PARTIAL_SUCCESS') or link.get('risk_score') is None
                   or (link.get('presentation') or {}).get('verdict_key') == 'incomplete'
                   or ((link.get('inspection') or {}).get('status') not in (None, 'COMPLETED'))]
        # Missing live checks are explicit, including offline-only URL results.
        if meta.get('coverage', {}).get('truncated'):
            key = 'incomplete'
            reason('failed', '/metadata/coverage/truncated')
        elif missing or (record.get('module') == 'phishing' and meta.get('missing_signals')):
            key = 'incomplete'
            reason('links_incomplete' if missing else 'failed', '/metadata/links' if missing else '/metadata/missing_signals')
        elif verdict in ('LIKELY_SCAM', 'SMISHING_RISK'):
            key = 'scam'
        elif verdict == 'SUSPICIOUS':
            key = 'risky'
        elif verdict == 'NO_STRONG_INDICATORS' and status == 'SUCCESS':
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
        result[language] = {
            'verdict_key': key, 'headline': words['image_partial_ai' if levels.get('ai') == 'high' else 'image_partial'] if is_image and key == 'incomplete' and status in ('SUCCESS','PARTIAL_SUCCESS') else words[key],
            'reasons': [{'text': words[code], 'evidence_id': pointer} for code, pointer in reason_keys] + custom,
            'next_steps': [words['next_image' if is_image else 'next_text']],
            'level': levels, 'limits': [words[code] for code in limits],
            'checks': [{'name':words[name], 'state':state, 'text':words[code], 'evidence_id':pointer} for name,state,code,pointer in checks],
        }
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
