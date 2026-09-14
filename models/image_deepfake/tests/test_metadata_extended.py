import io
import pytest
from PIL import Image
from models.image_deepfake.forensics.metadata_analyzer import MetadataAnalyzer


def test_extended_generator_signatures_filename():
    analyzer = MetadataAnalyzer()
    img = Image.new("RGB", (100, 100), color=(120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    modern_generators = [
        "gemini",
        "imagen",
        "sora",
        "grok",
        "meta ai",
        "canva",
        "recraft",
        "lensa",
        "remini"
    ]

    for gen in modern_generators:
        filename = f"image_generated_by_{gen.replace(' ', '_')}_output.jpg"
        res = analyzer.analyze(img_bytes, filename=filename)
        assert res["is_ai_signature_found"] is True, f"Failed for generator: {gen}"
        assert res["metadata_anomaly_score"] >= 0.80


def test_clean_camera_filename_not_flagged():
    analyzer = MetadataAnalyzer()
    img = Image.new("RGB", (100, 100), color=(120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    res = analyzer.analyze(img_bytes, filename="DSC_0042.JPG")
    assert res["is_ai_signature_found"] is False
    assert res["generator_name"] is None
