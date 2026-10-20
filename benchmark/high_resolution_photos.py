"""Real 2K research-photo guard, downloaded selectively from the official archive.

DIV2K is for academic research only; original owners retain image copyright.
The first eight fixed photos are a validation guard. The next eight remain test.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
import requests

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
URL='https://data.vision.ee.ethz.ch/cvl/DIV2K/DIV2K_valid_HR.zip'


class RangeReader(io.RawIOBase):
    def __init__(self):
        self.position=0
        r=requests.get(URL,headers={'Range':'bytes=-22'},timeout=30,stream=True)
        try:
            if r.status_code!=206:raise ValueError('Official archive server must support bounded ranges')
            self.size=int(r.headers['Content-Range'].rsplit('/',1)[1])
        finally:r.close()
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        self.position=offset if whence==0 else self.position+offset if whence==1 else self.size+offset
        if not 0<=self.position<=self.size:raise ValueError('Invalid remote archive offset')
        return self.position
    def read(self,size=-1):
        length=self.size-self.position if size<0 else min(size,self.size-self.position)
        if length==0:return b''
        if length>24*1024*1024:raise ValueError('Remote archive read exceeds bounded budget')
        start=self.position;end=start+length-1
        response=requests.get(URL,headers={'Range':f'bytes={start}-{end}'},timeout=(10,60))
        if response.status_code!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{self.size}' or len(response.content)!=length:
            raise ValueError('Remote archive returned the wrong byte range')
        self.position+=length
        return response.content


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evaluation-root',type=Path,required=True)
    a=p.parse_args();out=a.evaluation_root/'real-high-resolution';out.mkdir(exist_ok=True)
    def one(index):
        name=f'{index:04}.png';target=out/name
        if not target.exists():
            with zipfile.ZipFile(RangeReader()) as archive:data=archive.read('DIV2K_valid_HR/'+name)
            target.write_bytes(data)
        return dict(path=name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),family='div2k:'+name,
            generator='real',ai=False,manipulation=False,variant='native_high_resolution',
            split='validation' if index<809 else 'test')
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(one,range(801,817)))
    (out/'manifest.json').write_text(json.dumps(dict(rows=rows,source=URL,license='Academic research only; image owners retain copyright',
        limits=['Small high-resolution photo guard; actual camera devices and phone processing are not known.']),indent=2),encoding='utf-8')
    import torch,numpy as np
    torch.set_num_threads(2)
    from models.image_deepfake.inference.global_classifier import GlobalClassifier
    root=Path(__file__).resolve().parents[1]
    model=GlobalClassifier('community',root/'models/image_deepfake/artifacts/global')
    head=json.loads((a.evaluation_root/'adaptation/candidate-head.json').read_text())
    target=out/'validation.jsonl'
    existing=[json.loads(l) for l in target.read_text().splitlines()] if target.exists() else []
    seen={r['sha256'] for r in existing}
    for r in rows:
        if r['split']!='validation' or r['sha256'] in seen:continue
        result=model.predict((out/r['path']).read_bytes(),return_embedding=True)
        x=np.array(result.pop('embedding'));margin=float(((x-head['mean'])/head['scale'])@head['coef']+head['intercept'])
        value={**r,**result,'head_raw':float(1/(1+np.exp(-margin)))}
        with target.open('a') as f:f.write(json.dumps(value)+'\n')
        print(r['path'],'base',value['ai_score'],'modern',value['head_raw'],flush=True)


if __name__=='__main__':main()
