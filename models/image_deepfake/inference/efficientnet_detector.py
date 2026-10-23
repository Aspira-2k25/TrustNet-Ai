import time
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv
import numpy as np
import torch
import torchvision.models as models

load_dotenv()

from shared.schemas.detection_result import (
    DetectionResult,
    EvidenceItem,
    ModuleEnum,
    StatusEnum,
    NativeScoreSemanticsEnum
)
from models.image_deepfake.preprocessing.transforms import process_image_bytes
from models.image_deepfake.explainability.grad_cam import GradCAM
from models.image_deepfake.forensics.frequency_analyzer import FrequencyAnalyzer
from models.image_deepfake.forensics.ela_analyzer import ELAAnalyzer
from models.image_deepfake.forensics.noise_analyzer import NoiseAnalyzer
from models.image_deepfake.forensics.face_analyzer import FaceAnalyzer
from models.image_deepfake.forensics.pixel_morphing_analyzer import PixelMorphingAnalyzer
from models.image_deepfake.forensics.gabor_analyzer import GaborTextureAnalyzer
from models.image_deepfake.forensics.scene_analyzer import SceneContextAnalyzer
from models.image_deepfake.forensics.metadata_analyzer import MetadataAnalyzer
from models.image_deepfake.forensics.watermark_analyzer import WatermarkIconAnalyzer, WatermarkAnalyzer
from models.image_deepfake.forensics.recompression_analyzer import RecompressionAnalyzer
from models.image_deepfake.forensics.physics_eye_reflection_analyzer import PhysicsEyeReflectionAnalyzer
from models.image_deepfake.forensics.geometry_physics_analyzer import GeometryPhysicsAnalyzer
from models.image_deepfake.forensics.steganography_analyzer import SteganographyAnalyzer
from models.image_deepfake.inference.huggingface_client import HuggingFaceDeepfakeClient
from models.image_deepfake.inference.local_vit_detector import LocalViTDeepfakeDetector
from models.image_deepfake.inference.lm_studio_vision_client import LMStudioVisionClient

logger = logging.getLogger("trustnet.detector")


class BaseDetector:
    pass


class EfficientNetDetector(BaseDetector):
    """Versioned screening policy. Heuristics are observations, never authenticity votes."""
    def __init__(self, enable_explainability=True, policy=None, evaluation_candidate=False):
        import threading
        import os
        from types import SimpleNamespace
        from models.image_deepfake.inference.artifact import TrainedImageModel
        self.policy = policy or os.getenv('IMAGE_ASSESSMENT_POLICY', 'image-vit-v3')
        self.evaluation_candidate = evaluation_candidate
        if self.policy not in {'image-vit-v3', 'image-screening-v2', 'image-general-v4'}:
            raise ValueError('Unknown image assessment policy')
        self._lock = threading.Lock()
        self.cnn = (TrainedImageModel() if self.policy == 'image-screening-v2' else
                    SimpleNamespace(model=None, device='cpu', ready=False, manifest={}, error=None))
        self.model = self.cnn.model
        self.device = self.cnn.device
        self.enable_explainability = False
        self.grad_cam = None  # No ImageNet heatmap is presented as deepfake attribution.
        for name, factory in (
            ('freq_analyzer', FrequencyAnalyzer), ('ela_analyzer', ELAAnalyzer),
            ('noise_analyzer', NoiseAnalyzer), ('face_analyzer', lambda: FaceAnalyzer(localization='haar' if self.policy == 'image-screening-v2' else 'yunet')),
            ('pixel_analyzer', PixelMorphingAnalyzer), ('gabor_analyzer', GaborTextureAnalyzer),
            ('scene_analyzer', SceneContextAnalyzer), ('metadata_analyzer', MetadataAnalyzer),
            ('watermark_analyzer', WatermarkIconAnalyzer), ('recompression_analyzer', RecompressionAnalyzer),
            ('physics_analyzer', PhysicsEyeReflectionAnalyzer), ('geometry_analyzer', GeometryPhysicsAnalyzer),
            ('stego_analyzer', SteganographyAnalyzer)):
            setattr(self, name, factory())
        from models.image_deepfake.inference.general_image_client import GeneralImageClient
        self.general_client = GeneralImageClient() if self.policy == 'image-general-v4' else None
        self.hf_client = HuggingFaceDeepfakeClient()
        self.local_vit = self.hf_client.local_detector
        self.lm_studio_client = LMStudioVisionClient()

    def readiness(self):
        localization = self.face_analyzer.localizer.ready if self.face_analyzer.localizer else bool(self.face_analyzer.cascades and self.face_analyzer.eye_cascade is not None)
        if self.policy == 'image-general-v4':
            from models.image_deepfake.inference.general_policy import load
            state = self.general_client.readiness()
            operating = load(self.general_client.identity(), self.face_analyzer.localizer.identity, allow_candidate=self.evaluation_candidate)
            return {**state, 'policy':self.policy, 'localization':localization, 'decision_policy_validated':operating['validated'], 'decision_policy_note':operating['reason']}
        if self.policy == 'image-vit-v3':
            from models.image_deepfake.inference.vit_policy import load_policy
            loaded = self.local_vit._get_pipeline() is not None
            operating = load_policy(allow_candidate=self.evaluation_candidate, expected_revision=self.local_vit.revision)
            if operating['validated'] and operating.get('processor_sha256') != (self.local_vit.processor_identity or {}).get('sha256'):
                operating = {**operating, 'validated': False, 'reason': 'Runtime processor does not match the evaluated policy.'}
            return {'ready': bool(loaded and localization), 'vit_ready': loaded,
                    'localization': localization, 'policy': self.policy,
                    'model_error': self.local_vit._load_error,
                    'decision_policy_validated': operating['validated'],
                    'decision_policy_note': operating['reason']}
        return {'ready': bool(self.cnn.ready and localization),
                'trained_cnn': self.cnn.ready, 'model_error': self.cnn.error,
                'localization': localization, 'policy': 'image-screening-v2'}

    @staticmethod
    def _normalize(result, score_key=None):
        import math
        result = dict(result)
        message = str(result.get('finding') or result.get('note') or result.get('reason') or '')
        state = result.get('status', 'APPLIED')
        if 'fallback:' in message.lower() or state in {'FALLBACK', 'FAILED', 'UNAVAILABLE'}:
            state = 'UNAVAILABLE'
        if score_key and state == 'APPLIED':
            value = result.get(score_key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                state = 'UNAVAILABLE'
        result.pop('confidence', None)
        result['status'] = state
        if state != 'APPLIED' and score_key:
            result[score_key] = None
        return result

    def predict(self, input_data, scan_id=None, filename=None, enable_explanation=False):
        # Bound peak allocations and prevent shared mutable model state crossing requests.
        if not self._lock.acquire(blocking=False):
            return DetectionResult(scan_id=scan_id or str(uuid.uuid4()),module=ModuleEnum.image_deepfake,
                detector_id='image_deepfake.vit.v3' if self.policy == 'image-vit-v3' else 'image_deepfake.screening.v2',model_version=self.policy,preprocessing_version=self.policy,
                native_score=0,native_score_semantics=NativeScoreSemanticsEnum.anomaly_score,
                risk_score=0,confidence=0,label='unknown',verdict='UNKNOWN',status=StatusEnum.FAILED,
                timestamp=datetime.now(timezone.utc).isoformat(),error_code='INFERENCE_BUSY',
                metadata={'assessment_policy':self.policy, 'score_available':False},
                error_message='Image worker is busy; retry after the current scan completes.')
        try:
            return self._predict(input_data, scan_id, filename, enable_explanation)
        finally:
            self._lock.release()

    def _predict_vit(self, original, canonical, scan_id, filename, observations, jobs, started, explain):
        import hashlib
        from models.image_deepfake.inference.vit_policy import load_policy, scope_state
        face = observations['face']
        scope = scope_state(face)
        # Local candidate revision is established by loading its validated artifact.
        if scope == 'SUPPORTED':
            self.local_vit._get_pipeline()
        operating = load_policy(allow_candidate=self.evaluation_candidate, expected_revision=self.local_vit.revision)
        hf = {'is_hf_applied': False, 'note': 'Face model was not run outside assessed face scope.'}
        # One local backend owns all views. A skipped scope never falls through.
        if scope == 'SUPPORTED':
            full = self.local_vit.predict(canonical)
            hf = self.local_vit.predict_views(canonical, face['bounding_boxes'], full)
        if operating['validated'] and operating.get('processor_sha256') != (self.local_vit.processor_identity or {}).get('sha256'):
            operating = {**operating, 'validated': False, 'reason': 'Runtime processor does not match the evaluated policy.'}
        if face.get('localization_method') == 'opencv_yunet':
            operating = {**operating, 'validated':False, 'reason':'Face localizer changed; operating point requires independent revalidation.'}
        views = hf.get('face_predictions', [])
        scores = [v['risk_score'] for v in views if v.get('status') == 'APPLIED']
        score = max(scores) if scores else None
        complete = (scope == 'SUPPORTED' and 0 < len(views) == len(face['bounding_boxes']) <= 4
                    and all(v.get('status') == 'APPLIED' for v in views))
        missing = []
        if scope != 'SUPPORTED':
            missing.append(scope.lower())
        elif not complete:
            missing.append('detected_face_views')
        if score is None and scope == 'SUPPORTED':
            missing.append('vit_classifier')
        # Cross-view disagreement stays visible; no unvalidated numeric cutoff is used.
        frame = hf.get('full_frame_prediction', {'status': 'SKIPPED', 'risk_score': None})
        decisions = []
        if operating['validated']:
            decisions = ['high' if s >= operating['high'] else 'low' if s < operating['low'] else 'review'
                         for s in scores]
        disagreement = len(set(d for d in decisions if d != 'review')) > 1
        if score is None or not complete or not operating['validated'] or disagreement:
            verdict = 'UNSUPPORTED' if scope == 'NO_ASSESSABLE_FACE' else 'UNCERTAIN'
        else:
            verdict = ('LIKELY_AI_MANIPULATED' if score >= operating['high'] else
                       'LOW_MANIPULATION_SIGNAL' if score < operating['low'] else 'UNCERTAIN')
        reasons = []
        if scope == 'NO_ASSESSABLE_FACE':
            reasons.append('No assessable face detected. This face model cannot assess whole-image authorship; missed faces remain possible.')
        elif scope == 'LOCALIZATION_UNAVAILABLE':
            reasons.append('Face localization is unavailable; image authorship was not assessed.')
        if missing and scope == 'SUPPORTED':
            reasons.append('Required face assessment incomplete: ' + ', '.join(missing) + '.')
        if not operating['validated']:
            reasons.append(operating['reason'])
        if disagreement:
            reasons.append('Assessed face decisions disagree; manual review required.')
        reasons.append('Face scores are uncalibrated. The full-image score is diagnostic only; no camera provenance is established.')
        vision = {'status': 'SKIPPED'}
        if explain:
            try:
                vision = self.lm_studio_client.analyze(original, forensic_evidence={}, scene_type=observations['scene'].get('scene_type', 'unknown'))
            except Exception as error:
                vision = {'status': 'UNAVAILABLE', 'reason': str(error)}
        telemetry = [{'name': name, 'category': key, 'status': observations[key]['status'],
                      'finding': observations[key].get('finding') or observations[key].get('note'),
                      'reason': observations[key].get('reason'), 'measurement': observations[key].get(field)}
                     for key, name, engine, field, blob in jobs]
        telemetry.append({'name': 'Pinned local face ViT', 'category': 'primary_ml',
                          'status': 'APPLIED' if score is not None else 'SKIPPED' if scope != 'SUPPORTED' else 'UNAVAILABLE',
                          'finding': 'Face classifier only; full-frame result is diagnostic.', 'reason': hf.get('note') if score is None else None})
        telemetry.append({'name': 'LM Studio advisory vision', 'category': 'local_vision_reasoning',
                          'status': vision.get('status', 'UNAVAILABLE'), 'finding': vision.get('simple_explanation')})
        advisory_missing = [key for key, value in observations.items() if key != 'face' and value['status'] != 'APPLIED']
        metadata = {
            'assessment_policy': self.policy, 'scope': 'human-face screening', 'scope_state': scope,
            'score_available': score is not None, 'score_definition': 'Maximum assessed face ViT fake score; not whole-image authorship or confidence.',
            'confidence_available': False, 'confidence_definition': 'Not calibrated',
            'decision_policy_validated': operating['validated'], 'decision_policy': operating,
            'input_sha256': hashlib.sha256(original).hexdigest(),
            'preprocessing': 'exif-rgb-canonical-png; model-specific AutoImageProcessor',
            'hf_status': 'applied' if score is not None else 'unavailable', 'hf_risk_score': score,
            'hf_model': self.local_vit.model_name, 'hf_revision': self.local_vit.revision,
            'processor': getattr(self.local_vit, 'processor_identity', None),
            'localization_identity': face.get('localization_identity'),
            'generator_metadata': observations['metadata'],
            'inference_mode': 'local',
            'face_count': face.get('face_count', 0), 'face_boxes': face.get('bounding_boxes', []),
            'localization_available': face.get('localization_available', False),
            'model_views': {'full_frame': frame, 'faces': views, 'policy': 'face-max-v3',
                            'disagreement': disagreement, 'coverage_complete': complete,
                            'coverage_scope': 'detected regions only; missed faces cannot be counted'},
            'missing_required_checks': missing, 'advisory_unavailable': advisory_missing,
            'is_contradiction': disagreement, 'cross_domain_consistency': None,
            'why_reasons': reasons, 'vision_analysis': vision, 'observations': observations,
            'source_retention': 'not retained; upload again to inspect the original',
            'file_safety': {**observations['file_safety'], 'payload_detected': bool(observations['file_safety'].get('is_stego_detected')),
                            'affects_authorship_score': False},
            'decision_trace': [{'rule': 'face_max', 'score': score, 'frame_affects_decision': False},
                               {'rule': 'validated_operating_point_required', 'validated': operating['validated'], 'verdict': verdict}],
        }
        return DetectionResult(scan_id=scan_id, module=ModuleEnum.image_deepfake,
            detector_id='image_deepfake.vit.v3', model_version=self.local_vit.revision,
            preprocessing_version='face-crop-autoimageprocessor-v3',
            native_score=(score or 0) / 100, native_score_semantics=NativeScoreSemanticsEnum.anomaly_score,
            risk_score=score or 0, confidence=0, label='fake' if verdict == 'LIKELY_AI_MANIPULATED' else 'low_signal' if verdict == 'LOW_MANIPULATION_SIGNAL' else 'unknown',
            verdict=verdict, status=StatusEnum.SUCCESS if complete else StatusEnum.PARTIAL_SUCCESS,
            has_face=bool(face.get('has_face')), explanation=' '.join(reasons), metadata=metadata,
            analyzers=telemetry, evidence=[], vision_analysis=vision,
            processing_time_ms=int((time.monotonic() - started) * 1000), timestamp=datetime.now(timezone.utc).isoformat())

    def _predict(self, input_data, scan_id, filename, enable_explanation):
        import io
        import hashlib
        from PIL import Image
        from models.image_deepfake.preprocessing.validator import canonical_bytes
        started = time.monotonic()
        scan_id = scan_id or str(uuid.uuid4())
        try:
            canonical = canonical_bytes(input_data)
            jobs = [
                ('scene', 'Scene color/texture heuristic', self.scene_analyzer, 'scene_anomaly_score', canonical),
                ('metadata', 'Editable metadata clues', self.metadata_analyzer, 'metadata_anomaly_score', input_data),
                ('watermark', 'Corner shape heuristic', self.watermark_analyzer, 'watermark_anomaly_score', canonical),
                ('recompression', 'DCT block-grid heuristic', self.recompression_analyzer, 'recompression_score', input_data),
                ('face', 'Detected face boundary gradient heuristic', self.face_analyzer, 'boundary_anomaly_score', canonical),
                ('frequency', 'Frequency residual heuristic', self.freq_analyzer, 'spectral_anomaly_score', canonical),
                ('pixel', 'Pixel correlation heuristic', self.pixel_analyzer, 'pixel_morphing_score', canonical),
                ('gabor', 'Gabor texture heuristic', self.gabor_analyzer, 'gabor_anomaly_score', canonical),
                ('ela', 'JPEG recompression difference heuristic', self.ela_analyzer, 'ela_anomaly_score', canonical),
                ('noise', 'High-pass noise residual heuristic', self.noise_analyzer, 'noise_anomaly_score', canonical),
                ('file_safety', 'File trailer and bit-plane inspection', self.stego_analyzer, 'stego_anomaly_score', input_data),
            ]
            observations, analyzers = {}, []
            # At most two full-resolution analyzers allocate simultaneously.
            def run(job):
                key, name, engine, score_key, blob = job
                try:
                    value = engine.analyze(blob, filename) if key == 'metadata' else engine.analyze(blob)
                    return key, self._normalize(value, score_key)
                except Exception as error:
                    return key, {'status': 'UNAVAILABLE', score_key: None, 'reason': str(error)}
            with ThreadPoolExecutor(max_workers=2) as pool:
                observations.update(pool.map(run, jobs))
            face = observations['face']
            boxes = face.get('bounding_boxes', [])
            has_face = bool(face.get('has_face')) and face['status'] == 'APPLIED'
            scene = observations['scene']
            scene_type = scene.get('scene_type', 'unknown')
            if self.policy == 'image-general-v4':
                from models.image_deepfake.inference.general_screening import predict
                return predict(self, input_data, canonical, scan_id, observations, jobs, started)
            if self.policy == 'image-vit-v3':
                return self._predict_vit(input_data, canonical, scan_id, filename, observations,
                                         jobs, started, enable_explanation)
            hf = self.hf_client.predict(canonical, has_face=has_face, scene_type=scene_type)
            if not hf.get('is_hf_applied'):
                hf = self.local_vit.predict(canonical, has_face=has_face, scene_type=scene_type)
            if has_face and hasattr(self.local_vit, 'predict_views'):
                hf = self.local_vit.predict_views(canonical, boxes, hf)
            cnn = {'status': 'UNAVAILABLE', 'risk_score': None, 'reason': self.cnn.error}
            cnn_views = []
            if self.cnn.ready:
                if self.cnn.manifest['scope'] == 'general_image':
                    cnn_views.append(self.cnn.predict(canonical))
                elif has_face:
                    image = Image.open(io.BytesIO(canonical))
                    for x, y, w, h in sorted(boxes, key=lambda b:b[2]*b[3], reverse=True)[:4]:
                        if min(w, h) < 48 or x < 0 or y < 0 or x+w > image.width or y+h > image.height:
                            continue
                        stream = io.BytesIO(); image.crop((x,y,x+w,y+h)).save(stream, format='PNG')
                        cnn_views.append(self.cnn.predict(stream.getvalue()))
                if cnn_views:
                    cnn = max(cnn_views, key=lambda value:value['risk_score'])
            required = ['frequency', 'pixel', 'gabor', 'ela', 'noise', 'scene']
            missing = [key for key in required if observations[key]['status'] != 'APPLIED']
            if face.get('localization_available') is False or face['status'] == 'UNAVAILABLE':
                missing.append('localization')
            if cnn['status'] != 'APPLIED':
                missing.append('trained_cnn')
            if hf.get('inference_mode') == 'hosted_unpinned':
                missing.append('secondary_model_revision')
            if has_face and (hf.get('view_coverage_complete') is False or len(boxes) > 4):
                missing.append('detected_face_views')
            if scene_type in {'portrait','photograph_portrait'} and not has_face:
                missing.append('portrait_localization')
            # A face specialist cannot establish whole-scene authorship without a located face.
            if self.cnn.ready and self.cnn.manifest['scope'] == 'face' and not has_face:
                missing.append('face_model_scope')
            vit_available = bool(hf.get('is_hf_applied'))
            vit_score = float(hf['hf_risk_score']) if vit_available else None
            if vit_score is not None and (not np.isfinite(vit_score) or not 0 <= vit_score <= 100):
                vit_available, vit_score = False, None
            model_scores = [v['risk_score'] for v in cnn_views]
            if has_face and vit_score is not None:
                model_scores.append(vit_score)
            disagreement = bool(hf.get('model_view_disagreement')) or bool(
                model_scores and min(model_scores) <= 25 and max(model_scores) >= 70)
            # The trained checkpoint is the primary classifier. The ViT is a visible
            # diagnostic fallback when that artifact is missing, never a substitute.
            risk = float(cnn['risk_score'] if cnn['status'] == 'APPLIED' else vit_score if vit_score is not None else 50)
            risk = round(risk, 2)
            incomplete = bool(missing)
            verdict = ('UNCERTAIN' if incomplete or disagreement or 40 <= risk < 62 else
                       'LIKELY_AI_MANIPULATED' if risk >= 62 else 'LOW_MANIPULATION_SIGNAL')
            label = 'uncertain' if verdict == 'UNCERTAIN' else 'fake' if risk >= 62 else 'low_signal'
            reasons = []
            if disagreement: reasons.append('Full-image, face, or trained-model scores disagree; manual review required.')
            if missing: reasons.append('Required assessment unavailable: ' + ', '.join(sorted(set(missing))) + '.')
            reasons.append('Model scores are uncalibrated; low signal does not establish authenticity.')
            explanation = ' '.join(reasons)
            vision = {'status':'SKIPPED', 'model_name':None, 'simple_explanation':None}
            if enable_explanation:
                try:
                    vision = self.lm_studio_client.analyze(input_data, forensic_evidence={}, scene_type=scene_type)
                except Exception as error:
                    vision = {'status':'UNAVAILABLE','reason':str(error)}
                reasons.append('Optional vision observations are advisory and do not change the screening score.')
            # Eye/geometry proxies are optional observations, not physical proof or scoring votes.
            extra_engine = self.physics_analyzer if has_face else self.geometry_analyzer
            extra_key = 'physics' if has_face else 'geometry'
            try:
                observations[extra_key] = self._normalize(extra_engine.analyze(canonical))
            except Exception as error:
                observations[extra_key] = {'status':'UNAVAILABLE','reason':str(error)}
            extra = observations[extra_key]
            extra['proxy_threshold_crossed'] = extra.pop('is_physics_violation', extra.pop('is_geometry_violation', False))
            extra['proxy_score'] = extra.pop('physics_anomaly_score', extra.pop('geometry_anomaly_score', None))
            for key,name,engine,score_key,blob in jobs:
                value = observations[key]
                analyzers.append({'name':name, 'category':key, 'status':value['status'],
                                  'finding':value.get('finding') or value.get('note'),
                                  'reason':value.get('reason'), 'measurement':value.get(score_key)})
            analyzers.extend([
                {'name':'Trained EfficientNet-B0 classifier', 'category':'primary_ml', 'status':cnn['status'],
                 'finding':f"Fake score: {cnn['risk_score']}/100" if cnn['status']=='APPLIED' else None,
                 'reason':cnn.get('reason')},
                {'name':'Face ViT classifier', 'category':'secondary_ml', 'status':'APPLIED' if vit_available else 'UNAVAILABLE',
                 'finding':hf.get('note'), 'reason':None if vit_available else hf.get('note')},
                {'name':'LM Studio advisory vision', 'category':'local_vision_reasoning', 'status':vision.get('status','UNAVAILABLE'),
                 'finding':vision.get('simple_explanation'), 'reason':vision.get('reason')},
                {'name':'Eye highlight proxy' if has_face else 'Edge-distribution proxy', 'category':'advisory_proxy',
                 'status':observations[extra_key]['status'], 'finding':observations[extra_key].get('finding')},
            ])
            file_safety = observations['file_safety']
            metadata = {
                'assessment_policy':'image-screening-v2', 'confidence_available':False,
                'confidence_definition':'Correctness confidence has not been calibrated.',
                'score_definition':'Primary trained CNN score; diagnostic ViT fallback when the primary artifact is unavailable. Heuristics and file safety do not vote.',
                'input_sha256':hashlib.sha256(input_data).hexdigest(),
                'preprocessing':'exif-rgb-still-resize224-imagenet-v2',
                'cnn_status':cnn['status'], 'cnn_risk_score':cnn['risk_score'],
                'cnn_artifact':{key:self.cnn.manifest.get(key) for key in ('architecture','scope','weights_sha256','dataset_index_sha256','preprocessing','data_kind')}, 'cnn_error':self.cnn.error,
                'hf_status':'applied' if vit_available else 'unavailable', 'hf_risk_score':vit_score,
                'hf_model':hf.get('model_name'), 'hf_revision':None if hf.get('inference_mode')=='hosted_unpinned' else getattr(self.local_vit,'revision',None),
                'face_count':face.get('face_count',0), 'face_boxes':boxes,
                'localization_available':face.get('localization_available',False),
                'scene_label':scene.get('scene_label'), 'scene_type':scene_type,
                'model_views':{'full_frame':hf.get('full_frame_prediction',{'risk_score':vit_score}),
                    'faces':hf.get('face_predictions',[]), 'cnn':cnn_views,
                    'policy':'frame-and-faces-v2', 'disagreement':disagreement,
                    'coverage_complete':not incomplete, 'coverage_scope':'detected regions only; undiscovered faces cannot be counted'},
                'missing_required_checks':sorted(set(missing)), 'is_contradiction':disagreement,
                'cross_domain_consistency':None, 'provenance_verified':False, 'ai_signature_found':False,
                'why_reasons':reasons, 'vision_analysis':vision, 'lm_studio_status':vision.get('status'),
                'lm_studio_model':vision.get('model_name'),
                'watermark_found':bool(observations['watermark'].get('is_watermark_found')),
                'watermark_anomaly_score':observations['watermark'].get('watermark_anomaly_score'),
                'file_safety':{'status':file_safety['status'], 'payload_detected':bool(file_safety.get('is_stego_detected')),
                    'finding':file_safety.get('finding'), 'affects_authorship_score':False},
                'source_retention':'not retained; upload again to inspect the original',
                'decision_trace':[{'rule':'primary_cnn' if cnn['status']=='APPLIED' else 'diagnostic_vit_fallback',
                    'score':risk, 'artifact_ready':self.cnn.ready},
                    {'rule':'abstain_on_missing_or_disagreement', 'missing':sorted(set(missing)),
                     'disagreement':disagreement, 'verdict':verdict}],
                'observations':observations,
            }
            return DetectionResult(scan_id=scan_id,module=ModuleEnum.image_deepfake,
                detector_id='image_deepfake.screening.v2',model_version='v2',preprocessing_version=metadata['preprocessing'],
                native_score=risk/100,native_score_semantics=NativeScoreSemanticsEnum.anomaly_score,
                risk_score=risk,confidence=0,label=label,verdict=verdict,explanation=explanation,
                status=StatusEnum.PARTIAL_SUCCESS if incomplete else StatusEnum.SUCCESS,
                has_face=has_face,evidence=[],analyzers=analyzers,metadata=metadata,vision_analysis=vision,
                processing_time_ms=int((time.monotonic()-started)*1000),timestamp=datetime.now(timezone.utc).isoformat())
        except Exception as error:
            return DetectionResult(scan_id=scan_id,module=ModuleEnum.image_deepfake,
                detector_id='image_deepfake.vit.v3' if self.policy == 'image-vit-v3' else 'image_deepfake.screening.v2',model_version=self.policy,preprocessing_version=self.policy,
                native_score=0,native_score_semantics=NativeScoreSemanticsEnum.anomaly_score,
                risk_score=0,confidence=0,label='unknown',verdict='UNKNOWN',status=StatusEnum.FAILED,
                timestamp=datetime.now(timezone.utc).isoformat(),error_code='INFERENCE_FAILED',error_message=str(error),
                metadata={'assessment_policy':self.policy, 'score_available':False})
