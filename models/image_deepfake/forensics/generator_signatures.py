"""Editable tool-name clues, separate from cryptographically verified origin.

Names can occur in prompts, captions or copied metadata. This catalog does not
assert that every named service generates images or embeds a particular mark.
Proprietary invisible watermarks require their provider's verifier.
"""
import re


TOOL_PATTERNS = {
    'OpenAI': r'chatgpt|dall[ -]?e|gpt[- ]?image(?:[- .]\d+)?|openai',
    'Google': r'gemini|imagen(?:[- .]\d+)?|nano banana',
    'Meta': r'meta ai|imagine with meta|imagined with ai',
    'Midjourney': r'midjourney',
    'Black Forest Labs': r'flux(?:[ .-]\d+(?:\.\d+)?)?',
    'Stability AI': r'stable diffusion|sdxl|stable cascade',
    'Adobe': r'firefly|generative fill',
    'Higgsfield': r'higgsfield|hixfield',
    'Kling': r'kling(?: ai)?',
    'Kimi': r'kimi',
    'DeepSeek': r'deepseek',
    'Anthropic': r'claude',
    'xAI': r'grok(?: imagine)?',
    'Ideogram': r'ideogram',
    'Recraft': r'recraft',
    'Leonardo': r'leonardo(?:\.ai| ai)',
    'Reve': r'reve(?: ai| image)',
    'ByteDance': r'seedream(?:[- .]\d+(?:\.\d+)?)?',
    'Alibaba': r'qwen[- ]image|tongyi wanxiang',
    'Tencent': r'hunyuan[- ]?image',
    'Image workflow': r'comfyui|automatic1111|invokeai|fooocus',
    'Digital source declaration': r'trainedAlgorithmicMedia|compositeWithTrainedAlgorithmicMedia',
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
