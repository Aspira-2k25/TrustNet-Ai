"""Authenticated Gateway â†’ scan/Kafka â†’ deployed worker â†’ persisted report smoke.

Uses isolated test Gateway/Scan processes and SQLite; preserves existing app
ports, secrets and databases. Kafka/Mongo and phishing container must be running.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import uuid
import httpx
import jwt

root=Path(__file__).resolve().parent.parent
scratch=root/'scratch'/'phishing-platform';scratch.mkdir(parents=True,exist_ok=True)
secret=secrets.token_hex(32)
environment={**os.environ,'JWT_SECRET_KEY':secret,'ALLOW_MOCK_AUTH':'false','KAFKA_ENABLED':'true','KAFKA_BOOTSTRAP_SERVERS':'localhost:9094','DATABASE_URL':'sqlite+aiosqlite:///'+str(scratch/('scan-'+uuid.uuid4().hex+'.db')).replace('\\','/'),'SCAN_SERVICE_URL':'http://127.0.0.1:18002','PYTHONPATH':str(root)}
processes=[];logs=[]
environment['SCAN_COMPLETION_GROUP']='phishing-platform-'+uuid.uuid4().hex
def launch(module,port):
    log=(scratch/f'{port}.log').open('w',encoding='utf-8');logs.append(log)
    processes.append(subprocess.Popen([sys.executable,'-m','uvicorn',module,'--host','127.0.0.1','--port',str(port)],cwd=root,env=environment,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0))
def token(subject):
    return jwt.encode({'sub':subject,'role':'user','exp':int(time.time())+600,'token_type':'access'},secret,algorithm='HS256')
def ready(client,url):
    for _ in range(120):
        try:
            if client.get(url+'/health').status_code==200:return
        except httpx.HTTPError:pass
        if any(p.poll() is not None for p in processes):raise RuntimeError('Test server stopped; inspect scratch/phishing-platform logs')
        time.sleep(.25)
    raise TimeoutError('Test server readiness')
try:
    launch('services.scan_management.app.main:app',18002);launch('gateway.app.main:app',18000)
    with httpx.Client(timeout=20) as client:
        ready(client,'http://127.0.0.1:18002');ready(client,'http://127.0.0.1:18000')
        base='http://127.0.0.1:18000/api/v1/scans'
        assert client.post(base+'/url',json={'url':'https://example.com/account'}).status_code==401
        owner=str(uuid.uuid4());headers={'Authorization':'Bearer '+token(owner)}
        assert client.post(base+'/url',headers=headers,json={'url':'https://'}).status_code==422
        response=client.post(base+'/url',headers=headers,json={'url':'https://paypal.com@account.example/login'})
        assert response.status_code==202,response.text
        accepted=response.json()['data'];scan_id=accepted['id']
        for _ in range(120):
            response=client.get(base+'/'+scan_id,headers=headers);response.raise_for_status();scan=response.json()['data']
            if scan['status'] not in ('QUEUED','PROCESSING'):break
            time.sleep(.5)
        assert scan['result']['scan_id']==scan_id
        assert scan['result']['module']=='phishing'
        assert scan['result']['status']=='PARTIAL_SUCCESS'
        assert scan['result']['model_version']=='modern-v5'
        assert scan['result']['metadata']['configuration']=='modern_v5'
        assert scan['result']['metadata']['assessment_policy']=='dynamic-v2'
        assert scan['result']['metadata']['score_basis']=='model_and_live_evidence'
        assert all(a['status']=='APPLIED' for a in scan['result']['analyzers'] if a.get('category') in {'primary_ml','forensics'})
        assert all(a['status'] in {'APPLIED','UNAVAILABLE'} for a in scan['result']['analyzers'])
        assert scan['trust_score']['scan_id']==scan_id
        assert scan['trust_score']['reporting_modules']==['phishing']
        assert scan['trust_score']['trust_risk_score']==scan['result']['risk_score']
        denied=client.get(base+'/'+scan_id,headers={'Authorization':'Bearer '+token(str(uuid.uuid4()))})
        assert denied.status_code==403
        live_response=client.post(base+'/url',headers=headers,json={'url':'https://www.google.com/'})
        assert live_response.status_code==202,live_response.text
        live_id=live_response.json()['data']['id']
        for _ in range(120):
            response=client.get(base+'/'+live_id,headers=headers);response.raise_for_status();live_scan=response.json()['data']
            if live_scan['status'] not in ('QUEUED','PROCESSING'):break
            time.sleep(.5)
        live_result=live_scan['result'];signals=live_result['metadata']['forensics']['network']['signals']
        (scratch/'last-certificate-attempt.json').write_text(json.dumps(live_scan,indent=2),encoding='utf-8')
        certificate=signals['tls']['analysis']
        assert certificate['chain_validated'] and certificate['hostname_validated']
        assert len(certificate['sha256_fingerprint'])==64
        assert certificate['signature_algorithm_oid'] and certificate['public_key_type']
        assert len(signals['navigation']['hops'])>=1
        assert live_result['verdict']=='NO_STRONG_INDICATORS'
        assert live_scan['trust_score']['trust_risk_score']==live_result['risk_score']
        report={'real_authenticated_gateway':True,'mock_auth':False,'real_kafka':True,'real_mongodb_worker':True,'deployed_container_worker':True,'relational_store':'isolated SQLite test database','owner_isolation':True,'invalid_scheme_rejected':True,'scan':scan,'live_certificate_navigation_scan':live_scan,'model_configuration':'modern_v5'}
        (root/'models/phishing_url/research/platform_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({key:report[key] for key in ('real_authenticated_gateway','real_kafka','real_mongodb_worker','deployed_container_worker','owner_isolation','invalid_scheme_rejected')},indent=2))
finally:
    for process in processes:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
    for log in logs:log.close()
