"""Editable tool-name clues, separate from cryptographically verified origin.

Names can occur in prompts, captions or copied metadata. This catalog does not
assert that every named service generates images or embeds a particular mark.
Proprietary invisible watermarks require their provider's verifier.
"""
import re


TOOL_PATTERNS = {
    'OpenAI': r'chatgpt|dall[ -]?e(?:[- ]\d+)?|gpt[- ]?image(?:[- .]\d+)?|openai|sora',
    'Google': r'gemini|imagen(?:[- .]\d+)?|nano banana|synthid',
    'Meta': r'meta ai|imagine with meta|imagined with ai',
    'Midjourney': r'midjourney',
    'Black Forest Labs': r'flux(?:[ .-]\d+(?:\.\d+)?)?|bfl',
    'Stability AI': r'stable diffusion(?:[ -]xl)?|sdxl|stable cascade|stability\.ai|dreamstudio|clipdrop',
    'Adobe': r'adobe firefly|firefly|generative fill|generative expand|photoshop ai',
    'Microsoft': r'bing image creator|copilot designer|microsoft designer|bing creator',
    'Runway': r'runway(?:ml)?|gen-1|gen-2|gen-3',
    'Pika': r'pika(?: labs|\.art)?',
    'Luma AI': r'luma(?: ai)?|dream machine',
    'Higgsfield': r'higgsfield|hixfield',
    'Kling': r'kling(?: ai)?|kuaishou',
    'Kimi': r'kimi',
    'DeepSeek': r'deepseek',
    'Anthropic': r'claude',
    'xAI': r'grok(?: imagine)?',
    'Ideogram': r'ideogram',
    'Recraft': r'recraft',
    'Leonardo': r'leonardo(?:\.ai| ai)',
    'Reve': r'reve(?: ai| image)',
    'ByteDance': r'seedream(?:[- .]\d+(?:\.\d+)?)?|dreamina|douyin ai|capcut ai',
    'Alibaba': r'qwen[- ]image|tongyi wanxiang|wanxiang',
    'Tencent': r'hunyuan[- ]?image',
    'Baidu': r'ernie[- ]vilg|wenxin yige',
    'Minimax / Hailuo': r'hailuo(?: ai)?|minimax',
    'SeaArt': r'seaart',
    'Playground': r'playground(?: ai)?',
    'NovelAI': r'novelai',
    'Civitai': r'civitai',
    'Artbreeder': r'artbreeder',
    'NightCafe': r'nightcafe',
    'Craiyon': r'craiyon|dall[ -]?e mini',
    'Photoroom': r'photoroom',
    'Magnific': r'magnific(?: ai)?',
    'Krea': r'krea(?:\.ai| ai)?',
    'Freepik': r'pikaso|freepik ai',
    'Topaz': r'topaz gigapixel|topaz photo(?: ai)?|topaz labs',
    'FaceSwap': r'faceswap|roop|reactor|insightface|deepfacelab|face fusion|reface',
    'Image workflow': r'comfyui|automatic1111|invokeai|fooocus|webui|forge webui|sd-webui|vladmandic|easydiffusion|draw things',
    'Digital source declaration': r'trainedAlgorithmicMedia|compositeWithTrainedAlgorithmicMedia',
    'Diffusion prompt parameters': r'negative prompt|sampler:?\s*(?:euler|dpm|ddim)|cfg scale:?\s*\d+|model hash:',
}
_PATTERNS = [(tool, re.compile(r'(?<!\w)(?:' + pattern + r')(?!\w)', re.I))
             for tool, pattern in TOOL_PATTERNS.items()]


def metadata_clues(fields):
    """Return bounded, deduplicated mentions without retaining full field values."""
    clues = []
    for field, value in list(fields.items())[:256]:
        if not isinstance(value, str):
            continue
        for tool, pattern in _PATTERNS:
            match = pattern.search(value[:262144])
            if match:
                clues.append({'field': field, 'marker': match.group(), 'tool': tool,
                              'status': 'unverified editable metadata'})
                if len(clues) >= 128:
                    return clues
    return clues
