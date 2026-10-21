"""Frozen 300/300 public URL-label audit. Never opens evaluated destinations.

Source: Prasad & Chandra, UCI PhiUSIIL (2024), CC BY 4.0.
Official label 1=legitimate, 0=phishing. Historical source labels, not a live guarantee.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
import zipfile
from benchmark.message_candidate import metrics


SOURCE='https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--api',default='http://127.0.0.1:8007');a=p.parse_args()
    root=Path(__file__).resolve().parents[1];out=a.output.resolve()
    if out.is_relative_to(root):raise ValueError('Raw data stays outside runtime repository')
    out.mkdir(parents=True,exist_ok=True)
    import requests
    session=requests.Session();manifest=out/'manifest.json'
    if not manifest.exists():
        archive=out/'source.zip'
        if not archive.exists():
            response=session.get(SOURCE,timeout=60);response.raise_for_status()
            if len(response.content)>40*1024*1024:raise ValueError('Dataset archive exceeds expected bound')
            archive.write_bytes(response.content)
        groups={};conflicts=set()
        with zipfile.ZipFile(archive) as bundle:
            item=next(info for info in bundle.infolist() if info.filename.endswith('.csv'))
            if item.file_size>100*1024*1024:raise ValueError('Unexpected extracted size')
            with bundle.open(item) as raw:
                for row in csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig')):
                    url=row['URL'];host=urlsplit(url).hostname
                    if not host or not url.startswith(('https://','http://')) or len(url)>2048:continue
                    # One hostname per audit, eliminating repeated URLs on the same site.
                    truth=int(row['label'])==0;key=hashlib.sha256(url.encode()).hexdigest()
                    if host in groups and groups[host]['is_scam']!=truth:conflicts.add(host)
                    if host not in groups or key<groups[host]['sha256']:
                        groups[host]={'url':url,'hostname':host,'is_scam':truth,'sha256':key}
        rows=[]
        for truth in (False,True):
            pool=sorted((r for host,r in groups.items() if host not in conflicts and r['is_scam']==truth),key=lambda r:r['sha256'])
            if len(pool)<300:raise ValueError('Not enough distinct source-labelled sites')
            rows.extend(pool[:300])
        document={'source':SOURCE,'citation':'Prasad & Chandra (2024), PhiUSIIL, UCI dataset 967; https://doi.org/10.1016/j.cose.2023.103545',
                  'license':'CC BY 4.0','archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'selection':'One lowest-URL-SHA per hostname; discard conflicting hostname labels; first 300 SHA-sorted per class; no destination fetching.',
                  'limits':['Historical source-labelled legitimate/phishing URLs, not independently re-adjudicated current status.',
                            'Hostname deduplication does not eliminate registered-domain/campaign correlation.',
                            'No known use of this snapshot in current local training; upstream URL corpus overlap cannot be excluded.',
                            'Offline URL model only; no live DNS, TLS or HTML coverage is asserted.'], 'rows':rows}
        manifest.write_text(json.dumps(document,indent=2),encoding='utf-8')
    doc=json.loads(manifest.read_text(encoding='utf-8'))
    cache=out/'predictions.jsonl';done={}
    if cache.exists():
        with cache.open() as stream:done={r['sha256']:r for r in (json.loads(line) for line in stream if line.strip())}
    for row in doc['rows']:
        if row['sha256'] in done:continue
        started=time.monotonic();response=session.post(a.api+'/infer',json={'scan_id':'phiusiil-'+row['sha256'][:16],'url':row['url']},timeout=15);response.raise_for_status();result=response.json()['data']
        available=result['status'] in ('SUCCESS','PARTIAL_SUCCESS');positive=available and result.get('verdict')=='SUSPICIOUS'
        item={'sha256':row['sha256'],'positive':positive,'uncertain':not positive and result.get('verdict')!='NO_STRONG_INDICATORS','verdict':result.get('verdict'),'status':result['status'],'seconds':time.monotonic()-started}
        with cache.open('a') as stream:stream.write(json.dumps(item)+'\n')
        done[row['sha256']]=item
        if len(done)%100==0:print('PHIUSIIL',len(done),'/600',flush=True)
    selected=[done[r['sha256']] for r in doc['rows']]
    report={'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'metrics':metrics([r['is_scam'] for r in doc['rows']],[r['positive'] for r in selected],[r['uncertain'] for r in selected]),
            'p50_seconds':sorted(r['seconds'] for r in selected)[300],'p95_seconds':sorted(r['seconds'] for r in selected)[569],
            'limits':doc['limits'],'model_change':'None. Frozen source diagnostic; not a claim of improvement.'}
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
