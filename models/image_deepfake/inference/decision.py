"""Conservative evidence fusion. Absence of an alert never proves authenticity."""
import math


def finite_probability(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and 0<=value<=1


def decide(ai, manipulation, provenance, quality, regions, config):
    reasons=[]
    signed_ai=provenance.get('signature_trusted') and provenance.get('asserts_ai_generation')
    signed_edit=provenance.get('signature_trusted') and provenance.get('asserts_generative_edit')
    if signed_ai:
        return 'LIKELY_AI_GENERATED',['A trusted Content Credential declares AI generation. This is a signed origin claim, not proof from the pixels.']
    if signed_edit:
        return 'LIKELY_MANIPULATED',['A trusted Content Credential declares generative editing. Localization may not identify every edit.']
    if not quality.get('adequate'):
        return 'INCONCLUSIVE',['Image quality or supported pixel coverage limits the available evidence.']+quality.get('limits',[])
    if not config.get('calibration_ready'):
        return 'INCONCLUSIVE',['Decision boundaries have not passed the required validation checks. Raw model scores remain available as evidence.']
    ai_alert=finite_probability(ai) and ai>=config['ai_alert']
    uncorroborated=ai_alert and config.get('ai_alert_corroboration_required') and not config.get('ai_alert_corroborated',False)
    if ai_alert and not uncorroborated:
        return 'LIKELY_AI_GENERATED',['The AI image classifier exceeds its validation-selected alert boundary. Generator coverage remains limited.']
    if finite_probability(manipulation) and manipulation>=config['manipulation_alert'] and regions:
        return 'LIKELY_MANIPULATED',['The manipulation model exceeds its validation-selected boundary and produced a supported pixel region.']
    if uncorroborated:
        return 'INCONCLUSIVE',['The experimental modern-generator head raises a warning, but the primary classifier does not corroborate it. This head failed an independent real-photo guard and cannot issue a standalone AI verdict.']
    if not finite_probability(ai):reasons.append('No usable AI generation model probability is available.')
    if not finite_probability(manipulation):reasons.append('No usable manipulation probability is available; a low AI score cannot establish authenticity.')
    if provenance.get('ai_markers'):reasons.append('Editable metadata mentions a generative tool and prevents an authenticity conclusion.')
    if provenance.get('asserts_ai_generation') or provenance.get('asserts_generative_edit'):
        reasons.append('An origin credential declares generation or generative editing; an untrusted signature cannot establish an untouched camera original.')
    if not reasons and ai<=config['ai_authentic'] and manipulation<=config['manipulation_authentic'] and not regions:
        if not config.get('authenticity_enabled',True):
            return 'NO_STRONG_INDICATORS',['The completed AI and edit checks found no strong signs within their supported scope. This does not prove the image is real or unedited; generative fill, object removal and face swaps can be missed.']
        return 'LIKELY_AUTHENTIC',['Both assessed evidence streams fall below their conservative validation boundaries, with adequate quality and no contradictory provenance. This does not prove an untouched camera original.']
    if not config.get('authenticity_enabled',True):
        reasons.append(config.get('authenticity_limit','Authenticity has not been validated for modern generators. Low model scores are insufficient.'))
    return 'INCONCLUSIVE',reasons or ['Available model evidence is weak, intermediate or conflicting. Verify the image with an independent source.']
