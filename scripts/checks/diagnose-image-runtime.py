"""Non-sensitive fixture through the real, authenticated website image route."""
import json,struct,zlib,time,uuid,sys
from pathlib import Path
import httpx,jwt
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
from gateway.app.config.settings import settings
scratch=root/'runtime_state/qa/image-runtime';scratch.mkdir(parents=True,exist_ok=True)
def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
size=192
pixels=b''.join(b'\0'+bytes(v for x in range(size) for v in (x*255//size,y*255//size,(x+y)*127//size)) for y in range(size))
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',size,size,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')
token=jwt.encode({'sub':str(uuid.uuid4()),'role':'user','token_type':'access','exp':int(time.time())+600},settings.JWT_SECRET_KEY,algorithm=settings.JWT_ALGORITHM)
started=time.monotonic();print('Submitting synthetic test PNG to authenticated Gateway image route...',flush=True)
try:
    response=httpx.post('http://127.0.0.1:8000/api/v1/scans/analyze',headers={'Authorization':'Bearer '+token},files={'file':('runtime-fixture.png',png,'image/png')},data={'enable_explanation':'false'},timeout=httpx.Timeout(120,connect=5))
    try:body=response.json()
    except ValueError:body={'text':response.text[:2000]}
    report={'elapsed_seconds':round(time.monotonic()-started,2),'http_status':response.status_code,'response':body}
except httpx.HTTPError as exc:
    report={'elapsed_seconds':round(time.monotonic()-started,2),'transport_error':type(exc).__name__}
(scratch/'gateway-image-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='response'}),flush=True)
body=report.get('response',{});data=body.get('data') or {};result=data.get('result') or data
print(json.dumps({'error':body.get('error') or body.get('detail'),'result_status':result.get('status'),'error_code':result.get('error_code'),'error_message':result.get('error_message'),'analyzers':result.get('analyzers')},default=str),flush=True)
