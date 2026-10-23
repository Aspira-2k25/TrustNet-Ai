import io
import math
import os
import time
import threading
from models.image_deepfake.inference.classifier_contract import parse_binary_predictions
from typing import Dict, Any, Optional
from PIL import Image

class LocalViTDeepfakeDetector:
    """Pinned local ViT with bounded, separately recorded frame and face views.

    Model scores are uncalibrated. Scope routing belongs to the serving policy;
    direct prediction is also available to explicitly labeled benchmark runs.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        face_model_name: Optional[str] = None,
        general_model_name: Optional[str] = None
    ):
        self.face_model_name = face_model_name or model_name or "dima806/deepfake_vs_real_image_detection"
        self.model_name = self.face_model_name
        if general_model_name is not None:
            raise ValueError('Use a trained general_image CNN artifact; no second general ViT is implemented')
        self.general_model_name = None

        self.processor_identity = None
        self._pipeline = None
        self._load_error = None
        self._load_lock = threading.Lock()
        self._last_attempt = 0.0
        self.revision = os.getenv('HF_DEEPFAKE_REVISION', '29e4cf9efc543845610045f6ba7e88e5cf9d9301')
        self.artifact_directory = os.getenv('IMAGE_VIT_MODEL_DIR')

    def _get_pipeline(self):
        with self._load_lock:
            if self._pipeline is not None:
                return self._pipeline
            if self._load_error and time.monotonic() - self._last_attempt < 30:
                return None
            self._last_attempt = time.monotonic()
            try:
                import torch
                from transformers import pipeline, AutoImageProcessor, AutoModelForImageClassification
                options = dict(revision=self.revision,
                               local_files_only=os.getenv('IMAGE_ALLOW_MODEL_DOWNLOAD', 'false').lower() != 'true')
                source = self.model_name
                if self.artifact_directory:
                    from models.image_deepfake.inference.vit_artifact import validate
                    artifact = validate(self.artifact_directory)
                    self.revision = artifact['revision']
                    source = self.artifact_directory
                    options = dict(local_files_only=True)
                processor = AutoImageProcessor.from_pretrained(source, **options)
                model = AutoModelForImageClassification.from_pretrained(source, **options)
                if {str(v).lower() for v in model.config.id2label.values()} != {'real', 'fake'}:
                    raise ValueError('Model does not implement the real/fake label contract')
                import hashlib, json
                config = processor.to_dict()
                self.processor_identity = {'class': type(processor).__name__, 'config': config,
                    'sha256': hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()}
                self._pipeline = pipeline('image-classification', model=model, image_processor=processor,
                                          device=0 if torch.cuda.is_available() else -1)
                self._load_error = None
            except Exception as error:
                self._load_error = str(error)
            return self._pipeline

    def is_configured(self) -> bool:
        return self._pipeline is not None

    def predict_views(self, image_bytes, face_boxes, full_result):
        """Preserve frame and bounded face scores; disagreement is not certainty.

        The maximum is a screening index, not a calibrated multi-view probability.
        Only detector-provided, in-bounds boxes may be assessed. No skin fallback.
        """
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        width, height = image.size
        valid, rejected = [], 0
        for box in face_boxes:
            if (not isinstance(box, (list, tuple)) or len(box) != 4
                    or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in box)):
                rejected += 1
                continue
            x, y, w, h = map(int, box)
            if x < 0 or y < 0 or min(w, h) < 48 or x + w > width or y + h > height:
                rejected += 1
                continue
            if (x, y, w, h) not in valid:
                valid.append((x, y, w, h))
        valid.sort(key=lambda box: box[2] * box[3], reverse=True)
        faces = []
        def valid_score(prediction):
            value = prediction.get('hf_risk_score')
            return (bool(prediction.get('is_hf_applied'))
                    and isinstance(value, (int, float)) and not isinstance(value, bool)
                    and math.isfinite(value) and 0 <= value <= 100)

        scores = []
        full_available = valid_score(full_result)
        if full_available:
            scores.append(float(full_result['hf_risk_score']))
        for index, (x, y, w, h) in enumerate(valid[:4]):
            stream = io.BytesIO()
            image.crop((x, y, x + w, y + h)).save(stream, format='PNG')
            prediction = self.predict(stream.getvalue())
            available = valid_score(prediction)
            score = float(prediction['hf_risk_score']) if available else None
            faces.append({'index': index, 'box': [x, y, w, h],
                          'status': 'APPLIED' if available else 'UNAVAILABLE',
                          'risk_score': score, 'model_name': prediction.get('model_name'), 'revision': prediction.get('revision'),
                          'processor': prediction.get('processor'), 'crop_policy': 'detected-box-padding-0-v1'})
            if available:
                scores.append(score)
        complete = (full_available and bool(valid) and rejected == 0
                    and len(valid) <= 4 and all(p['status'] == 'APPLIED' for p in faces))
        disagreement = bool(scores and min(scores) <= 25 and max(scores) >= 70)
        result = dict(full_result)
        result.update(full_frame_prediction={
            'status': 'APPLIED' if full_available else 'UNAVAILABLE',
            'risk_score': full_result.get('hf_risk_score') if full_available else None,
            'model_name': full_result.get('model_name'), 'revision': full_result.get('revision'),
            'processor': full_result.get('processor'), 'backend': 'local',
        }, face_predictions=faces, model_view_disagreement=disagreement,
            view_coverage_complete=complete, faces_detected=len(face_boxes),
            faces_assessed=len(faces), view_policy='frame-and-faces-v1',
            aggregation='maximum model fake score; uncalibrated screening index')
        if scores:
            result.update(is_hf_applied=True, hf_risk_score=max(scores),
                          hf_label='fake' if max(scores) >= 50 else 'real', hf_confidence=0.0)
        else:
            result.update(is_hf_applied=False, hf_risk_score=50.0,
                          hf_label='unknown', hf_confidence=0.0)
        result['note'] = ('Frame and face model scores disagree; manual review required.' if disagreement else
                          'Frame and bounded face scores recorded; camera origin is not verified.')
        return result

    def predict(self, image_bytes: bytes, has_face: bool = True, scene_type: str = "general_object") -> Dict[str, Any]:
        """
        Runs local offline inference using dima806/deepfake_vs_real_image_detection.
        Evaluates deepfake vs real classification directly without external API dependencies.
        """
        target_model = self.model_name
        pipe = self._get_pipeline()

        if pipe is None:
            return {
                "is_hf_applied": False,
                "hf_risk_score": 50.0,
                "hf_label": "unknown",
                "hf_confidence": 0.0,
                "model_name": target_model,
                "note": f"Local ViT fallback unavailable: {self._load_error or 'model not loaded'}. "
                        f"Run `pip install transformers` and ensure model weights can be downloaded once.",
            }

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            results = pipe(image, top_k=None)

            risk_score = parse_binary_predictions(results)
            confidence = 0.0
            label = 'fake' if risk_score >= 50 else 'real'

            return {
                "is_hf_applied": True,
                "hf_risk_score": risk_score,
                "hf_label": label,
                "hf_confidence": round(confidence, 2),
                "model_name": f"{target_model} (local)",
                "revision": self.revision, "inference_mode": "local", "processor": self.processor_identity,
                "note": f"Local ViT ({target_model}) fake score: {risk_score:.2f}/100. "
                        "Model scores are uncalibrated and do not verify camera origin.",
            }
        except Exception as e:
            return {
                "is_hf_applied": False,
                "hf_risk_score": 50.0,
                "hf_label": "unknown",
                "hf_confidence": 0.0,
                "model_name": target_model,
                "note": f"Local ViT inference error: {str(e)}",
            }
