"""Add verified benign query coverage before any independent predictions."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import csv
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import urljoin,urlsplit,parse_qsl

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('reservation',ROOT/'scripts/research/reserve-phishing-recall-test.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
from models.phishing_url.inference.navigation import inspect_path
OLD=r.OUT;OUT=ROOT/'models/phishing_url/data/recall_independent_20261018_v2'


def main():
    if (OUT/'manifest.json').exists():raise SystemExit('Completed reservation is immutable')
    if (OLD/'sealed_test/consumption.json').exists():raise ValueError('Cannot revise an evaluated test')
    parent=json.loads((OLD/'manifest.json').read_text())
    if r.sha(OLD/'sealed_test/url_labels.csv')!=parent['url_labels_sha256'] or r.sha(OLD/'sealed_test/provenance.jsonl')!=parent['provenance_sha256']:
        raise ValueError('Parent reservation changed')
    records=[json.loads(line) for line in (OLD/'sealed_test/provenance.jsonl').read_text().splitlines()]
    domains={x['domain'] for x in records if x['label']==0};exclusions=json.loads((OLD/'exclusions.json').read_text());known_campaigns=set(exclusions['campaigns'])
    OUT.mkdir(parents=True,exist_ok=True)
    origins=json.loads((ROOT/'models/phishing_url/configs/recall_reference_sources.json').read_text())['origins']
    origins=[u for u in origins if r.normalize(u)[2] in domains]
    def collect(origin):
        path=OUT/'raw/official_query'/(hashlib.sha256(origin.encode()).hexdigest()[:20]+'.json')
        if path.exists():return json.loads(path.read_text())
        result={'origin':origin,'rows':[]}
        try:
            operator=r.normalize(origin)[2];response=r.c.official_get(origin,operator)
            parser=r.c.Links();parser.feed(response['body'].decode('utf-8',errors='replace'));links=set()
            for href in parser.links:
                try:
                    url,_,domain=r.normalize(urljoin(response['final_url'],href));p=urlsplit(url)
                    if domain!=operator or not p.query or p.fragment or r.private_or_tokenized(url):continue
                    if re.search(r'/(?:users?|profile|community|discuss|forum|issues|pull|gist)/',p.path,re.I):continue
                    if any('@' in value for _,value in parse_qsl(p.query)):continue
                    if any(key in p.query.lower() for key in ('ifkv=','dsh=','samlresponse=')):continue
                    if any(t['external_hostname'] for t in inspect_path(url)['navigation_parameters']):continue
                    if r.campaign_signature(url) in known_campaigns:continue
                    links.add(url)
                except ValueError:pass
            for url in sorted(links,key=lambda u:hashlib.sha256(u.encode()).hexdigest())[:4]:
                try:
                    observed=r.c.official_get(url,operator)
                    normalized,_,domain=r.normalize(observed['final_url'])
                    if not urlsplit(normalized).query:continue
                    result['rows'].append({'url':normalized,'label':0,'domain':domain,'campaign':r.campaign_signature(normalized),
                        'source':origin,'collected_at':datetime.now(timezone.utc).isoformat(),
                        'evidence':{'basis':'curated_operator_reference_verified_tls_http200_query_link',**{k:v for k,v in observed.items() if k!='body'}}})
                except Exception:pass
        except Exception as exc:result['error_type']=type(exc).__name__
        r.save(path,result);return result
    added=[];seen={r.normalize(x['url'])[1] for x in records};per_domain={}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(collect,u) for u in origins]):
            result=f.result()
            for row in result['rows']:
                wire=r.normalize(row['url'])[1];d=row['domain']
                if wire in seen or per_domain.get(d,0)>=3:continue
                seen.add(wire);per_domain[d]=per_domain.get(d,0)+1;added.append(row)
            r.log('query_reference',origin=result['origin'],rows=len(result['rows']))
    records+=sorted(added,key=lambda x:hashlib.sha256(x['url'].encode()).hexdigest())
    test=OUT/'sealed_test';test.mkdir(exist_ok=True)
    with (test/'url_labels.csv').open('x',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['url','label']);writer.writerows((x['url'],x['label']) for x in records)
    with (test/'provenance.jsonl').open('x',encoding='utf-8') as f:
        for x in records:f.write(json.dumps(x)+'\n')
    manifest={**parent,'created_at':datetime.now(timezone.utc).isoformat(),
              'parent_manifest_sha256':r.sha(OLD/'manifest.json'),'parent_status':'Superseded before any predictions; parent inputs unchanged.',
              'counts':{str(y):sum(x['label']==y for x in records) for y in (0,1)},
              'url_labels_sha256':r.sha(test/'url_labels.csv'),'provenance_sha256':r.sha(test/'provenance.jsonl'),
              'added_verified_query_references':len(added),'query_reference_domains':len(per_domain),
              'query_coverage_limited':len(added)<15 or len(per_domain)<5,'status':'sealed_unscored','model_predictions_generated':0}
    r.save(OUT/'manifest.json',manifest)
    r.save(ROOT/'models/phishing_url/research/recall_test_reservation_v2_20261018.json',manifest)
    r.log('recall_test_v2_reserved',counts=manifest['counts'],query_negatives=len(added),query_domains=len(per_domain))


if __name__=='__main__':main()
