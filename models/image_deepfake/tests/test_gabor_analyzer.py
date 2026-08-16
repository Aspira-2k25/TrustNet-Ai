import io
import pytest
import numpy as np
from PIL import Image
from models.image_deepfake.forensics.gabor_analyzer import GaborTextureAnalyzer


@pytest.fixture
def gabor_analyzer():
    return GaborTextureAnalyzer()


def test_gabor_analyzer_initialization(gabor_analyzer):
    assert gabor_analyzer is not None
    assert len(gabor_analyzer.orientations) == 4
    assert len(gabor_analyzer.wavelengths) == 2


def test_gabor_analyzer_on_synthetic_blank_image(gabor_analyzer):
    # A completely blank uniform image lacks natural texture energy
    img = Image.new("RGB", (256, 256), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    
    result = gabor_analyzer.analyze(buf.getvalue())
    assert "gabor_anomaly_score" in result
    assert "is_texture_anomalous" in result
    assert "mean_energy" in result
    assert "orientation_entropy" in result
    assert 0.0 <= result["gabor_anomaly_score"] <= 1.0
    # A flat blank image has zero texture energy -> should flag over-smoothing
    assert result["is_texture_anomalous"] is True


def test_gabor_analyzer_on_natural_textured_image(gabor_analyzer):
    # Natural image with rich isotropic gradient and Gaussian noise
    arr = np.zeros((256, 256, 3), dtype=np.float32)
    for y in range(256):
        for x in range(256):
            arr[y, x, 0] = 100 + y * 0.3 + x * 0.2
            arr[y, x, 1] = 90 + y * 0.2 + x * 0.15
            arr[y, x, 2] = 80 + y * 0.1 + x * 0.1

    noise = np.random.normal(0, 12.0, (256, 256, 3)).astype(np.float32)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    
    result = gabor_analyzer.analyze(buf.getvalue())
    assert result["status"] == "APPLIED"
    assert result["gabor_anomaly_score"] <= 0.40
    assert result["orientation_entropy"] >= 1.15


def test_gabor_analyzer_error_fallback(gabor_analyzer):
    # Invalid image bytes should trigger fallback gracefully without exception
    result = gabor_analyzer.analyze(b"corrupt_invalid_image_payload")
    assert result["status"] in ["FALLBACK", "SKIPPED"]
    assert 0.0 <= result["gabor_anomaly_score"] <= 1.0
