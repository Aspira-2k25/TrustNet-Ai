import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import httpx
from huggingface_hub import HfApi

from models.image_deepfake.inference.local_vit_detector import LocalViTDeepfakeDetector

load_dotenv()

class HuggingFaceDeepfakeClient:
    """
    Hugging Face Deepfake & General AI Image Inference Client.
    Connects to pre-trained classification models on Hugging Face Hub:
    - Face/Portrait specialist: dima806/deepfake_vs_real_image_detection
    - General synthetic scene specialist: umm-maybe/AI-image-detector
    Seamlessly falls back to local transformers execution on HTTP 402/403/rate limits.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        face_model_name: Optional[str] = None,
        general_model_name: Optional[str] = "DEFAULT"
    ):
        self.api_key = (api_key or os.getenv("HUGGINGFACE_API_KEY", "")).strip()
        self.face_model_name = (face_model_name or model_name or os.getenv("HF_DEEPFAKE_MODEL", "dima806/deepfake_vs_real_image_detection")).strip()
        self.model_name = self.face_model_name

        # If a specific single model was requested without general_model_name, restrict to that model
        if model_name is not None and general_model_name == "DEFAULT":
            self.general_model_name = None
        elif general_model_name == "DEFAULT":
            self.general_model_name = os.getenv("HF_GENERAL_MODEL", "umm-maybe/AI-image-detector").strip()
        else:
            self.general_model_name = general_model_name.strip() if general_model_name else None

        self.user_name: Optional[str] = None
        self._validate_token()
        self.local_detector = LocalViTDeepfakeDetector(
            face_model_name=self.face_model_name,
            general_model_name=self.general_model_name
        )

    def _validate_token(self):
        if self.api_key and self.api_key.startswith("hf_"):
            try:
                api = HfApi(token=self.api_key)
                user_info = api.whoami()
                if isinstance(user_info, dict):
                    self.user_name = user_info.get("name") or user_info.get("username") or user_info.get("fullname") or "Authenticated User"
                else:
                    self.user_name = getattr(user_info, "name", "Authenticated User")
            except Exception:
                self.user_name = "HF User"

    def is_configured(self) -> bool:
        if getattr(self, "_api_depleted", False):
            return False
        return bool(self.api_key and self.api_key.startswith("hf_"))

    def predict(self, image_bytes: bytes, has_face: bool = True, scene_type: str = "general_object") -> Dict[str, Any]:
        """
        Runs inference against Hugging Face deepfake and general synthetic image models.
        Routes to face-specialist model (dima806) when face/portrait is detected,
        and general-purpose synthetic image classifier (umm-maybe/AI-image-detector)
        when strictly non-human (landscapes, anime, architecture, general objects).
        """
        is_face_scenario = has_face or (scene_type in ["photograph_portrait"])
        if is_face_scenario:
            target_model = self.face_model_name
        else:
            if not self.general_model_name:
                return {
                    "is_hf_applied": False,
                    "hf_risk_score": 50.0,
                    "hf_label": "unknown",
                    "hf_confidence": 0.0,
                    "model_name": self.face_model_name,
                    "user": self.user_name,
                    "note": f"Hugging Face ({self.face_model_name}) skipped: image does not contain a human face (scene: {scene_type}). Forensic evaluation routed to texture, micro-structure, and metadata engines."
                }
            target_model = self.general_model_name

        if not self.is_configured():
            return self.local_detector.predict(image_bytes, has_face=has_face, scene_type=scene_type)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "image/jpeg"
        }

        endpoint_url = f"https://router.huggingface.co/hf-inference/models/{target_model}"

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(endpoint_url, headers=headers, content=image_bytes)

            if res.status_code == 200:
                data = res.json()
                fake_score = 0.5
                real_score = 0.5

                if isinstance(data, list):
                    for item in data:
                        lbl = str(item.get("label", "")).upper()
                        score = float(item.get("score", 0.5))
                        if any(k in lbl for k in ["FAKE", "SYNTHETIC", "DEEPFAKE", "AI", "ARTIFICIAL"]):
                            fake_score = score
                        elif any(k in lbl for k in ["REAL", "ORIGINAL", "AUTHENTIC", "HUMAN"]):
                            real_score = score

                risk_score = round(fake_score * 100.0, 2)
                confidence = max(fake_score, real_score)
                label = "fake" if risk_score >= 50.0 else "real"

                return {
                    "is_hf_applied": True,
                    "hf_risk_score": risk_score,
                    "hf_label": label,
                    "hf_confidence": round(confidence, 2),
                    "model_name": target_model,
                    "user": self.user_name,
                    "note": f"Hugging Face ({target_model}) evaluated image with {confidence*100:.1f}% confidence (User: {self.user_name})."
                }

            if res.status_code in [402, 403]:
                self._api_depleted = True

            # If cloud returns 402/403 or rate-limits, execute local offline fallback
            local_res = self.local_detector.predict(image_bytes, has_face=has_face, scene_type=scene_type)
            if local_res.get("is_hf_applied"):
                local_res["user"] = self.user_name
                return local_res

            return {
                "is_hf_applied": False,
                "hf_risk_score": 50.0,
                "hf_label": "unknown",
                "hf_confidence": 0.0,
                "model_name": target_model,
                "note": f"Hugging Face HTTP {res.status_code}: {res.text[:100]}"
            }

        except Exception as e:
            local_res = self.local_detector.predict(image_bytes, has_face=has_face, scene_type=scene_type)
            if local_res.get("is_hf_applied"):
                local_res["user"] = self.user_name
                return local_res

            return {
                "is_hf_applied": False,
                "hf_risk_score": 50.0,
                "hf_label": "unknown",
                "hf_confidence": 0.0,
                "model_name": target_model,
                "note": f"Hugging Face inference error: {str(e)}"
            }
