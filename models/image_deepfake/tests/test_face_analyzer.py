import io
import pytest
import numpy as np
from PIL import Image, ImageDraw
from models.image_deepfake.forensics.face_analyzer import FaceAnalyzer

def make_blank_image(color=(200, 200, 200), size=(300, 300)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def make_wood_like_skin_colored_image():
    """Generates a wooden/tan texture that previously tricked the skin-ratio filter."""
    img = Image.new("RGB", (400, 400), (180, 120, 70))
    draw = ImageDraw.Draw(img)
    # Add wood grain stripes
    for y in range(0, 400, 10):
        draw.line([(0, y), (400, y)], fill=(160, 100, 55), width=3)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def make_dark_image():
    img = Image.new("RGB", (300, 300), (15, 15, 20))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def test_face_analyzer_skips_non_face_image():
    analyzer = FaceAnalyzer()
    res = analyzer.analyze(make_blank_image())
    assert res["has_face"] is False
    assert res["face_count"] == 0
    assert res["status"] == "SKIPPED"
    assert res["boundary_anomaly_score"] == 0.0
    assert "No human facial region" in res["reason"]

def test_face_analyzer_skips_skin_colored_wood():
    """Verifies that non-face skin-colored objects do NOT trigger face detection."""
    analyzer = FaceAnalyzer()
    res = analyzer.analyze(make_wood_like_skin_colored_image())
    assert res["has_face"] is False
    assert res["face_count"] == 0
    assert res["status"] == "SKIPPED"
    assert res["boundary_anomaly_score"] == 0.0

def test_face_analyzer_handles_extreme_lighting():
    analyzer = FaceAnalyzer()
    res_dark = analyzer.analyze(make_dark_image())
    assert res_dark["has_face"] is False
    assert res_dark["status"] == "SKIPPED"

def test_face_analyzer_schema_contract():
    analyzer = FaceAnalyzer()
    res = analyzer.analyze(make_blank_image())
    required_keys = {"has_face", "face_count", "bounding_boxes", "status", "reason", "boundary_anomaly_score", "finding"}
    assert required_keys.issubset(res.keys())
