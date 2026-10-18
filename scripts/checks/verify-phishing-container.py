"""Run through docker exec ... python -; never prints collector credentials."""
import hashlib
import json
import os
from pathlib import Path
from urllib.request import urlopen
from models.phishing_url.inference.phishing_detector import PhishingDetector
from services.phishing_url.app.detection_service import DetectionService

path=Path(os.environ['PHISHING_MODEL_MANIFEST'])
detector=PhishingDetector(path);service=DetectionService(detector)
with urlopen('http://127.0.0.1:8007/ready',timeout=5) as response:
    ready=json.load(response)
expected=os.getenv('PHISHING_EXPECTED_MODEL_VERSION','regional-recall-v1')
assert ready['ready'] and detector.manifest['model_version']==expected
offline=[]
for i,url in enumerate(['https://google.com/','https://www.google.com/','https://paypal.com/','https://github.com/','https://docs.python.org/3/']):
    r=detector.predict({'scan_id':'container-offline-'+str(i),'url':url})
    assert r.verdict!='SUSPICIOUS',url
    offline.append({'url':url,'verdict':r.verdict,'risk_score':r.risk_score,'model_version':r.model_version})
live=[]
for i,url in enumerate(['https://google.com/','https://paypal.com/']):
    r=service.handle({'scan_id':'container-live-'+str(i),'module':'phishing','timestamp':'2026-10-18T00:00:00Z','payload':{'url':url}}).payload
    signals=r.metadata.get('forensics',{}).get('network',{}).get('signals',{})
    live.append({'url':url,'verdict':r.verdict,'risk_score':r.risk_score,'model_version':r.model_version,
                 'collector_applied':bool(r.metadata.get('collected_observations')),
                 'checks':{n:s.get('status') for n,s in signals.items()},
                 'http_status':signals.get('http',{}).get('status_code')})
    assert r.status.value=='PARTIAL_SUCCESS'
    assert r.verdict!='SUSPICIOUS',url
    assert r.metadata.get('collected_observations'),'Live collector did not respond'
print(json.dumps({'ready':ready,'model_version':detector.manifest['model_version'],
                  'manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                  'linux_offline_regressions':offline,'live_collection':live,
                  'not_an_authenticated_browser_or_published_kafka_event_test':True},indent=2))
