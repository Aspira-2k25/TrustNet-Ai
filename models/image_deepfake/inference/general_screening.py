"""General branch is independent of face presence. Metadata never determines its score."""
import hashlib
import os
import time
from datetime import datetime, timezone

from shared.schemas.detection_result import DetectionResult, ModuleEnum, StatusEnum, NativeScoreSemanticsEnum
from models.image_deepfake.inference.general_policy import load, POLICY


def predict(detector, original, canonical, scan_id, observations, jobs, started):
    client = detector.general_client
    general = client.predict(canonical)
    face = observations['face']
    face_result = {'status':'SKIPPED','risk_score':None,'reason':'Optional face specialist not enabled; does not vote in the general-image policy.'}
    if os.getenv('IMAGE_GENERAL_FACE_DIAGNOSTIC','false').lower() == 'true' and face.get('has_face') and face.get('status') == 'APPLIED':
        full = detector.local_vit.predict(canonical)
        face_result = detector.local_vit.predict_views(canonical,face['bounding_boxes'],full)
        face_result['status'] = 'APPLIED' if face_result.get('view_coverage_complete') else 'UNAVAILABLE'
        face_result['affects_decision'] = False
    score = general.get('risk_score') if general.get('status') == 'APPLIED' else None
    localizer = face.get('localization_identity') or (detector.face_analyzer.localizer.identity if detector.face_analyzer.localizer else None)
    operating = load(client.identity(),localizer,allow_candidate=detector.evaluation_candidate)
    verdict = 'UNCERTAIN'
    if score is not None and operating['validated']:
        verdict = ('LIKELY_AI_MANIPULATED' if score >= operating['high'] else
                   'LOW_MANIPULATION_SIGNAL' if score < operating['low'] else 'UNCERTAIN')
    reasons = [operating['reason'], general.get('limits',''), 'Model scores are not calibrated confidence or proof of camera origin.']
    if score is None:
        reasons.insert(0,'Whole-image classifier unavailable: '+general.get('reason','unknown'))
    provenance = observations['metadata']
    if provenance.get('has_unverified_generator_clue'):
        reasons.append(provenance.get('finding','Unverified generator metadata clue found.'))
    analyzers = [{'name':name,'category':key,'status':observations[key]['status'],
                  'finding':observations[key].get('finding'),'reason':observations[key].get('reason')}
                 for key,name,*_ in jobs]
    analyzers.append({'name':'Pretrained whole-image classifier','category':'primary_ml','status':general['status'],
                      'finding':f'Whole-image AI signal: {score:.2f}/100 (uncalibrated).' if score is not None else None,
                      'reason':general.get('reason')})
    metadata = {'assessment_policy':POLICY,'scope':general.get('scope','whole-image AI screening'),'scope_state':'SUPPORTED' if score is not None else 'CLASSIFIER_UNAVAILABLE',
                'score_available':score is not None,'confidence_available':False,'confidence_definition':'Not calibrated',
                'score_definition':'Registered whole-image classifier signal; face diagnostics, heuristics and metadata do not vote.',
                'decision_policy_validated':operating['validated'],'decision_policy':operating,
                'input_sha256':hashlib.sha256(original).hexdigest(),'preprocessing':'exif-rgb-canonical-png; registered model processor',
                'branches':{'general':general,'face':face_result},'generator_metadata':provenance,
                'hf_model':client.config.model,'hf_revision':general.get('model_revision'),
                'hf_status':'applied' if score is not None else 'unavailable','hf_risk_score':score,
                'inference_mode':client.config.backend,'model_identity':client.identity(),'localization_identity':localizer,
                'face_count':face.get('face_count',0),'face_boxes':face.get('bounding_boxes',[]),
                'localization_available':face.get('localization_available',False),
                'model_views':{'full_frame':general,'faces':face_result.get('face_predictions',[]),
                               'coverage_complete':score is not None,'policy':'general_only_face_diagnostic'},
                'missing_required_checks':[] if score is not None else ['general_image_classifier'],
                'observations':observations,'why_reasons':reasons,'source_retention':'not retained; re-upload original to inspect',
                'file_safety':{**observations['file_safety'],'affects_authorship_score':False}}
    return DetectionResult(scan_id=scan_id,module=ModuleEnum.image_deepfake,detector_id='image_deepfake.general.v4',
        model_version=general.get('model_revision') or 'hosted-unpinned',preprocessing_version=POLICY,
        native_score=(score or 0)/100,native_score_semantics=NativeScoreSemanticsEnum.anomaly_score,
        risk_score=score or 0,confidence=0,label='fake' if verdict=='LIKELY_AI_MANIPULATED' else 'low_signal' if verdict=='LOW_MANIPULATION_SIGNAL' else 'unknown',
        verdict=verdict if score is not None else 'UNKNOWN',status=StatusEnum.SUCCESS if score is not None else StatusEnum.UNAVAILABLE,
        error_code=None if score is not None else general.get('reason','GENERAL_MODEL_UNAVAILABLE'),
        error_message=None if score is not None else 'Whole-image assessment could not run.',
        metadata=metadata,explanation=' '.join(filter(None,reasons)),analyzers=analyzers,has_face=bool(face.get('has_face')),
        processing_time_ms=round((time.monotonic()-started)*1000),timestamp=datetime.now(timezone.utc).isoformat())
