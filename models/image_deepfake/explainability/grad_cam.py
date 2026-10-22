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


def copper_colormap(gray):
    """Copper gradient colormap transitioning from dark bronze (0) to radiant copper/amber (255)."""
    norm = gray.astype(np.float32) / 255.0
    r = np.clip(norm * 1.25 * 255, 0, 255).astype(np.uint8)
    g = np.clip(norm * 0.78 * 255, 0, 255).astype(np.uint8)
    b = np.clip(norm * 0.50 * 255, 0, 255).astype(np.uint8)
    return cv2.merge([b, g, r])


def generate(model,processor,data,feature_head=None,return_map=False,target_class=None):
    with Image.open(io.BytesIO(data)) as original:
        image=ImageOps.exif_transpose(original).convert('RGB')
    options={}
    if feature_head and feature_head.get('feature_input_size')==224:
        options={'size':{'shortest_edge':224},'crop_size':{'height':224,'width':224}}
    batch=processor(images=image,return_tensors='pt',**options)
    pixels=batch['pixel_values'].detach().requires_grad_(True)
    captures=[]
    # Support both model.vit.layers and model.vit.encoder.layer
    encoder_layers = getattr(model.vit, 'layers', None)
    if encoder_layers is None and hasattr(model.vit, 'encoder'):
        encoder_layers = getattr(model.vit.encoder, 'layer', None)
    if encoder_layers is None:
        raise ValueError('Unable to find transformer layers for Grad-CAM')
    last_layer = encoder_layers[-1]
    target_norm = getattr(last_layer, 'layernorm_before', None) or getattr(last_layer, 'layer_norm1', None)
    if target_norm is None:
        raise ValueError('Unable to find layernorm_before in last transformer layer')
    hook = target_norm.register_forward_hook(lambda module,args,output:captures.append(output))
    try:
        with torch.enable_grad():
            if feature_head:
                cls=model.vit(pixel_values=pixels,interpolate_pos_encoding=True).last_hidden_state[:,0]
                tensor=lambda name:torch.as_tensor(feature_head[name],dtype=cls.dtype,device=cls.device)
                score=(((cls-tensor('mean'))/tensor('scale'))*tensor('coef')).sum()+feature_head['intercept']
            else:
                out = model(pixel_values=pixels).logits
                target_idx = target_class if target_class is not None else 0
                if target_idx >= out.shape[-1]:
                    target_idx = 0
                score = out[:, target_idx].sum()
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
    # model view over an unrelated rectangular source photo if center cropped.
    size=options.get('size',processor.size)
    shortest=size.get('shortest_edge') if isinstance(size,dict) else getattr(size,'shortest_edge',None)
    do_crop=getattr(processor,'do_center_crop',False) or bool(feature_head and feature_head.get('feature_input_size')==224)
    ow,oh=image.size
    heat=cv2.GaussianBlur(heat,(0,0),max(1,w/96))
    if do_crop and shortest:
        rh,rw=(shortest,int(shortest*ow/oh)) if oh<=ow else (int(shortest*oh/ow),shortest)
        heat,visible,geometry=project_to_original(heat,image.size,(rh,rw))
    else:
        heat=cv2.resize(heat,(ow,oh),interpolation=cv2.INTER_LINEAR)
        visible=np.ones((oh,ow),dtype=bool)
        geometry=dict(resized_width=ow,resized_height=oh,crop_left=0,crop_top=0,crop_width=ow,crop_height=oh)
    positives=heat[visible & (heat>0)]
    floor=float(np.quantile(positives,.7)) if len(positives) else 1.
    alpha=np.where(visible & (heat>=floor),np.clip(.55*heat, .2, .7),0)[...,None]
    original=cv2.cvtColor(np.asarray(image),cv2.COLOR_RGB2BGR)
    color=copper_colormap(np.clip(heat*255,0,255).astype(np.uint8))
    overlay=np.clip(original*(1-alpha)+color*alpha,0,255).astype(np.uint8)

    # Canny edge enhancement: trace the sharp edges of the object inside the active attention area
    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    canny = cv2.Canny(gray, 40, 120)
    active_edges = (canny > 0) & (heat >= floor) & visible
    overlay[active_edges] = np.clip(overlay[active_edges].astype(np.int32) + [30, 140, 240], 0, 255).astype(np.uint8)

    result={'image':encode_png(overlay),'view_width':w,'view_height':h,'positive_gradient_signal':maximum>0,
        'original_width':ow,'original_height':oh,'geometry':geometry,'display_floor':floor,
        'legend':{'low':'dark copper bronze','high':'radiant golden amber','edges':'copper edges','unseen':'unchanged original pixels'},
        'target':'Frozen feature-head AI logit' if feature_head else 'Primary ViT AI logit',
        'note':'Copper Grad-CAM & Saliency with Canny edges show where the model looked (not edited pixels). Positive contributions are not proof of AI alone.'}
    if return_map:result.update(heatmap=heat,coverage=visible)
    return result
