import base64
import io
import cv2
import numpy as np
from models.image_deepfake.forensics.localization_output import pixel_mask,assets


def test_empty_mask_never_lowers_the_validated_pixel_threshold():
    heat=np.full((64,64),.8,dtype=np.float32)
    mask,regions=pixel_mask(heat,np.ones_like(heat),.9,.5,.005)
    assert not mask.any()
    assert regions==[]


def test_mask_uses_segmentation_and_reliability_not_image_edges():
    heat=np.zeros((80,100),np.float32)
    heat[20:45,30:60]=.99
    heat[1:3,1:3]=1
    reliability=np.ones_like(heat)
    mask,regions=pixel_mask(heat,reliability,.9,.5,.005)
    assert np.count_nonzero(mask)==750
    assert len(regions)==1
    assert regions[0]['x']==30 and regions[0]['y']==20
    assert pixel_mask(heat,np.zeros_like(heat),.9,.5,.005)[1]==[]


def test_outputs_preserve_native_geometry_and_raw_probabilities():
    rgb=np.full((81,103,3),120,np.uint8)
    heat=np.zeros((81,103),np.float32);heat[25:50,30:65]=.98
    reliability=np.ones_like(heat)
    encoded,regions=assets(rgb,heat,reliability,{'pixel_threshold':.9,'min_reliability':.5,'min_area_fraction':.005})
    for key in ('overlay','mask','heatmap'):
        decoded=cv2.imdecode(np.frombuffer(base64.b64decode(encoded[key]),np.uint8),cv2.IMREAD_UNCHANGED)
        assert decoded.shape[:2]==rgb.shape[:2]
    with np.load(io.BytesIO(base64.b64decode(encoded['raw_heatmap'])),allow_pickle=False) as raw:
        np.testing.assert_array_equal(raw['heatmap'],heat)
    assert len(regions)==1


def test_overlay_highlights_selected_pixels_and_leaves_other_pixels_unchanged():
    rgb=np.full((80,100,3),120,np.uint8)
    heat=np.zeros((80,100),np.float32);heat[20:50,30:70]=1
    output,regions=assets(rgb,heat,np.ones_like(heat),{'pixel_threshold':.9,'min_reliability':.5,'min_area_fraction':.005})
    overlay=cv2.imdecode(np.frombuffer(base64.b64decode(output['overlay']),np.uint8),cv2.IMREAD_COLOR)
    mask=cv2.imdecode(np.frombuffer(base64.b64decode(output['mask']),np.uint8),cv2.IMREAD_GRAYSCALE)
    np.testing.assert_array_equal(overlay[5,5],rgb[5,5])
    assert not np.array_equal(overlay[30,40],rgb[30,40])
    assert mask[30,40]==255 and mask[5,5]==0
    assert len(regions)==1
