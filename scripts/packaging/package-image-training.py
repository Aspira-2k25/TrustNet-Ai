"""Build a source-only Kaggle package and notebook; never include credentials or weights."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs'/'image-training'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    files=[]
    for folder in ['models/image_deepfake','shared/schemas','shared/constants','shared/logging','shared/config','shared/utils']:
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and path.suffix in {'.py','.yaml'} and not {'tests','__pycache__','artifacts'}.intersection(path.parts):
                files.append(path)
    for name in ('models/__init__.py','shared/__init__.py'):
        if (ROOT/name).is_file():files.append(ROOT/name)
    # v3/v4 face localization is a pinned local model, not a Haar fallback.
    for name in ('manifest.json','LICENSE','face_detection_yunet_2023mar.onnx'):
        files.append(ROOT/'models/image_deepfake/localization'/name)
    manifest={str(path.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(set(files))}
    archive=OUT/'TrustNet-Image-Training-Sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as package:
        for name in manifest:package.write(ROOT/name,name)
        package.writestr('training_source_manifest.json',json.dumps(manifest,indent=2))
    cells=[]
    def cell(kind,text):
        cells.append({'cell_type':kind,'id':f'image-training-{len(cells):02d}','metadata':{},
                      'source':text.splitlines(keepends=True),**({'outputs':[],'execution_count':None} if kind=='code' else {})})
    cell('markdown','''# TrustNet image classifier: Kaggle GPU training

Upload `TrustNet-Image-Training-Sources.zip` as a **private Kaggle dataset** and attach it here. Also attach [xhlulu/140k-real-and-fake-faces](https://www.kaggle.com/datasets/xhlulu/140k-real-and-fake-faces), version 2. Select a GPU accelerator and enable Internet for dependencies and pretrained weights. Run in a fresh session. Save the notebook version with outputs before the session ends.

This is a face/StyleGAN benchmark. It does not establish modern-generator, general-image, or zero subject-identity-leakage accuracy. The preparation step preserves publisher splits, removes detected byte/pixel duplicates, and groups source images; it has no verified person identities. Preserve upstream dataset licensing and attribution information. No credentials belong in this notebook or source archive.
''')
    cell('code','''from pathlib import Path
import hashlib, json, os, sys, zipfile, subprocess, importlib.metadata
WORK = Path('/kaggle/working/trustnet-image')
WORK.mkdir(parents=True, exist_ok=True)
# Keep Kaggle's GPU torch/torchvision installation. Install other dependencies before importing them.
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q',
    'numpy>=2,<3', 'scipy>=1.14,<2', 'scikit-learn>=1.6,<2', 'pillow>=10', 'PyYAML>=6,<7',
    'python-dotenv>=1,<2', 'pydantic>=2,<3', 'httpx>=0.27,<1',
    'transformers>=4.48,<6', 'huggingface-hub>=0.28,<2'])
opencv_variants = ('opencv-python', 'opencv-python-headless', 'opencv-contrib-python', 'opencv-contrib-python-headless')
installed = {}
for name in opencv_variants:
    try: installed[name] = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError: pass
if installed != {'opencv-python': '4.14.0.94'}:
    subprocess.check_call([sys.executable, '-m', 'pip', 'uninstall', '-y', *opencv_variants])
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'opencv-python==4.14.0.94'])
import torch, torchvision, cv2
assert torch.cuda.is_available(), 'Enable a Kaggle GPU accelerator; this notebook must not silently train on CPU.'
assert hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data'), 'Restart this session after installing dependencies.'
print('GPU:', torch.cuda.get_device_name(0), '| torch:', torch.__version__, '| OpenCV:', cv2.__version__)
''')
    cell('code','''packages = list(Path('/kaggle/input').rglob('TrustNet-Image-Training-Sources.zip'))
assert len(packages) == 1, 'Attach exactly one source archive dataset.'
SOURCE = WORK / 'source'
assert not SOURCE.exists(), 'Use a fresh working folder; do not overwrite a previous run.'
with zipfile.ZipFile(packages[0]) as archive:
    assert sum(item.file_size for item in archive.infolist()) < 10_000_000
    for item in archive.infolist():
        target = (SOURCE / item.filename).resolve()
        assert target.is_relative_to(SOURCE.resolve()), 'Unsafe archive path'
    archive.extractall(SOURCE)
source_manifest = json.loads((SOURCE / 'training_source_manifest.json').read_text())
for name, expected in source_manifest.items():
    assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == expected, name
os.chdir(SOURCE)
sys.path.insert(0, str(SOURCE))
print('Verified source files:', len(source_manifest))
''')
    cell('markdown','''## Prepare matching face crops
The CNN trains on the same Haar/eye-pair crop policy used in serving. Preparation can take substantial CPU time across 140k images. Faces that cannot be located reliably are excluded and counted. This changes the evaluated population; inspect the exclusion report. No claim of complete face coverage or subject-identity separation is made.
''')
    cell('code','''roots = [path for path in Path('/kaggle/input').rglob('140k-real-and-fake-faces') if path.is_dir()]
assert len(roots) == 1, 'Set DATASET_ROOT to the attached xhlulu dataset folder if auto-discovery is ambiguous.'
DATASET_ROOT = roots[0]
from models.image_deepfake.training.prepare_kaggle import prepare
PREPARED = WORK / 'prepared'
provenance = prepare(DATASET_ROOT, PREPARED)
print('Retained class counts:', provenance['counts'])
print('Excluded:', len(provenance['excluded_duplicates']))
print('Grouping limitations:', provenance['grouping'])
''')
    cell('code','''from models.image_deepfake.training.train import run_training
ARTIFACT = WORK / 'trained-artifact'
# Seed, 20-epoch maximum, validation selection and early stopping are in training.yaml.
# The untouched test split is evaluated only after selecting the best validation checkpoint.
training = run_training(str(PREPARED / 'training.yaml'), str(ARTIFACT), dry_run=False)
print('Held-out CNN metrics:', training['test_metrics'])
print('These metrics describe the retained publisher GAN-face split, not modern AI images.')
''')
    cell('code','''from models.image_deepfake.inference.artifact import TrainedImageModel
import shutil
shutil.copy2(PREPARED / 'dataset_provenance.json', ARTIFACT / 'dataset_provenance.json')
verified = TrainedImageModel(ARTIFACT)
assert verified.ready, verified.error
print('Verified checkpoint SHA-256:', verified.manifest['weights_sha256'])
del verified
torch.cuda.empty_cache()
''')
    cell('markdown','''## Check the actual serving policy
This runs a deterministic balanced sample from the publisher test split through the complete local screening policy, including localization and abstention. It is a separate result from the CNN's full retained test metrics. Missing/occluded faces are not silently counted as correct. External model inference is disabled; downloading pinned model weights is allowed for this cell.
''')
    cell('code','''import random
os.environ['IMAGE_MODEL_DIR'] = str(ARTIFACT)
os.environ['IMAGE_ALLOW_MODEL_DOWNLOAD'] = 'true'
os.environ['IMAGE_ALLOW_HOSTED_INFERENCE'] = 'false'
rows = json.loads((PREPARED / 'policy_test.json').read_text())
rng = random.Random(42)
sample = []
for label in (0, 1):
    candidates = [row for row in rows if row[1] == label]
    sample.extend(rng.sample(candidates, min(100, len(candidates))))
sample_path = WORK / 'serving-test-sample.json'
sample_path.write_text(json.dumps(sample))
from models.image_deepfake.evaluation.run import evaluate
policy_report = evaluate(sample_path, ARTIFACT / 'serving-policy-evaluation.json')
print('Sample size:', len(sample), '| Abstention:', policy_report['abstention_rate'])
print('Accepted decisions:', policy_report['accepted_decision_metrics'])
print('Confidence calibration is unavailable. Unseen-generator testing is still required.')
''')
    cell('code','''MODEL_ZIP = Path('/kaggle/working/TrustNet-Image-Trained-Artifact.zip')
allowed = ['best_model.pt', 'manifest.json', 'dataset_index.json', 'training_report.json',
           'dataset_provenance.json', 'serving-policy-evaluation.json']
with zipfile.ZipFile(MODEL_ZIP, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in allowed: archive.write(ARTIFACT / name, name)
print('Download:', MODEL_ZIP)
print('Archive SHA-256:', hashlib.sha256(MODEL_ZIP.read_bytes()).hexdigest())
print('Save this Kaggle notebook version with outputs. Keep training_state.pt if you need optimizer-state recovery.')
''')
    cell('markdown','''## Return to the local app
Download `TrustNet-Image-Trained-Artifact.zip` from Kaggle Output. From the local project root run:

```powershell
.\\.venv\\Scripts\\python.exe scripts/setup/install-image-model.py --package "C:\\path\\TrustNet-Image-Trained-Artifact.zip"
```

The installer rejects smoke artifacts, mismatched hashes, wrong labels and incompatible preprocessing. Restart the image and scan services after installing. Verify `/ready`, rescan images, and review abstention and real-photo errors before relying on the model. This notebook does not publish a model, upload private photos, bypass GPU quotas, or establish commercial licensing rights.
''')
    notebook={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'cells':cells}
    notebook_path=OUT/'TrustNet_Image_Kaggle_Training.ipynb'
    notebook_path.write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    # Notebook generation is validated locally; no Kaggle GPU run is implied.
    for item in cells:
        if item['cell_type']=='code':compile(''.join(item['source']),'<kaggle-cell>','exec')
    vit_cells=cells[:3]
    def vit_cell(kind, source):
        vit_cells.append({'cell_type':kind,'id':f'vit-{len(vit_cells):02d}','metadata':{},
            'source':source.splitlines(keepends=True),**({'outputs':[],'execution_count':None} if kind=='code' else {})})
    vit_cells[0]={**vit_cells[0], 'source':['# TrustNet existing ViT: baseline and conditional fine-tuning\n',
        '\nAttach the private source ZIP and labeled face data. Use a GPU and fresh session. ',
        'The xhlulu GAN-face dataset is an optional historical benchmark, not modern-generator validation. ',
        'This notebook does not publish a model or upload private portraits. Fine-tuning is disabled until explicitly selected.\n']}
    vit_cell('markdown','''## Prepare the historical benchmark (optional)
The publisher splits contain older face data with unknown upstream ViT overlap. This is a diagnostic benchmark only. End-to-end manifests retain localization failures; classifier manifests contain usable crops. Use independent recent data before selecting or promoting a policy.
''')
    vit_cell('code','''roots = [p for p in Path('/kaggle/input').rglob('140k-real-and-fake-faces') if p.is_dir()]
assert len(roots) == 1, 'Attach xhlulu/140k-real-and-fake-faces version 2, or replace this cell with your reviewed prepared manifests.'
from models.image_deepfake.training.prepare_kaggle import prepare
PREPARED = WORK / 'prepared-vit'
provenance = prepare(roots[0], PREPARED)
print(provenance['counts'])
print(provenance['limitations'])
''')
    vit_cell('markdown','''## Frozen ViT baseline
This deterministic balanced sample is a smoke evaluation. Increase to the complete independent holdout for a release benchmark. Do not use test results to fit thresholds. Direct full-frame scores are diagnostic; policy scores refer to detected faces. Both reports preserve failures in their denominators.
''')
    vit_cell('code','''import random
os.environ['IMAGE_ALLOW_MODEL_DOWNLOAD'] = 'true'
os.environ['IMAGE_ALLOW_HOSTED_INFERENCE'] = 'false'
rows = json.loads((PREPARED / 'policy_test.json').read_text())
rng = random.Random(42)
sample = []
for label in (0, 1):
    choices = [r for r in rows if r[1] == label]
    sample.extend(rng.sample(choices, min(100, len(choices))))
SAMPLE = WORK / 'vit-smoke-test.json'; SAMPLE.write_text(json.dumps(sample))
from models.image_deepfake.evaluation.benchmark import evaluate
for mode in ('vit_direct', 'vit_policy'):
    report = evaluate(SAMPLE, WORK / (mode+'-baseline.json'), mode=mode, purpose='test',
                      variants=('original','jpeg_75','resize_256'), bootstrap=200)
    print(mode, report['summary'])
print('No validated operating point is installed; policy decisions abstain while raw face scores remain measurable.')
''')
    vit_cell('markdown','''## Conditional training
Use reviewed face crops with train/validation/test source separation and licensed recent data. The training runner checks exact and candidate near-duplicate leakage. A source group does not prove unknown subject identity independence. Historical GAN-only training is not evidence of modern accuracy. Compare head-only and full tuning in separate fresh output directories; do not tune against the final test.
''')
    vit_cell('code','''RUN_TRAINING = False  # Set True only after baseline and reviewed data justify this experiment.
ARTIFACT = WORK / 'vit-candidate'
if RUN_TRAINING:
    from models.image_deepfake.training.train_vit import run
    manifest = run(PREPARED/'train.json', PREPARED/'validation.json', PREPARED/'test.json',
                   ARTIFACT, epochs=10, batch_size=16, seed=42, head_only=True, face_crops_prepared=True)
    print(manifest)
else:
    print('Training skipped. No candidate checkpoint or accuracy improvement is claimed.')
''')
    vit_cell('markdown','''## Independent policy validation and final test
With recent independent all-input manifests, evaluate a candidate using `evaluation.benchmark`, select boundaries using `evaluation.select_policy`, and run the frozen candidate on the final test. `evaluation.promote_policy` rejects overlap and unmet budgets. Never substitute the 200-image smoke sample for these gates. The policy requires at least 1000 independent scored examples per class for selection; final test requires at least 1000 per class. Inspect confidence intervals and critical slices even when automated gates pass.
''')
    vit_cell('code','''if RUN_TRAINING:
    allowed = ['vit_manifest.json','config.json','preprocessor_config.json','model.safetensors',
               'dataset_index.json','training_report.json']
    result_zip = Path('/kaggle/working/TrustNet-ViT-Candidate.zip')
    with zipfile.ZipFile(result_zip, 'w', zipfile.ZIP_DEFLATED) as package:
        for name in allowed: package.write(ARTIFACT/name, name)
    print('Download candidate:', result_zip)
    print('SHA-256:', hashlib.sha256(result_zip.read_bytes()).hexdigest())
    print('Keep training_state.pt separately for optimizer recovery. Installation does not activate a candidate.')
''')
    vit_cell('markdown','''## Local handoff
Install into a new version directory with `scripts/setup/install-image-vit.py --package <zip> --target models/image_deepfake/trained/vit-candidate-1`. Evaluate with `IMAGE_VIT_MODEL_DIR` pointing there. Keep the baseline configuration until independent final-test promotion succeeds. See `docs/image-vit-v3.md` in the local project for exact evaluation and rollback commands. No Kaggle execution is implied by generating this notebook.
''')
    vit_path=OUT/'TrustNet_ViT_Kaggle.ipynb'
    vit_path.write_text(json.dumps({**notebook,'cells':vit_cells},indent=2),encoding='utf-8')
    for item in vit_cells:
        if item['cell_type']=='code':compile(''.join(item['source']),'<vit-cell>','exec')
    (OUT/'SHA256SUMS.txt').write_text('\n'.join(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name for path in (archive,notebook_path,vit_path))+'\n')
    print(json.dumps({'source_files':len(manifest),'archive_bytes':archive.stat().st_size,'notebook_cells':len(cells),'output':str(OUT)}))

if __name__=='__main__':main()
