"""CPU multilingual candidate, frozen template-group split before fitting.

Public source labels are noisy. This is a development diagnostic, not field accuracy.
Test identities are frozen before training; existing observed cohorts are excluded.
All raw examples, cached API results and candidate weights stay outside the repo.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time


from shared.utils.message_normalization import normalize_message as normalize, message_language as route


def identity(text):
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def load(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def metrics(labels, positive, uncertain=None):
    import numpy as np
    from benchmark.real_photo_guard import wilson as wilson_interval
    y=np.asarray(labels,dtype=bool); p=np.asarray(positive,dtype=bool)
    tp=int((y&p).sum());fp=int((~y&p).sum());fn=int((y&~p).sum());n=int((~y).sum())
    precision=tp/max(1,tp+fp);recall=tp/max(1,tp+fn)
    return {'n':len(y),'tp':tp,'fp':fp,'fn':fn,'normal_n':n,'precision':precision,'recall':recall,
            'f1':2*precision*recall/max(1e-12,precision+recall),'false_positive_rate':fp/max(1,n),
            'fpr_95_ci':wilson_interval(fp,n),'inconclusive_rate':float(np.mean(uncertain)) if uncertain is not None else None}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--api',default='http://127.0.0.1:8005');a=parser.parse_args()
    root=Path(__file__).resolve().parents[1];out=a.output.resolve()
    if out.is_relative_to(root):raise ValueError('Keep raw research outside runtime repository')
    out.mkdir(parents=True,exist_ok=True)
    manifest=out/'manifest.json'
    if not manifest.exists():
        excluded=set()
        # Exclude every official val/test template and previously observed comparison.
        for name in ('val.jsonl','test.jsonl'):
            excluded.update(identity(r['text']) for r in load(a.source/name))
        previous=a.source/'comparison-manifest.json'
        if previous.exists():excluded.update(identity(r['text']) for r in json.loads(previous.read_text(encoding='utf-8'))['rows'])
        groups={};conflicts=set()
        for r in load(a.source/'train.jsonl'):
            if not 25<=len(r['text'])<=1800 or '\x00' in r['text']:continue
            if r['is_scam'] and r['head2_scam_intent']=='General Spam / Telemarketing':continue
            key=identity(r['text'])
            if key in excluded:continue
            if key in groups and groups[key]['is_scam']!=r['is_scam']:conflicts.add(key)
            groups.setdefault(key,r)
        selected=[]
        for lang in ('English','Hindi','Hinglish'):
            for label in (0,1):
                pool=sorted((k,r) for k,r in groups.items() if k not in conflicts and r['language']==lang and int(r['is_scam'])==label)
                # Reserve test and validation before selecting training examples.
                test_n=min(100,len(pool)//4);val_n=min(80,len(pool)//4)
                for index,(key,r) in enumerate(pool[:test_n+val_n+1600]):
                    split='test' if index<test_n else 'validation' if index<test_n+val_n else 'train'
                    selected.append({**r,'group_sha256':key,'split':split})
        document={'source':'sidzzz07/scamshield-dataset','revision':'059dee884476a45e380808e68d09e74baff67291',
            'license':'MIT dataset card; upstream source rights and annotation quality remain uncertain.',
            'selection':'Official train only; remove normalized templates present in official val/test or earlier comparison, conflicting labels; SHA order; reserve test then validation before fitting.',
            'limits':['Synthetic templates and noisy public labels remain. Normalizing numbers/URLs does not eliminate every paraphrase.',
                      'Unknown upstream English classifier training overlap. This is not independently adjudicated ground truth.'],
            'counts':dict(Counter(f"{r['split']}:{r['language']}:{int(r['is_scam'])}" for r in selected)),
            'conflicting_templates_removed':len(conflicts),'rows':selected}
        manifest.write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8')
    doc=json.loads(manifest.read_text(encoding='utf-8'));rows=doc['rows']
    print('FROZEN SPLIT',json.dumps(doc['counts']),flush=True)
    tr=[r for r in rows if r['split']=='train'];va=[r for r in rows if r['split']=='validation'];te=[r for r in rows if r['split']=='test']
    assert not ({r['group_sha256'] for r in tr}&{r['group_sha256'] for r in va+te})
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import make_union
    from sklearn.linear_model import LogisticRegression
    features=make_union(TfidfVectorizer(ngram_range=(1,2),max_features=20000,sublinear_tf=True,token_pattern=r'(?u)\b\w+\b'),
                        TfidfVectorizer(analyzer='char',ngram_range=(3,5),max_features=40000,sublinear_tf=True))
    x=features.fit_transform([normalize(r['text']) for r in tr]);y=[int(r['is_scam']) for r in tr]
    head=LogisticRegression(C=1,max_iter=500,class_weight='balanced',random_state=42).fit(x,y)
    vp=head.predict_proba(features.transform([normalize(r['text']) for r in va]))[:,1]
    thresholds={};validation={}
    for lang in ('English','Hindi','Hinglish'):
        idx=[i for i,r in enumerate(va) if route(r['text'])==lang];yy=np.array([va[i]['is_scam'] for i in idx],dtype=bool);pp=vp[idx]
        if not idx or not yy.any() or yy.all():
            thresholds[lang]=1.000001;validation[lang]={'n':len(idx),'coverage':'No supported threshold; abstain'};continue
        choices=sorted(set([1.000001]+pp.tolist()))
        eligible=[t for t in choices if np.mean(pp[~yy]>=t)<=.02]
        threshold=min(eligible,key=lambda t:(-float(np.mean(pp[yy]>=t)),t));thresholds[lang]=threshold
        validation[lang]=metrics(yy,pp>=threshold)
    # Cache safe arrays/config, never pickle executable models.
    config={'normalization':'nfkc-casefold-url-email-number-v1','thresholds':thresholds,'labels':['normal','scam'],
            'word_vocab':{k:int(v) for k,v in features.transformer_list[0][1].vocabulary_.items()},
            'char_vocab':{k:int(v) for k,v in features.transformer_list[1][1].vocabulary_.items()}}
    (out/'config.json').write_text(json.dumps(config,ensure_ascii=False),encoding='utf-8')
    np.savez_compressed(out/'weights.npz',coef=head.coef_,intercept=head.intercept_,word_idf=features.transformer_list[0][1].idf_,char_idf=features.transformer_list[1][1].idf_)
    print('FIT COMPLETE; validation only',json.dumps(validation),flush=True)
    scores=head.predict_proba(features.transform([normalize(r['text']) for r in te]))[:,1]
    positive=[float(score)>=thresholds[route(r['text'])] for score,r in zip(scores,te)]
    # Only now consume untouched test results, with no further selection or threshold edits.
    cache=out/'baseline.jsonl';baseline={r['group_sha256']:r for r in load(cache)} if cache.exists() else {}
    import requests
    session=requests.Session()
    for r in te:
        key=r['group_sha256']
        if key in baseline:continue
        started=time.monotonic();response=session.post(a.api+'/infer',json={'scan_id':'fresh-'+key[:20],'text':r['text'],'optional_analysis':False},timeout=30)
        response.raise_for_status();result=response.json()['data']
        item={'group_sha256':key,'verdict':result.get('verdict'),'status':result['status'],'seconds':time.monotonic()-started}
        with cache.open('a',encoding='utf-8') as stream:stream.write(json.dumps(item)+'\n')
        baseline[key]=item
        if len(baseline)%50==0:print('BASELINE',len(baseline),'/',len(te),flush=True)
    before=[];unknown=[]
    for r in te:
        value=baseline[r['group_sha256']];pos=value['verdict'] in ('LIKELY_SCAM','SMISHING_RISK') and value['status'] in ('SUCCESS','PARTIAL_SUCCESS')
        before.append(pos);unknown.append(not pos and value['verdict']!='NO_STRONG_INDICATORS')
    labels=[r['is_scam'] for r in te]
    report={'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'thresholds':thresholds,'validation':validation,
            'baseline':metrics(labels,before,unknown),'candidate':metrics(labels,positive),
            'by_language':{lang:{'baseline':metrics([r['is_scam'] for r in te if r['language']==lang],[p for p,r in zip(before,te) if r['language']==lang],[u for u,r in zip(unknown,te) if r['language']==lang]),
                                 'candidate':metrics([r['is_scam'] for r in te if r['language']==lang],[p for p,r in zip(positive,te) if r['language']==lang])} for lang in thresholds},
            'limits':doc['limits']+['Language routing uses message text, not source language annotations. Some public language annotations describe English bank messages as Hinglish.',
                                   'An initial offline comparison used annotated-language routing and was invalid for runtime. Corrected routing/threshold selection uses validation only; this test has now been consumed.'],
            'promotion':'Not automatic. Inspect language-specific false positives and source labels before runtime promotion.'}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
