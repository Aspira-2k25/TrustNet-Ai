"""Research edit challenge. Never invent a mask for a dataset lacking ground truth."""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def prepare(root):
    import pyarrow.parquet as pq
    from PIL import Image
    out=root/'edit-scope';manifest=out/'manifest.json'
    if manifest.exists():return
    rows=[]
    def save(data,kind,identity,mask=None,source=None):
        digest=hashlib.sha256(data).hexdigest();path=out/(digest+'.image');path.write_bytes(data)
        gt=None
        if mask is not None:
            gt=digest+'.mask.png';(out/gt).write_bytes(mask)
        rows.append({'path':path.name,'sha256':digest,'mask':gt,'edit_type':kind,'family':identity,'split':'test','source':source,'ai':False,'manipulation':True,'generator':'edited','variant':kind})
    records=pq.read_table(out/'cocoglide.parquet').to_pylist()
    fake=sorted([r for r in records if r['label']==1],key=lambda r:hashlib.sha256(r['key'].encode()).hexdigest())[:20]
    for r in fake:
        save(r['image']['bytes'],'glide_inpainting',r['key'],r['mask']['bytes'],'nebula/CocoGlide revision 275f045df7caa2544dd28de7fa86b044ab661bd0; underlying COCO/TruFor dataset rights apply, no raw redistribution')
    faces=pq.read_table(out/'face-swap.parquet').to_pylist()
    for r in sorted(faces,key=lambda r:hashlib.sha256(r['filename'].encode()).hexdigest())[:20]:
        save(r['image'],'face_swap',r['filename'],None,'bitmind/face-swap revision bef3ff0a292a73d3b6fdfe9d0f3acad2c454a8bd, Apache-2.0 card; masks absent, IoU unavailable')
    manifest.write_text(json.dumps({'rows':rows,'limits':['No headline real-world localization accuracy: small research challenge.','CocoGlide is an upstream TruFor evaluation benchmark, not a new independently collected modern editor cohort.','Face-swap source has no pixel masks, therefore IoU is unavailable, not zero.','Content-aware fill is a proxy, not modern diffusion removal.','Lossless/tiled production localization is uncalibrated; raw masks reported separately from supported production alerts.']},indent=2),encoding='utf-8')
    print('Edit cases prepared:',dict(Counter(r['edit_type'] for r in rows)))


def prepare_removal(root):
    import cv2
    import numpy as np
    from PIL import Image
    out=root/'edit-scope';manifest=out/'manifest.json'
    doc=json.loads(manifest.read_text(encoding='utf-8'));rows=doc['rows']
    if any(r['edit_type']=='content_aware_removal_proxy' for r in rows):return
    # Content-aware fill proxy: known operation mask, not hand-annotated semantic
    # object removal or diffusion generative fill. Report this distinction.
    real=json.loads((root/'images/manifest.json').read_text(encoding='utf-8'))['rows']
    selected=sorted([r for r in real if not r['ai'] and r['split']=='test' and r['variant']=='original'],key=lambda r:r['sha256'])[:12]
    for r in selected:
        with Image.open(root/'images'/r['path']) as image:rgb=np.array(image.convert('RGB'))
        h,w=rgb.shape[:2];mask=np.zeros((h,w),np.uint8);mask[h//3:h//3+h//5,w//3:w//3+w//5]=255
        filled=cv2.inpaint(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),mask,5,cv2.INPAINT_TELEA)
        ok,encoded=cv2.imencode('.jpg',filled,[cv2.IMWRITE_JPEG_QUALITY,90]);assert ok
        ok,gt=cv2.imencode('.png',mask);assert ok
        data=encoded.tobytes();digest=hashlib.sha256(data).hexdigest()
        (out/(digest+'.image')).write_bytes(data);(out/(digest+'.mask.png')).write_bytes(gt.tobytes())
        rows.append({'path':digest+'.image','sha256':digest,'mask':digest+'.mask.png','edit_type':'content_aware_removal_proxy','family':r['family'],'split':'test','source':'COCO, OpenCV TELEA local fill, rectangular operation mask; not verified semantic object removal','ai':False,'manipulation':True,'generator':'edited','variant':'content_aware_removal_proxy'})
    doc['rows']=rows
    manifest.write_text(json.dumps(doc,indent=2),encoding='utf-8')
    print('Removal proxy cases prepared:',len(selected),flush=True)


def evaluate(root):
    prepare_removal(root)
    import numpy as np
    from PIL import Image
    import torch
    torch.set_num_threads(2)
    from models.image_deepfake.inference.localizer import TruForLocalizer
    from models.image_deepfake.forensics.localization_output import pixel_mask
    from models.image_deepfake.forensics.source_evidence import inspect_source
    out=root/'edit-scope';doc=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    cfgpath=Path(__file__).resolve().parents[1]/'models/image_deepfake/calibration/evidence-v2.json'
    cfg=json.loads(cfgpath.read_text(encoding='utf-8'));fingerprint=hashlib.sha256(cfgpath.read_bytes()).hexdigest()
    target=out/'predictions.jsonl';existing=[json.loads(l) for l in target.read_text().splitlines()] if target.exists() else []
    seen={r['sha256'] for r in existing};model=TruForLocalizer()
    for i,r in enumerate(doc['rows']):
        if r['sha256'] in seen:continue
        data=(out/r['path']).read_bytes();value={**r,'config_sha256':fingerprint,'iou_raw':None,'iou_production':None,'localization_alert':False,'error':None}
        try:
            source=inspect_source(data);result=model.predict(data)
            heat=result.pop('heatmap');reliability=result.pop('reliability')
            np.savez_compressed(out/(r['sha256']+'.npz'),heatmap=heat,reliability=reliability)
            mask,regions=pixel_mask(heat,reliability,cfg['pixel_threshold'],cfg['min_reliability'],cfg['min_area_fraction'])
            raw_alert=result['raw_score']>=cfg['manipulation']['raw_alert'] and bool(regions)
            supported=result['inference_mode']=='native' and source['format']=='JPEG'
            value.update(result,raw_mask_alert=raw_alert,localization_alert=raw_alert and supported)
            if r['mask']:
                with Image.open(out/r['mask']) as gt:truth=np.asarray(gt.convert('L'))>127
                assert truth.shape==mask.shape,'Never resize or guess a ground-truth mask'
                predicted=mask>0;union=np.logical_or(truth,predicted).sum()
                iou=float(np.logical_and(truth,predicted).sum()/union) if union else 1.
                value['iou_raw']=iou if raw_alert else 0.
                value['iou_production']=iou if value['localization_alert'] else 0.
        except (ValueError,RuntimeError) as exc:value['error']=str(exc)
        with target.open('a',encoding='utf-8') as f:f.write(json.dumps(value)+'\n')
        existing.append(value);print('Edit scope',i+1,'/',len(doc['rows']),r['edit_type'],'alert',value['localization_alert'],'IoU',value['iou_production'],'error',value['error'],flush=True)
    report={}
    for kind in sorted({r['edit_type'] for r in existing}):
        group=[r for r in existing if r['edit_type']==kind];ious=[r['iou_production'] for r in group if r['iou_production'] is not None]
        report[kind]={'n':len(group),'detected_regions':sum(r['localization_alert'] for r in group),'missed_or_unavailable':sum(not r['localization_alert'] for r in group),'production_mean_iou':float(np.mean(ious)) if ious else None,'raw_research_mean_iou':float(np.mean([r['iou_raw'] for r in group if r['iou_raw'] is not None])) if ious else None,'errors':sum(r['error'] is not None for r in group)}
    (out/'metrics.json').write_text(json.dumps({'types':report,'limits':doc['limits']},indent=2),encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evaluation-root',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    if a.prepare_only:prepare(a.evaluation_root)
    else:evaluate(a.evaluation_root)
