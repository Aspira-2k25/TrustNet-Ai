"""CPU-only, resumable frozen-backbone comparison. No automatic promotion.

Raw sources/features stay outside the application. A new test manifest must be
frozen separately; previously inspected coverage-v3 tests are regression data.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from models.image_deepfake.inference.native_features import CropContract,native_crops,crop_batch,aggregate,augment_crops
from benchmark.feature_cache import append_record

SPECS={
 'community':{'id':'buildborderless/CommunityForensics-DeepfakeDet-ViT','revision':'ac6ee457bea904a373065754107451793b56db00','license':'MIT'},
 'dino':{'id':'facebook/dinov2-small','revision':'ed25f3a31f01632728cabb09d1542f84ab7b0056','license':'Apache-2.0'},
 'openclip':{'id':'laion/CLIP-ViT-B-16-laion2B-s34B-b88K','revision':'7288da5a0d6f0b51c4a2b27c624837a9236d0112','license':'MIT'},
}

def load(name,out):
 import torch
 from huggingface_hub import snapshot_download
 from transformers import AutoImageProcessor,AutoModel
 if name=='community':
  from models.image_deepfake.inference.global_classifier import GlobalClassifier
  m=GlobalClassifier(name,Path(__file__).resolve().parents[1]/'models/image_deepfake/artifacts/global')
  return m.processor,m.model.vit
 spec=SPECS[name];folder=out/'backbones'/name
 required=['config.json','preprocessor_config.json','model.safetensors'] if name=='dino' else ['open_clip_config.json','open_clip_model.safetensors']
 if not all((folder/file).exists() for file in required):
  snapshot_download(spec['id'],revision=spec['revision'],local_dir=folder,allow_patterns=[*required,'README.md'])
 integrity=folder/'verified-artifacts.json'
 hashes={}
 for file in required:
  with (folder/file).open('rb') as stream:hashes[file]=hashlib.file_digest(stream,'sha256').hexdigest()
 record={'model':spec,'files':hashes}
 if integrity.exists() and json.loads(integrity.read_text())!=record:raise ValueError('Cached backbone artifacts changed')
 integrity.write_text(json.dumps(record,indent=2))
 if name=='dino':return AutoImageProcessor.from_pretrained(folder,local_files_only=True),AutoModel.from_pretrained(folder,local_files_only=True).eval()
 import open_clip
 from transformers import CLIPImageProcessor
 model=open_clip.create_model('ViT-B-16',pretrained=str(folder/'open_clip_model.safetensors'),device='cpu').eval()
 return CLIPImageProcessor(),model.visual

def extract(name,processor,model,data,contract,augmentation_seed=None):
 import torch
 crops,geometry=native_crops(data,contract);vectors=[]
 if augmentation_seed is not None:
  crops,recipe=augment_crops(crops,augmentation_seed);geometry['augmentation']=recipe
 with torch.inference_mode():
  for offset in range(0,len(crops),3):
   batch=crop_batch(processor,crops[offset:offset+3])
   if name=='community':feature=model(**batch,interpolate_pos_encoding=True).last_hidden_state[:,0]
   elif name=='dino':feature=model(**batch).last_hidden_state[:,0]
   else:feature=model(batch['pixel_values'])
   vectors.extend(feature.cpu().numpy())
 return aggregate(vectors,contract.top_k),geometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--backbone',choices=SPECS,required=True);p.add_argument('--limit',type=int);p.add_argument('--include-regression-test',action='store_true');p.add_argument('--sealed-candidate',type=Path);p.add_argument('--backbone-cache',type=Path);p.add_argument('--augment',action='store_true');p.add_argument('--threads',type=int,default=2);a=p.parse_args()
 out=a.output.resolve();repo=Path(__file__).resolve().parents[1]
 if out.is_relative_to(repo):raise ValueError('Keep research outputs outside the runtime repository')
 out.mkdir(parents=True,exist_ok=True)
 source=a.source.resolve();manifest=source/'manifest.json';doc=json.loads(manifest.read_text());contract=CropContract()
 sealed=bool(a.sealed_candidate)
 if sealed:
  candidate=json.loads(a.sealed_candidate.read_text())
  if candidate['holdout_manifest_sha256']!=hashlib.sha256(manifest.read_bytes()).hexdigest():raise ValueError('Frozen candidate is for a different holdout')
 rows=[r for r in doc['rows'] if sealed or a.include_regression_test or r['split'] in {'train','calibration','threshold'}]
 if a.limit:
  # A stratified pilot, never the first few rows from only one label.
  groups={label:[r for r in rows if r['positive']==label] for label in (False,True)}
  rows=[r for i in range(a.limit//2) for label in (False,True) for r in groups[label][i:i+1]]
 protocol={'backbone':SPECS[a.backbone],'crops':asdict(contract),'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'split_scope':'sealed test after candidate freeze' if sealed else 'regression (already observed)' if a.include_regression_test else 'development only','preprocessing':'native pixels; normalization only; no resize or center crop'}
 protocol_path=out/(a.backbone+'-contract.json')
 if protocol_path.exists() and json.loads(protocol_path.read_text())!=protocol:raise ValueError('Cache contract changed')
 protocol_path.write_text(json.dumps(protocol,indent=2))
 target=out/(a.backbone+'-features.jsonl');seen=set()
 if target.exists():
  data=target.read_bytes();lines=data.splitlines(keepends=True);valid=[]
  for index,line in enumerate(lines):
   try:record=json.loads(line)
   except json.JSONDecodeError:
    if index!=len(lines)-1:raise
    # Preserve a crash-truncated tail separately before resuming completed rows.
    (out/(target.name+'.interrupted-tail')).write_bytes(line);target.write_bytes(b''.join(valid));break
   seen.add(record['identity']);valid.append(line)
 pending=[r for r in rows if r['identity'] not in seen]
 augmented=out/(a.backbone+'-augmented.jsonl')
 if a.augment:
  aug_contract={**protocol,'augmentation':'native-stress-v1: source-SHA seed; one JPEG q40-95 and blur/noise/screenshot-proxy view for one quarter of training originals; no resize'}
  aug_path=out/(a.backbone+'-augmentation-contract.json')
  if aug_path.exists() and json.loads(aug_path.read_text())!=aug_contract:raise ValueError('Augmentation cache contract changed')
  aug_path.write_text(json.dumps(aug_contract,indent=2))
 augmented_seen={json.loads(line)['identity'] for line in augmented.read_text().splitlines() if line.strip()} if augmented.exists() else set()
 extra=[r for r in rows if r['split']=='train' and int(r['sha256'][:8],16)%4==0 and r['identity'] not in augmented_seen] if a.augment else []
 if sealed and a.augment:raise ValueError('No training augmentation or selection on sealed test')
 if not pending and not extra:print('Feature cache already complete',len(rows),flush=True);return
 import torch
 torch.set_num_threads(a.threads);processor,model=load(a.backbone,a.backbone_cache or out);start=time.perf_counter()
 for index,row in enumerate(pending):
  tick=time.perf_counter();data=(source/row['path']).read_bytes()
  if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Source bytes changed')
  vector,geometry=extract(a.backbone,processor,model,data,contract)
  record={k:row[k] for k in ('identity','family','split','source','generator','positive','sha256')}
  record.update(embedding=vector.tolist(),geometry=geometry,seconds=time.perf_counter()-tick)
  append_record(target,record)
  if index%25==0:print(a.backbone,index+1,'/',len(pending),'elapsed',round(time.perf_counter()-start),'seconds',flush=True)
 print('COMPLETE',a.backbone,len(rows),flush=True)
 for index,row in enumerate(extra):
  tick=time.perf_counter();data=(source/row['path']).read_bytes()
  if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Source bytes changed')
  vector,geometry=extract(a.backbone,processor,model,data,contract,augmentation_seed=int(row['sha256'][:8],16))
  record={k:row[k] for k in ('identity','family','split','source','generator','positive','sha256')};record.update(embedding=vector.tolist(),geometry=geometry,seconds=time.perf_counter()-tick)
  append_record(augmented,record)
  if index%25==0:print(a.backbone,'training augmentation',index+1,'/',len(extra),flush=True)

if __name__=='__main__':main()
