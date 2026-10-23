import hashlib
import json
import pytest
from models.image_deepfake.inference.vit_artifact import validate
from models.image_deepfake.inference.vit_policy import MODEL


def artifact(tmp_path):
    files = {'config.json': json.dumps({'id2label': {'0': 'real', '1': 'fake'}}),
             'preprocessor_config.json': '{}', 'model.safetensors': 'contract fixture, not model weights',
             'training_report.json': '{}', 'dataset_index.json': json.dumps([
                 {'sha256': f'{split}-{label}', 'group': f'{split}-{label}', 'label': label, 'split': split}
                 for split in ('train', 'validation', 'test') for label in (0, 1)])}
    for name, content in files.items(): (tmp_path/name).write_text(content)
    hashes = {n: hashlib.sha256((tmp_path/n).read_bytes()).hexdigest() for n in files}
    manifest = {'format_version': 1, 'model_id': MODEL, 'architecture': 'ViTForImageClassification',
                'input_policy': 'detected-box-padding-0-v1', 'data_kind': 'real',
                'labels': {'0': 'real', '1': 'fake'}, 'files': hashes, 'revision': 'local-'+hashes['model.safetensors']}
    (tmp_path/'vit_manifest.json').write_text(json.dumps(manifest))
    return manifest


def test_changed_candidate_bytes_are_rejected(tmp_path):
    artifact(tmp_path); (tmp_path/'model.safetensors').write_text('changed')
    with pytest.raises(ValueError, match='hash mismatch'): validate(tmp_path)


def test_wrong_candidate_label_order_is_rejected(tmp_path):
    manifest = artifact(tmp_path); manifest['labels'] = {'0': 'fake', '1': 'real'}
    (tmp_path/'vit_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='contract'): validate(tmp_path)


def test_vit_training_never_silently_uses_cpu(tmp_path, monkeypatch):
    from models.image_deepfake.training.train_vit import run
    import torch
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)
    with pytest.raises(ValueError, match='GPU'):
        run('missing-train.json', 'missing-val.json', 'missing-test.json', tmp_path/'out')
    assert not (tmp_path/'out').exists()
