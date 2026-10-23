import io
import os
from PIL import Image, UnidentifiedImageError
from typing import Optional, Tuple
from PIL import ImageOps

MAX_PIXELS = int(os.getenv('IMAGE_MAX_PIXELS', '4000000'))
MAX_SIDE = int(os.getenv('IMAGE_MAX_SIDE', '4096'))

def decode_image(image_bytes: bytes):
    """One orientation/frame policy for all inference entry points."""
    valid, error = ImageValidator().validate(image_bytes)
    if not valid:
        raise ValueError(error)
    with Image.open(io.BytesIO(image_bytes)) as source:
        return ImageOps.exif_transpose(source).convert('RGB')

def canonical_bytes(image_bytes: bytes) -> bytes:
    stream = io.BytesIO()
    decode_image(image_bytes).save(stream, format='PNG')
    return stream.getvalue()

class ImageValidator:
    def __init__(self, max_size_bytes: Optional[int] = None):  # 15MB default
        self.max_size_bytes = max_size_bytes if max_size_bytes is not None else int(os.getenv("MAX_IMAGE_SIZE_MB", "10")) * 1024 * 1024
        self.allowed_formats = {"JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF", "ICO"}
        self.magic_bytes = {
            b'\xFF\xD8\xFF': "JPEG",
            b'\x89PNG\r\n\x1a\n': "PNG",
            b'RIFF': "WEBP",
            b'BM': "BMP",
            b'II*\x00': "TIFF",
            b'MM\x00*': "TIFF",
            b'GIF87a': "GIF",
            b'GIF89a': "GIF",
            b'\x00\x00\x01\x00': "ICO"
        }

    def validate(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validates image bytes based on size, magic byte file signatures, and safe decodability.
        Returns (is_valid, error_message).
        """
        if len(image_bytes) == 0:
            return False, "Image is empty."

        if len(image_bytes) > self.max_size_bytes:
            return False, f"Image size exceeds the maximum limit of {self.max_size_bytes} bytes."

        # Quick magic-byte header validation
        valid_magic = False
        for magic, fmt in self.magic_bytes.items():
            if image_bytes.startswith(magic):
                valid_magic = True
                break
        
        if not valid_magic:
            return False, "Invalid or unsupported image format based on file signature."

        # Safe decoding via Pillow
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                if img.width * img.height > MAX_PIXELS or max(img.size) > MAX_SIDE:
                    return False, f'Image exceeds decoded budget: {MAX_PIXELS} pixels / {MAX_SIDE}px per side.'
                if getattr(img, 'n_frames', 1) != 1:
                    return False, 'Animated or multi-page images are not supported; supply one still image.'
                img.verify()
                if img.format not in self.allowed_formats:
                    return False, f"Format {img.format} is not allowed. Allowed formats: {self.allowed_formats}"
        except UnidentifiedImageError:
            return False, "Cannot identify image file."
        except Exception as e:
            return False, f"Image decoding failed: {str(e)}"

        try:
            with Image.open(io.BytesIO(image_bytes)) as decoded:
                decoded.load()
        except Exception as error:
            return False, f'Image pixel decoding failed: {error}'
        return True, None
