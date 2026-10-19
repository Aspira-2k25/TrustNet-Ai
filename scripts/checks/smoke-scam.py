"""Standard-library smoke check: actual ready model + local inference + gateway auth."""
import json,uuid,sys
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
def request(url,payload=None):
 data=None if payload is None else json.dumps(payload).encode()
 with urlopen(Request(url,data=data,headers={'Content-Type':'application/json'}),timeout=30) as response:
  return json.load(response)
try:
 for port in [8001,8002,8000]:request(f'http://127.0.0.1:{port}/health')
 ready=request('http://127.0.0.1:8005/ready')
 result=request('http://127.0.0.1:8005/infer',{'scan_id':'smoke-'+uuid.uuid4().hex,'text':'Your appointment is confirmed for tomorrow at 10 AM.'})['data']
 assert result['status']=='SUCCESS' and result['model_version']==ready['model_version']
 assert result['metadata']['coverage']['truncated'] is False
 assert result['metadata']['assessment_dimensions']['sender_verification']['status']=='NOT_VERIFIED'
 try:
  request('http://127.0.0.1:8000/api/v1/scans/scam/analyze',{'text':'Your appointment is confirmed for tomorrow'})
  raise AssertionError('Gateway accepted unauthenticated request')
 except HTTPError as error:assert error.code==401
 print(json.dumps({'ready':True,'model':ready['model_version'],'actual_inference':'SUCCESS','gateway_unauthorized':401,'optional_provider':result['metadata']['optional_explanation']['status']},indent=2))
except (HTTPError,URLError,AssertionError,KeyError) as error:
 print('Smoke check failed: '+str(error)+'. Check runtime-logs, model installation and ports.',file=sys.stderr);sys.exit(1)
