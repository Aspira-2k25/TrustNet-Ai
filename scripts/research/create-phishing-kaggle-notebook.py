"""Create Kaggle notebook with safe input verification and restart checkpoints."""
import json
from pathlib import Path
def cell(kind,text):
    item={'cell_type':kind,'metadata':{},'source':text.splitlines(True)}
    if kind=='code':item.update(execution_count=None,outputs=[]);compile(text,'kaggle-cell','exec')
    return item
cells=[cell('markdown','''# TrustNet phishing — Kaggle GPU
Attach the refreshed phishing-gpu.zip as a **private Kaggle dataset**. Set accelerator to GPU. This trains phishing URLs offline, never fetching them. Keep dataset/splits unchanged. Percentage measures training batches only, excluding validation/fusion/test work.

To continue after a session cutoff, save/download notebook outputs including the whole checkpoints folder. Attach those outputs privately to the next run, set RESUME_FOLDER below to the directory containing resume.pt, and retain identical epochs/batch size. Unsaved /kaggle/working files may be lost. Older Colab checkpoints without resume.pt cannot resume optimizer/batch state.
'''),cell('code','''from pathlib import Path
import json, hashlib, shutil, sys, subprocess, os
inputs=Path('/kaggle/input')
manifests=list(inputs.rglob('GPU_PACKAGE_MANIFEST.json'))
assert len(manifests)==1, 'Attach exactly one extracted refreshed GPU package dataset'
source=manifests[0].parent
manifest=json.loads(manifests[0].read_text())
for name,digest in manifest.items():
    path=(source/name).resolve()
    assert path.is_relative_to(source.resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
root=Path('/kaggle/working/trustnet-phishing')
shutil.copytree(source,root,dirs_exist_ok=True)
subprocess.run([sys.executable,'-m','pip','install','lightgbm==4.7.0','scikit-learn==1.9.1','numpy==2.4.6','joblib==1.6.0','pydantic==2.13.5','transformers==5.19.0','safetensors==0.8.0','tldextract==5.4.0'],check=True)
subprocess.run([sys.executable,'-c','import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))'],check=True)
'''),cell('code','''saved=root/'models/phishing_url/checkpoints'
RESUME_FOLDER=None # e.g. /kaggle/input/my-private-training-output/checkpoints/bert
if RESUME_FOLDER:
    prior=Path(RESUME_FOLDER)
    assert (prior/'resume.pt').exists()
    shutil.copytree(prior,saved/'bert',dirs_exist_ok=True)
environment=os.environ.copy();environment['PYTHONPATH']=str(root)
def run(module,*arguments):
    command=[sys.executable,'-u','-m',module,*map(str,arguments)]
    with (root/'training.log').open('a') as log:
        process=subprocess.Popen(command,cwd=root,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        for line in process.stdout:print(line,end='',flush=True);log.write(line);log.flush()
        status=process.wait()
    assert status==0,f'Command failed: {status}'
resume=['--resume'] if (saved/'bert/resume.pt').exists() else []
run('models.phishing_url.training.train_bert','models/phishing_url/data/primary/prepared/prepared.csv','models/phishing_url/data/bert_source',saved/'bert','--epochs','3','--batch-size','8','--checkpoint-steps','500',*resume)
'''),cell('code','''run('models.phishing_url.training.tune_ensemble',saved/'lightgbm/validation_predictions.csv',saved/'bert/validation_predictions.csv',saved/'fusion')
run('models.phishing_url.training.build_bundle',saved/'lightgbm',saved/'bert',saved/'fusion',saved/'hybrid')
run('models.phishing_url.evaluation.evaluate','models/phishing_url/data/primary/prepared/prepared.csv',saved/'hybrid/manifest.json',root/'models/phishing_url/research/hybrid_test.json')
import zipfile
output=Path('/kaggle/working/phishing-trained-results.zip')
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
    for path in (saved/'hybrid').rglob('*'):
        if path.is_file():archive.write(path,str(path.relative_to(root)))
    archive.write(root/'models/phishing_url/research/hybrid_test.json','hybrid_test.json')
    archive.write(root/'training.log','training.log')
print('Download',output)
''')]
Path('docs/phishing/Phishing_Kaggle.ipynb').write_text(json.dumps({'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'nbformat':4,'nbformat_minor':5},indent=2),encoding='utf-8')
print('Kaggle notebook generated and code syntax checked')
