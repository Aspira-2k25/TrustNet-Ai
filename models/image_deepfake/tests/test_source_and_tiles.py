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


def test_original_png_metadata_clue_is_observed_but_not_trusted():
    import io
    from PIL import Image, PngImagePlugin
    from models.image_deepfake.forensics.source_evidence import inspect_source
    stream=io.BytesIO();info=PngImagePlugin.PngInfo()
    info.add_text('XML:com.adobe.xmp','<digitalSourceType>trainedAlgorithmicMedia</digitalSourceType>')
    info.add_text('parameters','SDXL, steps: 30')
    Image.new('RGB',(300,300),'white').save(stream,'PNG',pnginfo=info)
    result=inspect_source(stream.getvalue())
    clues=result['provenance']['ai_markers']
    assert {clue['marker'] for clue in clues}=={'trainedAlgorithmicMedia','SDXL'}
    assert all(clue['status']=='unverified editable metadata' for clue in clues)
    assert 'XML:com.adobe.xmp' in result['provenance']['metadata_fields']
    assert result['provenance']['c2pa_status']=='not_checked'


@pytest.mark.parametrize('tool',['Meta AI','Gemini','GPT-image-1','Higgsfield','Claude','Kimi','DeepSeek','Grok Imagine','Ideogram','Recraft','Midjourney'])
def test_named_tool_metadata_is_only_an_editable_clue(tool):
    metadata=PngImagePlugin.PngInfo();metadata.add_text('Software',tool)
    value=inspect_source(png(metadata=metadata))
    assert value['provenance']['ai_markers']
    assert all(clue['status']=='unverified editable metadata' for clue in value['provenance']['ai_markers'])
    assert value['quality']['adequate']


def test_official_c2pa_anchors_are_pinned_and_do_not_enable_remote_fetch():
    from models.image_deepfake.forensics.source_evidence import c2pa_verification_settings
    settings=c2pa_verification_settings()
    assert 'BEGIN CERTIFICATE' in settings['trust']['trust_anchors']
    assert 'allowed_list' not in settings['trust']
    assert settings['verify']==dict(remote_manifest_fetch=False,ocsp_fetch=False,verify_trust=True,verify_timestamp_trust=True)


def test_modified_trust_anchor_bundle_is_rejected(monkeypatch):
    from pathlib import Path
    from models.image_deepfake.forensics.source_evidence import c2pa_verification_settings
    original=Path.read_bytes;c2pa_verification_settings.cache_clear()
    monkeypatch.setattr(Path,'read_bytes',lambda p:b'changed trust anchors' if p.name=='official-trust-anchors.pem' else original(p))
    try:
        with pytest.raises(ValueError,match='integrity'):c2pa_verification_settings()
    finally:c2pa_verification_settings.cache_clear()


@pytest.mark.parametrize('label',['c2pa.actions','c2pa.actions.v2','c2pa.actions.v3'])
@pytest.mark.parametrize('scheme',['http','https'])
def test_signed_actions_support_standard_ai_generation_without_vendor_names(label,scheme):
    from models.image_deepfake.forensics.source_evidence import signed_source_declarations
    uri=scheme+'://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia'
    result=signed_source_declarations({'assertions':[{'label':label,'data':{'actions':[{'action':'c2pa.created','digitalSourceType':uri}]}}]})
    assert result==[{'assertion':label,'source_type':uri,'kind':'generation'}]


@pytest.mark.parametrize('label',['c2pa.metadata','stds.iptc','stds.iptc.photometadata'])
def test_signed_iptc_ai_edit_metadata_uses_namespaces_and_jsonld_graph(label):
    from models.image_deepfake.forensics.source_evidence import signed_source_declarations
    active={'assertions':[{'label':label,'data':{'@context':{'source':'http://iptc.org/std/Iptc4xmpExt/2008-02-29/'},
        '@graph':[{'source:DigitalSourceType':{'@id':'http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia'}}]}}]}
    assert signed_source_declarations(active)[0]['kind']=='generative_edit'


@pytest.mark.parametrize('source',['http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture',
    'http://cv.iptc.org/newscodes/digitalsourcetype/algorithmicMedia',
    'http://cv.iptc.org/newscodes/digitalsourcetype/compositeSynthetic',
    'https://fake.invalid/trainedAlgorithmicMedia'])
def test_camera_generic_synthetic_and_wrong_namespace_do_not_mean_ai(source):
    from models.image_deepfake.forensics.source_evidence import signed_source_declarations
    assert not signed_source_declarations({'assertions':[{'label':'c2pa.actions','data':{'actions':[{'digitalSourceType':source}]}}]})


def test_unsigned_ingredient_descriptions_and_foreign_namespaces_are_not_active_ai_claims():
    from models.image_deepfake.forensics.source_evidence import signed_source_declarations
    ai='http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia'
    active={'ingredients':[{'assertions':[{'label':'c2pa.actions','data':{'actions':[{'digitalSourceType':ai}]}}]}],
        'assertions':[{'label':'c2pa.metadata','data':{'@context':{'fake':'https://fake.invalid/'},'fake:DigitalSourceType':ai}},
            {'label':'not.c2pa.actions','data':{'actions':[{'digitalSourceType':ai}]}}]}
    assert not signed_source_declarations(active)


@pytest.mark.parametrize('alias',[
    'http://iptc.org/std/Iptc4xmpExt/2008-02-29/DigitalSourceType',
    {'@id':'iptc:DigitalSourceType','@type':'@id'},
])
def test_signed_source_property_aliases_in_local_context_lists(alias):
    from models.image_deepfake.forensics.source_evidence import signed_source_declarations
    data={'@context':['https://example.invalid/not-fetched',
          {'iptc':'http://iptc.org/std/Iptc4xmpExt/2008-02-29/','source':alias}],
          '@graph':[{'source':{'@id':'http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia'}}]}
    result=signed_source_declarations({'assertions':[{'label':'c2pa.metadata','data':data}]})
    assert len(result)==1 and result[0]['kind']=='generation'


@pytest.mark.parametrize('context',[
    {'source':'loop','loop':'source'},
    {'source':{'@id':'https://fake.invalid/DigitalSourceType'}},
])
def test_cyclic_or_foreign_alias_cannot_create_a_source_declaration(context):
    from models.image_deepfake.forensics.source_evidence import signed_source_declarations
    data={'@context':context,'source':'http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia'}
    assert signed_source_declarations({'assertions':[{'label':'c2pa.metadata','data':data}]})==[]
