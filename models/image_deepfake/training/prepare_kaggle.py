"""Prepare the publisher's face splits without inventing subject identities."""
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
import yaml
from PIL import Image, ImageOps

DATASET='https://www.kaggle.com/datasets/xhlulu/140k-real-and-fake-faces'

def prepare(dataset_root, output_root):
    root=Path(dataset_root).resolve();output=Path(output_root).resolve()
    if not root.is_dir():raise ValueError('Dataset mount not found')
    if output.exists() and any(output.iterdir()):raise ValueError('Preparation output must be empty')
    aliases={'train':'train','valid':'validation','val':'validation','validation':'validation','test':'test'}
    collected={split:[] for split in ('train','validation','test')}
    for path in sorted(root.rglob('*')):
        if path.suffix.lower() not in {'.jpg','.jpeg','.png'}:continue
        label={'real':0,'fake':1}.get(path.parent.name.lower())
        split=aliases.get(path.parent.parent.name.lower())
        if label is not None and split:
            collected[split].append((path,label))
    if any(not rows for rows in collected.values()):
        raise ValueError('Expected train/{real,fake}, valid/{real,fake}, test/{real,fake} folders')
    from models.image_deepfake.forensics.face_analyzer import FaceAnalyzer
    analyzer=FaceAnalyzer()
    if not analyzer.cascades or analyzer.eye_cascade is None:
        raise ValueError('Tested OpenCV face/eye resources are required before preparing training crops')
    output.mkdir(parents=True,exist_ok=True)
    policy_test=[]
    policy_splits={split:[] for split in collected}
    seen_bytes,seen_pixels={},{};exclusions=[];counts={};manifests={}
    for split,rows in collected.items():
        kept=[]
        for number,(path,label) in enumerate(rows,1):
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            with Image.open(path) as image:
                image=ImageOps.exif_transpose(image).convert('RGB')
                pixel_hash=hashlib.sha256(str(image.size).encode()+image.tobytes()).hexdigest()
            if digest in seen_bytes or pixel_hash in seen_pixels:
                exclusions.append({'path':str(path.relative_to(root)),'split':split,'reason':'duplicate bytes or decoded RGB pixels'})
                continue
            seen_bytes[digest]=split;seen_pixels[pixel_hash]=split
            policy_splits[split].append([str(path),label,'source-image:'+pixel_hash])
            if split=='test':policy_test.append([str(path),label,'source-image:'+pixel_hash])
            image_bytes=path.read_bytes()
            from models.image_deepfake.preprocessing.validator import canonical_bytes
            faces=analyzer.analyze(canonical_bytes(image_bytes)).get('bounding_boxes',[])
            if len(faces)!=1 or min(faces[0][2:])<48:
                exclusions.append({'path':str(path.relative_to(root)),'split':split,'reason':'one usable detected face required'})
                continue
            x,y,w,h=faces[0]
            with Image.open(path) as image:
                image=ImageOps.exif_transpose(image).convert('RGB')
                crop_dir=output/'crops'/split;crop_dir.mkdir(parents=True,exist_ok=True)
                crop_path=crop_dir/(digest+'.png')
                image.crop((x,y,x+w,y+h)).save(crop_path,format='PNG')
            if number%1000==0:print(f'{split}: processed {number}/{len(rows)}; retained {len(kept)+1}',flush=True)
            # This groups the same decoded source image, NOT a biometric identity.
            kept.append([str(crop_path),label,'source-image:'+pixel_hash])
        if {row[1] for row in kept}!={0,1}:raise ValueError('Both classes required in every prepared split')
        target=output/(split+'.json');target.write_text(json.dumps(kept),encoding='utf-8')
        manifests[split]=target.name;counts[split]=dict(Counter(str(row[1]) for row in kept))
    (output/'policy_test.json').write_text(json.dumps(policy_test),encoding='utf-8')
    for split, rows in policy_splits.items():
        (output/('policy_'+split+'.json')).write_text(json.dumps(rows),encoding='utf-8')
    config={'data':{'scope':'face','face_crops_prepared':True,**{split+'_manifest':name for split,name in manifests.items()}},
        'training':{'batch_size':32,'epochs':20,'learning_rate':.0001,'weight_decay':.00001,'seed':42,'early_stopping_patience':5}}
    (output/'training.yaml').write_text(yaml.safe_dump(config),encoding='utf-8')
    provenance={'dataset':DATASET,'version':2,'source':'publisher-provided train/validation/test folders',
        'license':'Other (specified in description); preserve upstream FFHQ and GAN license information',
        'counts':counts,'excluded_duplicates':[r for r in exclusions if r['reason']=='duplicate bytes or decoded RGB pixels'],
        'excluded_inputs':exclusions,'exclusion_counts':dict(Counter(r['reason'] for r in exclusions)),
        'input_policy':'haar-eye-pair-crop-v1',
        'grouping':'source-image byte/pixel identity only; subject identities and generator-disjoint splits are unavailable',
        'limitations':['GAN-face benchmark; not modern diffusion or general-image validation',
                      'No claim of zero subject-identity leakage or near-duplicate removal'],
        'manifest_sha256':{split:hashlib.sha256((output/name).read_bytes()).hexdigest() for split,name in manifests.items()}}
    (output/'dataset_provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    return provenance

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dataset-root',required=True);parser.add_argument('--output-root',required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.dataset_root,args.output_root),indent=2))
