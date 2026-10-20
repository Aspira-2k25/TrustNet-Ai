"""Pinned modern-generator challenge; positive-only recall, never accuracy."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import time
import requests

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
DATASET='Snowstorm1492/SafeIMG'
REVISION='389a7c555191c9e946727a470500fcd9b045381c'


def fetch(url):
    for attempt in range(3):
        try:
            r=requests.get(url,timeout=(10,60));r.raise_for_status();return r.content
        except requests.RequestException:
            if attempt==2:raise
            time.sleep(1+attempt)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    base=f'https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/'
    source=a.output/'source-metadata.jsonl'
    if not source.exists():source.write_bytes(fetch(base+'data/test/metadata.jsonl'))
    records=[json.loads(l) for l in source.read_text(encoding='utf-8').splitlines()]
    chosen=[]
    for category in sorted({r['category'] for r in records}):
        ordered=sorted([r for r in records if r['category']==category],key=lambda r:hashlib.sha256(r['file_name'].encode()).hexdigest())
        chosen.extend(ordered[:2])
    def one(row):
        name=row['file_name'];dest=a.output/'images'/name;dest.parent.mkdir(exist_ok=True)
        if not dest.exists():dest.write_bytes(fetch(base+'data/test/'+name))
        return dict(path=str(dest.relative_to(a.output)),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
            ai=True,generator='GPT Image 2 (SafeIMG authors)',category=row['category'],split='diagnostic',family=row['image_id'])
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(one,chosen))
    manifest=dict(dataset=DATASET,revision=REVISION,license='CC BY-NC-SA 4.0',rows=rows,
        limits=['Positive-only stratified challenge: accuracy, specificity and false-positive rate cannot be estimated.',
                'SafeIMG categories include document designs; these are not a representative inbox/photo sample.',
                'Author generator attribution is relied upon. No threshold selection or training uses these cases.'])
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    import torch
    torch.set_num_threads(2)
    from models.image_deepfake.inference.global_classifier import GlobalClassifier
    root=Path(__file__).resolve().parents[1]
    detector=GlobalClassifier('community',root/'models/image_deepfake/artifacts/global')
    boundary=json.loads((root/'models/image_deepfake/calibration/evidence-v2.json').read_text())['ai']['raw_alert']
    target=a.output/'predictions.jsonl'
    existing=[json.loads(l) for l in target.read_text().splitlines()] if target.exists() else []
    seen={r['sha256'] for r in existing}
    for row in rows:
        if row['sha256'] in seen:continue
        result=detector.predict((a.output/row['path']).read_bytes())
        value={**row,**result,'alert':result['ai_score']>=boundary}
        with target.open('a',encoding='utf-8') as f:f.write(json.dumps(value)+'\n')
        existing.append(value)
        print(row['path'],'raw',result['ai_score'],'alert',value['alert'],flush=True)
    report=dict(n=len(existing),alerts=sum(r['alert'] for r in existing),
        alert_recall=sum(r['alert'] for r in existing)/len(existing),scope='AI classifier stream only; no manipulation or quality verdict',
        accuracy=None,limits=manifest['limits'])
    (a.output/'metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
