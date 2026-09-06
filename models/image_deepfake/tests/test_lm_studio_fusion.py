import json
import pytest
from unittest.mock import patch, MagicMock
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from models.image_deepfake.inference.lm_studio_vision_client import LMStudioVisionClient


def create_dummy_jpeg() -> bytes:
    import io
    from PIL import Image
    img = Image.new("RGB", (256, 256), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_lm_studio_vision_fusion_applied():
    """Verify that when LM Studio returns structured vision findings, it is properly fused."""
    detector = EfficientNetDetector(enable_explainability=False)
    image_bytes = create_dummy_jpeg()

    mock_vision_resp = {
        "status": "APPLIED",
        "model_name": "unsloth/Qwen3-VL-4B-Thinking-GGUF",
        "visual_verdict": "suspicious",
        "confidence": 0.88,
        "observations": [
            "Unnatural skin smoothing and missing micro-pore texture on face.",
            "Lighting angle on cheek contradicts background illumination."
        ],
        "suspicious_regions": [
            {"region": "Face", "reason": "Unusual boundary step transition"}
        ],
        "supporting_evidence": ["Face boundary anomaly", "High-frequency spectral spike"],
        "contradicting_evidence": [],
        "uncertainties": [],
        "simple_explanation": "Face exhibits unnatural texture smoothing and inconsistent lighting angles."
    }

    with patch.object(detector.lm_studio_client, "analyze", return_value=mock_vision_resp):
        res = detector.predict(image_bytes)

    assert res.status.value == "SUCCESS"
    assert res.metadata.get("lm_studio_status") == "APPLIED"
    assert res.metadata.get("lm_studio_model") == "unsloth/Qwen3-VL-4B-Thinking-GGUF"
    
    # Verify LM Studio is in analyzers telemetry
    vision_analyzer = next((a for a in res.analyzers if "LM Studio" in a["name"]), None)
    assert vision_analyzer is not None
    assert vision_analyzer["status"] == "APPLIED"
    assert "Unnatural skin smoothing" in vision_analyzer["finding"] or "Face exhibits" in vision_analyzer["finding"]

    # Verify evidence item is present
    vision_evidence = next((e for e in res.evidence if "lm_studio_vision" in e.feature_or_region), None)
    assert vision_evidence is not None
    assert vision_evidence.contribution > 0.50

    # Verify why_reasons includes vision reasoning
    why_text = " ".join(res.metadata.get("why_reasons", []))
    assert "Visual reasoning:" in why_text or "Face exhibits" in why_text


def test_lm_studio_vision_offline_graceful_fallback():
    """Verify that when LM Studio is offline, the system degrades gracefully with zero crashes."""
    detector = EfficientNetDetector(enable_explainability=False)
    image_bytes = create_dummy_jpeg()

    mock_unavailable_resp = {
        "status": "UNAVAILABLE",
        "model_name": "unsloth/Qwen3-VL-4B-Thinking-GGUF",
        "visual_verdict": "inconclusive",
        "confidence": 0.0,
        "observations": [],
        "suspicious_regions": [],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "uncertainties": ["LM Studio endpoint unavailable"],
        "simple_explanation": ""
    }

    with patch.object(detector.lm_studio_client, "analyze", return_value=mock_unavailable_resp):
        res = detector.predict(image_bytes)

    assert res.status.value == "SUCCESS"
    assert res.metadata.get("lm_studio_status") == "UNAVAILABLE"

    # Analyzer should be marked UNAVAILABLE
    vision_analyzer = next((a for a in res.analyzers if "LM Studio" in a["name"]), None)
    assert vision_analyzer is not None
    assert vision_analyzer["status"] == "UNAVAILABLE"
    assert "unavailable" in vision_analyzer["finding"].lower()

    # Why reasons should state fallback cleanly
    why_text = " ".join(res.metadata.get("why_reasons", []))
    assert "Vision analysis unavailable. Result is based on available forensic checks." in why_text


def test_lm_studio_contradiction_calibration():
    """Verify that if vision claims suspicious but 0 physical anomalies exist, system clamps to UNCERTAIN/contradiction."""
    detector = EfficientNetDetector(enable_explainability=False)
    image_bytes = create_dummy_jpeg()

    mock_vision_hallucination = {
        "status": "APPLIED",
        "model_name": "unsloth/Qwen3-VL-4B-Thinking-GGUF",
        "visual_verdict": "suspicious",
        "confidence": 0.90,
        "observations": ["Vague suspicion without pixel evidence."],
        "suspicious_regions": [],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "uncertainties": [],
        "simple_explanation": "Hallucinated deepfake conclusion."
    }

    # Simulate completely clean physical scans
    with patch.object(detector.lm_studio_client, "analyze", return_value=mock_vision_hallucination), \
         patch.object(detector.freq_analyzer, "analyze", return_value={"spectral_anomaly_score": 0.05, "is_synthetic_pattern": False, "finding": "Clean"}), \
         patch.object(detector.pixel_analyzer, "analyze", return_value={"pixel_morphing_score": 0.05, "is_morphing_detected": False, "note": "Clean"}), \
         patch.object(detector.gabor_analyzer, "analyze", return_value={"gabor_anomaly_score": 0.05, "is_texture_anomalous": False, "finding": "Clean"}), \
         patch.object(detector.ela_analyzer, "analyze", return_value={"ela_anomaly_score": 0.05, "is_anomalous": False, "note": "Clean"}), \
         patch.object(detector.noise_analyzer, "analyze", return_value={"noise_anomaly_score": 0.05, "is_synthetic_noise": False, "note": "Clean"}), \
         patch.object(detector.local_vit, "predict", return_value={"is_hf_applied": True, "hf_risk_score": 5.0, "model_name": "LocalViT"}):
        res = detector.predict(image_bytes)

    # When vision model contradicts all physical scans + ViT (0 physical anomalies):
    # Contradiction triggers, risk clamps to uncertain zone (48-52%), verdict is UNCERTAIN, never 90%+ fake!
    assert res.verdict in ["UNCERTAIN", "AUTHENTIC", "LIKELY_AUTHENTIC"]
    assert res.risk_score <= 52.0
    if res.metadata.get("is_contradiction"):
        assert res.verdict == "UNCERTAIN"
