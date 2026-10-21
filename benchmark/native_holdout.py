"""Freeze unseen source identities before extracting any holdout features."""
import argparse,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark.coverage_data import download,ordered,DIT_REV

def family(token):
 digits=re.search(r'(?:COCO_val2014_)?(\d+)(?:\.[a-z]+)?$',token,re.I)
 return str(int(digits.group(1))) if digits else token

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();repo=Path(__file__).resolve().parents[1]
 if out.is_relative_to(repo):raise ValueError('Research data must stay outside the repository')
 out.mkdir(parents=True,exist_ok=True);selection=out/'source-selection.json'
 prior=json.loads((a.source/'manifest.json').read_text());old=prior['rows']+prior.get('quarantined',[])
 older=a.source.parent/'forensic-overhaul'
 for location in ['images/manifest.json','adaptation/manifest.json','real-guard-320/manifest.json']:
  path=older/location
  if path.exists():old.extend(json.loads(path.read_text(encoding='utf-8'))['rows'])
 used_real={family(r['family'].split(':',1)[-1]) for r in old if r.get('source') in {'COCO','TGIF'} or r['family'].startswith('coco:')}
 used_prompt={r['family'].split(':',1)[-1] for r in old if r.get('source')=='DiTFake'}
 siblings=json.loads(a.metadata.read_text())['siblings'];rows=[]
 if selection.exists():doc=json.loads(selection.read_text())
 else:
  names={Path(r['rfilename']).name:r['rfilename'] for r in siblings if '/0_real/' in r['rfilename']}
  names=ordered([name for name in names if family(Path(name).stem) not in used_real])[:1000]
  paths={Path(r['rfilename']).name:r['rfilename'] for r in siblings if '/0_real/' in r['rfilename']}
  for name in names:rows.append(dict(source='COCO',generator='real',positive=False,split='test',family='coco:'+family(Path(name).stem),url=f'https://huggingface.co/datasets/Jouesmak/DiTFake/resolve/{DIT_REV}/{paths[name]}',license='COCO source rights; DiTFake card Apache 2.0'))
  generators=['FLUX.1-schnell','PixArt-Sigma-XL-2-1024-MS','stable-diffusion-3-medium-diffusers']
  for gen in generators:
   names=ordered([r['rfilename'] for r in siblings if f'/{gen}/1_fake/' in r['rfilename'] and Path(r['rfilename']).stem not in used_prompt])[:150]
   if len(names)!=150:raise ValueError('Not enough untouched generator identities')
   for name in names:rows.append(dict(source='DiTFake',generator=gen,positive=True,split='test',family='dit-prompt:'+Path(name).stem,url=f'https://huggingface.co/datasets/Jouesmak/DiTFake/resolve/{DIT_REV}/{name}',license='Apache 2.0 card; source rights apply'))
  doc={'version':'native-v4-sealed-test-1','rows':rows,'archives':{},'heldout_generators':generators,'prior_manifest_sha256':hashlib.sha256((a.source/'manifest.json').read_bytes()).hexdigest(),'policy':'New image identities, fixed before outcomes. These generators were observed in an earlier experiment, so generator selection is not blind. None enter this head training/calibration/threshold split.'}
  selection.write_text(json.dumps(doc,indent=2));print('SEALED selection',hashlib.sha256(selection.read_bytes()).hexdigest(),len(rows),flush=True)
 download(out,doc)
 acquired=[json.loads(line) for line in (out/'acquired.jsonl').read_text().splitlines()]
 old_hashes={value for r in old for value in [r.get('sha256'),r.get('source_sha256')] if value}
 if len(acquired)!=len(doc['rows']):raise ValueError('Incomplete holdout download')
 source_quarantine=[r for r in acquired if r['sha256'] in old_hashes or (not r['positive'] and family(r['family'].split(':',1)[-1]) in used_real)]
 excluded_ids={r['identity'] for r in source_quarantine};rows=[r for r in acquired if r['identity'] not in excluded_ids]
 # Screen against all previously used files before any outcomes are extracted.
 # A perceptual hash is a duplicate heuristic, not proof of semantic independence.
 import numpy as np
 from PIL import Image
 from scipy.fft import dctn
 prior_hashes=json.loads((a.source/'perceptual-hashes.json').read_text());cache=out/'perceptual-hashes.json'
 phashes=json.loads(cache.read_text()) if cache.exists() else {}
 for row in rows:
  if row['sha256'] in phashes:continue
  with Image.open(out/row['path']) as image:pixels=np.asarray(image.convert('L').resize((32,32)),float)
  values=dctn(pixels,norm='ortho')[:8,:8].flatten()[1:];phashes[row['sha256']]=sum(int(v)<<i for i,v in enumerate(values>np.median(values)))
 cache.write_text(json.dumps(phashes));quarantined=[{'identity':r['identity'],'reason':'Prior source family or bytes, excluded before outcomes'} for r in source_quarantine];kept=[];within=[]
 for row in sorted(rows,key=lambda r:r['identity']):
  value=phashes[row['sha256']]
  near_prior=any((value^other).bit_count()<=4 for other in prior_hashes.values())
  near_within=any((value^other).bit_count()<=4 for other in within)
  if near_prior or near_within:quarantined.append({'identity':row['identity'],'reason':'pHash distance <=4 to prior source or retained test image'})
  else:kept.append(row);within.append(value)
 rows=kept
 target=out/'manifest.json';record={'rows':rows,'pre_outcome_duplicate_audit':{'exact_old_hash_overlap':0,'perceptual_hash_bits':63,'max_hamming':4,'quarantined':quarantined},'limitations':[doc['policy'],'New real test photos here are COCO only. Prior diverse-camera suites remain diagnostic checks. Unknown backbone-pretraining overlap.','pHash does not prove semantic or unknown generator-batch independence.']}
 target.write_text(json.dumps(record,indent=2));print('SEALED acquired manifest',hashlib.sha256(target.read_bytes()).hexdigest(),flush=True)
if __name__=='__main__':main()
