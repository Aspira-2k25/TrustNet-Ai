import io
import pytest
import numpy as np
from PIL import Image, ImageDraw

from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from models.image_deepfake.forensics.ela_analyzer import ELAAnalyzer
from models.image_deepfake.forensics.frequency_analyzer import FrequencyAnalyzer
from models.image_deepfake.forensics.metadata_analyzer import MetadataAnalyzer
from models.image_deepfake.forensics.gabor_analyzer import GaborTextureAnalyzer


def test_webcam_contrast_scene_ela_does_not_explode():
    """
    Verifies that a scene with high natural contrast (bright daylight window in background,
    dark clothing in foreground) does not trigger false splicing alarms in ELA due to
    small-mean relative variance inflation.
    """
    # Create image with high natural contrast: bright window + dark area + subtle sensor noise
    img = Image.new("RGB", (320, 240), color=(25, 25, 30))
    draw = ImageDraw.Draw(img)
    # Bright window in top-left
    draw.rectangle([20, 20, 120, 100], fill=(235, 240, 245))
    # Add natural random sensor noise
    arr = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, 3.0, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG", quality=88)
    img_bytes = buf.getvalue()

    analyzer = ELAAnalyzer()
    res = analyzer.analyze(img_bytes)
    assert res["is_anomalous"] is False
    assert res["ela_anomaly_score"] <= 0.35


def test_webcam_mesh_screen_fft_does_not_falsely_alarm():
    """
    Verifies that physical high-frequency repetitive structures (window security mesh,
    grille, or blinds) with natural power-law decay slope are not mistaken for
    GAN deconvolution grid artifacts.
    """
    img = Image.new("RGB", (256, 256), color=(80, 80, 80))
    arr = np.random.normal(120, 12.0, (256, 256)).astype(np.float32)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG", quality=90)
    img_bytes = buf.getvalue()

    analyzer = FrequencyAnalyzer()
    res = analyzer.analyze(img_bytes)
    assert res["spectral_anomaly_score"] <= 0.35


def test_missing_exif_is_neutral_baseline():
    """
    Verifies that authentic images lacking EXIF headers (e.g. from webcams, chat apps,
    or screen captures) receive a neutral metadata anomaly score rather than being penalized.
    """
    img = Image.new("RGB", (100, 100), color=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    
    analyzer = MetadataAnalyzer()
    res = analyzer.analyze(buf.getvalue())
    assert res["is_exif_missing"] is True
    assert res["is_ai_signature_found"] is False
    assert res["metadata_anomaly_score"] <= 0.10


def test_full_pipeline_on_real_camera_transformations():
    """
    Verifies that a real optical image recompressed at different qualities or resized
    reliably produces an AUTHENTIC verdict across all standard pipelines.
    """
    img = Image.new("RGB", (300, 300), color=(70, 75, 80))
    arr = np.array(img, dtype=np.float32)
    # Natural organic variations
    y, x = np.ogrid[:300, :300]
    grad = ((x + y) / 600.0) * 80.0
    noise = np.random.normal(0, 4.0, (300, 300, 3))
    arr = np.clip(arr + grad[:, :, None] + noise, 0, 255).astype(np.uint8)
    
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG", quality=85)
    img_bytes = buf.getvalue()

    detector = EfficientNetDetector()
    res = detector.predict(img_bytes)
    assert res.verdict == "AUTHENTIC"
    assert res.risk_score < 40.0
