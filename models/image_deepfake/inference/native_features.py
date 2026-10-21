"""Shared train/serve pixel contract for frozen native-crop feature heads.

Never resize a source image. Small images are edge-padded, with that limitation
recorded. This extractor is experimental until an independent promotion gate passes.
"""
import io
from dataclasses import dataclass
import numpy as np
from PIL import Image, ImageOps


@dataclass(frozen=True)
class CropContract:
    size: int = 224
    grid: int = 3
    top_k: int = 3
    count: int = 5
    version: str = 'native-crops-v1'

    def __post_init__(self):
        if self.size not in (224, 336) or self.grid not in (2, 3) or self.top_k < 1 or self.count not in (5,9):
            raise ValueError('Unsupported native crop contract')


def native_crops(data: bytes, contract: CropContract = CropContract()):
    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
    width, height = image.size
    pixels = np.asarray(image)
    padding = (max(0, contract.size-height), max(0, contract.size-width))
    if any(padding):
        pixels = np.pad(pixels, ((0, padding[0]), (0, padding[1]), (0, 0)), mode='edge')
    h, w = pixels.shape[:2]
    xs = sorted(set(round(v) for v in np.linspace(0, w-contract.size, contract.grid)))
    ys = sorted(set(round(v) for v in np.linspace(0, h-contract.size, contract.grid)))
    boxes = [(x, y, x+contract.size, y+contract.size) for y in ys for x in xs]
    if contract.count==5 and len(boxes)>5:
        boxes=[boxes[i] for i in (0,len(xs)-1,len(boxes)//2,len(boxes)-len(xs),len(boxes)-1)]
    crops = [Image.fromarray(pixels[y:b, x:r].copy()) for x, y, r, b in boxes]
    # A sparse crop grid is sampled evidence, not full pixel coverage.
    return crops, dict(source_size=[width, height], boxes=boxes, edge_padding=list(padding),
                       resized=False, full_coverage=False, contract=contract.__dict__)


def aggregate(features, top_k=3):
    """Per-channel mean and largest-k mean, in the declared crop order."""
    x = np.asarray(features, dtype=np.float32)
    if x.ndim != 2 or not len(x) or not np.isfinite(x).all():
        raise ValueError('Expected finite crop-by-channel features')
    k = min(top_k, len(x))
    return np.concatenate([x.mean(axis=0), np.sort(x, axis=0)[-k:].mean(axis=0)])


def crop_batch(processor, crops):
    batch = processor(images=crops, do_resize=False, do_center_crop=False, return_tensors='pt')
    if any(tuple(v.shape[-2:]) != (c.height, c.width) for v, c in zip(batch['pixel_values'], crops)):
        raise ValueError('Processor changed native crop geometry')
    return batch


def augment_crops(crops, seed):
    """Training-only JPEG/blur/noise/screenshot stress views, without resizing.

    Original uploads and the unaugmented native inference path are unchanged.
    The same source seed is shared by every frozen backbone.
    """
    from PIL import ImageFilter
    rng=np.random.default_rng(seed);quality=int(rng.integers(40,96));kind=int(rng.integers(0,4));result=[]
    for crop in crops:
        image=crop.copy()
        if kind==1:image=image.filter(ImageFilter.GaussianBlur(.5))
        elif kind==2:
            pixels=np.asarray(image,dtype=np.float32)
            image=Image.fromarray(np.clip(pixels+rng.normal(0,2,pixels.shape),0,255).astype(np.uint8))
        elif kind==3:
            pixels=np.array(image);pixels[:12]=235;image=Image.fromarray(pixels)
        buffer=io.BytesIO();image.save(buffer,'JPEG',quality=quality,subsampling=2)
        with Image.open(io.BytesIO(buffer.getvalue())) as decoded:result.append(decoded.convert('RGB'))
    return result,{'jpeg_quality':quality,'variant':['jpeg','blur','noise','screenshot_proxy'][kind],'resized':False}


def community_features(classifier, data, contract=CropContract(), batch_size=3):
    import torch
    crops, record = native_crops(data, contract)
    vectors = []
    with classifier.lock, torch.inference_mode():
        for start in range(0, len(crops), batch_size):
            batch = crop_batch(classifier.processor, crops[start:start+batch_size])
            vectors.extend(classifier.model.vit(**batch, interpolate_pos_encoding=True)
                           .last_hidden_state[:, 0].cpu().numpy())
    return aggregate(vectors, contract.top_k), record
