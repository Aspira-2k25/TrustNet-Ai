import io
import pytest
import numpy as np
from PIL import Image, ImageDraw
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from models.image_deepfake.forensics.watermark_analyzer import WatermarkIconAnalyzer
from models.image_deepfake.forensics.metadata_analyzer import MetadataAnalyzer


def create_realistic_photo_with_corner_sticker(size=(400, 400)):
    """
    Creates an image simulating real_10.jpg:
    Natural-like gradient texture with a small circular sticker/decal in the bottom-right corner.
    """
    arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    for y in range(size[1]):
        for x in range(size[0]):
            arr[y, x] = [
                int(120 + 30 * np.sin(x / 30.0)),
                int(100 + 25 * np.cos(y / 25.0)),
                int(80 + 20 * np.sin((x + y) / 40.0)),
            ]
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)
    # Add a small circular white badge/sticker in bottom-right
    cx, cy = size[0] - 25, size[1] - 25
    r = 10
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def create_photo_with_sparkle_watermark(size=(400, 400)):
    """Creates an image with an actual 4-pointed sparkle glyph."""
    arr = np.full((size[1], size[0], 3), 100, dtype=np.uint8)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)
    cx, cy = size[0] - 24, size[1] - 24
    r_outer = 12
    r_inner = 3
    points = [
        (cx, cy - r_outer),
        (cx + r_inner, cy - r_inner),
        (cx + r_outer, cy),
        (cx + r_inner, cy + r_inner),
        (cx, cy + r_outer),
        (cx - r_inner, cy + r_inner),
        (cx - r_outer, cy),
        (cx - r_inner, cy - r_inner),
    ]
    draw.polygon(points, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


class MockViTClientReal:
    """Simulates a ViT returning 99.1% REAL (0.9% risk score), exactly like real_10.jpg."""
    face_model_name = "dima806/deepfake_vs_real_image_detection"
    model_name = "dima806/deepfake_vs_real_image_detection"
    
    def predict(self, image_bytes: bytes, has_face: bool = True, scene_type: str = "portrait"):
        return {
            "is_hf_applied": True,
            "hf_risk_score": 0.9,
            "is_fake": False,
            "confidence": 0.991,
            "model_name": "dima806/deepfake_vs_real_image_detection",
            "inference_mode": "local_vit_offline",
            "note": "Vision Transformer: Authentic human photographic features verified (99.1% REAL)."
        }


def test_real_photo_with_corner_sticker_not_flagged_as_watermark():
    """
    Acceptance Criterion 1 & 2:
    Re-run real_10.jpg-equivalent image with corner sticker.
    Must NOT produce a 90+ confirmed fake score, and must NOT detect watermark.
    """
    img_bytes = create_realistic_photo_with_corner_sticker()
    detector = EfficientNetDetector()
    detector.hf_client = MockViTClientReal()
    detector.local_vit = MockViTClientReal()

    pred = detector.predict(img_bytes, filename="real_10.jpg")

    # Watermark must not be triggered by the circular sticker
    assert pred.metadata["watermark_found"] is False
    assert pred.metadata["watermark_anomaly_score"] == 0.0

    # Risk score must NOT be 96.0; it should be authentic or uncertain (<= 52.0), not confirmed fake
    assert pred.risk_score <= 52.0
    assert pred.risk_score != 96.0
    assert pred.verdict in ["AUTHENTIC", "LIKELY REAL", "UNCERTAIN"]


def test_telemetry_entries_are_never_identical():
    """
    Acceptance Criterion 3:
    Confirm 'Provenance & Metadata Forensics' and 'Visual Watermark Icon Scanner'
    telemetry entries show independently-computed finding strings and NEVER duplicate.
    """
    img_bytes = create_realistic_photo_with_corner_sticker()
    detector = EfficientNetDetector()
    detector.hf_client = MockViTClientReal()
    detector.local_vit = MockViTClientReal()

    pred = detector.predict(img_bytes, filename="real_10.jpg")

    meta_entry = next((a for a in pred.analyzers if a["name"] == "Provenance & Metadata Forensics"), None)
    wm_entry = next((a for a in pred.analyzers if a["name"] == "Visual Watermark Icon Scanner"), None)

    assert meta_entry is not None
    assert wm_entry is not None
    assert meta_entry["finding"] != wm_entry["finding"]
    assert "watermark" not in meta_entry["finding"].lower()
    assert "metadata" not in wm_entry["finding"].lower()


def test_watermark_hit_with_vit_real_clamps_to_uncertain_not_96():
    """
    Acceptance Criterion 1:
    Even when a watermark icon IS genuinely detected, if the Vision Transformer
    confirms REAL (99.1% real) and no other forensic domain corroborates,
    the score must fall into the contradiction-clamp / uncertain band (~45-55%),
    and NEVER jump to 96.0!
    """
    img_bytes = create_photo_with_sparkle_watermark()
    detector = EfficientNetDetector()
    detector.hf_client = MockViTClientReal()
    detector.local_vit = MockViTClientReal()

    pred = detector.predict(img_bytes, filename="test_sparkle.jpg")

    # Watermark is found
    assert pred.metadata["watermark_found"] is True
    # But because ViT is strongly real (99.1% REAL) and no other domain corroborates,
    # the score must be clamped around the uncertain / contradiction band, NOT 96.0!
    assert pred.risk_score <= 55.0
    assert pred.risk_score != 96.0
    assert pred.verdict in ["UNCERTAIN", "UNCERTAIN / INCONCLUSIVE", "SUSPICIOUS / LOW-CONFIDENCE AI"]

    # Telemetry check: metadata and watermark findings remain completely distinct
    meta_entry = next((a for a in pred.analyzers if a["name"] == "Provenance & Metadata Forensics"), None)
    wm_entry = next((a for a in pred.analyzers if a["name"] == "Visual Watermark Icon Scanner"), None)
    assert meta_entry is not None
    assert wm_entry is not None
    assert meta_entry["finding"] != wm_entry["finding"]
