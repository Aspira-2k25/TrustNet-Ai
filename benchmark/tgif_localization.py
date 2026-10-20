"""Actual TruFor evaluation on official TGIF partial edits and aligned operation masks."""
import argparse
from collections import defaultdict
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import time
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark.coverage_data import TGIF,tgif_session

def prepare(out,n):
    manifest=out/'manifest.json'
    if manifest.exists():return json.loads(manifest.read_text(encoding='utf-8'))
    out.mkdir(parents=True,exist_ok=True);session=tgif_session();rows=[];wanted=set()
    for kind in ['sd2-sp','ps-sp']:
        url=TGIF+f'{kind}/{kind}_testing.tar.gz';seen=set()
        response=session.get(url,headers={'X-Requested-With':'XMLHttpRequest'},stream=True,timeout=(12,90));response.raise_for_status()
        with response,tarfile.open(fileobj=response.raw,mode='r|gz') as archive:
            for member in archive:
                if not member.isfile() or not member.name.lower().endswith('.png'):continue
                name=Path(member.name).name;family=name.split('_')[0]
                if family in seen:continue
                seen.add(family);data=archive.extractfile(member).read();sha=hashlib.sha256(data).hexdigest();(out/(sha+'.png')).write_bytes(data)
                mask=name.split('.png')[0]+'.png_ps_mask.png'
                wanted.add(mask)
                rows.append(dict(kind=kind,family=family,path=sha+'.png',source_archive=url,member=member.name,sha256=sha,mask_name=mask))
                print('TGIF partial edits',kind,len(seen),'/',n,flush=True)
                if len(seen)>=n:break
    found={};url=TGIF+'masks/masks_testing.tar.gz';response=session.get(url,headers={'X-Requested-With':'XMLHttpRequest'},stream=True,timeout=(12,90));response.raise_for_status()
    with response,tarfile.open(fileobj=response.raw,mode='r|gz') as archive:
        for member in archive:
            name=Path(member.name).name
            if name not in wanted:continue
            data=archive.extractfile(member).read();sha=hashlib.sha256(data).hexdigest();(out/(sha+'.mask.png')).write_bytes(data);found[name]=dict(path=sha+'.mask.png',sha256=sha,member=member.name)
            if wanted<=found.keys():break
    for row in rows:
        if row['mask_name'] not in found:raise ValueError('No exact aligned TGIF mask: '+row['mask_name'])
        row['mask']=found[row['mask_name']]
    doc={'source':'https://github.com/IDLabMedia/tgif-dataset','license':'CC BY-SA 4.0; original source rights apply','selection':'First fixed unique COCO identities in official testing archives, one variant per identity and method; no outcome-based selection.','rows':rows,'limits':['Operation masks record editing operations, not proof that every changed pixel was synthesized.','Small ordered convenience sample; same COCO source may appear for both editing methods.','TruFor research licence; no model or threshold fitting on these cases.']}
    manifest.write_text(json.dumps(doc,indent=2),encoding='utf-8');return doc

def evaluate(out,doc):
    import torch
    torch.set_num_threads(2)
    from models.image_deepfake.inference.localizer import TruForLocalizer
    from models.image_deepfake.forensics.localization_output import pixel_mask
    cfgpath=Path(__file__).resolve().parents[1]/'models/image_deepfake/calibration/evidence-v2.json';cfg=json.loads(cfgpath.read_text())
    target=out/'predictions.jsonl';records=[json.loads(l) for l in target.read_text().splitlines()] if target.exists() else [];done={r['sha256'] for r in records};localizer=TruForLocalizer()
    for row in doc['rows']:
        if row['sha256'] in done:continue
        result={**row,'detected':False,'iou':0.,'production_supported':False,'error':None}
        started=time.monotonic()
        try:
            prediction=localizer.predict((out/row['path']).read_bytes())
            heat=prediction.pop('heatmap');reliability=prediction.pop('reliability')
            mask,regions=pixel_mask(heat,reliability,cfg['pixel_threshold'],cfg['min_reliability'],cfg['min_area_fraction'])
            with Image.open(out/row['mask']['path']) as gt:truth=np.asarray(gt.convert('L'))>127
            if truth.shape!=mask.shape:raise ValueError('Mask dimensions differ; resizing ground truth is forbidden')
            detected=prediction['raw_score']>=cfg['manipulation']['raw_alert'] and bool(regions)
            union=np.logical_or(truth,mask>0).sum();iou=float(np.logical_and(truth,mask>0).sum()/union) if union else 1.
            np.savez_compressed(out/(row['sha256']+'.maps.npz'),heatmap=heat,reliability=reliability)
            result.update(prediction,detected=detected,iou=iou if detected else 0.,ungated_mask_iou=iou,
                production_reason='Native PNG/tiled modes have no validated production threshold; raw localization metrics are diagnostic.')
        except (ValueError,RuntimeError,MemoryError) as e:result['error']=str(e)[:400]
        result['elapsed_seconds']=round(time.monotonic()-started,2)
        with target.open('a',encoding='utf-8') as f:f.write(json.dumps(result)+'\n')
        records.append(result);print('TGIF localization',len(records),'/',len(doc['rows']),result['kind'],'detected',result['detected'],'IoU',result['iou'],flush=True)
    metrics={}
    for kind in sorted({r['kind'] for r in records}):
        group=[r for r in records if r['kind']==kind];detected=sum(r['detected'] for r in group)
        metrics[kind]=dict(n=len(group),detected=detected,missed=len(group)-detected,mean_iou_including_misses=float(np.mean([r['iou'] for r in group])),errors=sum(r['error'] is not None for r in group),production_supported_detected=0)
    report={'metrics':metrics,'manifest_sha256':hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(cfgpath.read_bytes()).hexdigest(),'limits':doc['limits']+['Raw diagnostic detection does not promote PNG or tiled localization into supported production coverage.']}
    (out/'metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--per-method',type=int,default=10);a=p.parse_args();out=a.output.resolve()
    if out.is_relative_to(Path(__file__).resolve().parents[1]):raise SystemExit('Keep research data outside the application')
    evaluate(out,prepare(out,a.per_method))

if __name__=='__main__':main()
