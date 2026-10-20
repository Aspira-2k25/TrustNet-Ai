import hashlib
import io
import numpy as np
from PIL import Image,PngImagePlugin
import pytest
from models.image_deepfake.forensics.source_evidence import inspect_source,inspect_c2pa
from models.image_deepfake.inference.localizer import tile_starts


def png(size=(503,311),metadata=None):
    stream=io.BytesIO()
    Image.new('RGB',size,(90,110,150)).save(stream,format='PNG',pnginfo=metadata)
    return stream.getvalue()


def test_original_bytes_and_native_geometry_survive_inspection():
    data=png()
    before=bytes(data)
    value=inspect_source(data)
    assert data==before
    assert value['sha256']==hashlib.sha256(data).hexdigest()
    assert value['original_dimensions']==[503,311]
    assert value['oriented_dimensions']==[503,311]
    assert value['quality']['adequate']
    assert value['provenance']['ai_markers']==[]


def test_generator_text_is_editable_metadata_not_verified_c2pa():
    metadata=PngImagePlugin.PngInfo()
    metadata.add_text('Software','OpenAI ChatGPT')
    value=inspect_source(png(metadata=metadata))
    assert value['provenance']['ai_markers']
    assert value['provenance']['c2pa_status']=='not_checked'


@pytest.mark.parametrize('length',[32,223,511,512,513,1024,1991])
def test_overlapping_native_tiles_cover_every_source_pixel(length):
    starts=tile_starts(length,512,96)
    coverage=np.zeros(length,dtype=int)
    for start in starts:
        coverage[start:start+512]+=1
    assert np.all(coverage>0)
    assert all(0<=start<length for start in starts)


def test_empty_oversized_and_too_small_uploads_are_rejected():
    for data in (b'',b'x'*(10*1024*1024+1),png((16,16)),b'<html>not an image</html>'):
        with pytest.raises((ValueError,OSError)):
            inspect_source(data)


def test_small_images_explicitly_limit_authenticity_evidence():
    assert not inspect_source(png((128,128)))['quality']['adequate']


def test_plain_text_c2pa_marker_never_creates_a_trusted_claim():
    metadata=PngImagePlugin.PngInfo();metadata.add_text('Software','c2pa ChatGPT')
    value=inspect_c2pa(png(metadata=metadata),'image/png')
    assert not value['signature_trusted']
    assert not value['asserts_ai_generation']
