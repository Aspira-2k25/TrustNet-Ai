"""Native-window high-pass statistics, without a sensor or forgery claim."""
import cv2
import numpy as np


class NoiseAnalyzer:
    def analyze(self,gray):
        values=gray.astype(np.float32)
        residual=values-cv2.GaussianBlur(values,(3,3),.8)
        return {'residual_rms':round(float(np.sqrt(np.mean(residual**2))),3),
            'unit':'8-bit luminance levels',
            'note':'High-pass residual also contains ordinary edges and texture; it is not a sensor fingerprint or proof of AI.'}
