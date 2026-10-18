"""Authenticated async regression for bare domains, visual collisions and URI types."""
import json,os,secrets,subprocess,sys,time,uuid
from pathlib import Path
import httpx,jwt
root=Path(__file__).resolve().parents[2]
scratch=root/'runtime_state/qa/phishing-link-inputs';scratch.mkdir(parents=True,exist_ok=True)
secret=secrets.token_hex(32)
env={**os.environ,'JWT_SECRET_KEY':secret,'ALLOW_MOCK_AUTH':'false','KAFKA_ENABLED':'true',
     'KAFKA_BOOTSTRAP_SERVERS':'localhost:9094','SCAN_COMPLETION_GROUP':'link-inputs-'+uuid.uuid4().hex,
     'SCAN_SERVICE_URL':'http://127.0.0.1:18002','DATABASE_URL':'sqlite+aiosqlite:///'+str(scratch/(uuid.uuid4().hex+'.db')).replace('\\','/'),'PYTHONPATH':str(root)}
cases=[('reference','paypal.com'),('lookalike','paypaI.com'),('reference','https://paypal.com/'),
       ('lookalike','https://paypai.com/'),('lookalike','https://app1e.com/'),('reference','//www.google.com/'),
       ('offline_lookalike','ftp://paypaI.com/download'),('offline_lookalike','mailto:billing@paypaI.com'),
       ('offline','mailto:help@example.com'),('offline','javascript:alert(1)'),('offline','file:///etc/passwd')]
processes=[];logs=[];rows=[]
try:
    with httpx.Client(timeout=5) as ready_client:
        for _ in range(120):
            try:
                if ready_client.get('http://127.0.0.1:8007/ready').json().get('ready'):break
            except httpx.HTTPError:pass
            time.sleep(.5)
        else:raise TimeoutError('Start existing Kafka/Mongo and wait for phishing readiness before launching test servers.')
    for module,port in [('services.scan_management.app.main:app',18002),('gateway.app.main:app',18000)]:
        log=(scratch/f'{port}.log').open('w',encoding='utf-8');logs.append(log)
        processes.append(subprocess.Popen([sys.executable,'-m','uvicorn',module,'--host','127.0.0.1','--port',str(port)],cwd=root,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0))
    with httpx.Client(timeout=20) as client:
        for port in (18000,18002):
            for _ in range(120):
                try:
                    if client.get(f'http://127.0.0.1:{port}/health').status_code==200:break
                except httpx.HTTPError:pass
                if any(p.poll() is not None for p in processes):raise RuntimeError('Isolated test server stopped')
                time.sleep(.5)
            else:raise TimeoutError('Test server readiness')
        for _ in range(120):
            try:
                if client.get('http://127.0.0.1:8007/ready').json().get('ready'):break
            except httpx.HTTPError:pass
            time.sleep(.5)
        else:raise TimeoutError('Phishing worker readiness')
        headers={'Authorization':'Bearer '+jwt.encode({'sub':str(uuid.uuid4()),'role':'user','token_type':'access','exp':int(time.time())+1800},secret,algorithm='HS256')}
        base='http://127.0.0.1:18000/api/v1/scans'
        for kind,url in cases:
            response=client.post(base+'/url',headers=headers,json={'url':url});assert response.status_code==202,response.text
            scan_id=response.json()['data']['id']
            for _ in range(180):
                response=client.get(base+'/'+scan_id,headers=headers);response.raise_for_status();scan=response.json()['data']
                if scan['status'] not in {'QUEUED','PROCESSING'}:break
                time.sleep(.5)
            else:raise TimeoutError(scan_id)
            result=scan['result'];meta=result['metadata'];forensic=meta['forensics']
            assert scan['raw_input']==url
            assert meta['input_handling']['original']==url
            assert meta['link_analysis_version']=='links-v1'
            if kind in {'lookalike','offline_lookalike'}:
                assert result['verdict']=='SUSPICIOUS'
                assert result['risk_score']>=80
                assert forensic['visual_domain_match']
                assert scan['trust_score']['trust_risk_score']==result['risk_score']
            elif kind=='reference':
                assert result['verdict']=='NO_STRONG_INDICATORS'
                assert not forensic['visual_domain_match']
            else:
                assert result['error_code']=='NON_WEB_LINK' and result['label']=='unknown'
            if kind.startswith('offline'):
                assert forensic['network']['status']=='NOT_COLLECTED'
                assert result['model_version']=='link-forensics-v1'
            rows.append({'case':kind,'scan':scan})
            print(f"{len(rows)}/{len(cases)} {url}: {result['verdict']} score={scan.get('trust_score',{}).get('trust_risk_score') if scan.get('trust_score') else None}",flush=True)
finally:
    (root/'models/phishing_url/research/link_input_regression.json').write_text(json.dumps({'observed_at':time.time(),'results':rows,'expected_cases':len(cases)},indent=2),encoding='utf-8')
    for process in processes:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
    for log in logs:log.close()
