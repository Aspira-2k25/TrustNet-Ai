import io
import json
import pytest
from PIL import Image
from models.image_deepfake.inference.lm_studio_vision_client import LMStudioVisionClient


def test_image_optimization_downscales_and_formats_base64():
    client = LMStudioVisionClient()
    # Create large 2000x1500 test image
    img = Image.new("RGB", (2000, 1500), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    img_bytes = buf.getvalue()

    data_url = client.optimize_image_for_vision(img_bytes, max_dim=896)
    assert data_url.startswith("data:image/jpeg;base64,")
    # Base64 payload should be reasonable size (under 150 KB)
    b64_payload = data_url.split(",")[1]
    assert len(b64_payload) < 200000


def test_parse_qwen_thinking_tags_and_json():
    client = LMStudioVisionClient()
    raw_response = """
<think>
Inspecting the facial features in the image.
Left cheek appears to have consistent skin pore texture.
Specular reflections in both eyes are consistent with single light source.
No obvious blending artifacts found along the jawline.
</think>
```json
{
  "visual_verdict": "authentic",
  "confidence": 0.91,
  "observations": [
    "Uniform skin texture across forehead and cheeks",
    "Consistent eye specular reflections"
  ],
  "suspicious_regions": [],
  "supporting_evidence": [
    "Natural micro-contrast around hairline",
    "Continuous lighting gradient"
  ],
  "contradicting_evidence": [],
  "uncertainties": [],
  "simple_explanation": "Visual inspection confirms natural camera capture with anatomically coherent facial structures."
}
```
"""
    result = client._parse_and_validate_response(raw_response, model_name="unsloth/Qwen3-VL-4B-Thinking-GGUF")
    assert result["visual_verdict"] == "authentic"
    assert result["confidence"] == 0.91
    assert len(result["observations"]) == 2
    assert len(result["suspicious_regions"]) == 0
    assert "consistent with single light source" in result["thinking_process"]
    assert "Visual inspection confirms" in result["simple_explanation"]


def test_parse_trailing_commas_repair():
    client = LMStudioVisionClient()
    raw_response = """
{
  "visual_verdict": "suspicious",
  "confidence": 0.84,
  "observations": [
    "Unnatural boundary along the collar",
  ],
  "suspicious_regions": [
    {
      "region": "neck",
      "reason": "Blending step gradient",
    },
  ],
  "supporting_evidence": [
    "Inconsistent sharpness",
  ],
  "contradicting_evidence": [],
  "uncertainties": [],
  "simple_explanation": "Noticeable boundary blending discontinuity near the collar.",
}
"""
    result = client._parse_and_validate_response(raw_response, model_name="test-model")
    assert result["visual_verdict"] == "suspicious"
    assert result["confidence"] == 0.84
    assert len(result["observations"]) == 1
    assert len(result["suspicious_regions"]) == 1
    assert result["suspicious_regions"][0]["region"] == "neck"


def test_offline_fallback_does_not_crash():
    # Point client to non-existent port to test offline handling
    client = LMStudioVisionClient(base_url="http://127.0.0.1:59999/v1", timeout=1)
    img = Image.new("RGB", (100, 100), color=(50, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    
    result = client.analyze(
        image_bytes=buf.getvalue(),
        forensic_evidence={"has_face": False, "ela_anomaly_score": 0.05}
    )
    assert result["status"] == "UNAVAILABLE"
    assert result["visual_verdict"] == "inconclusive"
    assert "unavailable" in result["simple_explanation"].lower()
