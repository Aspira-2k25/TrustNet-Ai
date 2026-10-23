"""Record model/runtime identity without images, credentials or environment dumps."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector

parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True); args = parser.parse_args()
target = Path(args.output)
if target.exists(): raise ValueError('Refusing to overwrite a baseline')
detector = EfficientNetDetector()
state = detector.readiness()
versions = {}
for name in ('torch', 'torchvision', 'transformers', 'pillow', 'opencv-python', 'numpy'):
    try: versions[name] = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError: versions[name] = None
report = {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
          'working_tree_modified': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
          'python': platform.python_version(), 'platform': platform.platform(), 'dependencies': versions,
          'readiness': state, 'model_id': detector.local_vit.model_name, 'model_revision': detector.local_vit.revision,
          'processor': detector.local_vit.processor_identity,
          'limits': 'Runtime identity only. No dataset accuracy or promotion is established.'}
target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('Recorded runtime identity: '+str(target))
