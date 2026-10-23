"""Fail setup verification when OpenCV cannot load required face/eye resources."""
import sys
from pathlib import Path

try:
    import cv2
    root = Path(cv2.data.haarcascades)
    for name in ('haarcascade_frontalface_alt2.xml', 'haarcascade_eye.xml'):
        resource = root / name
        if not resource.is_file() or cv2.CascadeClassifier(str(resource)).empty():
            raise RuntimeError(f'Missing or invalid cascade: {name}')
except Exception as error:
    print(f'[FAIL] Image localization unavailable: {error}')
    sys.exit(1)
print(f'[PASS] OpenCV {cv2.__version__}: face and eye cascades load successfully.')
