import os
import io
import uuid
from typing import Tuple, Dict, Set
from fastapi import HTTPException, status
from PIL import Image
from services.scan_management.app.config.settings import settings

ALLOWED_EXTENSIONS: Dict[str, Set[str]] = {
    "image": {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".gif", ".ico"},
    "audio": {".wav", ".mp3", ".ogg", ".flac"},
    "video": {".mp4", ".mov", ".avi", ".mkv"}
}

ALLOWED_MIME_TYPES: Dict[str, Set[str]] = {
    "image": {
        "image/jpeg", "image/png", "image/webp", "image/bmp", "image/x-ms-bmp",
        "image/tiff", "image/gif", "image/x-icon", "image/vnd.microsoft.icon", "application/octet-stream"
    },
    "audio": {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/ogg", "audio/flac"},
    "video": {"video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska"}
}

MAX_FILE_SIZES: Dict[str, int] = {
    "image": settings.MAX_IMAGE_SIZE_MB * 1024 * 1024,
    "audio": settings.MAX_AUDIO_SIZE_MB * 1024 * 1024,
    "video": settings.MAX_VIDEO_SIZE_MB * 1024 * 1024
}

def validate_and_sanitize_upload(
    file_bytes: bytes,
    original_filename: str,
    declared_content_type: str,
    expected_modality: str
) -> Tuple[str, str, int]:
    """
    Validates uploaded media through the multi-stage security pipeline.
    Accepts all standard image types (JPEG, PNG, WebP, BMP, TIFF, GIF, ICO).
    
    Returns:
        Tuple[storage_key, sanitized_filename, file_size_bytes]
    """
    if expected_modality not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_MODALITY", "message": f"Unsupported modality: {expected_modality}"}
        )

    # 1. Size Validation
    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_FILE", "message": "Uploaded file is empty"}
        )
        
    max_size = MAX_FILE_SIZES.get(expected_modality, 15 * 1024 * 1024)
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": f"File exceeds maximum allowed size of {max_size // (1024*1024)}MB"}
        )

    # 2. Extension Validation
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS[expected_modality]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_EXTENSION", "message": f"File extension '{ext}' is not allowed for {expected_modality}"}
        )

    # 3. Magic-Byte & Decodability Validation
    if expected_modality == "image":
        try:
            image = Image.open(io.BytesIO(file_bytes))
            image.verify()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_IMAGE_BYTES", "message": "File header/magic bytes do not match a valid image"}
            )

    # 4. Sanitization & Storage Key Generation (UUID)
    unique_key = str(uuid.uuid4())
    sanitized_filename = f"{unique_key}{ext}"
    storage_key = f"quarantine/{expected_modality}/{sanitized_filename}"

    return storage_key, sanitized_filename, file_size
