"""Reproducible URL smoke suite through authenticated Gateway/Kafka/Mongo.

These examples have no verified ground-truth labels: this is functional testing,
not a new accuracy benchmark. No submitted URL is fetched.
"""
import json
import os
from pathlib import Path
import random
import secrets
import subprocess
import sys
import time
import uuid
import httpx
import jwt

root=Path(__file__).resolve().parents[1]
scratch=root/'scratch'/'phishing-url-suite'; scratch.mkdir(parents=True,exist_ok=True)
secret=secrets.token_hex(32)
environment={**os.environ,'JWT_SECRET_KEY':secret,'ALLOW_MOCK_AUTH':'false','KAFKA_ENABLED':'true',
             'SCAN_COMPLETION_GROUP':'phishing-url-suite-'+uuid.uuid4().hex,
             'KAFKA_BOOTSTRAP_SERVERS':'localhost:9094','SCAN_SERVICE_URL':'http://127.0.0.1:18002',
             'DATABASE_URL':'sqlite+aiosqlite:///'+str(scratch/('scan-'+uuid.uuid4().hex+'.db')).replace('\\','/'),
             'PYTHONPATH':str(root)}
rng=random.Random(42)
cases=[('public address',u) for u in [
    'https://www.google.com/','https://www.wikipedia.org/','https://github.com/',
    'https://www.microsoft.com/','https://www.amazon.in/','https://www.python.org/',
    'https://www.bbc.com/news','https://www.paypal.com/signin',
    'https://example.com/','https://example.com/account']]
cases += [('synthetic random',f"https://{rng.choice(['account','verify','secure','news'])}-{rng.randrange(10000):04}.example/{rng.choice(['login','index','billing','help'])}?id={rng.randrange(100000)}") for _ in range(10)]
cases += [('edge case',u) for u in ['http://192.0.2.1/login',
    'https://paypal.com@account.example/login','https://xn--pple-43d.example/',
    'https://shop.example:8443/a%2Fb?q=hello%20world', 'https://example.com/'+('a'*180)]]
invalid=['not a url','ftp://example.com/file','javascript:alert(1)','file:///etc/passwd','https://']
focus='--focus' in sys.argv
if focus:
    cases=[('forensic regression',u) for u in ['https://www.google.com','https://www.google.com/','https://google.com','https://google.com/','https://www.wikipedia.org/','https://github.com/','https://example.com/account','https://paypal.com@account.example/login']]
processes=[]; logs=[]; scans=[]; rejections=[]
try:
    for module,port in [('services.scan_management.app.main:app',18002),('gateway.app.main:app',18000)]:
        log=(scratch/f'{port}.log').open('w',encoding='utf-8'); logs.append(log)
        processes.append(subprocess.Popen([sys.executable,'-m','uvicorn',module,'--host','127.0.0.1','--port',str(port)],
            cwd=root,env=environment,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0))
    with httpx.Client(timeout=10) as client:
        for port in (18000,18002):
            for attempt in range(120):
                try:
                    if client.get(f'http://127.0.0.1:{port}/health').status_code==200: break
                except httpx.HTTPError: pass
                if any(p.poll() is not None for p in processes): raise RuntimeError('Suite server failed; inspect scratch logs')
                time.sleep(.5)
            else: raise TimeoutError('Suite server readiness')
        for attempt in range(120):
            try:
                response=client.get('http://127.0.0.1:8007/ready')
                if response.status_code==200 and response.json()['ready']: break
            except httpx.HTTPError: pass
            time.sleep(.5)
        else: raise TimeoutError('Phishing worker readiness')
        token=jwt.encode({'sub':str(uuid.uuid4()),'role':'user','exp':int(time.time())+1800,'token_type':'access'},secret,algorithm='HS256')
        headers={'Authorization':'Bearer '+token}; base='http://127.0.0.1:18000/api/v1/scans'
        for category,url in cases:
            accepted=client.post(base+'/url',headers=headers,json={'url':url}); assert accepted.status_code==202,accepted.text
            scan_id=accepted.json()['data']['id']
            for attempt in range(120):
                response=client.get(base+'/'+scan_id,headers=headers); response.raise_for_status(); scan=response.json()['data']
                if scan['status'] not in ('QUEUED','PROCESSING'): break
                time.sleep(.5)
            else: raise TimeoutError(scan_id)
            result=scan['result']
            assert result['scan_id']==scan_id and result['module']=='phishing'
            assert result['model_version']=='hybrid-v1'
            assert result['metadata']['assessment_policy']=='forensics-v1'
            assert result['verdict'] in ('SUSPICIOUS','NO_STRONG_INDICATORS','UNCERTAIN') and result['explanation']
            if result['status']=='UNAVAILABLE':
                assert result['error_code'] in {'MODEL_DISAGREEMENT','UNVALIDATED_COVERAGE','MODEL_UNCORROBORATED','FORENSIC_REVIEW'}
                assert scan['trust_score']['trust_risk_score'] is None
            else:
                assert result['status']=='PARTIAL_SUCCESS'
                assert result['metadata']['assessment_dimensions']['website_verification']['status']=='NOT_VERIFIED'
                assert scan['trust_score']['trust_risk_score']==result['risk_score']
            if url.startswith('https://') and result['status']=='PARTIAL_SUCCESS':
                assert not result['metadata']['confidence_available']
                assert result['metadata']['coverage']['status']=='OUTSIDE_VALIDATED_COVERAGE'
            assert all(a['status']=='APPLIED' for a in result['analyzers'])
            scans.append({'category':category,'scan':scan})
            print(f"{len(scans)}/{len(cases)} {result['verdict']} trust_risk={scan['trust_score']['trust_risk_score']} {url}",flush=True)
        for url in invalid:
            response=client.post(base+'/url',headers=headers,json={'url':url})
            assert response.status_code==422,(url,response.status_code)
            rejections.append({'url':url,'http_status':response.status_code})
    output=root/'models/phishing_url/research'
    report={'seed':42,'functional_test_only':True,'ground_truth_verified':False,'urls_fetched':False,
            'relational_store':'isolated SQLite','valid_cases':len(scans),'invalid_rejected':len(rejections),
            'results':scans,'rejections':rejections}
    stem='forensics_regression' if focus else 'forensics_url_suite'
    (output/(stem+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    lines=['# Phishing URL functional test results','',
           f'{len(cases)} varied addresses and {len(invalid)} invalid inputs. Seed: 42. No URLs fetched. These predictions are not an accuracy benchmark.','',
           '**Policy:** forensic indicators are evaluated alongside model diagnostics. Unsupported v1 HTTPS model scores are withheld. Strong forensic findings use an explicitly uncalibrated severity index, not a phishing probability. This functional suite does not establish accuracy.','',
           '| URL | Verdict | Trust score / 100 (higher = risk) | Confidence | Inference ms |','|---|---|---:|---:|---:|']
    for entry in scans:
        s=entry['scan']; r=s['result']
        confidence=f"{r['confidence']:.1%}" if r['metadata'].get('confidence_available') else 'Unavailable (coverage)'
        score=s['trust_score']['trust_risk_score']
        rendered=f'{score:.1f} ({r["metadata"].get("score_basis")})' if score is not None else 'Unavailable (uncertain)'
        lines.append(f"| `{s['raw_input']}` | {r['metadata']['display_verdict']} | {rendered} | {confidence} | {r['processing_time_ms']} |")
    lines += ['','All 5 malformed/non-HTTP inputs rejected with HTTP 422.',
              'All valid results passed the shared result, explanation, evidence/analysis, coverage, scan-ID and persisted trust-score contract checks.']
    (output/(stem+'.md')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
finally:
    for process in processes:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
    for log in logs: log.close()
