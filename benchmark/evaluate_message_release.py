"""Evaluate the actual final API, including rules, URL fusion and public contract.

Use a previously frozen manifest. This never fits or selects a threshold.
Reports available-branch warnings separately from incomplete final presentations.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
from benchmark.message_candidate import metrics


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--api',default='http://127.0.0.1:8005');a=p.parse_args()
    root=Path(__file__).resolve().parents[1];out=a.output.resolve()
    if out.is_relative_to(root):raise ValueError('Keep raw evaluation outputs outside runtime repo')
    out.mkdir(parents=True,exist_ok=True);doc=json.loads(a.manifest.read_text(encoding='utf-8'))
    rows=[r for r in doc['rows'] if r.get('split','test')=='test']
    import requests
    session=requests.Session();ready=session.get(a.api+'/ready',timeout=5);ready.raise_for_status()
    files=[*sorted((root/'models/scam_message').glob('*.py')),*sorted((root/'shared/presentation').glob('*.*')),*sorted((root/'models/scam_message/multilingual_artifacts').glob('*.*')),root/'services/scam_message/app/link_fusion.py',root/'shared/utils/message_normalization.py']
    contract={'source_manifest_sha256':hashlib.sha256(a.manifest.read_bytes()).hexdigest(),'ready':ready.json(),
              'source_sha256':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
    cp=out/'runtime-contract.json'
    if cp.exists() and json.loads(cp.read_text())!=contract:raise ValueError('Runtime changed; choose a new evaluation output folder')
    cp.write_text(json.dumps(contract,indent=2))
    cache=out/'predictions.jsonl';done={}
    if cache.exists():
        with cache.open() as stream:done={r['id']:r for r in (json.loads(line) for line in stream if line.strip())}
    for row in rows:
        key=row.get('group_sha256') or row['text_sha256']
        if key in done:continue
        start=time.monotonic();response=session.post(a.api+'/infer',json={'scan_id':'release-'+key[:20],'text':row['text'],'optional_analysis':False},timeout=30);response.raise_for_status();result=response.json()['data']
        view=result['presentation']
        item={'id':key,'verdict':result.get('verdict'),'status':result['status'],'public_verdict':view['verdict_key'],
              'rules':[f['code'] for f in result.get('metadata',{}).get('rule_findings',[])],'seconds':time.monotonic()-start}
        done[key]=item
        with cache.open('a') as stream:stream.write(json.dumps(item)+'\n')
        if len(done)%100==0:print('RELEASE',len(done),'/',len(rows),flush=True)
    selected=[done[r.get('group_sha256') or r['text_sha256']] for r in rows]
    positive=[r['verdict'] in ('LIKELY_SCAM','SMISHING_RISK') and r['status'] in ('SUCCESS','PARTIAL_SUCCESS') for r in selected]
    public_positive=[r['public_verdict'] in ('scam','risky') for r in selected]
    uncertain=[r['public_verdict'] in ('not_sure','incomplete') for r in selected]
    truth=[r['is_scam'] for r in rows]
    by={}
    for field in ('language','head2_scam_intent'):
        by[field]={}
        for name in sorted({r.get(field,'unknown') for r in rows}):
            indices=[i for i,r in enumerate(rows) if r.get(field,'unknown')==name]
            by[field][name]=metrics([truth[i] for i in indices],[positive[i] for i in indices],[uncertain[i] for i in indices])
    latency=sorted(r['seconds'] for r in selected)
    report={'manifest_sha256':contract['source_manifest_sha256'],'model':ready.json(),
            'available_branch_warnings':metrics(truth,positive),
            'final_public_contract':metrics(truth,public_positive,uncertain),
            'public_verdict_counts':dict(Counter(r['public_verdict'] for r in selected)),
            'p50_seconds':latency[len(latency)//2],'p95_seconds':latency[int(.95*(len(latency)-1))],
            'error_analysis':by,'limits':doc.get('limits',[])+[
                'This frozen set has already been consumed during candidate comparison. No test threshold tuning is performed here.',
                'Available-branch warning recall is not final UI recall: incomplete link checks retain reasons but force an incomplete headline.',
                'Source language/category annotations can be noisy; synthetic templates and unknown upstream overlap remain.']}
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='error_analysis'},indent=2),flush=True)


if __name__=='__main__':main()
