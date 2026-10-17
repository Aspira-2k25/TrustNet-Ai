"""Package the immutable data, pinned BERT source and training code for GPU use."""
import hashlib
import json
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parent.parent
output=root/'exports'/'phishing-gpu.zip';output.parent.mkdir(parents=True,exist_ok=True)
files=[]
for directory in ('models/phishing_url','shared'):
    files.extend(path for path in (root/directory).rglob('*.py') if '__pycache__' not in path.parts)
files.extend(path for path in (root/'models/phishing_url/data/bert_source').iterdir() if path.is_file())
files.extend([root/'models/phishing_url/data/primary/prepared/prepared.csv',root/'models/phishing_url/data/primary/prepared/preparation.json',root/'models/phishing_url/data/dataset_manifest.json',root/'scripts/train-phishing-gpu.sh',root/'services/phishing_url/requirements.lock',root/'docs/phishing/gpu_run.md'])
files.extend(path for path in (root/'models/phishing_url/checkpoints/lightgbm').iterdir() if path.is_file())
files.extend([root/'docs/phishing/Phishing_Kaggle.ipynb',root/'docs/phishing/kaggle_run.md'])
manifest={str(path.relative_to(root)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
    for path in files:archive.write(path,str(path.relative_to(root)))
    archive.writestr('GPU_PACKAGE_MANIFEST.json',json.dumps(manifest,indent=2))
report={'package':str(output.relative_to(root)),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size,'file_count':len(files),'full_training_executed':False}
(root/'models/phishing_url/research/gpu_package.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
