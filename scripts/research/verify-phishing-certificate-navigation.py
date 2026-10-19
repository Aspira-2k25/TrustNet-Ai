"""Live collector regression using public transport-security demonstration URLs."""
import json
import sys
from pathlib import Path
from datetime import datetime,timezone
import httpx

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root))
from models.phishing_url.inference.forensics import analyze
token=(root/'runtime_state/phishing/collector-token').read_text().strip()
cases=[('valid_certificate','https://www.google.com/'),
       ('redirect_navigation','http://github.com/'),
       ('expired_certificate','https://expired.badssl.com/'),
       ('hostname_mismatch','https://wrong.host.badssl.com/')]
rows=[]
with httpx.Client(timeout=35) as client:
    for kind,url in cases:
        response=client.post('http://127.0.0.1:8008/collect',json={'url':url,'include_html':True},headers={'x-collector-token':token})
        response.raise_for_status();observation=response.json();signals=observation['signals']
        if kind in {'valid_certificate','redirect_navigation'}:
            cert=signals.get('tls',{}).get('analysis') or {}
            passed=bool(cert.get('chain_validated') and cert.get('hostname_validated') and len(signals.get('navigation',{}).get('hops',[]))>=(2 if kind=='redirect_navigation' else 1))
        else:
            passed=signals.get('tls',{}).get('validated') is False and signals.get('http',{}).get('status')=='unavailable' and 'TLS_VALIDATION_FAILED' in {f['code'] for f in analyze(url,observation)['findings']}
        rows.append({'case':kind,'url':url,'verified':passed,'observations':observation})
        print(kind+(': verified' if passed else ': not established; inspect recorded observation'),flush=True)
(root/'models/phishing_url/research/certificate_navigation_live.json').write_text(json.dumps({'observed_at':datetime.now(timezone.utc).isoformat(),'cases':rows},indent=2),encoding='utf-8')
assert all(row['verified'] for row in rows),'Some live checks were not established; observations have been preserved.'
