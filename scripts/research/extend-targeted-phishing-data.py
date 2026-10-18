"""Create a new pretraining dataset revision using eight additional provider pages.

Does not overwrite the original reservation or open reported phishing pages.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('targeted_collector',ROOT/'scripts/research/collect-targeted-phishing-data.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
import httpx

PARENT=ROOT/'models/phishing_url/data/targeted_20261018_v1'
OUT=ROOT/'models/phishing_url/data/targeted_20261018_v2'


def main():
    if (OUT/'additional_manifest.json').exists() or (OUT/'dataset_manifest.json').exists():raise SystemExit('Extension already frozen')
    OUT.mkdir(parents=True,exist_ok=True)
    for name in ('new_evidence.jsonl','collection_manifest.json','supplemental_evidence.jsonl','supplemental_manifest.json'):
        shutil.copy2(PARENT/name,OUT/name)
    rows=[];events=[]
    with httpx.Client(timeout=30,headers={'User-Agent':'TrustNet-Academic-Dataset/1.0'},follow_redirects=False) as client:
        for page in range(9,17):
            path=OUT/'raw'/('phishstats-'+str(page)+'.json')
            try:
                if path.exists():payload=json.loads(path.read_text())
                else:
                    raw,headers=c.provider_get(client,'https://api.phishstats.info/api/phishing',params={'_size':100,'_p':page,'_sort':'-date','_where':'(score,gt,6.9)'})
                    items=json.loads(raw)
                    if not isinstance(items,list):raise ValueError('Unexpected provider schema')
                    payload={'collected_at':c.now(),'rows':items,'http':headers,'sha256':c.sha(raw)};c.save(path,payload)
                for item in payload['rows']:
                    try:
                        score=float(item.get('score',0))
                        if score<7:continue
                    except (TypeError,ValueError):continue
                    rows.append({'url':item.get('url'),'label':1,'source':'phishstats_report','source_url':'https://phishstats.info/api-docs',
                        'collected_at':payload['collected_at'],'verified_at':item.get('date'),'label_basis':'provider_report_score_at_least_7',
                        'label_quality':'provider_report_not_independently_adjudicated','evidence':{'report_id':item.get('id'),'provider_score':score}})
                events.append({'source':'PhishStats','page':page,'status':'collected','rows':len(payload['rows']),'sha256':payload['sha256']})
                c.log('additional_provider_page',page=page,rows=len(payload['rows']))
                if len(payload['rows'])<100:break
            except Exception as exc:
                events.append({'source':'PhishStats','page':page,'status':'unavailable','reason':type(exc).__name__+': '+str(exc)[:160]});break
    path=OUT/'additional_evidence.jsonl'
    with path.open('w',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=True)+'\n')
    c.save(OUT/'additional_manifest.json',{'collected_at':c.now(),'rows':len(rows),'new_evidence_sha256':c.sha(path.read_bytes()),'sources':events,
        'parent_dataset':'targeted_20261018_v1','parent_collection_sha256':c.sha((PARENT/'collection_manifest.json').read_bytes()),
        'positive_urls_visited':0,'purpose':'Expand novel-domain coverage before any retraining or independent test evaluation.'})
    c.log('extension_frozen',rows=len(rows))

if __name__=='__main__':main()
