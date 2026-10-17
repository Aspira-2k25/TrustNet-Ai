"""Small reproducible sample and read-only external comparisons; no scan submissions."""
import json, random, sys, time
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
import httpx
root = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from models.phishing_url.inference.forensics import canonical_url
out = root/'models/phishing_url/research'
path = out/'dynamic_web_sample.json'
if path.exists():
    print('Existing timestamped sample retained:', path)
    sys.exit(0)
rng = random.Random(20261016)
headers = {'User-Agent': 'TrustNet-Phishing-Audit/2.0 (read-only research)'}
with httpx.Client(timeout=20, headers=headers) as client:
    r = client.get('https://api.phishstats.info/api/phishing', params={'_where':'(score,gt,7)', '_sort':'-date', '_size':100})
    r.raise_for_status()
    items = r.json()
    rng.shuffle(items)
    cases, domains = [], set()
    for item in items:
        try:
            url = canonical_url(item['url'])
            host = urlsplit(url).hostname
            if host in domains: continue
            domains.add(host)
            cases.append({'url':url, 'reference_label':'provider_reported_phishing', 'reference':'PhishStats',
                          'reference_id':item.get('id'), 'reference_date':item.get('date'), 'reference_score':item.get('score')})
        except ValueError:
            continue
        if len(cases) == 8: break
    legitimate = ['https://google.com/','https://www.google.com/','https://wikipedia.org/','https://github.com/',
                  'https://microsoft.com/','https://amazon.in/','https://python.org/','https://bbc.com/',
                  'https://mozilla.org/','https://cloudflare.com/','https://stackoverflow.com/', 'https://ubuntu.com/',
                  'https://w3.org/','https://nasa.gov/','https://who.int/','https://khanacademy.org/','https://gnu.org/','https://kernel.org/']
    selected = ['https://www.google.com/', 'https://github.com/'] + rng.sample([u for u in legitimate if u not in {'https://www.google.com/','https://github.com/'}],6)
    cases += [{'url':u, 'reference_label':'legitimate_official_homepage', 'reference':'official organisation homepage; not a guarantee of current safety'} for u in selected]
    # At most eight searches; a missing, blocked or stale report is not a verdict.
    for index, case in enumerate(cases):
        if index not in {0,1,2,3,8,9,10,11}:
            case['urlscan'] = {'status':'NOT_QUERIED', 'reason':'Small public quota; no bulk mirroring.'}
            continue
        query = 'page.url.keyword:' + json.dumps(case['url'].lower())
        try:
            response = client.get('https://urlscan.io/api/v1/search/', params={'q':query,'size':1})
            if response.status_code != 200:
                case['urlscan'] = {'status':'UNAVAILABLE', 'http_status':response.status_code}
                continue
            hits = response.json().get('results', [])
            hit = next((h for h in hits if any(canonical_url(h.get(part,{}).get('url','')) == canonical_url(case['url']) for part in ('page','task') if h.get(part,{}).get('url'))), None)
            if not hit:
                case['urlscan'] = {'status':'NO_EXACT_REPORT', 'verdict':None}
                continue
            result = client.get(hit['result'])
            if result.status_code != 200:
                case['urlscan'] = {'status':'UNAVAILABLE', 'http_status':result.status_code}
                continue
            data = result.json()
            case['urlscan'] = {'status':'OBSERVED', 'report_url':'https://urlscan.io/result/'+hit['_id']+'/',
                               'scanned_at':data.get('task',{}).get('time'), 'verdict':data.get('verdicts',{}).get('urlscan',{}),
                               'definition':'Existing archived report, not a new scan or definitive ground truth.'}
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            case['urlscan'] = {'status':'UNAVAILABLE','reason':type(exc).__name__}
        time.sleep(.5)
report = {'sampled_at':datetime.now(timezone.utc).isoformat(), 'seed':20261016,
          'ground_truth_note':'Source-labelled sample. Provider reports may contain errors or refer to sites now taken down. Absence from a provider is not a clean verdict.',
          'virustotal':{'status':'NOT_QUERIED','reason':'Requires API credentials or user sign-in; no results fabricated.'},
          'cases':cases}
path.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'cases':len(cases), 'urlscan_statuses':[c['urlscan']['status'] for c in cases]},indent=2))
