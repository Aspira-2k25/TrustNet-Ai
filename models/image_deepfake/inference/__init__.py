"""
TrustNet AI — Image Deepfake Inference Engines.
Fuses PyTorch convolutional detectors, Vision Transformers, and local Vision AI reasoning.
"""
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from models.image_deepfake.inference.local_vit_detector import LocalViTDeepfakeDetector
from models.image_deepfake.inference.huggingface_client import HuggingFaceDeepfakeClient
from models.image_deepfake.inference.lm_studio_vision_client import LMStudioVisionClient

__all__ = [
    "EfficientNetDetector",
    "LocalViTDeepfakeDetector",
    "HuggingFaceDeepfakeClient",
    "LMStudioVisionClient",
]
