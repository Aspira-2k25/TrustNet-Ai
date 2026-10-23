"""Validate a Kaggle artifact before installing it. Never overwrite existing models."""
import argparse
import json
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from models.image_deepfake.inference.artifact import TrainedImageModel

def install(package_path,target=None):
    model_root=(ROOT/'models/image_deepfake').resolve()
    destination=Path(target or model_root/'artifacts').resolve()
    if not destination.is_relative_to(model_root) or destination==model_root:
        raise ValueError('Model destination must be a dedicated directory under models/image_deepfake')
    if destination.exists():raise ValueError('Destination already exists; preserve it and select a new version directory with --target')
    destination.parent.mkdir(parents=True,exist_ok=True)
    allowed={'best_model.pt','manifest.json','dataset_index.json','training_report.json',
             'dataset_provenance.json','serving-policy-evaluation.json'}
    with tempfile.TemporaryDirectory(dir=model_root,prefix='.install-image-') as temporary:
        stage=Path(temporary)
        with zipfile.ZipFile(package_path) as package:
            entries=package.infolist()
            if len(entries)>len(allowed) or len({item.filename for item in entries})!=len(entries):
                raise ValueError('Unexpected or duplicate archive entries')
            if sum(item.file_size for item in entries)>512*1024*1024:
                raise ValueError('Artifact exceeds the extraction budget')
            for item in entries:
                if item.filename not in allowed or stat.S_ISLNK(item.external_attr>>16):
                    raise ValueError('Unsafe or unsupported artifact entry')
                (stage/item.filename).write_bytes(package.read(item))
        model=TrainedImageModel(stage)
        if not model.ready:raise ValueError('Artifact rejected: '+str(model.error))
        digest=model.manifest['weights_sha256']
        del model
        # Both resolved directories were checked against the explicit model root.
        stage.rename(destination)
    return {'directory':str(destination),'weights_sha256':digest,
            'next_step':'Restart image/scan services. For a version directory, set IMAGE_MODEL_DIR to this path.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--package',required=True);parser.add_argument('--target')
    args=parser.parse_args()
    try:print(json.dumps(install(args.package,args.target),indent=2))
    except Exception as error:parser.exit(1,str(error)+'\n')
