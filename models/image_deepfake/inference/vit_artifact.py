"""Validate a local fine-tuned ViT candidate before loading its files."""
import hashlib
import json
from pathlib import Path
from models.image_deepfake.inference.vit_policy import MODEL


def validate(directory):
    root = Path(directory).resolve()
    manifest = json.loads((root/'vit_manifest.json').read_text())
    if (manifest.get('format_version') != 1 or manifest.get('model_id') != MODEL
            or manifest.get('architecture') != 'ViTForImageClassification'
            or manifest.get('input_policy') != 'detected-box-padding-0-v1'
            or manifest.get('data_kind') != 'real' or manifest.get('labels') != {'0': 'real', '1': 'fake'}):
        raise ValueError('Unsupported ViT artifact contract')
    required = {'config.json', 'preprocessor_config.json', 'model.safetensors', 'dataset_index.json', 'training_report.json'}
    if set(manifest.get('files', {})) != required:
        raise ValueError('Incomplete or unexpected artifact files')
    for name, expected in manifest['files'].items():
        file = root/name
        if file.is_symlink() or file.resolve().parent != root or not file.is_file():
            raise ValueError('Unsafe artifact path')
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError('ViT artifact file hash mismatch: ' + name)
    config = json.loads((root/'config.json').read_text())
    if config.get('id2label') != {'0': 'real', '1': 'fake'}:
        raise ValueError('ViT label order mismatch')
    index = json.loads((root/'dataset_index.json').read_text())
    seen, groups = set(), {}
    for row in index:
        if row['sha256'] in seen: raise ValueError('Duplicate training provenance content')
        seen.add(row['sha256'])
        if row['group'] in groups and groups[row['group']] != row['split']:
            raise ValueError('Training provenance crosses source groups')
        groups[row['group']] = row['split']
    for split in ('train', 'validation', 'test'):
        if {r['label'] for r in index if r['split'] == split} != {0, 1}:
            raise ValueError('Both classes required in every artifact split')
    if manifest.get('revision') != 'local-'+manifest['files']['model.safetensors']:
        raise ValueError('Local model revision must match weights')
    return manifest
