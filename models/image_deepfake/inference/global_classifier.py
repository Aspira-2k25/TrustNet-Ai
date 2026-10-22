"""Pinned classifiers with explicit label semantics and unmodified source bytes."""
import io
from pathlib import Path
import threading

from PIL import Image, ImageOps
import numpy as np
import torch

CANDIDATES = {
    'dima806': {'id':'dima806/deepfake_vs_real_image_detection',
        'ai_label':'Fake', 'real_label':'Real', 'license':'apache-2.0'},
    'community': {'id':'buildborderless/CommunityForensics-DeepfakeDet-ViT',
        'revision':'ac6ee457bea904a373065754107451793b56db00',
        'output_kind':'single_sigmoid', 'license':'mit'},
    'siglip': {'id':'Ateeqq/ai-vs-human-image-detector',
        'revision':'60e82406916921b823616bee33397baab38af3f0', 'ai_label':'ai', 'real_label':'hum', 'license':'apache-2.0'},
    'siglip_three': {'id':'prithivMLmods/AI-vs-Deepfake-vs-Real-9999',
        'revision':'c706302d833f58adc1cb09c98545b53f985e9f5a', 'ai_label':'Artificial', 'real_label':'Real one', 'license':'apache-2.0'},
}


class GlobalClassifier:
    def __init__(self, name, model_path=None):
        from transformers import AutoImageProcessor, AutoModelForImageClassification
        spec=CANDIDATES[name]
        location=str(model_path or spec['id'])
        options={'local_files_only':True}
        if not model_path and spec.get('revision'):
            options['revision']=spec['revision']
        self.processor=AutoImageProcessor.from_pretrained(location,**options)
        self.model=AutoModelForImageClassification.from_pretrained(location,**options).eval()
        self.labels={int(k):str(v) for k,v in self.model.config.id2label.items()}
        self.single_logit=spec.get('output_kind')=='single_sigmoid'
        # Normalize labels to casefold
        normalized={v.casefold():k for k,v in self.labels.items()}
        if self.single_logit:
            cfg=self.model.config
            if cfg.num_labels!=1 or cfg.num_attention_heads!=6 or cfg.intermediate_size!=1536:
                raise ValueError('Community Forensics architecture differs from the pinned corrected checkpoint')
            self.ai_index,self.real_index=0,1
            self.labels={0:'ai',1:'real'}
        elif spec['ai_label'].casefold() not in normalized or spec['real_label'].casefold() not in normalized:
            raise ValueError(f'Unexpected classifier label mapping: {self.labels}')
        else:
            self.ai_index=normalized[spec['ai_label'].casefold()]
            self.real_index=normalized[spec['real_label'].casefold()]
        self.spec=spec
        self.lock=threading.Lock()

    def predict(self, image_bytes, return_embedding=False):
        with Image.open(io.BytesIO(image_bytes)) as original:
            original_shape=original.size
            image=ImageOps.exif_transpose(original).convert('RGB')
        # This is the classifier's documented model view. Native source pixels are
        # retained separately for localization and never replaced with this tensor.
        batch=self.processor(images=image,return_tensors='pt')
        with self.lock, torch.inference_mode():
            if return_embedding:
                if not self.single_logit:raise ValueError('Embedding extraction is defined only for the selected ViT')
                features=self.model.vit(**batch).last_hidden_state[:,0]
                logits=self.model.classifier(features)
            else:
                logits=self.model(**batch).logits
            if self.single_logit:
                positive=float(logits.sigmoid().item())
                probabilities=np.asarray([positive,1-positive])
            else:
                probabilities=logits.softmax(-1)[0].cpu().numpy()
        if not np.isfinite(probabilities).all():
            raise ValueError('Non-finite model output')
        result=dict(ai_score=float(probabilities[self.ai_index]), real_score=float(probabilities[self.real_index]),
            class_probabilities={label:float(probabilities[index]) for index,label in self.labels.items()},
            original_shape=original_shape, model_view_shape=list(batch['pixel_values'].shape),
            model_id=self.spec['id'], revision=self.spec.get('revision'), calibrated=False)
        if return_embedding:result['embedding']=features[0].cpu().numpy().tolist()
        return result

    def explain(self,image_bytes,feature_head=None):
        from models.image_deepfake.explainability.grad_cam import generate
        with self.lock:
            return generate(self.model,self.processor,image_bytes,feature_head,target_class=self.ai_index)
