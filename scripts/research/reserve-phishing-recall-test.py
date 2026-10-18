"""Reserve a new domain/campaign-separated test without model predictions.

Provider pages are never visited. Only fixed feeds and curated reference pages
are fetched. Feed labels/reference evidence remain explicitly uncertain.
"""
import csv
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from urllib.parse import urljoin,urlsplit
import zipfile

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import httpx
from models.phishing_url.datasets.targeted import normalize,registered_domain,campaign_signature,private_or_tokenized
spec=importlib.util.spec_from_file_location('reference_collection',ROOT/'scripts/research/collect-targeted-phishing-data.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
OUT=ROOT/'models/phishing_url/data/recall_independent_20261018_v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2),encoding='utf-8')
def log(stage,**kw):print(json.dumps({'stage':stage,**kw}),flush=True)


def main():
    if (OUT/'manifest.json').exists():raise SystemExit('Reservation is immutable; use a new version')
    OUT.mkdir(parents=True,exist_ok=True)
    known=set();campaigns=set()
    def exclude(url):
        try:
            p=urlsplit(url);host=(p.hostname or '').encode('idna').decode('ascii').lower().rstrip('.')
            if not host:return
            known.add(registered_domain(host))
            sig=campaign_signature(url)
            if sig:campaigns.add(sig)
        except (ValueError,UnicodeError):pass
    cache=OUT/'exclusions.json'
    if cache.exists():
        previous=json.loads(cache.read_text());known.update(previous['domains']);campaigns.update(previous['campaigns'])
    else:
        log('scan_historical_sources')
        with (ROOT/'models/phishing_url/data/primary/prepared/prepared.csv').open(encoding='utf-8') as f:
            for r in csv.DictReader(f):exclude(r['url'])
        with zipfile.ZipFile(ROOT/'models/phishing_url/data/phiusiil/source.zip') as z:
            with io.TextIOWrapper(z.open('PhiUSIIL_Phishing_URL_Dataset.csv'),encoding='utf-8-sig') as f:
                for r in csv.DictReader(f):exclude(r['URL'])
        for path in (ROOT/'models/phishing_url/data/targeted_20261018_v2').rglob('*.csv'):
            with path.open(encoding='utf-8') as f:
                for r in csv.DictReader(f):
                    if r.get('url'):exclude(r['url'])
        path=ROOT/'models/phishing_url/data/improvement_20261018/fresh_holdout_v2/holdout.csv'
        with path.open(encoding='utf-8') as f:
            for r in csv.DictReader(f):exclude(r['url'])
        # Any later revision must also exclude this round's reserved/evaluated
        # domains and the rest of its feed snapshot, not recycle it as fresh.
        for prior in (ROOT/'models/phishing_url/data').glob('recall_independent_*'):
            if prior.resolve()==OUT.resolve():continue
            prior_test=prior/'sealed_test/url_labels.csv'
            if prior_test.exists():
                with prior_test.open(encoding='utf-8') as f:
                    for row in csv.DictReader(f):exclude(row['url'])
            prior_feed=prior/'raw/openphish.txt'
            if prior_feed.exists():
                for line in prior_feed.read_text(encoding='utf-8').splitlines():
                    if line.startswith(('http://','https://')):exclude(line.strip())
        for name in ('targeted_dataset_sources.json','targeted_dataset_supplemental_sources.json'):
            for origin in json.loads((ROOT/'models/phishing_url/configs'/name).read_text())['origins']:exclude(origin)
        save(cache,{'domains':sorted(known),'campaigns':sorted(campaigns),'role':'All historical raw-source and previously evaluated domains/campaigns; not features'})
    log('exclusions_ready',domains=len(known),campaigns=len(campaigns))
    records={};conflicts=set();events=[];now=datetime.now(timezone.utc).isoformat()
    def add(url,label,source,evidence):
        try:
            normalized,wire,domain=normalize(url)
            if domain in known or private_or_tokenized(normalized):return
            if any(key in urlsplit(normalized).query.lower() for key in ('ifkv=','dsh=','samlresponse=','access_token=')):return
            sig=campaign_signature(normalized)
            if sig and sig in campaigns:return
            if wire in records and records[wire]['label']!=label:conflicts.add(wire);return
            records.setdefault(wire,{'url':normalized,'label':label,'domain':domain,'campaign':sig,'source':source,'collected_at':now,'evidence':evidence})
        except (ValueError,UnicodeError):return
    feeds=[('openphish','https://raw.githubusercontent.com/openphish/public_feed/refs/heads/main/feed.txt'),
           ('phishing_database','https://raw.githubusercontent.com/Phishing-Database/Phishing.Database/master/phishing-links-ACTIVE-NOW.txt')]
    with httpx.Client(timeout=httpx.Timeout(20,connect=5),follow_redirects=False,headers={'User-Agent':'TrustNet-Academic-Research/1.0'}) as client:
        for name,url in feeds:
            path=OUT/'raw'/(name+'.txt');path.parent.mkdir(exist_ok=True)
            try:
                if not path.exists():
                    with client.stream('GET',url) as response:
                        response.raise_for_status();body=bytearray()
                        for chunk in response.iter_bytes():
                            body.extend(chunk)
                            if len(body)>32_000_000:raise ValueError('Feed size bound exceeded')
                    path.write_bytes(body)
                count=0
                for line in path.read_text(encoding='utf-8').splitlines():
                    line=line.strip()
                    if line.startswith(('http://','https://')):
                        add(line,1,name,{'basis':'provider_report_not_independent_adjudication','feed_url':url,'feed_sha256':sha(path) if count==0 else None});count+=1
                events.append({'provider':name,'url':url,'sha256':sha(path),'status':'collected','provider_rows':count})
            except Exception as exc:events.append({'provider':name,'status':'unavailable','error_type':type(exc).__name__})
            log('feed_collected',provider=name,eligible=len(records))
        license_path=OUT/'raw/phishing_database_LICENSE'
        if not license_path.exists():
            response=client.get('https://raw.githubusercontent.com/Phishing-Database/Phishing.Database/master/LICENSE')
            response.raise_for_status();license_path.write_bytes(response.content)
    origins=json.loads((ROOT/'models/phishing_url/configs/recall_reference_sources.json').read_text())['origins']
    origins=[u for u in origins if normalize(u)[2] not in known]
    def reference(origin):
        path=OUT/'raw/official'/(hashlib.sha256(origin.encode()).hexdigest()[:20]+'.json')
        if path.exists():return json.loads(path.read_text())
        result={'origin':origin,'rows':[]}
        try:
            operator=normalize(origin)[2];response=c.official_get(origin,operator);parser=c.Links();parser.feed(response['body'].decode('utf-8',errors='replace'))
            links={response['final_url']}
            for href in parser.links:
                try:
                    url,_,domain=normalize(urljoin(response['final_url'],href));p=urlsplit(url)
                    if domain==operator and not p.query and not p.fragment and not private_or_tokenized(url):links.add(url)
                except ValueError:pass
            chosen=[response['final_url']]+[u for u in sorted(links,key=lambda x:hashlib.sha256(x.encode()).hexdigest()) if u!=response['final_url']][:4]
            for target in chosen:
                try:
                    observed=response if target==response['final_url'] else c.official_get(target,operator)
                    result['rows'].append({'url':observed['final_url'],'evidence':{k:v for k,v in observed.items() if k!='body'}})
                except Exception:pass
        except Exception as exc:result['error_type']=type(exc).__name__
        save(path,result);return result
    log('reference_collection',novel_origins=len(origins))
    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(reference,u) for u in origins]):
            result=future.result()
            for row in result['rows']:add(row['url'],0,result['origin'],{'basis':'curated_operator_reference_verified_tls_http200',**row['evidence']})
            log('reference_collected',origin=result['origin'],rows=len(result['rows']))
    for wire in conflicts:records.pop(wire,None)
    selected=[];counts={};domain_counts={0:{},1:{}};seen_campaigns=set()
    # Freeze deterministically without consulting any model outcome.
    for row in sorted(records.values(),key=lambda r:hashlib.sha256(('recall-test:'+r['url']).encode()).hexdigest()):
        y=row['label'];d=row['domain'];limit=5 if y==0 else 2
        if domain_counts[y].get(d,0)>=limit or counts.get(y,0)>=150:continue
        sig=row['campaign']
        if sig and sig in seen_campaigns:continue
        selected.append(row);domain_counts[y][d]=domain_counts[y].get(d,0)+1;counts[y]=counts.get(y,0)+1
        if sig:seen_campaigns.add(sig)
    minimum=counts.get(0,0)>=50 and counts.get(1,0)>=50 and len(domain_counts[0])>=10 and len(domain_counts[1])>=25
    save(OUT/'collection.json',{'sources':events,'eligible_counts':counts,'domains':{str(y):len(v) for y,v in domain_counts.items()},'coverage_met':minimum,'conflicts_quarantined':len(conflicts)})
    if not minimum:
        log('reservation_incomplete',counts=counts,domains={str(y):len(v) for y,v in domain_counts.items()});return
    test=OUT/'sealed_test';test.mkdir(exist_ok=True)
    with (test/'url_labels.csv').open('x',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['url','label']);writer.writerows((r['url'],r['label']) for r in selected)
    with (test/'provenance.jsonl').open('x',encoding='utf-8') as f:
        for row in selected:f.write(json.dumps(row)+'\n')
    manifest={'created_at':now,'counts':counts,'domains':{str(y):len(v) for y,v in domain_counts.items()},
              'url_labels_sha256':sha(test/'url_labels.csv'),'provenance_sha256':sha(test/'provenance.jsonl'),
              'exclusions_sha256':sha(cache),'source_events':events,'domain_overlap':0,'known_campaign_overlap':0,
              'model_predictions_generated':0,'status':'sealed_unscored','minimum_coverage_met':True,
              'limitations':['Provider reports/reference negatives are not independent content adjudication.','Collection is recent; provider snapshot may be older. No temporal independence guarantee.','Novel-domain convenience sample; no production certification.','OpenPhish raw feed is research-only and must not be redistributed; Phishing.Database MIT license retained.']}
    save(OUT/'manifest.json',manifest)
    save(ROOT/'models/phishing_url/research/recall_test_reservation_20261018.json',manifest)
    log('recall_test_reserved',counts=counts,domains=manifest['domains'])


if __name__=='__main__':main()
