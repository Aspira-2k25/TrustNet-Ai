"""Collect label evidence without visiting provider-reported phishing URLs.

Only fixed provider feeds and curated public operator pages are fetched. Official
pages use public-address pinning, verified TLS, bounded reads and operator-scoped
redirects. No forms, JavaScript, credentials or logged-in sessions are used.
"""
import argparse
import bz2
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urljoin,urlsplit

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import httpx
from models.phishing_url.datasets.targeted import normalize,registered_domain,tags,private_or_tokenized
from services.phishing_url.app.services.safe_fetch import public_addresses,PinnedHTTPSConnection

OUT=ROOT/'models/phishing_url/data/targeted_20261018_v1'
CONFIG=ROOT/'models/phishing_url/configs/targeted_dataset_sources.json'

def now():return datetime.now(timezone.utc).isoformat()
def sha(body):return hashlib.sha256(body).hexdigest()
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2),encoding='utf-8')
def log(stage,**values):print(json.dumps({'stage':stage,**values}),flush=True)


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.password_inputs=0
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a' and attrs.get('href'):self.links.append(attrs['href'])
        if tag=='input' and attrs.get('type','').lower()=='password':self.password_inputs+=1


def official_get(url,operator,max_bytes=400000):
    deadline=time.monotonic()+10;hops=[]
    for _ in range(4):
        normalized,_,group=normalize(url);p=urlsplit(normalized)
        if p.scheme!='https' or p.port not in (None,443) or group!=operator or private_or_tokenized(url):
            raise ValueError('Nonpublic, tokenized or out-of-operator request disallowed')
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('Official collection deadline')
        addresses=public_addresses(p.hostname,443)
        connection=PinnedHTTPSConnection(p.hostname,addresses[0],443,remaining)
        try:
            connection.request('GET',(p.path or '/')+('?'+p.query if p.query else ''),headers={'Host':p.hostname,'User-Agent':'TrustNet-Academic-Dataset/1.0','Accept-Encoding':'identity','Connection':'close'})
            certificate=connection.sock.getpeercert(binary_form=True)
            response=connection.getresponse();hops.append({'url':normalized,'status':response.status})
            if response.status in {301,302,303,307,308}:
                target=response.getheader('Location')
                if not target:raise ValueError('Redirect without destination')
                url=urljoin(normalized,target);continue
            if response.status!=200:raise ValueError('HTTP '+str(response.status))
            if response.getheader('Content-Encoding','identity').lower()!='identity':raise ValueError('Encoded response unsupported')
            content_type=response.getheader('Content-Type','')
            if 'html' not in content_type.lower():raise ValueError('Not a public HTML reference page')
            body=bytearray()
            while len(body)<=max_bytes:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('Read deadline')
                if connection.sock:connection.sock.settimeout(remaining)
                chunk=response.read1(min(8192,max_bytes+1-len(body)))
                if not chunk:break
                body.extend(chunk)
            return {'final_url':normalized,'http_status':200,'tls_validated':True,'certificate_sha256':sha(certificate),
                    'body_sha256':sha(body[:max_bytes]),'body_truncated':len(body)>max_bytes,'hops':hops,'body':bytes(body[:max_bytes])}
        finally:connection.close()
    raise ValueError('Official redirect limit')


def official_source(origin,config):
    cache=OUT/'raw/official'/ (sha(origin.encode())[:20]+'.json')
    if cache.exists():return json.loads(cache.read_text())
    result={'source':origin,'collected_at':now(),'rows':[],'review':[]}
    try:
        operator=normalize(origin)[2];response=official_get(origin,operator)
        parser=Links();parser.feed(response['body'].decode('utf-8',errors='replace'))
        candidates={response['final_url']:origin}
        per_kind={}
        for href in parser.links:
            target=urljoin(response['final_url'],href)
            try:
                normalized,_,group=normalize(target)
                if group!=operator or private_or_tokenized(normalized):continue
                p=urlsplit(normalized)
                # Exclude user-content routes and outbound navigation parameters.
                if re.search(r'/(?:users?|profile|community|discuss|forum|issues|pull|gist|status)/',p.path,re.I):continue
                if 'navigation_parameter' in tags(normalized):continue
                category='auth' if 'authentication_account_payment' in tags(normalized) else 'long' if len(p.path)>=30 else 'other'
                if per_kind.get(category,0)>=config['per_category_limit']:continue
                if category=='other' and p.path not in ('','/'):continue
                candidates.setdefault(normalized,response['final_url']);per_kind[category]=per_kind.get(category,0)+1
            except ValueError:continue
        chosen=sorted(candidates,key=lambda u:(0 if 'authentication_account_payment' in tags(u) else 1 if len(urlsplit(u).path)>=30 else 2,sha(u.encode())))[:config['per_origin_limit']]
        # Verify both requested and final page. Unverified links stay in review,
        # never becoming an automatic zero label merely because they were linked.
        requested=[response['final_url']]+[u for u in chosen if u!=response['final_url']][:config['verify_links_per_origin']]
        for target in requested:
            try:
                observed=response if target==response['final_url'] else official_get(target,operator)
                page=Links();page.feed(observed['body'].decode('utf-8',errors='replace'))
                evidence={k:v for k,v in observed.items() if k!='body'}
                for url in {target,observed['final_url']}:
                    result['rows'].append({'url':url,'label':0,'source':'curated_official_page','source_url':origin,
                        'collected_at':result['collected_at'],'verified_at':now(),'label_basis':'curated_operator_reference_with_observed_link_and_verified_tls_http200',
                        'label_quality':'reference_negative_not_independently_adjudicated','evidence':{**evidence,'discovered_on':candidates.get(target,origin),'password_inputs_in_inspected_html':page.password_inputs}})
            except Exception as exc:result['review'].append({'url':target,'reason':type(exc).__name__+': '+str(exc)[:160]})
        for target in chosen:
            if target not in requested:result['review'].append({'url':target,'reason':'discovered_but_not_live_verified'})
        result['status']='collected'
    except Exception as exc:result.update(status='unavailable',reason=type(exc).__name__+': '+str(exc)[:160])
    save(cache,result);return result


def provider_get(client,url,params=None,max_bytes=16000000):
    with client.stream('GET',url,params=params) as response:
        response.raise_for_status();body=bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body)>max_bytes:raise ValueError('Provider response size limit')
        return bytes(body),{'etag':response.headers.get('etag'),'last_modified':response.headers.get('last-modified'),'http_status':response.status_code}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--supplement',action='store_true');args=parser.parse_args()
    if args.supplement:
        return supplement()
    if (OUT/'collection_manifest.json').exists():raise SystemExit('Collection frozen; use a new dataset version')
    OUT.mkdir(parents=True,exist_ok=True);rows=[];reviews=[];events=[]
    phishtank=OUT/'raw/phishtank.json'
    with httpx.Client(timeout=30,headers={'User-Agent':'phishtank/TrustNetAcademicResearch'},follow_redirects=False) as client:
        if not phishtank.exists():
            try:
                raw,headers=provider_get(client,'https://data.phishtank.com/data/online-valid.json.bz2')
                decoder=bz2.BZ2Decompressor();body=decoder.decompress(raw,max_length=64000000)
                if not decoder.eof:raise ValueError('Feed decompression limit or incomplete stream')
                data=json.loads(body)
                if not isinstance(data,list):raise ValueError('Unexpected feed schema')
                save(phishtank,{'collected_at':now(),'rows':data,'http':headers,'sha256':sha(raw)})
            except Exception as exc:events.append({'source':'PhishTank','status':'unavailable','reason':type(exc).__name__+': '+str(exc)[:160]})
        if phishtank.exists():
            payload=json.loads(phishtank.read_text())
            for item in payload['rows']:
                if str(item.get('verified')).lower()!='yes' or str(item.get('online')).lower()!='yes':continue
                rows.append({'url':item.get('url'),'label':1,'source':'phishtank_verified_online','source_url':'https://phishtank.org/developer_info.php',
                    'collected_at':payload['collected_at'],'verified_at':item.get('verification_time'),'label_basis':'provider_community_verified_online_record',
                    'label_quality':'provider_verified_not_independently_adjudicated','evidence':{'report_id':item.get('phish_id'),'submitted_at':item.get('submission_time'),'target':item.get('target')}})
            events.append({'source':'PhishTank','status':'collected','rows':len(rows),'sha256':payload['sha256']})
        # Eight paginated requests at most; preserve quota for ordinary module use.
        # These reports are a separate label tier and never used as negative labels.
        for page in range(1,9):
            path=OUT/'raw'/('phishstats-'+str(page)+'.json')
            try:
                if path.exists():payload=json.loads(path.read_text())
                else:
                    raw,headers=provider_get(client,'https://api.phishstats.info/api/phishing',params={'_size':100,'_p':page,'_sort':'-date','_where':'(score,gt,6.9)'})
                    items=json.loads(raw)
                    if not isinstance(items,list):raise ValueError('Unexpected PhishStats schema')
                    payload={'collected_at':now(),'rows':items,'http':headers,'sha256':sha(raw)};save(path,payload)
                for item in payload['rows']:
                    if float(item.get('score',0))<7:continue
                    rows.append({'url':item.get('url'),'label':1,'source':'phishstats_report','source_url':'https://phishstats.info/api-docs',
                        'collected_at':payload['collected_at'],'verified_at':item.get('date'),'label_basis':'provider_report_score_at_least_7',
                        'label_quality':'provider_report_not_independently_adjudicated','evidence':{'report_id':item.get('id'),'provider_score':item.get('score')}})
                events.append({'source':'PhishStats','page':page,'status':'collected','rows':len(payload['rows']),'sha256':payload['sha256']})
                if len(payload['rows'])<100:break
            except Exception as exc:
                events.append({'source':'PhishStats','page':page,'status':'unavailable','reason':type(exc).__name__+': '+str(exc)[:160]});break
        log('provider_collection',positive_records=len(rows),sources=[{'source':e['source'],'status':e['status']} for e in events])
    config=json.loads(CONFIG.read_text())
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(official_source,origin,config):origin for origin in config['origins']}
        for future in as_completed(futures):
            result=future.result();rows.extend(result['rows']);reviews.extend(result['review'])
            events.append({k:v for k,v in result.items() if k not in {'rows','review'}})
            log('official_reference',origin=result['source'],status=result['status'],verified_rows=len(result['rows']))
    path=OUT/'new_evidence.jsonl'
    with path.open('w',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=True)+'\n')
    with (OUT/'collection_review.jsonl').open('w',encoding='utf-8') as f:
        for row in reviews:f.write(json.dumps(row,ensure_ascii=True)+'\n')
    manifest={'collected_at':now(),'rows':len(rows),'classes':{str(y):sum(r['label']==y for r in rows) for y in (0,1)},'sources':events,
              'source_configuration_sha256':sha(CONFIG.read_bytes()),'new_evidence_sha256':sha(path.read_bytes()),
              'positive_urls_visited':0,'label_predictions_used':False,'limitations':['Reference and provider labels are evidence tiers, not infallible truth.','Provider outages and blocked official pages are recorded, never replaced with invented labels.']}
    save(OUT/'collection_manifest.json',manifest)
    log('collection_frozen',rows=len(rows),classes=manifest['classes'])

def supplement():
    if not (OUT/'collection_manifest.json').exists():raise SystemExit('Collect the initial batch first')
    if (OUT/'supplemental_manifest.json').exists():raise SystemExit('Supplement is already frozen')
    if (OUT/'dataset_manifest.json').exists():raise SystemExit('Never alter evidence after dataset reservation/export')
    configuration=ROOT/'models/phishing_url/configs/targeted_dataset_supplemental_sources.json'
    config=json.loads(configuration.read_text());rows=[];review=[];events=[]
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(official_source,origin,config):origin for origin in config['origins']}
        for future in as_completed(futures):
            result=future.result();rows.extend(result['rows']);review.extend(result['review'])
            events.append({k:v for k,v in result.items() if k not in {'rows','review'}})
            log('supplemental_reference',origin=result['source'],status=result['status'],verified_rows=len(result['rows']))
    path=OUT/'supplemental_evidence.jsonl'
    with path.open('w',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=True)+'\n')
    with (OUT/'supplemental_review.jsonl').open('w',encoding='utf-8') as f:
        for row in review:f.write(json.dumps(row,ensure_ascii=True)+'\n')
    save(OUT/'supplemental_manifest.json',{'collected_at':now(),'rows':len(rows),'source_configuration_sha256':sha(configuration.read_bytes()),
                                        'new_evidence_sha256':sha(path.read_bytes()),'sources':events,'positive_urls_visited':0})
    log('supplement_frozen',rows=len(rows))

if __name__=='__main__':main()
