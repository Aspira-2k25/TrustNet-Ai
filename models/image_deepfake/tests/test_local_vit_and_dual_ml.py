import io
import pytest
from PIL import Image
from models.image_deepfake.inference.local_vit_detector import LocalViTDeepfakeDetector
from models.image_deepfake.inference.huggingface_client import HuggingFaceDeepfakeClient


def make_test_image():
    img = Image.new("RGB", (128, 128), color=(180, 120, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_local_vit_detector_loads():
    detector = LocalViTDeepfakeDetector()
    assert detector.is_configured() is True


def test_local_vit_detector_predict_portrait():
    detector = LocalViTDeepfakeDetector()
    img_bytes = make_test_image()
    res = detector.predict(img_bytes, has_face=True, scene_type="photograph_portrait")
    assert res["is_hf_applied"] is True
    assert 0.0 <= res["hf_risk_score"] <= 100.0
    assert res["hf_label"] in ["real", "fake"]
    assert "dima806" in res["model_name"]


def test_local_vit_detector_predict_non_portrait():
    detector = LocalViTDeepfakeDetector()
    img_bytes = make_test_image()
    res = detector.predict(img_bytes, has_face=False, scene_type="nature_landscape")
    assert res["is_hf_applied"] is True
    assert 0.0 <= res["hf_risk_score"] <= 100.0
    assert "dima806" in res["model_name"]


def test_huggingface_client_fallback():
    # Client with invalid token should seamlessly fall back to local offline detector
    client = HuggingFaceDeepfakeClient(api_key="hf_invalid_token_xyz")
    img_bytes = make_test_image()
    res = client.predict(img_bytes, has_face=True, scene_type="photograph_portrait")
    # Must succeed via local offline fallback
    assert res["is_hf_applied"] is True
    assert 0.0 <= res["hf_risk_score"] <= 100.0
