import json
import shutil
from pathlib import Path
import pytest
from models.image_deepfake.training.train import run_training
from models.image_deepfake.inference.artifact import TrainedImageModel, sha256

CONFIG=Path(__file__).resolve().parents[1]/'configs/baseline_config.yaml'

@pytest.fixture(scope='module')
def smoke_artifact(tmp_path_factory):
    output=tmp_path_factory.mktemp('image-contract')/'smoke'
    manifest=run_training(str(CONFIG),str(output),dry_run=True)
    assert manifest['deployable'] is False
    assert manifest['data_kind']=='smoke'
    assert (output/'training_report.json').is_file()
    return output

def test_smoke_training_completes_but_is_not_deployable(smoke_artifact):
    model=TrainedImageModel(smoke_artifact)
    assert not model.ready
    assert 'untrained' in model.error

def test_loader_requires_hash_and_exact_label_preprocessing_contract(smoke_artifact,tmp_path):
    # A random smoke model is used only to exercise serialization compatibility.
    # Marking this isolated test fixture real does not measure or claim accuracy.
    root=tmp_path/'fixture';shutil.copytree(smoke_artifact,root)
    path=root/'manifest.json';manifest=json.loads(path.read_text())
    import hashlib
    index=[{'split':split,'label':label,'sha256':hashlib.sha256(f'{split}-{label}'.encode()).hexdigest(),
            'group_sha256':hashlib.sha256(f'group-{split}-{label}'.encode()).hexdigest()}
           for split in ('train','validation','test') for label in (0,1)]
    (root/'dataset_index.json').write_text(json.dumps(index))
    manifest.update(deployable=True,data_kind='real',dataset_index_sha256=sha256(root/'dataset_index.json'))
    path.write_text(json.dumps(manifest))
    model=TrainedImageModel(root)
    assert model.ready, model.error
    manifest['labels']={'0':'fake','1':'real'};path.write_text(json.dumps(manifest))
    assert not TrainedImageModel(root).ready
    manifest['labels']={'0':'real','1':'fake'};path.write_text(json.dumps(manifest))
    with (root/'best_model.pt').open('ab') as stream:stream.write(b'corruption')
    assert 'hash mismatch' in TrainedImageModel(root).error

def test_real_training_missing_manifests_fails_before_training(tmp_path):
    with pytest.raises(ValueError,match='face_crops_prepared'):
        run_training(str(CONFIG),str(tmp_path/'empty'))

def test_training_rejects_unknown_settings(tmp_path):
    import yaml
    config=yaml.safe_load(CONFIG.read_text());config['training']['imaginary_setting']=True
    path=tmp_path/'bad.yaml';path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError,match='must define only'):
        run_training(str(path),str(tmp_path/'out'),True)
