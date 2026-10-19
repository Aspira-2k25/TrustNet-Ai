"""Create a Colab notebook for the existing checked GPU package."""
import json
from pathlib import Path

def markdown(text):return {'cell_type':'markdown','metadata':{},'source':text.splitlines(True)}
def code(text):return {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':text.splitlines(True)}
cells=[markdown('''# TrustNet phishing training on Colab
Select **Runtime → Change runtime type → GPU**. Upload phishing-gpu.zip to My Drive/TrustNetPhishing first. This notebook trains phishing URL models only; it does not fetch dataset URLs or run the website services.

Colab GPU availability and session duration are limited. The current trainer saves its best model after an epoch but does not resume optimizer/batch state after interruption. A full run may not fit one free session; do not describe a shortened run as the full experiment.
'''),code('''from google.colab import drive
drive.mount('/content/drive')
from pathlib import Path
import zipfile, hashlib, json
root = Path('/content/trustnet-phishing')
root.mkdir(parents=True, exist_ok=True)
package = Path('/content/drive/MyDrive/TrustNetPhishing/phishing-gpu.zip')
assert package.exists(), 'Upload phishing-gpu.zip to My Drive/TrustNetPhishing'
with zipfile.ZipFile(package) as archive:
    for member in archive.namelist():
        assert (root/member).resolve().is_relative_to(root.resolve()), 'Unsafe archive path'
    archive.extractall(root)
manifest = json.loads((root/'GPU_PACKAGE_MANIFEST.json').read_text())
for name, digest in manifest.items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest, name
print('Package files verified')
'''),code('''import subprocess, sys
env = Path('/content/phishing-env')
subprocess.run([sys.executable, '-m', 'venv', '--system-site-packages', str(env)], check=True)
python = str(env/'bin/python')
# Preserve Colab's installed CUDA PyTorch instead of installing the Windows lock.
subprocess.run([python, '-m', 'pip', 'install',
    'lightgbm==4.7.0', 'scikit-learn==1.9.1', 'numpy==2.4.6',
    'joblib==1.6.0', 'pydantic==2.13.5', 'transformers==5.19.0',
    'safetensors==0.8.0', 'tldextract==5.4.0'], check=True)
subprocess.run([python, '-c',
    'import torch; assert torch.cuda.is_available(), "Select a GPU runtime"; print(torch.cuda.get_device_name(0))'], check=True)
subprocess.run([python, '-m', 'pip', 'freeze'], stdout=(root/'colab-environment.txt').open('w'), check=True)
'''),code('''# Persist generated checkpoints to Drive; keep large input reads on local disk.
saved = Path('/content/drive/MyDrive/TrustNetPhishing/checkpoints')
saved.mkdir(parents=True, exist_ok=True)
checkpoints = root/'models/phishing_url/checkpoints'
for name in ('bert', 'fusion', 'hybrid'):
    local = checkpoints/name
    destination = saved/name
    destination.mkdir(parents=True, exist_ok=True)
    if not local.exists():
        local.symlink_to(destination, target_is_directory=True)
print('Checkpoint output uses Drive. Existing output folders are preserved.')
'''),code('''# Full dataset; lower batch size if GPU memory is insufficient.
batch_size = 8
dataset = 'models/phishing_url/data/primary/prepared/prepared.csv'
subprocess.run([python, '-m', 'models.phishing_url.training.train_bert', dataset,
    'models/phishing_url/data/bert_source', 'models/phishing_url/checkpoints/bert',
    '--epochs', '3', '--batch-size', str(batch_size)], cwd=root, check=True)
'''),code('''subprocess.run([python, '-m', 'models.phishing_url.training.tune_ensemble',
    'models/phishing_url/checkpoints/lightgbm/validation_predictions.csv',
    'models/phishing_url/checkpoints/bert/validation_predictions.csv',
    'models/phishing_url/checkpoints/fusion'], cwd=root, check=True)
subprocess.run([python, '-m', 'models.phishing_url.training.build_bundle',
    'models/phishing_url/checkpoints/lightgbm', 'models/phishing_url/checkpoints/bert',
    'models/phishing_url/checkpoints/fusion', 'models/phishing_url/checkpoints/hybrid'], cwd=root, check=True)
subprocess.run([python, '-m', 'models.phishing_url.evaluation.evaluate', dataset,
    'models/phishing_url/checkpoints/hybrid/manifest.json',
    'models/phishing_url/research/hybrid_test.json'], cwd=root, check=True)
'''),code('''from google.colab import files
output = Path('/content/drive/MyDrive/TrustNetPhishing/phishing-trained-results.zip')
with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    bundle = root/'models/phishing_url/checkpoints/hybrid'
    for path in bundle.rglob('*'):
        if path.is_file(): archive.write(path, str(path.relative_to(root)))
    for relative in ('models/phishing_url/research/hybrid_test.json', 'colab-environment.txt'):
        archive.write(root/relative, relative)
files.download(str(output))
'''),markdown('''Return phishing-trained-results.zip to the TrustNet checkout. Review the hybrid test results before replacing the current RF baseline. Nothing in this notebook claims that the GPU run has already completed.
''')]
path=Path('docs/phishing/Phishing_Colab.ipynb')
path.write_text(json.dumps({'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'},'accelerator':'GPU'},'nbformat':4,'nbformat_minor':5},indent=2),encoding='utf-8')
for cell in cells:
    if cell['cell_type']=='code':compile(''.join(cell['source']),str(path),'exec')
print(f'Created and syntax-checked {path}')
