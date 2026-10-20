"""Frozen fresh real-source guard. Transformations are proxies, not platform captures."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import sys
import requests
from PIL import Image,ImageDraw,ImageEnhance,ImageFilter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark.prepare import fetch,DATASET,REVISION


def wilson(k,n):
    if not n:return None
    z=1.959963984540054;p=k/n;den=1+z*z/n
    centre=(p+z*z/(2*n))/den
    delta=z*((p*(1-p)/n+z*z/(4*n*n))**.5)/den
    return [max(0,centre-delta),min(1,centre+delta)]


def prepare(root):
    out=root/'real-guard-320';out.mkdir(exist_ok=True)
    manifest=out/'manifest.json'
    if manifest.exists():return manifest
    used=set()
    for folder in ['images','adaptation']:
        rows=json.loads((root/folder/'manifest.json').read_text(encoding='utf-8'))['rows']
        used|={r['family'] for r in rows}
    j=requests.get(f'https://huggingface.co/api/datasets/{DATASET}/revision/{REVISION}',timeout=60).json()
    names=sorted({r['rfilename'] for r in j['siblings'] if '/0_real/' in r['rfilename']},key=lambda s:hashlib.sha256(s.encode()).hexdigest())
    choices=[];seen=set()
    categories=['original','compressed_jpeg50_proxy','compressed_jpeg75_proxy','screenshot_proxy','filtered_proxy','beauty_smoothing_proxy','low_light_proxy']
    for name in names:
        family='coco:'+Path(name).name
        if family in used or family in seen:continue
        seen.add(family)
        choices.append(dict(url=f'https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{name}',family=family,variant=categories[len(choices)%len(categories)],camera='Unknown; COCO device metadata not established',source='COCO via pinned DiTFake'))
        if len(choices)==300:break
    sidd='cdtrejo/sidd-medium-lmdb';rev='7815324edfedc64b3ca8ee59942e389317d05733'
    j=requests.get(f'https://huggingface.co/api/datasets/{sidd}/revision/{rev}',timeout=60).json()
    files=[r['rfilename'] for r in j['siblings'] if '_NOISY_SRGB_010.PNG' in r['rfilename']]
    # Spread across scene, phone and illumination strata instead of adjacent bursts.
    groups={}
    for name in files:
        parts=Path(name).parent.name.split('_');groups.setdefault((parts[2],parts[-1]),[]).append(name)
    selected=[]
    for key in sorted(groups):
        group=sorted(groups[key],key=lambda s:hashlib.sha256(s.encode()).hexdigest())
        selected.extend(group[:2])
    for name in selected[:20]:
        parts=Path(name).parent.name.split('_')
        choices.append(dict(url=f'https://huggingface.co/datasets/{sidd}/resolve/{rev}/{name}',family='sidd-scene:'+parts[1],capture=Path(name).parent.name,variant='phone_low_light' if parts[-1]=='L' else 'phone_native',camera=parts[2],source='SIDD MIT; smartphone noisy sRGB',original_scene=parts[1]))
    def download(row):
        key=hashlib.sha256(row['url'].encode()).hexdigest()[:24]
        original=out/'originals'/key;original.parent.mkdir(exist_ok=True)
        if not original.exists():original.write_bytes(fetch(row['url']))
        data=original.read_bytes();source_sha=hashlib.sha256(data).hexdigest()
        path=original
        if row['variant'].endswith('_proxy'):
            with Image.open(io.BytesIO(data)) as im:image=im.convert('RGB')
            v=row['variant'];quality=90
            if v=='filtered_proxy':image=ImageEnhance.Color(ImageEnhance.Contrast(image).enhance(1.08)).enhance(1.1)
            if v=='beauty_smoothing_proxy':image=image.filter(ImageFilter.SMOOTH_MORE)
            if v=='low_light_proxy':image=ImageEnhance.Brightness(image).enhance(.28)
            if v=='screenshot_proxy':
                canvas=Image.new('RGB',(image.width,image.height+64),'#fafafa');canvas.paste(image,(0,32));image=canvas
            if v=='compressed_jpeg50_proxy':quality=50
            if v=='compressed_jpeg75_proxy':quality=75
            encoded=io.BytesIO();image.save(encoded,'JPEG',quality=quality);data=encoded.getvalue()
            path=out/'views'/(key+'.jpg');path.parent.mkdir(exist_ok=True);path.write_bytes(data)
        return {**row,'path':str(path.relative_to(out)),'sha256':hashlib.sha256(data).hexdigest(),'source_sha256':source_sha,'ai':False,'manipulation':False,'generator':'real','split':'test'}
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=[]
        for i,row in enumerate(pool.map(download,choices)):
            rows.append(row)
            if i%40==0:print('Prepared fresh real photos',i+1,'/',len(choices),flush=True)
    assert len({r['source_sha256'] for r in rows})==len(rows)
    doc={'rows':rows,'limits':['300 independent COCO source images plus smartphone captures from SIDD; SIDD scene repetitions are correlated.','Compression, screenshot, filter, beauty smoothing and low-light COCO variants are software proxies, not actual WhatsApp/Instagram outputs or camera beauty-mode captures.','COCO cameras are unknown. DSLR-specific and actual beauty-mode/platform validation remain unestablished.','No model training or threshold selection may use this holdout; failed promotion consumes it as validation.']}
    manifest.write_text(json.dumps(doc,indent=2),encoding='utf-8');return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evaluation-root',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');p.add_argument('--manifest',type=Path)
    a=p.parse_args();manifest=a.manifest or prepare(a.evaluation_root)
    if a.prepare_only:print('Manifest frozen:',manifest);return
    import torch
    torch.set_num_threads(2)
    from models.image_deepfake.inference.forensic_detector import ForensicDetector
    doc=json.loads(manifest.read_text(encoding='utf-8'));target=manifest.parent/'predictions.jsonl'
    config=Path(__file__).resolve().parents[1]/'models/image_deepfake/calibration/evidence-v2.json'
    fingerprint=hashlib.sha256(config.read_bytes()).hexdigest()
    existing=[json.loads(l) for l in target.read_text(encoding='utf-8').splitlines()] if target.exists() else []
    assert all(r['config_sha256']==fingerprint for r in existing),'Do not mix thresholds within a holdout'
    seen={r['sha256'] for r in existing};detector=ForensicDetector()
    for i,row in enumerate(doc['rows']):
        if row['sha256'] in seen:continue
        data=(manifest.parent/row['path']).read_bytes()
        try:
            r=detector.predict(data);analysis=r.metadata['image_analysis']
            value={**row,'verdict':r.verdict,'ai_policy_score':analysis['ai_policy_score'],'manipulation_raw_score':analysis['manipulation_raw_score'],'milliseconds':r.processing_time_ms,'error':None}
        except ValueError as exc:value={**row,'verdict':'INCONCLUSIVE','error':str(exc)}
        value['config_sha256']=fingerprint
        with target.open('a',encoding='utf-8') as f:f.write(json.dumps(value)+'\n')
        existing.append(value);print('Real guard',i+1,'/',len(doc['rows']),value['verdict'],flush=True)
    def stats(rows):
        rejected=sum(r.get('error') is not None for r in rows)
        assessed=[r for r in rows if r.get('error') is None]
        fp=sum(r['verdict'] in ['LIKELY_AI_GENERATED','LIKELY_MANIPULATED'] for r in assessed);n=len(assessed)
        return {'submitted_n':len(rows),'n':n,'rejected_n':rejected,'false_alerts':fp,'false_positive_rate':fp/n if n else None,'wilson_95_ci':wilson(fp,n),'inconclusive_rate':sum(r['verdict']=='INCONCLUSIVE' for r in assessed)/n if n else None}
    # Primary CI uses the 300 unique COCO families. Smartphone strata have
    # correlated captures; do not pretend these are independent Bernoulli trials.
    independent=[r for r in existing if r['family'].startswith('coco:')]
    result={'independent_coco':stats(independent),'all_descriptive':stats(existing),'strata':{k:stats([r for r in existing if r['variant']==k]) for k in sorted({r['variant'] for r in existing})},'limits':doc['limits'],'config_sha256':fingerprint}
    (manifest.parent/'metrics.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
