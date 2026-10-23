"""Independent image evidence streams with explicit calibrated coverage limits."""
import io
import hashlib
import json
from pathlib import Path
import time
import uuid
import os
from datetime import datetime,timezone
import numpy as np
import cv2
from PIL import Image,ImageOps
from shared.schemas.detection_result import DetectionResult
from shared.constants.modules import ModuleEnum
from shared.constants.status import StatusEnum
from shared.constants.native_score_semantics import NativeScoreSemanticsEnum
from models.image_deepfake.forensics.source_evidence import inspect_source,inspect_c2pa
from models.image_deepfake.forensics.localization_output import assets
from models.image_deepfake.inference.decision import decide
from models.image_deepfake.inference.global_classifier import GlobalClassifier
from models.image_deepfake.inference.localizer_backend import create_localizer
from models.image_deepfake.inference.feature_head import head_score,policy_score,sigmoid,logit

ROOT=Path(__file__).resolve().parents[1]


def calibrated(score,config):
    if score is not None and config.get('kind')=='platt_logit':
        return sigmoid(config['coef']*logit(score)+config['intercept'])
    return float(np.interp(score,config['x'],config['y'])) if score is not None else None


class ForensicDetector:
    def __init__(self, model_name=None):
        import torch
        torch.set_num_threads(2)
        self.config=json.loads((ROOT/'calibration/evidence-v2.json').read_text())
        hf_pref = model_name or os.getenv('HF_DEEPFAKE_MODEL', 'buildborderless/CommunityForensics-DeepfakeDet-ViT')
        self.modern_head=None
        if hf_pref in ('dima806','dima806/deepfake_vs_real_image_detection'):
            # An explicit rollback must not silently load another model/profile.
            self.global_model=GlobalClassifier('dima806')
            self.model_name='dima806'
        elif hf_pref in ('community','buildborderless/CommunityForensics-DeepfakeDet-ViT'):
            manifest=json.loads((ROOT/'calibration/global-artifacts.json').read_text())
            for name,entry in manifest['files'].items():
                with (ROOT/'artifacts/global'/name).open('rb') as stream:
                    if hashlib.file_digest(stream,'sha256').hexdigest()!=entry['sha256']:
                        raise ValueError('Image classifier integrity failed: '+name)
            self.global_model=GlobalClassifier('community',ROOT/'artifacts/global')
            self.model_name='community'
            if self.config.get('modern_head_sha256'):
                data=(ROOT/'calibration/modern-feature-head.json').read_bytes()
                if hashlib.sha256(data).hexdigest()!=self.config['modern_head_sha256']:
                    raise ValueError('Modern image head integrity failed')
                self.modern_head=json.loads(data)
        else:
            raise ValueError('Unsupported image model selection; use community or the explicit dima806 rollback')
        self.localizer=None
        self.localizer_error=None
        try:
            self.localizer=create_localizer(os.getenv('IMAGE_LOCALIZER_BACKEND','trufor'))
            if self.localizer is None:
                self.localizer_error='Pixel localization is disabled. Editing cannot be ruled out.'
        except (ImportError,OSError,ValueError) as exc:
            self.localizer_error=f'Analysis incomplete: edit checker unavailable ({type(exc).__name__}): {str(exc)[:200]}'

    def predict(self,image_bytes,scan_id=None,filename=None,enable_explanation=True):
        started=time.monotonic()
        source=inspect_source(image_bytes)
        source['provenance'].update(inspect_c2pa(image_bytes,source['mime_type']))
        provenance=source['provenance']; quality=source['quality']
        global_result=self.global_model.predict(image_bytes,return_embedding=self.modern_head is not None)
        modern_raw=head_score(global_result.pop('embedding'),self.modern_head) if self.modern_head else None

        model_name=getattr(self,'model_name','community')
        if model_name=='dima806':
            ai_raw=float(global_result['ai_score'])
            ai_prob=ai_raw
        else:
            ai_raw=policy_score(global_result['ai_score'],modern_raw,self.config['ai']) if self.modern_head else global_result['ai_score']
            ai_prob=calibrated(ai_raw,self.config['ai'])

        manipulation_prob=None; manipulation_raw=None; regions=[]; encoded={}
        local_note=self.localizer_error or ''
        local=None
        if self.localizer:
            try:
                local_budget=int(os.getenv('IMAGE_LOCALIZER_TIMEOUT','75'))
                local=self.localizer.predict(image_bytes,time_budget=max(.1,local_budget-(time.monotonic()-started)))
                covered=local['inference_mode']=='native' and source['format']=='JPEG'
                manipulation_raw=float(local['raw_score'])
                manipulation_prob=calibrated(manipulation_raw,self.config['manipulation'])
                with Image.open(io.BytesIO(image_bytes)) as image:
                    rgb=np.asarray(ImageOps.exif_transpose(image).convert('RGB'))
                encoded,regions=assets(rgb,local['heatmap'],local['reliability'],self.config)
                has_suspicious_pixel=bool(manipulation_raw is not None and manipulation_raw>=self.config['manipulation']['raw_alert'] and regions)
                if not has_suspicious_pixel:
                    regions=[]
                    from models.image_deepfake.forensics.localization_output import encode_png
                    encoded['mask']=encode_png(np.zeros(rgb.shape[:2],np.uint8))
                local_note=('Native JPEG score calibrated on synthetic splice and copy-move validation. ' if covered else
                    f"Segmentation computed in {local['inference_mode']} mode. ")
                local_note+='Heatmaps are model estimates; a coloured pixel alone is not a confirmed edit. TruFor is licensed for nonprofit/informational use.'
            except (ValueError,RuntimeError,MemoryError) as exc:
                local_note=f'Localization unavailable: {str(exc)[:200]}. No authenticity conclusion is drawn.'

        config={**self.config,
                'ai_alert': 0.50 if model_name=='dima806' else self.config['ai']['raw_alert'],
                'manipulation_alert':self.config['manipulation']['raw_alert'],
                'ai_alert_corroborated':True if model_name=='dima806' else (global_result['ai_score']>=self.config['ai']['primary_raw_alert'])}
        verdict,reasons=decide(ai_raw,manipulation_raw,provenance,quality,regions,config)
        head_only_warning=bool(ai_raw>=config['ai_alert'] and self.config.get('ai_alert_corroboration_required') and not config['ai_alert_corroborated'])
        if head_only_warning and not any('does not corroborate' in reason for reason in reasons):
            reasons.append('The experimental feature head raises a warning, but the primary classifier does not corroborate it. The mapped AI reading is not a supported AI verdict or a probability that this photo is fake.')
        if provenance.get('asserts_ai_generation') and not provenance.get('signature_trusted'):
            reasons.append('A Content Credential declares AI generation, but its signature or certificate trust could not be validated. This is an unverified origin claim, not proof from the pixels.')
        if provenance.get('ai_markers'):
            tools_list = sorted({c.get('tool') for c in provenance['ai_markers'] if c.get('tool')})
            reasons.append(f"Image metadata inspection identified AI tool signatures: {', '.join(tools_list[:4])}.")
        if manipulation_raw is None:reasons.append(local_note)

        probabilities=[p for p in [ai_prob,manipulation_prob] if p is not None]
        index=max(probabilities,default=0)*100
        spec_id = getattr(self.global_model, 'spec', {}).get('id') if (hasattr(self.global_model, 'spec') and isinstance(self.global_model.spec, dict)) else 'CommunityForensics-ViT'
        analysis=dict(ai_generated_prob=ai_prob,manipulation_prob=manipulation_prob,
            ai_raw_score=global_result['ai_score'],modern_generator_raw_score=modern_raw,
            ai_policy_score=ai_raw,manipulation_raw_score=manipulation_raw,
            provenance=provenance,quality=quality,regions=regions,reasons=reasons,
            source_sha256=source['sha256'],source=source,
            ai_note=f"Hugging Face {spec_id} Vision Transformer deepfake classifier running locally." if model_name=='dima806' else 'CommunityForensics ViT with a locally trained modern-generator feature head. Calibration uses limited reference collections and their class balance, not every generator or deployment prevalence. A low reading alone cannot establish authenticity.',
            localization_note=local_note,assets={},
            model_view_note=f"Original bytes retained. Classifier tensor {global_result['model_view_shape']}; localization uses native pixels or overlapping native tiles. Classifier attention is never a tamper mask.",
            localization_mode=local['inference_mode'] if local else None,
            calibration_version=self.config['version'])
        analysis['ai_decision_boundary']=config['ai_alert']
        analysis['ai_model_id']=spec_id
        analysis['authenticity_enabled']=bool(config.get('authenticity_enabled'))
        analysis['analysis_complete']=local is not None and manipulation_raw is not None
        analysis['ai_checks_disagree']=head_only_warning
        analysis['ai_reading_status']='quality_limited' if not quality.get('adequate') else 'conflicting_models' if head_only_warning else 'available'
        analysis['edit_coverage']={
            'evaluated':['Synthetic splicing','Synthetic copy-move','Small TGIF SD2 and Photoshop/Firefly partial-edit sample'],
            'not_established':['Generative fill / inpainting','Object removal','Face swap'],
            'policy':'Low scores do not rule out editing. Authenticity verdicts are disabled until broader independent validation passes.',
        }
        analysis['localizer_license']='Research only: TruFor permits nonprofit/informational use. Not licensed for unrestricted commercial deployment.' if self.localizer else 'No localization backend enabled.'

        try:
            from models.image_deepfake.forensics.supporting_signals import analyze
            supporting=analyze(image_bytes)
            encoded.update(supporting.pop('assets'))
            analysis['supporting_forensics']=supporting
        except (ValueError,OSError,RuntimeError,MemoryError,cv2.error) as exc:
            analysis['supporting_forensics']={'affects_verdict':False,'notice':f'Classical diagnostics unavailable ({type(exc).__name__}).'}

        if enable_explanation and time.monotonic()-started<25 and hasattr(self.global_model,'explain'):
            try:
                head=self.modern_head if (self.config['ai'].get('mode')=='isotonic_feature_head' and model_name!='dima806') else None
                attention=self.global_model.explain(image_bytes,feature_head=head)
                encoded['attention']=attention.pop('image')
                analysis['model_attention']=attention
            except (ValueError,OSError,RuntimeError,MemoryError,cv2.error,AttributeError) as exc:
                analysis['model_attention']={'note':f'Grad-CAM attention map unavailable ({type(exc).__name__}). This does not change the verdict.'}
        return DetectionResult(scan_id=scan_id or str(uuid.uuid4()),module=ModuleEnum.image_deepfake,
            detector_id='image_deepfake.evidence.v2',model_version=f"{spec_id} + TruFor",
            preprocessing_version='original-bytes-native-localization-v2',native_score=ai_raw,
            native_score_semantics=NativeScoreSemanticsEnum.anomaly_score,
            risk_score=round(index,2),confidence=0.,label=verdict,verdict=verdict,
            status=StatusEnum.SUCCESS if (local is not None and manipulation_raw is not None) else StatusEnum.PARTIAL_SUCCESS,explanation=' '.join(reasons),
            metadata={'image_analysis':analysis,'image_assets_base64':encoded,
                'score_semantics':'Maximum available calibrated stream reading; not a joint fraud probability. Confidence is not estimated.',
                'ai_generated_prob':ai_prob},processing_time_ms=round((time.monotonic()-started)*1000),
            timestamp=datetime.now(timezone.utc).isoformat())
