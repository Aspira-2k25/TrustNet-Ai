"""Measure real local CPU APIs. Timings are a small diagnostic, not an SLA."""
import argparse,io,json,time,uuid
from pathlib import Path
import httpx
import numpy as np
from PIL import Image


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--images',type=Path,nargs='*',default=[]);p.add_argument('--repeats',type=int,default=2);a=p.parse_args()
    rows=[]
    with httpx.Client(timeout=32,trust_env=False) as client:
        for port in [8003,8005,8007]:client.get(f'http://127.0.0.1:{port}/ready').raise_for_status()
        texts=['Your appointment is confirmed for tomorrow at 10 AM.','Your OTP is 234567. Do not share this code with anyone.','Send me your OTP now to stop your account being blocked.','Aapka OTP 234567 hai. Kisi ko mat batana.','Aap lottery jeet gaye. Prize lene ke liye pehle processing fee bhejo.','Your receipt is ready at https://example.com/.']
        urls=['https://example.com/','https://www.wikipedia.org/','http://127.0.0.1/private','https://paypal.com.login-help.example.net/verify','https://xn--pple-43d.example/login','https://192.0.2.1/login']
        for module,port,items,key in [('message',8005,texts,'text'),('link_quick',8007,urls,'url')]:
            for _ in range(a.repeats):
                for item in items:
                    tick=time.perf_counter();response=client.post(f'http://127.0.0.1:{port}/infer',json={'scan_id':'timing-'+uuid.uuid4().hex,key:item});response.raise_for_status();result=response.json()['data']
                    rows.append({'module':module,'seconds':time.perf_counter()-tick,'status':result['status'],'verdict':result.get('verdict'),'processing_time_ms':result.get('processing_time_ms')})
        fixtures=[]
        if a.images:fixtures=[(path.name,path.read_bytes()) for path in a.images]
        else:
            buffer=io.BytesIO();Image.new('RGB',(300,300),(85,120,145)).save(buffer,'JPEG',quality=90);fixtures=[('synthetic-timing-fixture.jpg',buffer.getvalue())]
        for _ in range(a.repeats):
            for name,data in fixtures:
                tick=time.perf_counter();response=client.post('http://127.0.0.1:8003/detect/file',files={'file':(name,data)},data={'enable_explanation':'true'});response.raise_for_status();result=response.json()['data'];analysis=result['metadata']['image_analysis']
                row={'module':'image','seconds':time.perf_counter()-tick,'fixture':name,'status':result['status'],'verdict':result['verdict'],'complete':analysis['analysis_complete'],'processing_time_ms':result['processing_time_ms'],'note':analysis.get('localization_note')}
                rows.append(row);print(json.dumps(row),flush=True)
    summary={module:{'n':len(group),'p50_seconds':float(np.percentile([r['seconds'] for r in group],50)),'p95_seconds':float(np.percentile([r['seconds'] for r in group],95)),'max_seconds':max(r['seconds'] for r in group)} for module in sorted({r['module'] for r in rows}) for group in [[r for r in rows if r['module']==module]]}
    report={'scope':'Actual local CPU APIs, sequential diagnostic fixtures; includes response transfer and optional image attention. Not a field latency distribution or accuracy benchmark.','summary':summary,'rows':rows}
    a.output.parent.mkdir(exist_ok=True,parents=True);a.output.write_text(json.dumps(report,indent=2));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
