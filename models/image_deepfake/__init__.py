"""
TrustNet AI — Image Deepfake Detection Model Package.
Fuses convolutional spatial representations (EfficientNet-B0), Vision Transformers (ViT),
multi-spectral physical heuristics (ELA, FFT, PRNU, Gabor, Face X-Ray, Bayer CFA),
and vision-language explainability.
"""
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector

__all__ = ["EfficientNetDetector"]
