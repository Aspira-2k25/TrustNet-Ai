"""Install a validated local ViT into a new version directory without activation."""
import argparse
import json
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from models.image_deepfake.inference.vit_artifact import validate


def install(package, target):
    root = (ROOT/'models/image_deepfake').resolve(); destination = Path(target).resolve()
    if destination == root or not destination.is_relative_to(root) or destination.exists():
        raise ValueError('Choose a new dedicated version directory under models/image_deepfake')
    allowed = {'vit_manifest.json', 'config.json', 'preprocessor_config.json', 'model.safetensors', 'dataset_index.json', 'training_report.json'}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root, prefix='.install-vit-') as temporary:
        stage = Path(temporary)
        with zipfile.ZipFile(package) as archive:
            entries = archive.infolist()
            if set(e.filename for e in entries) != allowed or len(entries) != len(allowed):
                raise ValueError('Unexpected, missing or duplicate archive entries')
            if sum(e.file_size for e in entries) > 512*1024*1024:
                raise ValueError('Extraction budget exceeded')
            for entry in entries:
                if stat.S_ISLNK(entry.external_attr >> 16): raise ValueError('Symlinks forbidden')
                (stage/entry.filename).write_bytes(archive.read(entry))
        manifest = validate(stage)
        # Confirm architecture/processor compatibility using local files only.
        from transformers import AutoImageProcessor, AutoModelForImageClassification
        processor = AutoImageProcessor.from_pretrained(stage, local_files_only=True)
        model = AutoModelForImageClassification.from_pretrained(stage, local_files_only=True)
        if type(model).__name__ != 'ViTForImageClassification': raise ValueError('Wrong model architecture')
        del processor, model
        stage.rename(destination)
    return {'directory': str(destination), 'revision': manifest['revision'], 'activated': False,
            'next_step': 'Evaluate with IMAGE_VIT_MODEL_DIR set to this directory. Keep the default model until independent test promotion passes.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--package', required=True); parser.add_argument('--target', required=True)
    args = parser.parse_args(); print(json.dumps(install(args.package, args.target), indent=2))
