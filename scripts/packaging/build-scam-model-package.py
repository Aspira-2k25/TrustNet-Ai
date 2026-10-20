"""Create the selected weights/tokenizer package without introducing Git LFS."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parents[2];assets=root/'models/scam_message/artifacts'
version=json.loads((assets/'manifest.json').read_text(encoding='utf-8'))['model_version']
name='TrustNet-Scam-Model-'+version+'.zip'
target=root/'exports'/name;target.parent.mkdir(exist_ok=True)
files={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(assets.iterdir()) if p.is_file()}
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
 for file in files:archive.write(assets/file,'artifacts/'+file)
 archive.write(root/'models/scam_message/MODEL_CARD.md','MODEL_CARD.md')
 for file in ['APACHE-2.0.txt','CC-BY-4.0.txt','THIRD-PARTY-NOTICES.md']:
  archive.write(root/'licenses/scam'/file,file)
metadata={'model_version':version,'filename':name,
          'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,'files':files,
          'distribution':'Share this archive separately; no remote upload or Git LFS configured.'}
(root/'models/scam_message/model-package.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
target.with_suffix('.zip.sha256').write_text(metadata['sha256']+'  '+name+'\n',encoding='ascii')
print(json.dumps({k:v for k,v in metadata.items() if k!='files'},indent=2))
