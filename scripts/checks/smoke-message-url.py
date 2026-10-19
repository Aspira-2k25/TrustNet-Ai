"""Verify real selected message+URL inference and authenticated Gateway boundary."""
import json,sys,uuid
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

def call(url,payload=None):
    req=Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=45) as response:return json.load(response)

try:
    for port in (8000,8001,8002):call(f'http://127.0.0.1:{port}/health')
    call('http://127.0.0.1:8005/ready');call('http://127.0.0.1:8007/ready')
    result=call('http://127.0.0.1:8005/infer',{'scan_id':'smoke-'+uuid.uuid4().hex,'text':'Your appointment is confirmed. View your receipt at https://example.com/.'})['data']
    f=result['metadata']['fusion']
    assert result['status']=='SUCCESS' and f['policy']=='message-url-max-v1'
    assert f['links_found']==f['links_assessed']==1 and f['url_score'] is not None
    assert result['risk_score']==max(f['message_score'],f['url_score'])
    assert result['metadata']['links'][0]['model_version']=='regional-recall-v1'
    assert result['metadata']['links'][0]['coverage']['website_fetched'] is False
    assert not f['calibrated'] and result['confidence']==0
    try:
        call('http://127.0.0.1:8000/api/v1/scans/scam/analyze',{'text':'Your appointment is confirmed tomorrow.'})
        raise AssertionError('Unauthenticated request accepted')
    except HTTPError as exc:assert exc.code==401
    print(json.dumps({'ready':True,'scam_model':result['model_version'],'phishing_model':result['metadata']['links'][0]['model_version'],
        'fusion_policy':f['policy'],'actual_link_inference':'PASS','gateway_auth':'PASS',
        'combined_calibrated_probability':False,'scope':'Inference and authentication; not a benchmark, browser or persistence test'},indent=2))
except (HTTPError,URLError,AssertionError,KeyError,TypeError,TimeoutError) as exc:
    print('Smoke check failed: '+str(exc)+'. Inspect runtime-logs and model installers.',file=sys.stderr)
    sys.exit(1)
