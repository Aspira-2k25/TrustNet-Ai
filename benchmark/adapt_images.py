"""CPU feature-head adaptation, separated families and matched file formats.

Train/validation only. Test images are prepared and frozen but never scored here.
SafeIMG CC BY-NC-SA 4.0; COCO image rights remain applicable. No raw redistribution.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import requests
from PIL import Image,ImageOps

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark.modern_images import fetch,DATASET,REVISION


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evaluation-root',type=Path,required=True)
    a=p.parse_args();out=a.evaluation_root/'adaptation';out.mkdir(exist_ok=True)
    manifest=out/'manifest.json'
    if not manifest.exists():
        metadata=[json.loads(l) for l in (a.evaluation_root/'modern/source-metadata.jsonl').read_text(encoding='utf-8').splitlines()]
        selected=[]
        for category in sorted({r['category'] for r in metadata}):
            ordered=sorted([r for r in metadata if r['category']==category],key=lambda r:hashlib.sha256(r['file_name'].encode()).hexdigest())
            for index,r in enumerate(ordered[2:10]):
                selected.append(dict(url=f'https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/test/{r["file_name"]}',
                    family='safeimg:'+r['image_id'],category=category,ai=True,
                    split='train' if index<4 else 'validation' if index<6 else 'test'))
        old=json.loads((a.evaluation_root/'images/manifest.json').read_text())
        used={Path(r['source_path']).name for r in old['rows'] if r['generator']=='real'}
        dataset=old['dataset'];rev=old['revision']
        tree=requests.get(f'https://huggingface.co/api/datasets/{dataset}/revision/{rev}',timeout=60);tree.raise_for_status()
        seen=set(used);real=[]
        for r in sorted(tree.json()['siblings'],key=lambda r:hashlib.sha256(r['rfilename'].encode()).hexdigest()):
            name=r['rfilename'];identity=Path(name).name
            if '/0_real/' not in name or identity in seen:continue
            seen.add(identity);real.append(name)
            if len(real)==96:break
        if len(real)!=96:raise ValueError('Insufficient independent real source families')
        for index,name in enumerate(real):
            selected.append(dict(url=f'https://huggingface.co/datasets/{dataset}/resolve/{rev}/{name}',
                family='coco:'+Path(name).name,category='real_photo',ai=False,
                split='train' if index<48 else 'validation' if index<72 else 'test'))
        def download(row):
            key=hashlib.sha256(row['url'].encode()).hexdigest()[:24]
            original=out/'originals'/key;original.parent.mkdir(exist_ok=True)
            if not original.exists():original.write_bytes(fetch(row['url']))
            with Image.open(original) as source:
                # Training/evaluation control only; runtime original pixels remain intact.
                image=ImageOps.fit(source.convert('RGB'),(512,512),method=Image.Resampling.LANCZOS)
            encoded=io.BytesIO();image.save(encoded,'JPEG',quality=70)
            data=encoded.getvalue()
            if len(data)>262144:raise ValueError('Matched control exceeded byte budget')
            data+=b'\0'*(262144-len(data))
            path=out/'matched'/(key+'.jpg');path.parent.mkdir(exist_ok=True);path.write_bytes(data)
            return {**row,'path':str(path.relative_to(out)),'sha256':hashlib.sha256(data).hexdigest(),
                'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest()}
        with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(download,selected))
        assert len({r['family'] for r in rows})==len(rows)
        hashes={}
        for r in rows:hashes.setdefault(r['source_sha256'],set()).add(r['split'])
        assert all(len(s)==1 for s in hashes.values()),'Source duplicate crosses splits'
        manifest.write_text(json.dumps(dict(rows=rows,licenses=['SafeIMG CC BY-NC-SA 4.0','DiTFake dataset Apache 2.0, underlying COCO image rights apply'],
            limits=['Small adaptation sample; domains and upstream pretrained overlap limit generalization.',
                    'Real photo device coverage and modern commercial generators other than this dataset remain unvalidated.']),indent=2),encoding='utf-8')
    rows=json.loads(manifest.read_text())['rows']
    selected=[r for r in rows if r['split']!='test']
    cache=out/'features.jsonl'
    existing=[json.loads(l) for l in cache.read_text().splitlines()] if cache.exists() else []
    seen={r['sha256'] for r in existing}
    pending=[r for r in selected if r['sha256'] not in seen]
    if pending:
        import torch
        torch.set_num_threads(2)
        from models.image_deepfake.inference.global_classifier import GlobalClassifier
        root=Path(__file__).resolve().parents[1]
        model=GlobalClassifier('community',root/'models/image_deepfake/artifacts/global')
        for index,r in enumerate(pending):
            result=model.predict((out/r['path']).read_bytes(),return_embedding=True)
            value={**r,**result}
            with cache.open('a',encoding='utf-8') as f:f.write(json.dumps(value)+'\n')
            existing.append(value)
            if index%16==0:print('Feature extraction',index+1,'/',len(pending),flush=True)
    import numpy as np
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    train=[r for r in existing if r['split']=='train'];val=[r for r in existing if r['split']=='validation']
    classifier=make_pipeline(StandardScaler(),LogisticRegression(C=1.,class_weight='balanced',max_iter=1000,random_state=42))
    classifier.fit([r['embedding'] for r in train],[r['ai'] for r in train])
    probabilities=classifier.predict_proba([r['embedding'] for r in val])[:,1]
    labels=np.array([r['ai'] for r in val])
    boundary=float(np.nextafter(max(probabilities[~labels]),np.inf))
    scaler,head=classifier.steps[0][1],classifier.steps[1][1]
    result=dict(version='community-modern-feature-head-candidate-1',backbone_revision='ac6ee457bea904a373065754107451793b56db00',
        feature='Final normalized ViT CLS embedding, 384 dimensions',mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),
        coef=head.coef_[0].tolist(),intercept=float(head.intercept_[0]),raw_alert=boundary,
        validation=dict(n=len(val),roc_auc=float(roc_auc_score(labels,probabilities)),
            observed_real_alerts=int(sum(probabilities[~labels]>=boundary)),recall=float(np.mean(probabilities[labels]>=boundary))),
        manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),training_n=len(train),
        license='Candidate trained on SafeIMG CC BY-NC-SA 4.0 and COCO; academic/noncommercial use only. Do not redistribute raw images.',
        promoted=False)
    (out/'candidate-head.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['mean','scale','coef']},indent=2))


if __name__=='__main__':main()
