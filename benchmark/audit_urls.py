"""Offline-model diagnostic: OpenPhish feed versus Tranco domain references.

Not a verified-benign benchmark or permission to redistribute source data.
Keep all acquired URLs external. Never navigate to an evaluated destination.
"""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark.audit_messages import summarize


def digest(data):return hashlib.sha256(data).hexdigest()


def prepare(out,session):
    path=out/'manifest.json'
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    feed_url='https://raw.githubusercontent.com/openphish/public_feed/refs/heads/main/feed.txt'
    feed=session.get(feed_url,timeout=30);feed.raise_for_status();(out/'openphish-feed.txt').write_bytes(feed.content)
    urls=sorted({line.strip() for line in feed.text.splitlines() if line.startswith(('https://','http://')) and len(line.strip())<=2048},key=lambda s:digest(s.encode()))
    if len(urls)<300:raise ValueError('Feed has fewer than 300 distinct supported URLs; do not fabricate more')
    identity=session.get('https://tranco-list.eu/top-1m-id',timeout=20);identity.raise_for_status()
    archive=session.get('https://tranco-list.eu/top-1m.csv.zip',timeout=30);archive.raise_for_status()
    (out/'tranco-list.zip').write_bytes(archive.content)
    with zipfile.ZipFile(io.BytesIO(archive.content)) as zipped:
        name=next(n for n in zipped.namelist() if n.endswith('.csv'))
        with zipped.open(name) as stream:
            domains=[]
            for line in stream:
                rank,domain=line.decode().strip().split(',',1)
                if int(rank)>1000:break
                domains.append(domain)
    references=sorted(set(domains),key=lambda s:digest(s.encode()))[:300]
    if len(references)!=300:raise ValueError('Incomplete Tranco reference set')
    rows=[{'url':url,'is_scam':True,'source':'OpenPhish','text_sha256':digest(url.encode())} for url in urls[:300]]
    rows.extend({'url':'https://'+domain+'/','is_scam':False,'source':'Tranco-root-domain-reference','text_sha256':digest(('https://'+domain+'/').encode())} for domain in references)
    hosts=Counter(urlsplit(r['url']).hostname for r in rows if r['is_scam'])
    doc={'acquired_utc':datetime.now(timezone.utc).isoformat(),'source_hashes':{'openphish':digest(feed.content),'tranco_zip':digest(archive.content)},'tranco_list_id':identity.text.strip(),'phishing_distinct_hostnames':len(hosts),'largest_phishing_hostname_count':max(hosts.values()),'rows':rows,
         'terms':['OpenPhish personal/academic research terms: https://openphish.com/terms.html. No runtime feed integration, training or redistribution of raw URLs.','Tranco provider attribution/licences: https://tranco-list.eu/. Raw data remains external.'],
         'limits':['Tranco popularity is a weak negative reference, not independently verified legitimacy.','Phishing full URLs versus reference root domains create a URL-shape confound. These are diagnostic source labels, not field accuracy.','Campaign/hostname correlation and unknown upstream training overlap remain.','Offline address/model checks only. No evaluated destination was fetched; TLS/DNS/HTML/JS signals are not measured.']}
    path.write_text(json.dumps(doc,indent=2),encoding='utf-8');return doc


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--api',default='http://127.0.0.1:8007');a=p.parse_args();out=a.output.resolve()
    if out.is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('Keep restricted source data outside runtime repository')
    out.mkdir(parents=True,exist_ok=True)
    import requests
    session=requests.Session();ready=session.get(a.api+'/ready',timeout=5);ready.raise_for_status();doc=prepare(out,session)
    root=Path(__file__).resolve().parents[1]
    code=sorted((root/'models/phishing_url').rglob('*.py'))
    bundles=sorted((root/'models/phishing_url/artifacts').rglob('*manifest*.json'))
    contract={'manifest_sha256':digest((out/'manifest.json').read_bytes()),'runtime_source_sha256':{str(path.relative_to(root)):digest(path.read_bytes()) for path in [*code,*bundles]}}
    contract_path=out/'runtime-contract.json'
    if contract_path.exists() and json.loads(contract_path.read_text())!=contract:raise ValueError('Source model or diagnostic manifest changed; do not reuse cached predictions')
    contract_path.write_text(json.dumps(contract,indent=2))
    cache=out/'predictions.jsonl';done={r['text_sha256']:r for r in map(json.loads,cache.read_text().splitlines())} if cache.exists() else {}
    for row in doc['rows']:
        key=row['text_sha256']
        if key in done:continue
        started=time.monotonic()
        try:
            response=session.post(a.api+'/infer',json={'scan_id':'url-audit-'+key[:16],'url':row['url']},timeout=15);response.raise_for_status();result=response.json()['data'];verdict=result.get('verdict');status=result.get('status')
            # Normalize solely for the shared diagnostic metric function. Keep
            # the actual API verdict/status and model version in each record.
            usable=status in {'SUCCESS','PARTIAL_SUCCESS'}
            item={'text_sha256':key,'api_verdict':verdict,'api_status':status,'model_version':result.get('model_version'),'risk_score':result.get('risk_score'),'seconds':time.monotonic()-started,'verdict':'LIKELY_SCAM' if usable and verdict=='SUSPICIOUS' else 'NO_STRONG_INDICATORS' if usable and verdict=='NO_STRONG_INDICATORS' else 'UNABLE_TO_ASSESS','status':'SUCCESS' if usable else status}
        except (requests.RequestException,KeyError,ValueError) as exc:item={'text_sha256':key,'error':type(exc).__name__,'seconds':time.monotonic()-started}
        with cache.open('a',encoding='utf-8') as stream:stream.write(json.dumps(item)+'\n')
        done[key]=item
        if len(done)%50==0:print('URL DIAGNOSTIC',len(done),'/',len(doc['rows']),flush=True)
        if all(v.get('error') for v in list(done.values())[-3:]) and len(done)>=3:raise RuntimeError('Repeated service failures; inspect rather than continuing')
    metrics=summarize(doc['rows'],done)
    metrics['reference_false_warning_rate']=metrics.pop('normal_false_warning_rate')
    report={'source_manifest_sha256':digest((out/'manifest.json').read_bytes()),'metrics':metrics,'models':sorted({v.get('model_version') for v in done.values() if v.get('model_version')}),'source_host_count':doc['phishing_distinct_hostnames'],'limits':doc['limits'],'promotion':'Diagnostic only. No model or decision threshold changed.'}
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
