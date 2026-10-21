"""Verify real message/URL integration, auth, history and ownership in QA state.

Run with .venv while scam/phishing are ready. Add --kafka for the worker path.
No user database or mailbox is used. Logs remain in ignored runtime_state/qa.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import uuid

import httpx

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kafka', action='store_true')
    parser.add_argument('--inspect', action='store_true', help='Request and persist one live website inspection')
    parser.add_argument('--require-live', action='store_true', help='Require live observations, rather than an explicit unavailable result')
    parser.add_argument('--image', action='store_true',help='Verify real image service, saved original/evidence and owner access')
    args = parser.parse_args()
    for port in (18000, 18001, 18002):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise SystemExit(f'QA port {port} is occupied; preserving its process.')
    state = ROOT / 'runtime_state/qa' / uuid.uuid4().hex
    state.mkdir(parents=True)
    environment = {
        **os.environ, 'JWT_SECRET_KEY': secrets.token_urlsafe(48),
        'ALLOW_MOCK_AUTH': 'false', 'ENVIRONMENT': 'test',
        'KAFKA_ENABLED': str(args.kafka).lower(),
        'KAFKA_BOOTSTRAP_SERVERS': 'localhost:9094',
        'SCAN_COMPLETION_GROUP': 'qa-' + uuid.uuid4().hex,
        'DATABASE_URL': 'sqlite+aiosqlite:///' + (state / 'qa.db').as_posix(),
        'STORAGE_DIR': str(state / 'uploads'),
        'SCAN_SERVICE_URL': 'http://127.0.0.1:18002',
        'AUTH_SERVICE_URL': 'http://127.0.0.1:18001',
        'SCAM_SERVICE_URL': os.getenv('SCAM_SERVICE_URL','http://127.0.0.1:8005'),
        'PHISHING_SERVICE_URL': os.getenv('PHISHING_SERVICE_URL','http://127.0.0.1:8007'),
        'IMAGE_SERVICE_URL':os.getenv('IMAGE_SERVICE_URL','http://127.0.0.1:8003'), 'PYTHONPATH': str(ROOT),
    }
    processes, logs = [], []
    try:
        for name, module, port in (
            ('auth', 'services.auth.app.main:app', 18001),
            ('scan', 'services.scan_management.app.main:app', 18002),
            ('gateway', 'gateway.app.main:app', 18000),
        ):
            log = (state / f'{name}.log').open('w', encoding='utf-8')
            logs.append(log)
            processes.append(subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', module, '--host', '127.0.0.1', '--port', str(port)],
                cwd=ROOT, env=environment, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            ))
        with httpx.Client(timeout=45, trust_env=False) as client:
            deadline = time.monotonic() + 45
            for port in (18001, 18002, 18000):
                while True:
                    if any(p.poll() is not None for p in processes):
                        raise RuntimeError(f'QA service exited; inspect {state}')
                    try:
                        if client.get(f'http://127.0.0.1:{port}/health', timeout=2).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    if time.monotonic() >= deadline:
                        raise TimeoutError('QA service readiness failed')
                    time.sleep(.25)
            ready = client.get(environment['PHISHING_SERVICE_URL']+'/ready')
            ready.raise_for_status()
            assert ready.json()['ready'] is True
            expected_model = os.getenv('PHISHING_EXPECTED_MODEL_VERSION', 'regional-recall-v1')
            client.get(environment['SCAM_SERVICE_URL']+'/ready').raise_for_status()
            base = 'http://127.0.0.1:18000/api/v1'
            assert client.get(base + '/scans').status_code == 401

            def register():
                response = client.post(base + '/auth/register', json={
                    'email': 'qa-' + uuid.uuid4().hex + '@example.com',
                    'password': secrets.token_urlsafe(24), 'role': 'admin',
                })
                assert response.status_code == 201, response.text
                account = response.json()['data']
                assert account['role'] == 'user'
                return {'Authorization': 'Bearer ' + account['access_token']}

            owner, other = register(), register()
            scans = []
            for payload in (
                {'text': 'Your appointment is confirmed for tomorrow at 10 AM.'},
                {'text': 'Your appointment is confirmed. View the receipt at https://example.com/.'},
                {'message_type': 'email', 'text_format': 'html',
                 'text': '<p>Review your receipt.</p><a href="https://example.com/receipt">Open receipt</a>',
                 'displayed_links': [{'text': 'Open receipt', 'href': 'https://example.com/receipt'}]},
            ):
                response = client.post(base + '/scans/scam/analyze', headers=owner, json=payload)
                assert response.status_code == 200, response.text
                scan = response.json()['data']
                result = scan['result']
                assert result['status'] in ('SUCCESS', 'PARTIAL_SUCCESS')
                fusion = result['metadata']['fusion']
                assert fusion['policy'] == 'message-url-max-v1'
                if fusion['links_found']:
                    assert fusion['links_assessed'] == 1
                    assert result['metadata']['links'][0]['model_version'] == expected_model
                    assert result['risk_score'] == max(fusion['message_score'], fusion['url_score'])
                    assert not fusion['calibrated'] and result['confidence'] == 0
                else:
                    assert fusion['status'] == 'NO_LINKS'
                saved = client.get(base + '/scans/' + scan['id'], headers=owner)
                assert saved.status_code == 200
                assert saved.json()['data']['result'] == result
                assert client.get(base + '/scans/' + scan['id'], headers=other).status_code == 403
                scans.append(scan['id'])
            inspection_state = 'not requested'
            if args.image:
                import io,hashlib
                from PIL import Image
                buffer=io.BytesIO();Image.new('RGB',(300,300),(85,120,145)).save(buffer,'JPEG',quality=90)
                original=buffer.getvalue()
                image_response=client.post(base+'/scans/analyze',headers=owner,
                    files={'file':('qa-photo-fixture.jpg',original,'image/jpeg')},data={'enable_explanation':'true'},timeout=140)
                assert image_response.status_code==200,image_response.text
                image_scan=image_response.json()['data'];identifier=image_scan['id']
                analysis=image_scan['result']['metadata']['image_analysis']
                assert image_scan['result']['status']=='SUCCESS'
                assert analysis['source_sha256']==hashlib.sha256(original).hexdigest()
                assert analysis['supporting_forensics']['affects_verdict'] is False
                assert analysis['supporting_forensics']['ela']['status']=='APPLIED'
                assert analysis['model_attention']['view_width']>0
                assert {'ela','attention'}.issubset(analysis['assets'])
                for kind in ['original',*analysis['assets']]:
                    path=base+'/scans/'+identifier+'/image/'+kind
                    asset=client.get(path,headers=owner);assert asset.status_code==200
                    if kind=='original':assert asset.content==original
                    assert client.get(path,headers=other).status_code in [403,404]
                    assert client.get(path).status_code==401
                saved=client.get(base+'/scans/'+identifier,headers=owner)
                assert saved.status_code==200 and saved.json()['data']['result']==image_scan['result']
                scans.append(identifier)
            if args.inspect or args.require_live:
                inspection_path = base + '/scans/' + scans[1] + '/links/0/inspection'
                assert client.post(inspection_path, headers=other, json={}).status_code == 403
                before = client.get(base + '/scans/' + scans[1], headers=owner).json()['data']['result']
                inspected = client.post(inspection_path, headers=owner, json={})
                assert inspected.status_code == 200, inspected.text
                after = inspected.json()['data']['result']
                snapshot = after['metadata']['links'][0]['inspection']
                inspection_state = snapshot['status']
                assert after['risk_score'] == before['risk_score']
                assert after['metadata']['fusion'] == before['metadata']['fusion']
                assert snapshot['status'] in ('COMPLETED', 'UNAVAILABLE')
                if args.require_live:
                    assert snapshot['status'] == 'COMPLETED', snapshot.get('reason')
                    assert snapshot['summary']['live_checks_observed'] > 0
                saved = client.get(base + '/scans/' + scans[1], headers=owner).json()['data']['result']
                assert saved['metadata']['links'][0]['inspection'] == snapshot
            response = client.post(base + '/scans/url', headers=owner, json={'url': 'https://example.com/'})
            assert response.status_code == 202, response.text
            url_scan = response.json()['data']
            deadline = time.monotonic() + 60
            while url_scan['status'] in ('QUEUED', 'PROCESSING'):
                if time.monotonic() >= deadline:
                    raise TimeoutError('Phishing worker did not complete the queued scan')
                time.sleep(.5)
                response = client.get(base + '/scans/' + url_scan['id'], headers=owner)
                response.raise_for_status()
                url_scan = response.json()['data']
            assert url_scan['result']['status'] in ('SUCCESS', 'PARTIAL_SUCCESS')
            assert url_scan['result']['model_version'] == expected_model
            assert url_scan['trust_score']['module_scores']['phishing'] == url_scan['result']['risk_score']
            history = client.get(base + '/scans', headers=owner).json()['data']['scans']
            assert set(scans + [url_scan['id']]).issubset({s['id'] for s in history})
            report = {
                'result': 'PASS', 'real_registration_and_authentication': True,
                'real_message_and_link_models': True, 'plain_text_and_html_email': True,
                'history_persistence': True, 'owner_isolation': True,
                'public_role_escalation_rejected': True,
                'standalone_url_path': 'Kafka worker' if args.kafka else 'HTTP fallback',
                'phishing_model': expected_model, 'user_databases_used': False,
                'website_inspection': inspection_state,
                'real_image_private_evidence':args.image,
                'scope': 'Integration smoke, not accuracy or live Gmail verification',
            }
            (state / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps(report, indent=2))
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        for log in logs:
            log.close()


if __name__ == '__main__':
    main()
