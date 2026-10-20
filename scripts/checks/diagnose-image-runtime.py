"""Verify loaded artifacts and real image inference without modifying user data."""
import hashlib
import io
import json
import sys
import httpx
from PIL import Image

try:
    with httpx.Client(timeout=httpx.Timeout(130,connect=5)) as client:
        ready=client.get('http://127.0.0.1:8003/ready');ready.raise_for_status()
        assert ready.json()['localizer_ready'], 'Research localizer is unavailable; install it or use an explicitly documented reduced-coverage mode'
        buffer=io.BytesIO();Image.new('RGB',(192,192),(80,130,160)).save(buffer,'PNG');data=buffer.getvalue()
        response=client.post('http://127.0.0.1:8003/detect/file',files={'file':('smoke-fixture.png',data,'image/png')})
        response.raise_for_status();result=response.json()['data']
        assert result['status']=='SUCCESS' and result['detector_id']=='image_deepfake.evidence.v2'
        assert result['metadata']['image_analysis']['source_sha256']==hashlib.sha256(data).hexdigest()
        assert result['verdict']=='INCONCLUSIVE', 'Small synthetic fixture must not imply authenticity'
        print(json.dumps({'result':'PASS','real_image_service_inference':True,'original_source_hash':'PASS','verdict':result['verdict'],'localizer_ready':True,'authenticity_enabled':ready.json()['authenticity_enabled'],'scope':'Runtime smoke only, not photo accuracy or localization quality'}))
except (httpx.HTTPError,AssertionError,KeyError,ValueError) as exc:
    print('Image smoke FAILED: '+str(exc),file=sys.stderr);raise SystemExit(1)
