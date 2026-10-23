import importlib.util
from pathlib import Path
import zipfile
import pytest

@pytest.fixture
def installer(tmp_path):
    source=Path(__file__).resolve().parents[3]/'scripts/setup/install-image-model.py'
    spec=importlib.util.spec_from_file_location('image_installer_fixture',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROOT=tmp_path
    return module

def test_installer_rejects_traversal_before_activation(installer,tmp_path):
    package=tmp_path/'bad.zip'
    with zipfile.ZipFile(package,'w') as archive:archive.writestr('../escaped.py','bad')
    with pytest.raises(ValueError,match='Unsafe'):
        installer.install(package)
    assert not (tmp_path/'models/image_deepfake/artifacts').exists()
    assert not (tmp_path/'models/escaped.py').exists()

def test_installer_preserves_existing_directory(installer,tmp_path):
    active=tmp_path/'models/image_deepfake/artifacts';active.mkdir(parents=True)
    (active/'keep.txt').write_text('preserve')
    with pytest.raises(ValueError,match='already exists'):
        installer.install(tmp_path/'missing.zip')
    assert (active/'keep.txt').read_text()=='preserve'

def test_installer_rejects_incomplete_artifact(installer,tmp_path):
    package=tmp_path/'incomplete.zip'
    with zipfile.ZipFile(package,'w') as archive:archive.writestr('manifest.json','{}')
    with pytest.raises(ValueError,match='Artifact rejected'):
        installer.install(package)
    assert not (tmp_path/'models/image_deepfake/artifacts').exists()
