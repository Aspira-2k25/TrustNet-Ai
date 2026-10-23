"""Pinned local YuNet acceptance authority; never downloads or falls back to Haar."""
import hashlib
import json
import math
import threading
from pathlib import Path


class FaceLocalizer:
    def __init__(self):
        self.model = None
        self.error = None
        self.identity = None
        self.rejected = []
        self._lock = threading.Lock()
        try:
            import cv2
            root = Path(__file__).resolve().parents[1] / 'localization'
            manifest = json.loads((root / 'manifest.json').read_text())
            path = (root / manifest['file']).resolve()
            if path.parent != root.resolve() or hashlib.sha256(path.read_bytes()).hexdigest() != manifest['sha256']:
                raise ValueError('Face detector integrity check failed')
            self.model = cv2.FaceDetectorYN.create(str(path), '', (320, 320), .9, .3, 5000)
            self.identity = {**manifest, 'confidence_threshold': .9, 'max_input_edge': 1280,
                             'strategy': 'yunet-landmarks-v1'}
        except Exception as error:
            self.error = type(error).__name__ + ': face localization unavailable'

    @property
    def ready(self):
        return self.model is not None

    @staticmethod
    def valid(row, width, height):
        if len(row) != 15 or not all(math.isfinite(float(v)) for v in row):
            return False
        x, y, w, h = map(float, row[:4])
        if row[14] < .9 or min(w, h) < 28 or x < 0 or y < 0 or x+w > width or y+h > height:
            return False
        points = [(float(row[i]), float(row[i+1])) for i in range(4, 14, 2)]
        if any(not (x <= px <= x+w and y <= py <= y+h) for px, py in points):
            return False
        eye1, eye2, nose, mouth1, mouth2 = points
        return (.12*w < abs(eye1[0]-eye2[0]) < .85*w
                and abs(eye1[1]-eye2[1]) < .3*h
                and abs(mouth1[1]-mouth2[1]) < .3*h
                and (eye1[1]+eye2[1])/2 < (mouth1[1]+mouth2[1])/2
                and min(eye1[1],eye2[1]) <= nose[1] <= max(mouth1[1],mouth2[1]))

    def detect(self, rgb):
        import cv2
        with self._lock:
            self.rejected = []
            if not self.ready:
                raise RuntimeError(self.error)
            height, width = rgb.shape[:2]
            scale = min(1., 1280/max(width,height))
            source = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            if scale < 1:
                source = cv2.resize(source, (round(width*scale), round(height*scale)))
            sh, sw = source.shape[:2]
            self.model.setInputSize((sw,sh))
            _, faces = self.model.detect(source)
            boxes = []
            for row in faces if faces is not None else []:
                if not self.valid(row,sw,sh):
                    self.rejected.append({'reason':'confidence, bounds or landmark geometry rejected'})
                    continue
                x,y,w,h = [round(float(v)/scale) for v in row[:4]]
                boxes.append((x,y,min(w,width-x),min(h,height-y)))
            return boxes
