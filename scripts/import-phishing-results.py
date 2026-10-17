"""Import only model artifacts and evidence from the trusted Kaggle output ZIP."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
archive = Path(sys.argv[1])
prefix = 'trustnet-phishing/'
allowed = ('models/phishing_url/checkpoints/hybrid/',
           'models/phishing_url/checkpoints/bert/',
           'models/phishing_url/checkpoints/fusion/')
evidence = {'models/phishing_url/research/hybrid_test.json', 'training.log'}
with zipfile.ZipFile(archive) as source:
    for member in source.infolist():
        if not member.filename.startswith(prefix) or member.is_dir():
            continue
        relative = member.filename[len(prefix):]
        # Keep the large optimizer state in the original ZIP for recovery.
        if relative.endswith('/resume.pt'):
            continue
        if not (relative.startswith(allowed) or relative in evidence):
            continue
        target = root / relative
        if relative == 'training.log':
            target = root / 'models/phishing_url/research/kaggle_training.log'
        if not target.resolve().is_relative_to(root):
            raise ValueError('Unsafe archive path')
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open(member) as incoming, target.open('wb') as outgoing:
            shutil.copyfileobj(incoming, outgoing)

bundle = root / 'models/phishing_url/checkpoints/hybrid'
manifest = json.loads((bundle / 'manifest.json').read_text())
fusion = manifest['fusion']
files = {manifest['lightgbm']['artifact']: manifest['lightgbm']['sha256'],
         fusion['calibrator']: fusion['calibrator_sha256'],
         **manifest['bert']['files'],
         **{v['artifact']: v['sha256'] for v in fusion['fallbacks'].values()}}
for relative, digest in files.items():
    path = (bundle / relative).resolve()
    if not path.is_relative_to(bundle.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError(f'Bundle checksum mismatch: {relative}')
dataset = root / 'models/phishing_url/data/primary/prepared/prepared.csv'
assert hashlib.sha256(dataset.read_bytes()).hexdigest() == manifest['bert']['dataset_sha256']
assert manifest['bert']['full_training_partition']
report = {'archive': archive.name, 'verified_bundle_files': len(files),
          'manifest_sha256': hashlib.sha256((bundle / 'manifest.json').read_bytes()).hexdigest(),
          'dataset_sha256': manifest['bert']['dataset_sha256'],
          'full_training_partition': True, 'epochs': len(manifest['bert']['history'])}
(root / 'models/phishing_url/research/kaggle_import.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
