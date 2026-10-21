import io
import numpy as np
import pytest
from PIL import Image
from models.image_deepfake.inference.native_features import CropContract, native_crops, aggregate, crop_batch


def encoded(pixels):
    stream=io.BytesIO(); Image.fromarray(pixels).save(stream, 'PNG'); return stream.getvalue()


def test_native_crops_preserve_exact_pixels_and_coordinates():
    pixels=np.random.default_rng(8).integers(0,256,(503,601,3),dtype=np.uint8)
    crops, record=native_crops(encoded(pixels),CropContract(count=9))
    assert len(crops)==9 and record['resized'] is False
    for crop,(x,y,r,b) in zip(crops,record['boxes']):
        np.testing.assert_array_equal(np.asarray(crop), pixels[y:b,x:r])


def test_small_source_pads_without_scaling_and_records_limit():
    pixels=np.full((90,120,3),27,np.uint8)
    crops, record=native_crops(encoded(pixels))
    assert len(crops)==1 and record['edge_padding']==[134,104]
    np.testing.assert_array_equal(np.asarray(crops[0])[:90,:120],pixels)


def test_mean_topk_contract():
    np.testing.assert_allclose(aggregate([[1,8],[3,2],[5,5]],2),[3,5,4,6.5])
    with pytest.raises(ValueError): aggregate([[float('nan')]])


def test_processor_must_not_resize():
    class Processor:
        def __call__(self,images,**kwargs):
            assert kwargs['do_resize'] is False and kwargs['do_center_crop'] is False
            return {'pixel_values':np.zeros((len(images),3,224,224))}
    crop_batch(Processor(),[Image.new('RGB',(224,224))])
    with pytest.raises(ValueError): crop_batch(Processor(),[Image.new('RGB',(336,336))])


def test_training_stress_is_deterministic_and_preserves_original_pixels():
    from models.image_deepfake.inference.native_features import augment_crops
    pixels=np.random.default_rng(19).integers(0,256,(224,224,3),dtype=np.uint8)
    original=Image.fromarray(pixels.copy())
    for seed in range(8):
        first,metadata=augment_crops([original],seed)
        second,repeated=augment_crops([original],seed)
        assert metadata==repeated and metadata['resized'] is False
        assert 40<=metadata['jpeg_quality']<=95
        assert first[0].size==original.size
        np.testing.assert_array_equal(first[0],second[0])
        np.testing.assert_array_equal(original,pixels)
