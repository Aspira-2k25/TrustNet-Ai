"""Gradient-weighted ViT activation map in the classifier's own image view."""
import io
import math
import cv2
import numpy as np
import torch
from PIL import Image,ImageOps
from models.image_deepfake.forensics.localization_output import encode_png


def project_to_original(heat,original_size,resize_size):
    """Invert the processor's aspect-preserving resize and rounded center crop.

    Pixels outside the classifier view have zero coverage, not invented attention.
    """
    width,height=original_size;rh,rw=resize_size
    h,w=heat.shape
    top=int(round((rh-h)/2.));left=int(round((rw-w)/2.))
    if top<0 or left<0:raise ValueError('Padded classifier views require a separate inverse mapping')
    canvas=np.zeros((rh,rw),np.float32);coverage=np.zeros_like(canvas)
    canvas[top:top+h,left:left+w]=heat;coverage[top:top+h,left:left+w]=1
    mapped=cv2.resize(canvas,(width,height),interpolation=cv2.INTER_LINEAR)
    visible=cv2.resize(coverage,(width,height),interpolation=cv2.INTER_NEAREST)>0
    mapped[~visible]=0
    return mapped,visible,dict(resized_width=rw,resized_height=rh,crop_left=left,crop_top=top,crop_width=w,crop_height=h)


def generate(model,processor,data,feature_head=None,return_map=False):
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
    # Reconstruct the exact supported processor geometry. Never stretch a square
    # model view over an unrelated rectangular source photo.
    size=options.get('size',processor.size)
    shortest=size.get('shortest_edge') if isinstance(size,dict) else size.shortest_edge
    if not processor.do_resize or not shortest:raise ValueError('Unsupported attention resize contract')
    ow,oh=image.size
    rh,rw=(shortest,int(shortest*ow/oh)) if oh<=ow else (int(shortest*oh/ow),shortest)
    heat=cv2.GaussianBlur(heat,(0,0),max(1,w/96))
    heat,visible,geometry=project_to_original(heat,image.size,(rh,rw))
    positives=heat[visible & (heat>0)]
    floor=float(np.quantile(positives,.7)) if len(positives) else 1.
    alpha=np.where(visible & (heat>=floor),.4*heat,0)[...,None]
    original=cv2.cvtColor(np.asarray(image),cv2.COLOR_RGB2BGR)
    color=cv2.applyColorMap(np.clip(heat*255,0,255).astype(np.uint8),cv2.COLORMAP_INFERNO)
    overlay=np.clip(original*(1-alpha)+color*alpha,0,255).astype(np.uint8)
    result={'image':encode_png(overlay),'view_width':w,'view_height':h,'positive_gradient_signal':maximum>0,
        'original_width':ow,'original_height':oh,'geometry':geometry,'display_floor':floor,
        'legend':{'low':'dark purple','high':'pale yellow','unseen':'unchanged original pixels'},
        'target':'Frozen feature-head AI logit' if feature_head else 'Primary ViT AI logit',
        'note':'Where the model looked (this is not where the edit is). Grad-CAM is mapped back to the original image geometry; areas outside the classifier view are unchanged. Positive contributions are not edited pixels, proof of AI, or an explanation of every fusion branch.'}
    if return_map:result.update(heatmap=heat,coverage=visible)
    return result
