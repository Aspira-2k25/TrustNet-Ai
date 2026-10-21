"""JPEG recompression observation, never an AI probability or edit mask."""
import io
import cv2
import numpy as np
from PIL import Image
from .localization_output import encode_png


class ELAAnalyzer:
    def analyze(self,native_window,is_jpeg):
        if not is_jpeg:
            return {'status':'NOT_APPLICABLE','note':'ELA is limited to JPEG input. Converting PNG or WebP to JPEG would introduce a new compression history.'},None
        buffer=io.BytesIO();native_window.save(buffer,'JPEG',quality=90,subsampling=2)
        with Image.open(io.BytesIO(buffer.getvalue())) as recompressed:
            difference=np.abs(np.asarray(native_window,dtype=np.float32)-np.asarray(recompressed.convert('RGB'),dtype=np.float32))
        observation={'status':'APPLIED','reencode_quality':90,'fixed_display_gain':8,
            'mean_absolute_difference':round(float(difference.mean()),3),
            'note':'JPEG recompression difference at fixed 8x display gain. Bright pixels can occur on genuine edges; this is not a localized edit mask.'}
        visual=encode_png(cv2.cvtColor(np.clip(difference*8,0,255).astype(np.uint8),cv2.COLOR_RGB2BGR))
        return observation,visual
