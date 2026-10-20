"""Native pixel segmentation with overlapping tiles, never an attention map."""
import hashlib
import io
import json
from pathlib import Path
import threading
import time

import numpy as np
from PIL import Image,ImageOps
import torch
from torch.nn import functional as F


def tile_starts(length, tile, overlap):
    if tile < 32 or overlap < 0 or overlap >= tile:
        raise ValueError('Invalid tile geometry')
    if length <= tile:
        return [0]
    result=list(range(0,length-tile+1,tile-overlap))
    if result[-1]!=length-tile:
        result.append(length-tile)
    return result


class TruForLocalizer:
    def __init__(self, tile=512, overlap=96, max_tiles=48, time_budget=60):
        from models.image_deepfake.vendor.trufor.config.default import _C
        from models.image_deepfake.vendor.trufor.models.cmx.builder_np_conf import EncoderDecoder
        root=Path(__file__).resolve().parents[1]
        vendor=root/'vendor/trufor'
        manifest=json.loads((vendor/'manifest.json').read_text())
        weights=root/'artifacts/trufor.pth.tar'
        with weights.open('rb') as stream:weight_digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if weight_digest!=manifest['weights_sha256']:
            raise ValueError('Localizer weight integrity check failed')
        for name,digest in manifest['source_sha256'].items():
            if hashlib.sha256((vendor/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('Localizer source integrity check failed')
        config=_C.clone()
        config.merge_from_file(str(vendor/'config/trufor_ph3.yaml'))
        config.MODEL.PRETRAINED=''
        config.MODEL.EXTRA.NP_WEIGHTS=''
        config.freeze()
        self.model=EncoderDecoder(cfg=config).eval()
        # This verified upstream checkpoint stores a NumPy scalar metric along
        # with tensors. Permit only its numeric constructors, never arbitrary
        # checkpoint code or weights_only=False.
        scalar=np.core.multiarray.scalar
        allowed=[(scalar,'numpy.core.multiarray.scalar'),np.dtype,type(np.dtype('float64')),type(np.dtype('float32'))]
        with torch.serialization.safe_globals(allowed):
            state=torch.load(weights,map_location='cpu',weights_only=True)
        self.model.load_state_dict(state['state_dict'],strict=True)
        self.tile,self.overlap,self.max_tiles=tile,overlap,max_tiles
        self.time_budget=time_budget
        self.lock=threading.Lock()

    def predict(self, data, time_budget=None):
        with Image.open(io.BytesIO(data)) as source:
            image=ImageOps.exif_transpose(source).convert('RGB')
        pixels=np.asarray(image,dtype=np.float32)/255
        h,w=pixels.shape[:2]
        # Preserve full-image forensic context when it fits the CPU budget.
        # Unnecessarily cropping a small photo changes the global detector's
        # distribution and inflates a maximum-of-tiles anomaly score.
        native=w*h<=393216
        xs=[0] if native else tile_starts(w,self.tile,self.overlap)
        ys=[0] if native else tile_starts(h,self.tile,self.overlap)
        if len(xs)*len(ys)>self.max_tiles:
            raise ValueError('Native image exceeds the bounded localization tile budget; no pixels were silently resized or skipped')
        heat=np.zeros((h,w),np.float32)
        confidence=np.zeros_like(heat)
        mass=np.zeros_like(heat)
        scores=[]
        with self.lock,torch.inference_mode():
            started=time.monotonic()
            for y in ys:
                for x in xs:
                    if time.monotonic()-started>(self.time_budget if time_budget is None else time_budget):
                        raise ValueError('Native localization exceeded its CPU time budget; incomplete pixel maps are not returned')
                    patch=pixels[y:y+(h if native else self.tile),x:x+(w if native else self.tile)]
                    ph,pw=patch.shape[:2]
                    tensor=torch.from_numpy(patch.copy()).permute(2,0,1).unsqueeze(0)
                    # Padding supplies context for very small images, never scales pixels.
                    tensor=F.pad(tensor,(0,max(0,32-pw),0,max(0,32-ph)),mode='replicate')
                    logits,reliability,detection,_=self.model(tensor)
                    local=logits.softmax(1)[0,1,:ph,:pw].cpu().numpy()
                    conf=reliability.sigmoid()[0,0,:ph,:pw].cpu().numpy()
                    weight=np.maximum(.05,np.outer(np.hanning(ph),np.hanning(pw))).astype(np.float32)
                    heat[y:y+ph,x:x+pw]+=local*weight
                    confidence[y:y+ph,x:x+pw]+=conf*weight
                    mass[y:y+ph,x:x+pw]+=weight
                    scores.append(float(detection.sigmoid().item()))
        assert np.all(mass>0), 'Every native pixel must have coverage'
        return dict(heatmap=heat/mass,reliability=confidence/mass,
            raw_score=max(scores),tile_scores=scores,tiles=len(scores),
            coverage=1.0,width=w,height=h,method='TruFor pixel segmentation',
            inference_mode='native' if native else 'overlapping_native_tiles',calibrated=False)
