import io
import pytest
import torch
from PIL import Image
from models.image_deepfake.preprocessing.validator import ImageValidator
from models.image_deepfake.preprocessing.transforms import process_image_bytes

def create_mock_image_bytes(format="JPEG", size=(100, 100), color="red"):
    img = Image.new("RGB", size, color=color)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format=format)
    return img_byte_arr.getvalue()

def test_image_validator_success():
    validator = ImageValidator()
    img_bytes = create_mock_image_bytes(format="JPEG")
    is_valid, error = validator.validate(img_bytes)
    assert is_valid is True
    assert error is None

def test_image_validator_invalid_magic_bytes():
    validator = ImageValidator()
    # Random text, not an image
    is_valid, error = validator.validate(b"This is not an image")
    assert is_valid is False
    assert "Invalid or unsupported image format based on file signature" in error

def test_image_validator_exceeds_size():
    # Max size 10 bytes
    validator = ImageValidator(max_size_bytes=10)
    img_bytes = create_mock_image_bytes(format="JPEG")
    is_valid, error = validator.validate(img_bytes)
    assert is_valid is False
    assert "exceeds the maximum limit" in error

def test_process_image_bytes():
    img_bytes = create_mock_image_bytes(format="JPEG")
    tensor = process_image_bytes(img_bytes)
    
    assert isinstance(tensor, torch.Tensor)
    # Expected shape for EfficientNet input with batch dimension
    assert tensor.shape == (1, 3, 224, 224)
