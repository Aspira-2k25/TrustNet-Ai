import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import httpx
from huggingface_hub import HfApi

load_dotenv()

class HuggingFaceDeepfakeClient:
    """
    Hugging Face Deepfake Model Inference Client.
    Connects to pre-trained deepfake classification models on Hugging Face Hub (e.g. dima806/deepfake_vs_real_image_detection).
    """
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = (api_key or os.getenv("HUGGINGFACE_API_KEY", "")).strip()
        self.model_name = (model_name or os.getenv("HF_DEEPFAKE_MODEL", "dima806/deepfake_vs_real_image_detection")).strip()
        self.user_name: Optional[str] = None
        self._validate_token()

    def _validate_token(self):
        if self.api_key and self.api_key.startswith("hf_"):
            try:
                api = HfApi(token=self.api_key)
                user_info = api.whoami()
                self.user_name = user_info.get("name", "Authenticated User")
            except Exception:
                self.user_name = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("hf_"))

    def predict(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Runs inference against Hugging Face deepfake models.
        Returns normalized risk score, label, and confidence.
        """
        if not self.is_configured():
            return {
                "is_hf_applied": False,
                "hf_risk_score": 50.0,
                "hf_label": "unknown",
                "hf_confidence": 0.0,
                "model_name": self.model_name,
                "note": "Hugging Face token not configured."
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "image/jpeg"
        }

        endpoint_url = f"https://router.huggingface.co/hf-inference/models/{self.model_name}"

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
                        if "FAKE" in lbl or "SYNTHETIC" in lbl or "DEEPFAKE" in lbl:
                            fake_score = score
                        elif "REAL" in lbl or "ORIGINAL" in lbl or "AUTHENTIC" in lbl:
                            real_score = score

                risk_score = round(fake_score * 100.0, 2)
                confidence = max(fake_score, real_score)
                label = "fake" if risk_score >= 50.0 else "real"

                return {
                    "is_hf_applied": True,
                    "hf_risk_score": risk_score,
                    "hf_label": label,
                    "hf_confidence": round(confidence, 2),
                    "model_name": self.model_name,
                    "user": self.user_name,
                    "note": f"Hugging Face ({self.model_name}) evaluated image with {confidence*100:.1f}% confidence (User: {self.user_name})."
                }

            elif res.status_code == 403:
                # Token validated through HfApi; router fallback
                return {
                    "is_hf_applied": False,
                    "hf_risk_score": 50.0,
                    "hf_label": "unknown",
                    "hf_confidence": 0.0,
                    "model_name": self.model_name,
                    "user": self.user_name,
                    "note": f"Hugging Face API rate limited or forbidden (User: {self.user_name}). Deferring to local physics engines."
                }

            else:
                return {
                    "is_hf_applied": False,
                    "hf_risk_score": 50.0,
                    "hf_label": "unknown",
                    "hf_confidence": 0.0,
                    "model_name": self.model_name,
                    "note": f"Hugging Face HTTP {res.status_code}: {res.text[:100]}"
                }

        except Exception as e:
            return {
                "is_hf_applied": False,
                "hf_risk_score": 50.0,
                "hf_label": "unknown",
                "hf_confidence": 0.0,
                "model_name": self.model_name,
                "note": f"Hugging Face inference error: {str(e)}"
            }
