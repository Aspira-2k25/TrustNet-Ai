import io

import pytest
from PIL import Image, PngImagePlugin

from models.image_deepfake.forensics.generator_signatures import metadata_clues
from models.image_deepfake.forensics.source_evidence import inspect_source


@pytest.mark.parametrize('name', [
    'Kimi', 'DeepSeek', 'Meta AI', 'Claude', 'Midjourney', 'Higgsfield',
    'Hixfield', 'FLUX.1', 'Kling AI', 'GPT-image-1', 'Gemini', 'Imagen 4',
    'Nano Banana', 'SDXL', 'Firefly', 'Grok Imagine', 'Ideogram', 'Recraft',
    'Leonardo.ai', 'Seedream 4', 'Qwen-Image', 'HunyuanImage', 'ComfyUI',
])
def test_original_metadata_tool_mentions_are_unverified(name):
    info = PngImagePlugin.PngInfo()
    info.add_text('Software', name)
    stream = io.BytesIO()
    Image.new('RGB', (300, 300), 'white').save(stream, 'PNG', pnginfo=info)
    provenance = inspect_source(stream.getvalue())['provenance']
    assert provenance['ai_markers']
    assert all(item['status'] == 'unverified editable metadata'
               for item in provenance['ai_markers'])
    assert provenance['c2pa_status'] == 'not_checked'
    assert not provenance.get('signature_trusted')


def test_multiple_tools_in_one_field_are_not_lost():
    clues = metadata_clues({'Software': 'Gemini, Midjourney, FLUX.1'})
    assert {clue['tool'] for clue in clues} == {'Google', 'Midjourney', 'Black Forest Labs'}


@pytest.mark.parametrize('text', ['King of the jungle', 'metadata', 'Claude Monet',
                                       'My birthday photo', 'sunflowerflux'])
def test_names_are_clues_not_generator_attribution(text):
    clues = metadata_clues({'Description': text})
    if text == 'Claude Monet':
        # A name in an ordinary caption illustrates why mentions cannot prove AI.
        assert clues[0]['status'] == 'unverified editable metadata'
    else:
        assert clues == []


def test_output_and_field_scanning_are_bounded_and_do_not_expose_full_values():
    clues = metadata_clues({str(i): 'Gemini private text not retained' for i in range(1000)})
    assert len(clues) == 128
    assert all(clue['marker'] == 'Gemini' for clue in clues)
    assert 'private text' not in str(clues)
