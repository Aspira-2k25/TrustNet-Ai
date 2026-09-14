import io
from typing import Dict, Any, Optional
from PIL import Image

class LocalViTDeepfakeDetector:
    """
    Offline fallback for the learned deep-model signal.

    The existing HuggingFaceDeepfakeClient calls the paid, rate-limited
    HF Inference API over HTTP. When the account runs out of monthly
    credits (HTTP 402) or gets rate-limited (403), `is_hf_applied` becomes
    False and the entire "primary_ml" signal drops out of the fusion
    with zero weight (see efficientnet_detector.py, anomaly_weights list) --
    that's root cause #1 in the false-negative report.

    This class downloads the SAME model weights once from the HF Hub
    (a one-time, free download, not an API call) and runs inference
    locally with `transformers`, so there is no per-request cost, no
    rate limit, and no dependency on API credits ever again.

    Usage: call this INSTEAD of / AS A FALLBACK to HuggingFaceDeepfakeClient
    when `hf_res["is_hf_applied"]` is False. Same return-dict shape, so it's
    a drop-in replacement in the fusion code.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        face_model_name: Optional[str] = None,
        general_model_name: Optional[str] = None
    ):
        self.face_model_name = face_model_name or model_name or "dima806/deepfake_vs_real_image_detection"
        self.model_name = self.face_model_name
        self.general_model_name = None

        self._pipeline = None
        self._load_error: Optional[str] = None

    def _get_pipeline(self):
        if self._pipeline is None and self._load_error is None:
            try:
                from transformers import pipeline
                # device=-1 forces CPU; change to 0 if a CUDA GPU is available.
                self._pipeline = pipeline(
                    "image-classification",
                    model=self.model_name,
                    device=-1,
                )
            except Exception as e:
                self._pipeline = None
                self._load_error = str(e)
        return self._pipeline

    def is_configured(self) -> bool:
        return True

    def predict(self, image_bytes: bytes, has_face: bool = True, scene_type: str = "general_object") -> Dict[str, Any]:
        """
        Runs local offline inference using dima806/deepfake_vs_real_image_detection.
        Evaluates deepfake vs real classification directly without external API dependencies.
        """
        target_model = self.model_name
        is_face_only_model = any(k in target_model.lower() for k in ["face", "portrait", "deepfake_vs_real"])
        is_strictly_non_human = (not has_face) and (scene_type not in ["photograph_portrait"])
        if is_face_only_model and is_strictly_non_human and not self.general_model_name:
            return {
                "is_hf_applied": False,
                "hf_risk_score": 50.0,
                "hf_label": "unknown",
                "hf_confidence": 0.0,
                "model_name": target_model,
                "note": f"Local ViT ({target_model}) skipped: image does not contain a human face (scene: {scene_type}). Face specialist model is not applicable to non-human subjects."
            }

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
            results = pipe(image)  # list of {"label": ..., "score": ...}

            fake_score = 0.5
            real_score = 0.5
            for item in results:
                lbl = str(item.get("label", "")).upper()
                score = float(item.get("score", 0.5))
                # Handles dima806 ('REAL' / 'FAKE') labels
                if any(k in lbl for k in ["FAKE", "SYNTHETIC", "DEEPFAKE", "AI", "ARTIFICIAL", "LABEL_1"]):
                    fake_score = score
                elif any(k in lbl for k in ["REAL", "ORIGINAL", "AUTHENTIC", "HUMAN", "LABEL_0"]):
                    real_score = score

            risk_score = round(fake_score * 100.0, 2)
            confidence = max(fake_score, real_score)
            label = "fake" if risk_score >= 50.0 else "real"

            return {
                "is_hf_applied": True,
                "hf_risk_score": risk_score,
                "hf_label": label,
                "hf_confidence": round(confidence, 2),
                "model_name": f"{target_model} (local)",
                "note": f"Local ViT ({target_model}) evaluated image offline with {confidence*100:.1f}% confidence. "
                        f"No API credits used.",
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
