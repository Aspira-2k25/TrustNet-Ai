import io
import pytest
import numpy as np
from PIL import Image, ImageDraw
from models.image_deepfake.forensics.watermark_analyzer import WatermarkIconAnalyzer


def create_blank_image(size=(300, 300), color=(100, 100, 100)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_image_with_circle_sticker(size=(400, 400), corner="bottom_right"):
    """Simulates a real photo with a small circular badge/sticker/lens flare in corner (like real_10.jpg)."""
    img = Image.new("RGB", size, (40, 40, 40))
    draw = ImageDraw.Draw(img)
    w, h = size
    cx = w - 24 if "right" in corner else 24
    cy = h - 24 if "bottom" in corner else 24
    r = 10
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def create_image_with_rectangular_decal(size=(400, 400), corner="bottom_right"):
    """Simulates a real photo with a rectangular decal or logo in corner."""
    img = Image.new("RGB", size, (40, 40, 40))
    draw = ImageDraw.Draw(img)
    w, h = size
    cx = w - 24 if "right" in corner else 24
    cy = h - 24 if "bottom" in corner else 24
    draw.rectangle([cx - 10, cy - 8, cx + 10, cy + 8], fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def create_image_with_corner_sparkle(size=(400, 400), corner="bottom_right"):
    """Draw a 4-pointed sparkle icon in the chosen corner (concave star shape with 4 notches)."""
    img = Image.new("RGB", size, (40, 40, 40))
    draw = ImageDraw.Draw(img)
    w, h = size
    cx = w - 24 if "right" in corner else 24
    cy = h - 24 if "bottom" in corner else 24
    r_outer = 12
    r_inner = 3

    # 4-pointed star coordinates
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


def test_watermark_clean_image():
    analyzer = WatermarkIconAnalyzer()
    res = analyzer.analyze(create_blank_image())
    assert res["status"] in ["APPLIED", "SKIPPED"]
    assert res["is_watermark_found"] is False
    assert res["watermark_anomaly_score"] == 0.0


def test_watermark_detected_on_synthetic_sparkle():
    analyzer = WatermarkIconAnalyzer()
    img_bytes = create_image_with_corner_sparkle(size=(400, 400), corner="bottom_right")
    res = analyzer.analyze(img_bytes)
    assert res["status"] == "APPLIED"
    assert res["is_watermark_found"] is True
    assert 0.60 <= res["watermark_anomaly_score"] <= 0.90
    assert res["watermark_location"] == "bottom_right"
    assert "corner" in res["finding"].lower()
    assert "star/sparkle-style glyph" in res["finding"]


def test_watermark_rejects_circular_sticker_false_positive():
    """Regression test for real_10.jpg failure mode: circular stickers/badges must NOT trigger watermark."""
    analyzer = WatermarkIconAnalyzer()
    img_bytes = create_image_with_circle_sticker(size=(400, 400), corner="bottom_right")
    res = analyzer.analyze(img_bytes)
    assert res["status"] in ["APPLIED", "SKIPPED"]
    assert res["is_watermark_found"] is False
    assert res["watermark_anomaly_score"] == 0.0


def test_watermark_rejects_rectangular_decal_false_positive():
    """Regression test: rectangular decals or logos must NOT trigger the pointed sparkle detector."""
    analyzer = WatermarkIconAnalyzer()
    img_bytes = create_image_with_rectangular_decal(size=(400, 400), corner="bottom_right")
    res = analyzer.analyze(img_bytes)
    assert res["status"] in ["APPLIED", "SKIPPED"]
    assert res["is_watermark_found"] is False
    assert res["watermark_anomaly_score"] == 0.0


def test_watermark_score_capped_at_90():
    """Ensures watermark anomaly score is never allowed to claim near-certainty (> 0.90) on shape alone."""
    analyzer = WatermarkIconAnalyzer()
    img_bytes = create_image_with_corner_sparkle(size=(400, 400), corner="bottom_right")
    res = analyzer.analyze(img_bytes)
    assert res["watermark_anomaly_score"] <= 0.90


def test_watermark_schema_contract():
    analyzer = WatermarkIconAnalyzer()
    res = analyzer.analyze(create_blank_image())
    required_keys = {"status", "is_watermark_found", "watermark_anomaly_score", "watermark_location", "finding"}
    assert required_keys.issubset(res.keys())
