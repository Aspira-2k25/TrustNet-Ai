"""Create masks and overlays from segmentation probabilities, not image edges."""
import base64
import io
import cv2
import numpy as np


def pixel_mask(heatmap,reliability,threshold,min_reliability,min_area_fraction):
    if heatmap.shape!=reliability.shape or heatmap.ndim!=2:
        raise ValueError('Segmentation and reliability dimensions must match')
    if not np.isfinite(heatmap).all() or not np.isfinite(reliability).all():
        raise ValueError('Invalid segmentation probabilities')
    candidate=((heatmap>=threshold)&(reliability>=min_reliability)).astype(np.uint8)
    count,labels,stats,_=cv2.connectedComponentsWithStats(candidate,8)
    minimum=max(16,round(candidate.size*min_area_fraction))
    mask=np.zeros_like(candidate)
    regions=[]
    for index in range(1,count):
        x,y,w,h,area=map(int,stats[index])
        if area<minimum:
            continue
        mask[labels==index]=255
        regions.append(dict(x=x,y=y,width=w,height=h,area_pixels=area,
            mean_probability=float(heatmap[labels==index].mean()),
            mean_reliability=float(reliability[labels==index].mean())))
    return mask,regions


def encode_png(array):
    success,encoded=cv2.imencode('.png',array)
    if not success:
        raise ValueError('Failed to encode forensic output')
    return base64.b64encode(encoded).decode('ascii')


def assets(rgb,heatmap,reliability,config):
    if rgb.shape[:2]!=heatmap.shape:
        raise ValueError('Localization must align to native oriented source pixels')
    mask,regions=pixel_mask(heatmap,reliability,config['pixel_threshold'],
        config['min_reliability'],config['min_area_fraction'])
    color=cv2.applyColorMap((np.clip(heatmap,0,1)*255).astype(np.uint8),cv2.COLORMAP_INFERNO)
    bgr=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
    overlay=bgr.copy()
    selected=mask>0
    overlay[selected]=cv2.addWeighted(bgr,.35,color,.65,0)[selected]
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    # Glowing dual-contour for sharp visual contrast
    cv2.drawContours(overlay,contours,-1,(40,180,255),2)
    cv2.drawContours(overlay,contours,-1,(255,255,255),1)
    # Highlight each detected AI / edited region with bounding box
    for r in regions:
        rx, ry, rw, rh = r['x'], r['y'], r['width'], r['height']
        cv2.rectangle(overlay, (rx, ry), (rx + rw, ry + rh), (40, 180, 255), 1)
    raw=io.BytesIO()
    np.savez_compressed(raw,heatmap=heatmap.astype(np.float32),reliability=reliability.astype(np.float32))
    return dict(overlay=encode_png(overlay),heatmap=encode_png(color),mask=encode_png(mask),
                raw_heatmap=base64.b64encode(raw.getvalue()).decode('ascii')),regions
