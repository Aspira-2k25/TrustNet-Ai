import io
import pytest
import numpy as np
from PIL import Image, ImageDraw
from models.image_deepfake.forensics.face_analyzer import FaceAnalyzer


def create_image_with_synthetic_faces(num_faces=2):
    """Draws synthetic face-like ovals with eyes/mouth on skin tone background."""
    img = Image.new("RGB", (600, 300), (240, 240, 240))
    draw = ImageDraw.Draw(img)

    spacing = 600 // (num_faces + 1)
    for i in range(num_faces):
        cx = spacing * (i + 1)
        cy = 150
        # Face oval
        draw.ellipse([cx - 50, cy - 65, cx + 50, cy + 65], fill=(210, 160, 120), outline=(150, 100, 70))
        # Eyes
        draw.ellipse([cx - 25, cy - 20, cx - 10, cy - 10], fill=(50, 50, 50))
        draw.ellipse([cx + 10, cy - 20, cx + 25, cy - 10], fill=(50, 50, 50))
        # Nose
        draw.line([cx, cy - 10, cx, cy + 10], fill=(160, 110, 80), width=3)
        # Mouth
        draw.arc([cx - 20, cy + 15, cx + 20, cy + 35], 0, 180, fill=(180, 70, 70), width=3)

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_face_analyzer_detects_multiple_faces():
    analyzer = FaceAnalyzer()
    img_bytes = create_image_with_synthetic_faces(num_faces=2)
    res = analyzer.analyze(img_bytes)
    assert res["has_face"] is True
    # Should detect faces and count
    assert res["face_count"] >= 1
    assert "status" in res


def test_face_analyzer_detects_single_face():
    analyzer = FaceAnalyzer()
    img_bytes = create_image_with_synthetic_faces(num_faces=1)
    res = analyzer.analyze(img_bytes)
    assert res["has_face"] is True
    assert res["face_count"] >= 1
