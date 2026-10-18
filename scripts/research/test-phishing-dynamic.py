"""Reproducible URL smoke suite through authenticated Gateway/Kafka/Mongo.

These examples have no verified ground-truth labels: this is functional testing,
not a new accuracy benchmark. Live requests use the protected isolated collector.
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

root=Path(__file__).resolve().parents[2]
scratch=root/'runtime_state/qa'/'phishing-url-suite'; scratch.mkdir(parents=True,exist_ok=True)
secret=secrets.token_hex(32)
environment={**os.environ,'JWT_SECRET_KEY':secret,'ALLOW_MOCK_AUTH':'false','KAFKA_ENABLED':'true',
             'SCAN_COMPLETION_GROUP':'phishing-url-suite-'+uuid.uuid4().hex,
             'KAFKA_BOOTSTRAP_SERVERS':'localhost:9094','SCAN_SERVICE_URL':'http://127.0.0.1:18002',
             'DATABASE_URL':'sqlite+aiosqlite:///'+str(scratch/('scan-'+uuid.uuid4().hex+'.db')).replace('\\','/'),
             'PYTHONPATH':str(root)}
sample=json.loads((root/'models/phishing_url/research/dynamic_web_sample.json').read_text())
cases=[(r['reference_label'],r['url']) for r in sample['cases']]
reference_by_url={r['url']:r for r in sample['cases']}
path_mode='--paths' in sys.argv
if path_mode:
    cases=[('legitimate_official_url',u) for u in ['https://www.google.com/search?q=security','https://github.com/openai','https://docs.python.org/3/','https://en.wikipedia.org/wiki/Phishing']]
    reference_by_url={u:{'url':u,'reference_label':kind,'reference':'official organisation page; not an absolute safety guarantee','urlscan':{'status':'NOT_QUERIED'}} for kind,u in cases}

invalid=[] if path_mode else ['not a url','http:example.com','https://-bad.com','https://example.com:99999','https://']
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
            assert result['model_version']=='modern-v5'
            assert result['metadata']['assessment_policy']=='dynamic-v2'
            assert result['verdict'] in ('SUSPICIOUS','NO_STRONG_INDICATORS','REVIEW_RECOMMENDED') and result['explanation']
            assert result['status']=='PARTIAL_SUCCESS'
            assert result['metadata']['forensics']['network']['status']!='NOT_COLLECTED'
            assert scan['trust_score']['trust_risk_score']==result['risk_score']
            assert 'Frozen' not in result['explanation']
            scans.append({'category':category,'scan':scan})
            print(f"{len(scans)}/{len(cases)} {result['verdict']} trust_risk={scan['trust_score']['trust_risk_score']} {url}",flush=True)
        for url in invalid:
            response=client.post(base+'/url',headers=headers,json={'url':url})
            assert response.status_code==422,(url,response.status_code)
            rejections.append({'url':url,'http_status':response.status_code})
    output=root/'models/phishing_url/research'
    model_counts={'legitimate_false_alerts':0,'reported_phishing_alerts':0,'legitimate_total':0,'reported_phishing_total':0}
    combined_counts=dict(model_counts)
    for entry in scans:
        s=entry['scan'];r=s['result'];ref=reference_by_url[s['raw_input']]
        entry['reference']=ref
        legitimate=entry['category'].startswith('legitimate_')
        model_alert=r['metadata']['diagnostic_model']['probability']>=r['metadata']['threshold']
        combined_alert=r['verdict']=='SUSPICIOUS'
        for counts,alert in [(model_counts,model_alert),(combined_counts,combined_alert)]:
            counts['legitimate_total' if legitimate else 'reported_phishing_total']+=1
            if alert: counts['legitimate_false_alerts' if legitimate else 'reported_phishing_alerts']+=1
    report={'seed':sample['seed'],'sampled_at':sample['sampled_at'],'reference_labels_are_not_definitive_ground_truth':True,
            'websites_fetched_with_protected_collector':True,'model_only_counts':model_counts,'combined_counts':combined_counts,
            'warning':'Combined counts use the same provider as the positive reference labels; not an independent accuracy benchmark.',
            'external_access':{'urlscan':'See per-case observed/no-exact-report/HTTP error status.','virustotal':sample['virustotal']},
            'valid_cases':len(scans),'invalid_rejected':len(rejections),'results':scans,'rejections':rejections}
    (output/('dynamic_url_paths.json' if path_mode else 'dynamic_url_audit.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    lines=['# Dynamic phishing URL audit','',
           f'{len(scans)} source-labelled URLs. Seed 20261016. Live protected collection enabled.',
           'Provider reports may be wrong or stale. Reputation-enriched counts are not independent accuracy, because the positive sample comes from that provider.','',
           'Model-only counts: '+str(model_counts),'Combined counts: '+str(combined_counts),'',
           '| URL (defanged) | Reference | Model estimate | Risk index | Result | Live checks | urlscan comparison |',
           '|---|---|---:|---:|---|---|---|']
    for entry in scans:
        s=entry['scan'];r=s['result'];m=r['metadata'];ref=entry['reference']
        display=s['raw_input'].replace('https://','hxxps://').replace('http://','hxxp://').replace('.','[.]').replace('|','%7C').replace('`','%60')[:220]
        signals=m['forensics']['network'].get('signals',{})
        coverage=', '.join(k for k,v in signals.items() if str(v.get('status','')).lower()=='observed')
        lines.append(f"| {display} | {entry['category']} | {m['diagnostic_model']['probability']:.3f} | {r['risk_score']:.1f} | {r['verdict']} | {coverage} | {ref['urlscan']['status']} |")
    lines += ['',f'{len(rejections)} invalid/non-HTTP inputs rejected with HTTP 422.',
              'Exact source IDs/dates, model scores, observations, provider states and stored shared trust reports are in dynamic_url_audit.json.']
    (output/('dynamic_url_paths.md' if path_mode else 'dynamic_url_audit.md')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'model_only':model_counts,'combined':combined_counts},indent=2),flush=True)

finally:
    for process in processes:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
    for log in logs: log.close()
