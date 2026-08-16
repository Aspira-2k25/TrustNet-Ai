import pytest
import uuid
import torch
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from models.image_deepfake.tests.test_preprocessing import create_mock_image_bytes
from shared.schemas.detection_result import DetectionResult
from shared.constants.status import StatusEnum
from shared.constants.native_score_semantics import NativeScoreSemanticsEnum

def test_efficientnet_detector_success():
    detector = EfficientNetDetector()
    img_bytes = create_mock_image_bytes(format="JPEG")
    
    scan_id = str(uuid.uuid4())
    result = detector.predict(img_bytes, scan_id=scan_id)
    
    assert isinstance(result, DetectionResult)
    assert result.scan_id == scan_id
    assert result.status == StatusEnum.SUCCESS
    assert result.error_code is None
    assert result.error_message is None
    assert 0.0 <= result.risk_score <= 100.0
    assert 0.0 <= result.native_score <= 1.0
    assert result.native_score_semantics == NativeScoreSemanticsEnum.probability_of_negative_class
    # Validate universal risk_score inversion formula: risk_score = round((1 - native_score) * 100)
    expected_risk = round((1.0 - result.native_score) * 100.0, 2)
    assert abs(result.risk_score - expected_risk) < 1e-4
    assert result.detector_id == "image_deepfake.efficientnet_b0.v1"

def test_efficientnet_detector_failure():
    detector = EfficientNetDetector()
    
    scan_id = str(uuid.uuid4())
    # Pass invalid bytes to trigger an exception
    result = detector.predict(b"not an image", scan_id=scan_id)
    
    assert isinstance(result, DetectionResult)
    assert result.scan_id == scan_id
    assert result.status == StatusEnum.FAILED
    assert result.error_code == "INFERENCE_FAILED"
    assert result.error_message is not None


def test_efficientnet_detector_reduces_false_positive_on_photographic_scene():
    detector = EfficientNetDetector(enable_explainability=False)

    from PIL import Image, ImageDraw
    import io

    def make_photo_like_image():
        image = Image.new('RGB', (512, 512), (240, 240, 240))
        draw = ImageDraw.Draw(image)

        for x in range(512):
            for y in range(512):
                if y < 250:
                    image.putpixel((x, y), (125 + (x // 6) % 30, 150 + (y // 7) % 25, 195 + (x // 8) % 40))
                else:
                    image.putpixel((x, y), (90 + (x // 10) % 20, 110 + (y // 8) % 25, 70 + (x // 12) % 25))

        draw.ellipse((110, 80, 420, 420), fill=(210, 180, 150))
        draw.rectangle((60, 340, 460, 470), fill=(80, 98, 72))
        draw.rectangle((180, 170, 330, 315), fill=(130, 160, 200))
        draw.line((260, 260, 320, 330), fill=(60, 60, 60), width=18)

        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=92)
        return buffer.getvalue()

    def make_synthetic_pattern_image():
        image = Image.new('RGB', (512, 512), (30, 30, 30))
        pixels = image.load()
        for y in range(512):
            for x in range(512):
                pixels[x, y] = ((x * 7 + y * 13) % 256, (x * 11 + y * 17) % 256, (x * 13 + y * 19) % 256)
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=94)
        return buffer.getvalue()

    photo_result = detector.predict(make_photo_like_image(), scan_id='photo-regression')
    synthetic_result = detector.predict(make_synthetic_pattern_image(), scan_id='synthetic-regression')

    assert photo_result.status == StatusEnum.SUCCESS
    assert synthetic_result.status == StatusEnum.SUCCESS
    assert photo_result.risk_score < 40.0
    assert photo_result.risk_score < synthetic_result.risk_score
    assert photo_result.label == 'real'
