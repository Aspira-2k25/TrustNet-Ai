"""Frozen, public-source 400/400 message diagnostic against the running API.

No training, threshold changes, optional provider or automatic website fetching.
Public labels, prior observations and possible upstream overlap limit conclusions.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time


def sha(text):return hashlib.sha256(' '.join(text.casefold().split()).encode()).hexdigest()
def records(path):
    # JSON strings can contain Unicode U+2028/U+0085. str.splitlines() treats
    # those as delimiters, unlike the physical newlines used by JSONL.
    with path.open(encoding='utf-8') as stream:return [json.loads(line) for line in stream if line.strip()]


def prepare(source,output):
    manifest=output/'manifest.json'
    if manifest.exists():return json.loads(manifest.read_text(encoding='utf-8'))
    pool=records(source/'test.jsonl');seen=set();rows=[]
    # Reserve minority-language examples first; never synthesize benchmark labels.
    for label in (False,True):
        selected=[]
        for language,cap in [('Hindi',100),('Hinglish',100),('English',400)]:
            group={}
            for row in pool:
                text=row['text'];identity=sha(text)
                if bool(row['is_scam'])!=label or row['language']!=language or identity in seen:continue
                if not 25<=len(text)<=10000 or '\x00' in text:continue
                if label and row['head2_scam_intent']=='General Spam / Telemarketing':continue
                group.setdefault(identity,row)
            for identity,row in sorted(group.items())[:min(cap,400-len(selected))]:
                seen.add(identity);selected.append({**row,'text_sha256':identity})
        if len(selected)!=400:raise ValueError('Not enough distinct eligible public examples for a 400/400 diagnostic')
        rows.extend(selected)
    old=source/'comparison-manifest.json'
    previously_used={r['text_sha256'] for r in json.loads(old.read_text(encoding='utf-8'))['rows']} if old.exists() else set()
    for row in rows:row['previously_observed']=row['text_sha256'] in previously_used
    doc={'source':'sidzzz07/scamshield-dataset','revision':'059dee884476a45e380808e68d09e74baff67291',
         'source_test_sha256':hashlib.sha256((source/'test.jsonl').read_bytes()).hexdigest(),
         'source_terms':'MIT dataset card; upstream source rights and annotation quality still apply. Raw data remains external.',
         'selection':'SHA-sorted distinct official-test text; reserve up to 100 per minority language and class; fill remaining slots from English; exclude general spam positives.',
         'counts':dict(Counter(r['language']+':'+str(int(r['is_scam'])) for r in rows)),
         'previously_observed_n':sum(r['previously_observed'] for r in rows),'rows':rows,
         'limits':['Not an untouched independent test: some examples were previously used in the small multilingual comparison.',
                   'Upstream English training overlap, synthetic templates and noisy public annotations are not excluded.',
                   'Hindi/Hinglish scam positives are scarce. Aggregate results do not establish language-specific field accuracy.']}
    manifest.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8');return doc


def summarize(rows,predictions):
    tp=fp=tn=fn=unknown=failed=0;latency=[]
    for row in rows:
        item=predictions[row['text_sha256']];truth=bool(row['is_scam'])
        verdict=item.get('verdict');positive=verdict in {'LIKELY_SCAM','SMISHING_RISK'} and item.get('status') in {'SUCCESS','PARTIAL_SUCCESS'}
        negative=verdict=='NO_STRONG_INDICATORS' and item.get('status')=='SUCCESS'
        if not positive and not negative:unknown+=1
        if item.get('error'):failed+=1
        tp+=int(truth and positive);fp+=int(not truth and positive)
        tn+=int(not truth and negative);fn+=int(truth and not positive)
        if 'seconds' in item:latency.append(item['seconds'])
    real=sum(not bool(r['is_scam']) for r in rows);fake=len(rows)-real
    def quantile(q):
        if not latency:return None
        ordered=sorted(latency);position=(len(ordered)-1)*q;i=int(position)
        return ordered[i]+(ordered[min(i+1,len(ordered)-1)]-ordered[i])*(position-i)
    return {'n':len(rows),'scam_n':fake,'normal_n':real,'tp':tp,'fp':fp,'tn_decided':tn,'missed_scams_including_abstentions':fn,
            'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/fake if fake else None,
            'f1_including_abstentions':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            'normal_false_warning_rate':fp/real if real else None,'inconclusive_rate':unknown/len(rows) if rows else None,
            'selective_accuracy':(tp+tn)/(len(rows)-unknown) if len(rows)>unknown else None,
            'service_errors':failed,'p50_seconds':quantile(.5),'p95_seconds':quantile(.95)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--api',default='http://127.0.0.1:8005');a=p.parse_args()
    root=Path(__file__).resolve().parents[1];out=a.output.resolve()
    if out.is_relative_to(root):raise ValueError('Keep public text and QA outputs outside runtime repository')
    out.mkdir(parents=True,exist_ok=True);doc=prepare(a.source,out);manifest_sha=hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest()
    import requests
    session=requests.Session();ready=session.get(a.api+'/ready',timeout=5);ready.raise_for_status()
    runtime_files=['models/scam_message/detector.py','models/scam_message/rules.py','models/scam_message/presentation.py','models/scam_message/coverage.py','services/scam_message/app/link_fusion.py']
    contract={'manifest_sha256':manifest_sha,'model':ready.json(),'runtime_source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in runtime_files}}
    contract_file=out/'runtime-contract.json'
    if contract_file.exists() and json.loads(contract_file.read_text())!=contract:raise ValueError('Runtime or manifest changed; do not mix cached assessments')
    contract_file.write_text(json.dumps(contract,indent=2));cache=out/'predictions.jsonl';done={r['text_sha256']:r for r in records(cache)} if cache.exists() else {}
    for row in doc['rows']:
        identity=row['text_sha256']
        if identity in done:continue
        started=time.monotonic()
        try:
            response=session.post(a.api+'/infer',json={'scan_id':'audit-'+identity[:20],'text':row['text'],'optional_analysis':False},timeout=30);response.raise_for_status();result=response.json()['data']
            item={'text_sha256':identity,'verdict':result.get('verdict'),'status':result.get('status'),'risk_score':result.get('risk_score'),'rule_findings':result.get('metadata',{}).get('rule_findings',[]),'seconds':time.monotonic()-started}
        except (requests.RequestException,KeyError,ValueError) as exc:
            item={'text_sha256':identity,'error':type(exc).__name__,'seconds':time.monotonic()-started}
        with cache.open('a',encoding='utf-8') as stream:stream.write(json.dumps(item)+'\n')
        done[identity]=item
        if len(done)%25==0:print('MESSAGE AUDIT',len(done),'/',len(doc['rows']),flush=True)
        if sum(bool(v.get('error')) for v in list(done.values())[-3:])==3:raise RuntimeError('Three consecutive service errors; inspect availability rather than continuing')
    rows=doc['rows'];report={'manifest_sha256':manifest_sha,'model':ready.json(),'overall':summarize(rows,done),'by_language':{lang:summarize([r for r in rows if r['language']==lang],done) for lang in sorted({r['language'] for r in rows})},'previously_observed_n':doc['previously_observed_n'],'limits':doc['limits'],'promotion':'Diagnostic only. No weights or thresholds changed.'}
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
