"""Load versioned, model-local preprocessing and calibration configuration."""
import json


def load_runtime(path):
    config = json.loads((path / 'runtime.json').read_text(encoding='utf-8'))
    if config['labels'] != ['ham', 'smishing', 'spam']:
        raise ValueError('Unsupported semantic label mapping')
    if not 0 < config['temperature'] < 100 or not 0 < config['threshold'] < 1:
        raise ValueError('Invalid semantic calibration')
    return config
