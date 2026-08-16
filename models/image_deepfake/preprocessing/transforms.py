import io
import torch
from PIL import Image
from torchvision import transforms

def get_efficientnet_transforms() -> transforms.Compose:
    """
    Returns the standard transforms required for EfficientNet-B0:
    - Resize to 224x224
    - Convert to Tensor
    - Normalize using ImageNet mean and std
    """
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                             std=[0.229, 0.224, 0.225])
    ])

def process_image_bytes(image_bytes: bytes) -> torch.Tensor:
    """
    Decodes image bytes and applies EfficientNet transforms.
    Returns a tensor of shape (1, 3, 224, 224).
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    transform = get_efficientnet_transforms()
    tensor = transform(img)
    # Add batch dimension
    return tensor.unsqueeze(0)
