"""Resume-safe evaluation of the actual detector, including abstention coverage."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def metrics(rows):
    from sklearn.metrics import roc_auc_score
    available = [r for r in rows if r.get('prediction') is not None]
    tp=sum(r['positive'] and r['prediction'] for r in available)
    tn=sum(not r['positive'] and not r['prediction'] for r in available)
    fp=sum(not r['positive'] and r['prediction'] for r in available)
    fn=sum(r['positive'] and not r['prediction'] for r in available)
    scores=[r for r in rows if r.get('score') is not None]
    return dict(n=len(rows), coverage=len(available)/len(rows) if rows else 0,
        inconclusive_share=sum(r.get('prediction') is None for r in rows)/len(rows) if rows else 0,
        confusion=dict(tn=tn,fp=fp,fn=fn,tp=tp),
        selective_accuracy=(tp+tn)/len(available) if available else None,
        correct_fraction_of_all=(tp+tn)/len(rows) if rows else None,
        precision=tp/(tp+fp) if tp+fp else None,
        recall=tp/sum(r['positive'] for r in rows) if any(r['positive'] for r in rows) else None,
        conditional_recall_among_decided=tp/(tp+fn) if tp+fn else None,
        f1=2*tp/(2*tp+fp+sum(r['positive'] for r in rows)-tp) if 2*tp+fp+sum(r['positive'] for r in rows)-tp else None,
        selective_f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
        abstained_positive=sum(r['positive'] and r.get('prediction') is None for r in rows),
        abstained_negative=sum(not r['positive'] and r.get('prediction') is None for r in rows),
        false_positive_rate=fp/sum(not r['positive'] for r in rows) if any(not r['positive'] for r in rows) else None,
        roc_auc=roc_auc_score([r['positive'] for r in scores],[r['score'] for r in scores]) if len({r['positive'] for r in scores})==2 else None,
        localization_iou_mean=sum(r['iou'] for r in rows if r.get('iou') is not None)/sum(r.get('iou') is not None for r in rows) if any(r.get('iou') is not None for r in rows) else None)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--detector',choices=['baseline','current'],default='current')
    parser.add_argument('--split',choices=['validation','test'])
    parser.add_argument('--limit',type=int)
    parser.add_argument('--baseline-root',type=Path,help='Frozen source export used only for baseline inference')
    args=parser.parse_args()
    if args.detector=='baseline' and not args.baseline_root:
        parser.error('Historical baseline requires --baseline-root pointing to the frozen source export; legacy heuristics are not part of the runtime.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.resolve().is_relative_to(ROOT):
        raise SystemExit('Keep substantial evaluation output outside the repository')
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    manifest_hash=hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    import torch
    torch.set_num_threads(2)
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['HUGGINGFACE_API_KEY']=''
    if args.detector=='baseline':
        if args.baseline_root:
            sys.path.insert(0,str(args.baseline_root.resolve()))
        from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
        detector=EfficientNetDetector(enable_explainability=False)
    else:
        from models.image_deepfake.inference.forensic_detector import ForensicDetector
        detector=ForensicDetector()
    from PIL import Image
    records=[]
    if args.output.exists():
        records=[json.loads(line) for line in args.output.read_text().splitlines() if line]
        assert all(r['manifest_sha256']==manifest_hash and r['detector']==args.detector for r in records)
    seen={r['sha256'] for r in records}
    selected=[r for r in manifest['rows'] if not args.split or r['split']==args.split]
    if args.limit:selected=selected[:args.limit]
    for index,row in enumerate(selected):
        if row['sha256'] in seen:
            continue
        data=(args.manifest.parent/row['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==row['sha256']
        with Image.open(io.BytesIO(data)) as image:
            before=image.size
        started=time.monotonic()
        result=detector.predict(data,filename='evaluation-image'+Path(row['path']).suffix)
        success=str(result.status).split('.')[-1] in ('SUCCESS','PARTIAL_SUCCESS')
        verdict=result.verdict
        prediction=(False if verdict in ('AUTHENTIC','LIKELY_AUTHENTIC') else True if verdict in ('LIKELY_AI_MANIPULATED','LIKELY_AI_GENERATED','LIKELY_MANIPULATED') else None) if success else None
        record={**row,'manifest_sha256':manifest_hash,'detector':args.detector,'positive':row['ai'] or row['manipulation'],
            'prediction':prediction,'score':result.risk_score/100 if success else None,'verdict':verdict,
            'confidence':result.confidence,'milliseconds':round((time.monotonic()-started)*1000),
            'status':str(result.status),'error':result.error_code,'original_shape':before,
            'raw_ai_score':result.metadata.get('hf_risk_score'),'ai_generated_prob':result.metadata.get('ai_generated_prob'),
            'iou':None}
        with args.output.open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(record)+'\n')
        records.append(record); seen.add(row['sha256'])
        print(f"{index+1}/{len(selected)} {row['generator']} {row['variant']} {verdict} score={result.risk_score} ai_raw={record['raw_ai_score']} shape={before} ms={record['milliseconds']}",flush=True)
    report={'manifest_sha256':manifest_hash,'all':metrics(records),
        'test':metrics([r for r in records if r['split']=='test']),
        'by_generator':{g:metrics([r for r in records if r['generator']==g and r['split']=='test']) for g in sorted({r['generator'] for r in records})},
        'by_variant':{g:metrics([r for r in records if r['variant']==g and r['split']=='test']) for g in sorted({r['variant'] for r in records})},
        'limits':manifest['limits']}
    args.output.with_suffix('.metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
