"""Pinned, resumable source acquisition. Raw data belongs outside the repository."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import time
import tarfile
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
import zlib
import requests
import httpx
from PIL import Image

GEN_REV='ed371660f5af74a165570a2234b9beea0abb81ef'
DIT_REV='ca9ea06c8f926c3a11ca4b657074cc7cbb99e5c7'
SIDD_REV='7815324edfedc64b3ca8ee59942e389317d05733'
RAISE='https://www.grip.unina.it/download/prog/DMimageDetection/real_RAISE_1k.zip'
TGIF='https://cloud.ilabt.imec.be/public.php/dav/files/xEeAzrY7ES9KA8o/'

def sha(data):return hashlib.sha256(data).hexdigest()
def ordered(values):return sorted(values,key=lambda x:sha(str(x).encode()))
CLIENT=httpx.Client(timeout=httpx.Timeout(60,connect=12),follow_redirects=True,limits=httpx.Limits(max_connections=16,max_keepalive_connections=16))

def get(url,**kw):
    for attempt in range(3):
        try:
            r=CLIENT.get(url,**kw);r.raise_for_status();return r
        except httpx.HTTPError:
            if attempt==2:raise
            time.sleep(attempt+1)

class RemoteZIP(io.RawIOBase):
    def __init__(self,url):
        self.url=url;self.position=0
        r=get(url,headers={'Range':'bytes=-22'})
        if r.status_code!=206:raise ValueError('Archive lacks HTTP range support')
        self.size=int(r.headers['Content-Range'].rsplit('/',1)[1])
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.position
    def seek(self,n,whence=0):
        self.position=n if whence==0 else self.position+n if whence==1 else self.size+n
        if not 0<=self.position<=self.size:raise ValueError('Invalid archive offset')
        return self.position
    def block(self,start,length):
        if length>32*1024*1024:raise ValueError('Archive member exceeds bounded download')
        if not length:return b''
        end=start+length-1
        url=self.url+('&' if '?' in self.url else '?')+f'coverage_range={start}-{end}'
        r=get(url,headers={'Range':f'bytes={start}-{end}'})
        if r.status_code!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{end}/{self.size}' or len(r.content)!=length:raise ValueError('Invalid remote byte range')
        return r.content
    def read(self,n=-1):
        length=self.size-self.position if n<0 else min(n,self.size-self.position)
        value=self.block(self.position,length);self.position+=length;return value
    def member(self,info):
        # Fetch the local header and compressed member in one validated range.
        # The slack covers ordinary local extra fields; unusually large extras
        # fall back to a second exact read rather than guessing offsets.
        length=min(self.size-info.header_offset,30+len(info.filename.encode('utf-8'))+512+info.compress_size)
        chunk=self.block(info.header_offset,length);header=chunk[:30]
        if header[:4]!=b'PK\x03\x04':raise ValueError('Invalid ZIP header')
        name,extra=struct.unpack_from('<HH',header,26)
        offset=30+name+extra
        payload=chunk[offset:offset+info.compress_size] if offset+info.compress_size<=len(chunk) else self.block(info.header_offset+offset,info.compress_size)
        data=zlib.decompress(payload,-15) if info.compress_type==8 else payload if info.compress_type==0 else None
        if data is None or len(data)!=info.file_size or zlib.crc32(data)!=info.CRC:raise ValueError('Archive integrity failure')
        return data

def tgif_session():
    s=requests.Session();s.get('https://cloud.ilabt.imec.be/index.php/s/xEeAzrY7ES9KA8o',timeout=40).raise_for_status()
    s.auth=('xEeAzrY7ES9KA8o','');return s

def dav(s,folder):
    r=s.request('PROPFIND',TGIF+folder,headers={'Depth':'1','X-Requested-With':'XMLHttpRequest'},timeout=60);r.raise_for_status()
    return [urllib.parse.unquote(n.text).removeprefix('/public.php/dav/files/xEeAzrY7ES9KA8o/') for n in ET.fromstring(r.content).findall('.//{DAV:}href')][1:]

def catalog(out,include_tgif=True,tgif_only=False):
    target=out/('tgif-source-selection.json' if tgif_only else 'source-selection.json')
    if target.exists():return json.loads(target.read_text(encoding='utf-8'))
    rows=[];archives={};tg=tgif_session()
    print('TGIF directories',dav(tg,''),flush=True)
    def add(source,gen,positive,split,family,**extra):rows.append(dict(source=source,generator=gen,positive=positive,split=split,family=family,**extra))
    # Official TGIF archives are gzip tar streams, not individually addressable images.
    saved=out/'tgif-generation-selection.json'
    if not include_tgif:tg_rows=[]
    elif saved.exists():tg_rows=json.loads(saved.read_text(encoding='utf-8'))
    else:
        tg_rows=[]
        for archive_path,split,n,gen in [('sdxl-fr/sdxl-fr_training.tar.gz','train',50,'TGIF-SDXL-fr'),('sd2-fr/sd2-fr_validation.tar.gz','calibration',20,'TGIF-SD2-fr'),('sd2-fr/sd2-fr_training.tar.gz','threshold',20,'TGIF-SD2-fr')]:
            response=tg.get(TGIF+archive_path,headers={'X-Requested-With':'XMLHttpRequest'},stream=True,timeout=(12,90));response.raise_for_status()
            seen=set()
            with response,tarfile.open(fileobj=response.raw,mode='r|gz') as archive:
                for member in archive:
                    if not member.isfile() or not member.name.lower().endswith('.png'):continue
                    identity=Path(member.name).name.split('_')[0]
                    if identity in seen:continue
                    seen.add(identity);data=archive.extractfile(member).read()
                    path=out/'tgif-originals'/sha(data);path.parent.mkdir(exist_ok=True);path.write_bytes(data)
                    tg_rows.append(dict(source='TGIF',generator=gen,positive=True,split=split,family='coco:'+identity,local_path=str(path.relative_to(out)),archive_url=TGIF+archive_path,member=member.name,license='CC BY-SA 4.0; COCO source rights'))
                    if len(seen)%25==0:print('TGIF stream',split,len(seen),'/',n,flush=True)
                    if len(seen)==n:break
            if len(seen)!=n:raise ValueError('Insufficient distinct TGIF families')
        saved.write_text(json.dumps(tg_rows,indent=2),encoding='utf-8')
    rows.extend(tg_rows);tg_ids={str(int(r['family'].split(':',1)[1])) for r in tg_rows}
    if tgif_only:
        doc={'rows':rows,'archives':{},'version':'tgif-source-selection-1'};target.write_text(json.dumps(doc,indent=2),encoding='utf-8');return doc
    for gen in ['ADM','BigGAN','glide','Midjourney','SD_v14','VQDM','SD_v15','wukong']:
        url=f'https://huggingface.co/datasets/shimei123/Genimage/resolve/{GEN_REV}/{gen}.zip'
        reader=RemoteZIP(url)
        with zipfile.ZipFile(reader) as archive:entries=[x for x in archive.infolist() if '/1_fake/' in x.filename and x.filename.lower().endswith(('.png','.jpg','.jpeg'))]
        entries=ordered(entries);chosen=entries[:440] if gen not in {'SD_v15','wukong'} else entries[:400]
        archives[gen]=dict(url=url,size=reader.size,members={x.filename:dict(header_offset=x.header_offset,compress_size=x.compress_size,file_size=x.file_size,CRC=x.CRC,compress_type=x.compress_type) for x in chosen})
        for i,x in enumerate(chosen):
            split=('train' if i<340 else 'seen_test') if gen not in {'SD_v15','wukong'} else ('calibration' if i<200 else 'threshold')
            # ImageNet prompt/class IDs do not establish independence from backbone pretraining.
            add('GenImage',gen,True,split,'genimage:'+gen+':'+Path(x.filename).name,archive=gen,member=x.filename,license='GenImage CC BY-NC-SA 4.0; upstream generator/source terms')
        print('Catalogued',gen,len(chosen),flush=True)
    dit=get(f'https://huggingface.co/api/datasets/Jouesmak/DiTFake/revision/{DIT_REV}').json()
    old=out.parent/'forensic-overhaul';used=set()
    for p in [old/'images/manifest.json',old/'adaptation/manifest.json',old/'real-guard-320/manifest.json']:
        if p.exists():used.update(r['family'] for r in json.loads(p.read_text(encoding='utf-8'))['rows'])
    real={Path(x['rfilename']).name:x['rfilename'] for x in dit['siblings'] if '/0_real/' in x['rfilename']}
    real=[name for name in ordered(real) if 'coco:'+name not in used and str(int(name.rsplit('_',1)[-1].split('.')[0])) not in tg_ids]
    # A single COCO identity cannot enter real and generated partitions.
    for i,name in enumerate(real[:2900]):
        split='train' if i<1600 else 'calibration' if i<1900 else 'threshold' if i<2200 else 'test'
        path=f'DiTFake/test/FLUX.1-schnell/0_real/{name}'
        add('COCO','real',False,split,'coco:'+name,url=f'https://huggingface.co/datasets/Jouesmak/DiTFake/resolve/{DIT_REV}/{path}',license='COCO source image licences; DiTFake card Apache 2.0')
    reserved_ids={Path(n).stem.replace('COCO_val2014_','').lstrip('0') for n in real[:2900]}|tg_ids
    for gen in ['FLUX.1-schnell','PixArt-Sigma-XL-2-1024-MS','stable-diffusion-3-medium-diffusers']:
        names=ordered([x['rfilename'] for x in dit['siblings'] if f'/{gen}/1_fake/' in x['rfilename']])
        accepted=[]
        for name in names:
            identity=Path(name).stem
            if identity.lstrip('0') in reserved_ids or 'prompt:'+Path(name).name in used:continue
            reserved_ids.add(identity.lstrip('0'));accepted.append(name)
            if len(accepted)==250:break
        for name in accepted:add('DiTFake',gen,True,'test','dit-prompt:'+Path(name).stem,url=f'https://huggingface.co/datasets/Jouesmak/DiTFake/resolve/{DIT_REV}/{name}',license='Apache 2.0 card, source rights apply')
    csv_url='https://storage.googleapis.com/openimages/2018_04/validation/validation-images-with-rotation.csv'
    metadata=get(csv_url).content;(out/'openimages-source.csv').write_bytes(metadata)
    photos=ordered(list(csv.DictReader(io.StringIO(metadata.decode('utf-8')))))[:900]
    for i,r in enumerate(photos):
        split='train' if i<500 else 'calibration' if i<600 else 'threshold' if i<700 else 'test'
        add('OpenImages','real',False,split,'openimages:'+r['ImageID'],url=f'https://open-images-dataset.s3.amazonaws.com/validation/{r["ImageID"]}.jpg',license=r['License'],attribution={'author':r['Author'],'landing':r['OriginalLandingURL']})
    reader=RemoteZIP(RAISE)
    with zipfile.ZipFile(reader) as archive:entries=ordered([x for x in archive.infolist() if x.filename.lower().endswith(('.png','.jpg','.tif','.tiff'))])[:400]
    archives['RAISE']=dict(url=RAISE,size=reader.size,members={x.filename:dict(header_offset=x.header_offset,compress_size=x.compress_size,file_size=x.file_size,CRC=x.CRC,compress_type=x.compress_type) for x in entries})
    for i,x in enumerate(entries):add('RAISE','real',False,['train','calibration','threshold','test'][i//100],'raise:'+Path(x.filename).stem,archive='RAISE',member=x.filename,license='RAISE/Synthbuster noncommercial; original image rights')
    sidd=get(f'https://huggingface.co/api/datasets/cdtrejo/sidd-medium-lmdb/revision/{SIDD_REV}').json()
    counts=Counter()
    for name in ordered([x['rfilename'] for x in sidd['siblings'] if '_GT_SRGB_010.PNG' in x['rfilename']]):
        scene=name.split('/')[2].split('_')[1];split='train' if int(scene)<=6 else 'calibration' if scene=='007' else 'threshold' if scene=='008' else 'test'
        budget={'train':40,'calibration':10,'threshold':10,'test':20}[split]
        if counts[split]>=budget:continue
        counts[split]+=1
        add('SIDD','real',False,split,'sidd-scene:'+scene,url=f'https://huggingface.co/datasets/cdtrejo/sidd-medium-lmdb/resolve/{SIDD_REV}/{name}',license='SIDD academic research terms; mirror card has no blanket licence',scene=scene)
    doc=dict(version='coverage-v3-source-selection-1',rows=rows,archives=archives,heldout_generators=['FLUX.1-schnell','PixArt-Sigma-XL-2-1024-MS','stable-diffusion-3-medium-diffusers'],limits=['Unseen means excluded from this head fitting and validation; upstream backbone pretraining overlap is unknown.','Seen-generator test is supplemental, source-separated and never used for fitting or thresholds.','SIDD captures are grouped by scene, so sample count is not independent scene count.','Photographic collection labels are not manual ground truth; screenshots/filter/compression are software proxies.'])
    target.write_text(json.dumps(doc,indent=2),encoding='utf-8');return doc

def download(out,doc):
    cache=out/'originals';cache.mkdir(exist_ok=True);target=out/'acquired.jsonl'
    done={r['identity']:r for r in [json.loads(l) for l in target.read_text(encoding='utf-8').splitlines()] } if target.exists() else {}
    def one(row):
        identity=sha(json.dumps(row,sort_keys=True).encode())
        if identity in done:return None
        path=cache/identity
        if not path.exists():
            if 'local_path' in row:data=(out/row['local_path']).read_bytes()
            elif 'archive' in row:
                a=doc['archives'][row['archive']];info=zipfile.ZipInfo(row['member'])
                for key,value in a['members'][row['member']].items():setattr(info,key,value)
                reader=RemoteZIP.__new__(RemoteZIP);reader.url=a['url'];reader.size=a['size'];reader.position=0;data=reader.member(info)
            elif row['source']=='TGIF':
                s=tgif_session();r=s.get(row['url'],timeout=60);r.raise_for_status();data=r.content
            else:data=get(row['url']).content
            with Image.open(io.BytesIO(data)) as image:image.verify()
            path.write_bytes(data)
        data=path.read_bytes()
        with Image.open(io.BytesIO(data)) as image:width,height=image.size
        return {**row,'identity':identity,'path':str(path.relative_to(out)),'sha256':sha(data),'width':width,'height':height}
    errors=[];pending=doc['rows']
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures={pool.submit(one,r):r for r in pending}
        for index,future in enumerate(as_completed(futures)):
            try:
                value=future.result()
                if value:
                    with target.open('a',encoding='utf-8') as f:f.write(json.dumps(value)+'\n')
            except Exception as e:
                errors.append({'row':futures[future],'error':str(e)[:300]})
                if len(errors)<=3:print('Acquisition failure',type(e).__name__,str(e)[:160],flush=True)
            if (index+1)%100==0:print('Acquisition',index+1,'/',len(pending),'errors',len(errors),flush=True)
    (out/'download-errors.json').write_text(json.dumps(errors,indent=2),encoding='utf-8')
    print('Acquisition complete; failures',len(errors),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--core-only',action='store_true');p.add_argument('--tgif-only',action='store_true');a=p.parse_args();out=a.output.resolve()
    if out.is_relative_to(Path(__file__).resolve().parents[1]):raise SystemExit('Keep raw data outside the repository')
    out.mkdir(exist_ok=True,parents=True);download(out,catalog(out,include_tgif=not a.core_only,tgif_only=a.tgif_only))

if __name__=='__main__':main()
