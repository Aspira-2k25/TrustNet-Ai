"""Explanation contracts on a tiny real ViT, without network or accuracy claims."""
import base64
import io
import cv2
import numpy as np
import torch
from PIL import Image
from transformers import ViTConfig,ViTForImageClassification,CLIPImageProcessor
from models.image_deepfake.explainability.grad_cam import generate


def test_grad_cam_uses_classifier_view_without_mutating_weights_or_leaking_hooks():
    torch.manual_seed(42)
    model=ViTForImageClassification(ViTConfig(image_size=32,patch_size=8,hidden_size=32,
        num_hidden_layers=2,num_attention_heads=4,intermediate_size=64,num_labels=1)).eval()
    processor=CLIPImageProcessor(size={'shortest_edge':32},crop_size={'height':32,'width':32})
    image=Image.fromarray(np.random.default_rng(2).integers(0,256,(80,100,3),dtype=np.uint8))
    buffer=io.BytesIO();image.save(buffer,'PNG');data=buffer.getvalue()
    params=[p.detach().clone() for p in model.parameters()]
    layer=model.vit.layers[-1].layernorm_before
    hooks=len(layer._forward_hooks)
    result=generate(model,processor,data)
    decoded=cv2.imdecode(np.frombuffer(base64.b64decode(result['image']),np.uint8),cv2.IMREAD_COLOR)
    assert decoded.shape==(32,32,3)
    assert result['view_width']==32 and result['view_height']==32
    assert 'not edited pixels' in result['note']
    assert len(layer._forward_hooks)==hooks
    assert all(p.grad is None and torch.equal(p,before) for p,before in zip(model.parameters(),params))
