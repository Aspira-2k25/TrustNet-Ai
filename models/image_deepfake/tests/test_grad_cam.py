import io
import uuid
import torch
import numpy as np
from PIL import Image

from models.image_deepfake.explainability.grad_cam import GradCAM
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from models.image_deepfake.training.train import build_model
from models.image_deepfake.preprocessing.transforms import process_image_bytes
from shared.schemas.evidence import EvidenceItem

def create_sample_image_bytes() -> bytes:
    img = Image.new("RGB", (224, 224), color=(180, 120, 90))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def test_grad_cam_heatmap_generation():
    model = build_model(pretrained=False)  # Standalone utility fixture, not a served attribution.
    grad_cam = GradCAM(model)
    
    img_bytes = create_sample_image_bytes()
    tensor = process_image_bytes(img_bytes)
    
    heatmap = grad_cam.generate_heatmap(tensor)
    
    assert isinstance(heatmap, np.ndarray)
    assert heatmap.ndim == 2
    assert heatmap.shape == (224, 224)
    assert 0.0 <= np.min(heatmap)
    assert np.max(heatmap) <= 1.0

def test_grad_cam_evidence_generation():
    model = build_model(pretrained=False)  # Standalone utility fixture, not a served attribution.
    grad_cam = GradCAM(model)
    
    img_bytes = create_sample_image_bytes()
    tensor = process_image_bytes(img_bytes)
    
    evidence_list = grad_cam.generate_evidence(tensor, risk_score=75.0)
    
    assert isinstance(evidence_list, list)
    assert len(evidence_list) >= 1
    
    item = evidence_list[0]
    assert isinstance(item, EvidenceItem)
    assert "visual_saliency" in item.feature_or_region
    assert 0.0 <= item.contribution <= 1.0
    assert len(item.human_readable_note) > 0

def test_detector_integration_with_grad_cam():
    detector = EfficientNetDetector(enable_explainability=True, policy='image-screening-v2')
    img_bytes = create_sample_image_bytes()
    
    scan_id = str(uuid.uuid4())
    result = detector.predict(img_bytes, scan_id=scan_id)
    
    assert result.status.value == "PARTIAL_SUCCESS"
    assert result.evidence == []
    assert detector.grad_cam is None
    assert detector.model is None
