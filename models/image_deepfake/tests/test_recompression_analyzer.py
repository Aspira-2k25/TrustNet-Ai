import io
import pytest
import numpy as np
from PIL import Image
from models.image_deepfake.forensics.recompression_analyzer import RecompressionAnalyzer


def create_smooth_image():
    # Smooth gradient with no 8x8 block artifacts
    arr = np.linspace(50, 200, 256, dtype=np.uint8)
    grid = np.tile(arr, (256, 1))
    img = Image.fromarray(grid, mode="L").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_heavily_recompressed_jpeg():
    # Save image at very low quality to induce strong 8x8 DCT block boundaries
    arr = np.random.randint(40, 220, (128, 128), dtype=np.uint8)
    img = Image.fromarray(arr, mode="L").convert("RGB")
    buf = io.BytesIO()
    # Save once
    img.save(buf, format="JPEG", quality=10)
    buf.seek(0)
    # Reopen and recompress again (double JPEG)
    img2 = Image.open(buf)
    buf2 = io.BytesIO()
    img2.save(buf2, format="JPEG", quality=20)
    return buf2.getvalue()


def test_recompression_analyzer_clean():
    analyzer = RecompressionAnalyzer()
    res = analyzer.analyze(create_smooth_image())
    assert res["status"] == "APPLIED"
    assert "already_recompressed" in res
    assert "blockiness_ratio" in res
    assert res["already_recompressed"] is False


def test_recompression_analyzer_heavily_recompressed():
    analyzer = RecompressionAnalyzer()
    res = analyzer.analyze(create_heavily_recompressed_jpeg())
    assert res["status"] == "APPLIED"
    assert res["blockiness_ratio"] >= 1.0


def test_recompression_analyzer_schema():
    analyzer = RecompressionAnalyzer()
    res = analyzer.analyze(create_smooth_image())
    required_keys = {"status", "already_recompressed", "recompression_score", "blockiness_ratio", "finding"}
    assert required_keys.issubset(res.keys())
