"""Same-split comparison: deployed hybrid, multilingual TF-IDF, frozen MuRIL head.

Small public diagnostic, not a field-accuracy claim. Spam-only positives excluded.
Upstream English training overlap and noisy public labels limit interpretation.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def load(path):return [json.loads(l) for l in path.read_text(encoding='utf-8').split('\n') if l.strip()]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evaluation-root',type=Path,required=True)
    a=p.parse_args();out=a.evaluation_root/'text/multilingual'
    manifest=out/'comparison-manifest.json'
    if not manifest.exists():
        rows=[];seen=set();selection={}
        for split,file,count in [('train','train',30),('validation','val',8),('test','test',10)]:
            candidates=load(out/(file+'.jsonl'));selection[split]={}
            for lang in ['English','Hindi','Hinglish']:
                for label in [0,1]:
                    group=[]
                    for r in candidates:
                        text=r['text'];normalized=' '.join(text.casefold().split());sha=hashlib.sha256(normalized.encode()).hexdigest()
                        if r['language']!=lang or r['is_scam']!=label or sha in seen or len(text)<25 or len(text)>1200:continue
                        if label and r['head2_scam_intent']=='General Spam / Telemarketing':continue
                        if lang=='Hindi' and sum('\u0900'<=c<='\u097f' for c in text)<10:continue
                        if lang=='Hinglish' and not re.search(r'\b(aap|aapka|apna|hai|hain|karo|karna|bhej|bhi|nahi|paise|mera|tum|kal|raha)\b',text,re.I):continue
                        group.append((sha,r))
                    group.sort(key=lambda pair:pair[0])
                    for sha,r in group[:count]:
                        seen.add(sha);rows.append({**r,'split':split,'text_sha256':sha})
                    selection[split][lang+':'+str(label)]=min(len(group),count)
        manifest.write_text(json.dumps({'rows':rows,'counts':selection,'source':'sidzzz07/scamshield-dataset','revision':'059dee884476a45e380808e68d09e74baff67291','license':'MIT dataset card; upstream source rights and annotation quality still apply','limits':['Small filtered public-source diagnostic; synthetic templates and label noise remain.','English source may overlap deployed model training. No field accuracy or independently adjudicated ground truth is claimed.','MuRIL is a frozen language encoder with a newly trained linear head, not an existing scam classifier.']},ensure_ascii=False,indent=2),encoding='utf-8')
    doc=json.loads(manifest.read_text(encoding='utf-8'));rows=doc['rows'];print('Frozen split counts:',json.dumps(doc['counts']),flush=True)
    import numpy as np
    import torch
    torch.set_num_threads(2)
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import make_pipeline,make_union
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score,precision_recall_fscore_support,roc_auc_score
    tr=[r for r in rows if r['split']=='train'];va=[r for r in rows if r['split']=='validation'];te=[r for r in rows if r['split']=='test']
    cache=out/'muril-features.jsonl';features={r['text_sha256']:r for r in load(cache)} if cache.exists() else {}
    pending=[r for r in rows if r['text_sha256'] not in features]
    if pending:
        from transformers import AutoTokenizer,AutoModel
        tokenizer=AutoTokenizer.from_pretrained(out/'muril',local_files_only=True)
        model=AutoModel.from_pretrained(out/'muril',local_files_only=True).eval()
        with torch.inference_mode():
            for start in range(0,len(pending),4):
                group=pending[start:start+4];inputs=tokenizer([r['text'] for r in group],padding=True,truncation=True,max_length=128,return_tensors='pt')
                hidden=model(**inputs).last_hidden_state
                mask=inputs['attention_mask'].unsqueeze(-1)
                values=((hidden*mask).sum(1)/mask.sum(1)).cpu().numpy()
                for r,value in zip(group,values):
                    record={'text_sha256':r['text_sha256'],'embedding':value.tolist()};features[r['text_sha256']]=record
                    with cache.open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
                print('MuRIL features',min(start+4,len(pending)),'/',len(pending),flush=True)
        del model,tokenizer
        import gc;gc.collect()
    embedding=lambda group:np.array([features[r['text_sha256']]['embedding'] for r in group])
    head=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=1000,class_weight='balanced',random_state=42)).fit(embedding(tr),[r['is_scam'] for r in tr])
    tfidf=make_pipeline(make_union(TfidfVectorizer(ngram_range=(1,2),max_features=10000,sublinear_tf=True),TfidfVectorizer(analyzer='char',ngram_range=(3,5),max_features=20000,sublinear_tf=True)),LogisticRegression(C=1,max_iter=1000,class_weight='balanced',random_state=42)).fit([r['text'] for r in tr],[r['is_scam'] for r in tr])
    candidates={}
    for name,model,input_fn in [('muril_frozen_linear',head,embedding),('multilingual_tfidf_logistic',tfidf,lambda g:[r['text'] for r in g])]:
        vp=model.predict_proba(input_fn(va))[:,1];labels=np.array([r['is_scam'] for r in va])
        possible=sorted(set([.5]+vp.tolist()))
        valid=[t for t in possible if np.mean(vp[labels==0]>=t)<=.05]
        threshold=min(valid,key=lambda t:(-np.mean(vp[labels==1]>=t),t)) if valid else float(np.nextafter(max(vp),np.inf))
        candidates[name]={'threshold':threshold,'probabilities':model.predict_proba(input_fn(te))[:,1].tolist()}
    # Deployed semantic hybrid is evaluated as-is: no threshold refit on this set.
    deployed=out/'deployed-predictions.jsonl';records=load(deployed) if deployed.exists() else []
    done={r['text_sha256'] for r in records}
    if len(done)<len(te):
        from models.scam_message.detector import ScamDetector
        detector=ScamDetector()
        for r in te:
            if r['text_sha256'] in done:continue
            result=detector.predict(r['text'],'language-comparison')
            record={'text_sha256':r['text_sha256'],'verdict':result.verdict,'risk_score':result.risk_score,'model_probabilities':result.metadata.get('probabilities'),'model_risk_score':result.metadata.get('model_risk_score')}
            with deployed.open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
            records.append(record)
    by_sha={r['text_sha256']:r for r in records}
    def summarize(group,probabilities,predictions):
        y=np.array([r['is_scam'] for r in group]);pred=np.array(predictions);decided=pred>=0
        tp=int(sum((pred==1)&(y==1)));fp=int(sum((pred==1)&(y==0)));fn=int(sum((pred==0)&(y==1)))
        recall=tp/int(sum(y==1)) if sum(y==1) else None
        precision=tp/(tp+fp) if tp+fp else None
        return {'n':len(y),'tp':tp,'fp':fp,'fn_decided':fn,'inconclusive_n':int(sum(~decided)),'inconclusive_rate':float(np.mean(~decided)),'precision':precision,'recall_including_abstentions':recall,'f1_including_abstentions':2*tp/(2*tp+fp+sum(y==1)-tp) if 2*tp+fp+sum(y==1)-tp else None,'accuracy_all':float(np.mean(pred==y)),'selective_accuracy':float(np.mean(pred[decided]==y[decided])) if any(decided) else None,'roc_auc':roc_auc_score(y,probabilities) if probabilities is not None and len(set(y))==2 else None}
    report={'counts':doc['counts'],'limits':doc['limits'],'models':{}}
    for name,item in candidates.items():
        probabilities=np.array(item['probabilities']);pred=(probabilities>=item['threshold']).astype(int)
        report['models'][name]={'validation_selected_threshold':item['threshold'],'all':summarize(te,probabilities,pred),'by_language':{lang:summarize([r for r in te if r['language']==lang],probabilities[[r['language']==lang for r in te]],pred[[r['language']==lang for r in te]]) for lang in ['English','Hindi','Hinglish']}}
    pred=[]
    from models.scam_message.presentation import enrich
    from models.scam_message.coverage import limited_language
    from models.scam_message.rules import analyze
    from shared.schemas.detection_result import DetectionResult
    from shared.schemas.message_input import MessageInput
    from datetime import datetime,timezone
    for r in te:
        cached=by_sha[r['text_sha256']];probs=cached.get('model_probabilities') or {}
        # Reuse cached inference and apply the same pure presentation step used
        # by the HTTP service. Raw detector labels are not the deployed verdict.
        findings=analyze(r['text']);limited=limited_language(r['text'])
        result=DetectionResult(scan_id='comparison',module='scam_message',detector_id='cached-deployed',model_version='cached',preprocessing_version='cached',
            native_score=cached['risk_score']/100,native_score_semantics='anomaly_score',risk_score=cached['risk_score'],
            confidence=0 if findings or limited else max(probs.values(),default=0),label=max(probs,key=probs.get) if probs else 'not_assessed',
            verdict=cached['verdict'],status='SUCCESS',timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={'coverage':{},'limitations':[],'threshold':.45,'rule_findings':findings,'language_coverage_limited':limited})
        v=enrich(result,MessageInput(text=r['text'])).verdict
        pred.append(1 if v=='LIKELY_SCAM' else -1 if v in ['UNABLE_TO_ASSESS','SUSPICIOUS'] else 0)
    report['models']['deployed_hybrid_with_rules']={'all':summarize(te,None,pred),'by_language':{lang:summarize([r for r in te if r['language']==lang],None,[v for r,v in zip(te,pred) if r['language']==lang]) for lang in ['English','Hindi','Hinglish']}}
    report['promotion']='No automatic promotion from a small noisy diagnostic. Compare per-language false alerts and validate independently before replacing runtime weights.'
    (out/'comparison-metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
