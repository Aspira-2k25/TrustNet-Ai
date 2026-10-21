"""Gradient-weighted ViT activation map in the classifier's own image view."""
import io
import math
import cv2
import numpy as np
import torch
from PIL import Image,ImageOps
from models.image_deepfake.forensics.localization_output import encode_png


def generate(model,processor,data,feature_head=None):
    with Image.open(io.BytesIO(data)) as original:
        image=ImageOps.exif_transpose(original).convert('RGB')
    options={}
    if feature_head and feature_head.get('feature_input_size')==224:
        options={'size':{'shortest_edge':224},'crop_size':{'height':224,'width':224}}
    batch=processor(images=image,return_tensors='pt',**options)
    pixels=batch['pixel_values'].detach().requires_grad_(True)
    captures=[]
    # Before the last attention operation: final patch tokens after attention
    # have no path back to the classification token in a CLS-only head.
    hook=model.vit.layers[-1].layernorm_before.register_forward_hook(lambda module,args,output:captures.append(output))
    try:
        with torch.enable_grad():
            if feature_head:
                cls=model.vit(pixel_values=pixels,interpolate_pos_encoding=True).last_hidden_state[:,0]
                tensor=lambda name:torch.as_tensor(feature_head[name],dtype=cls.dtype,device=cls.device)
                score=(((cls-tensor('mean'))/tensor('scale'))*tensor('coef')).sum()+feature_head['intercept']
            else:score=model(pixel_values=pixels).logits[:,0].sum()
            activation=captures[-1]
            gradients=torch.autograd.grad(score,activation,retain_graph=False)[0]
            weights=gradients[:,1:,:].mean(dim=1,keepdim=True)
            patch_map=torch.relu((activation[:,1:,:]*weights).sum(dim=-1))[0].detach().cpu().numpy()
    finally:hook.remove()
    side=math.isqrt(len(patch_map))
    if side*side!=len(patch_map) or not np.isfinite(patch_map).all():raise ValueError('Invalid Grad-CAM token geometry')
    maximum=float(patch_map.max(initial=0))
    heat=patch_map.reshape(side,side)/(maximum if maximum>0 else 1.)
    h,w=map(int,pixels.shape[-2:]);heat=cv2.resize(heat,(w,h),interpolation=cv2.INTER_LINEAR)
    view=pixels.detach()[0].permute(1,2,0).cpu().numpy()
    if processor.do_normalize:view=view*np.asarray(processor.image_std)+np.asarray(processor.image_mean)
    view=cv2.cvtColor(np.clip(view*255,0,255).astype(np.uint8),cv2.COLOR_RGB2BGR)
    color=cv2.applyColorMap((heat*255).astype(np.uint8),cv2.COLORMAP_INFERNO)
    overlay=cv2.addWeighted(view,.6,color,.4,0) if maximum>0 else view
    return {'image':encode_png(overlay),'view_width':w,'view_height':h,'positive_gradient_signal':maximum>0,
        'target':'Frozen feature-head AI logit' if feature_head else 'Primary ViT AI logit',
        'note':'Grad-CAM model attention on the classifier resized/cropped view. It highlights positive gradient contributions, not edited pixels, proof of AI, or an explanation of every fusion branch.'}
