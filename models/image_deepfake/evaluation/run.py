"""Evaluate the deployed screening policy, including abstention, on labeled still images."""
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from models.image_deepfake.evaluation.metrics import calculate_metrics

def evaluate(manifest_path, output_path):
    path=Path(manifest_path).resolve()
    samples=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(samples,list) or not samples:
        raise ValueError('Evaluation manifest must be a nonempty list of [path,label,group]')
    detector=EfficientNetDetector(enable_explainability=False, policy='image-screening-v2')
    if not detector.readiness()['ready']:
        raise ValueError('Real evaluation requires a valid trained model artifact and localization runtime')
    forbidden={row['sha256'] for row in detector.cnn.dataset_index if row['split'] in {'train','validation'}}
    forbidden_groups={row['group_sha256'] for row in detector.cnn.dataset_index if row['split'] in {'train','validation'}}
    seen=set();records=[]
    for row in samples:
        if not isinstance(row,list) or len(row)!=3 or type(row[1]) is not int or row[1] not in (0,1) or not isinstance(row[2],str) or not row[2]:
            raise ValueError('Invalid evaluation row')
        blob=(path.parent/row[0]).read_bytes();digest=hashlib.sha256(blob).hexdigest()
        if digest in forbidden or hashlib.sha256(str(row[2]).encode()).hexdigest() in forbidden_groups:
            raise ValueError('Evaluation leaks a training or validation image/source group')
        if digest in seen:raise ValueError('Duplicate evaluation content')
        seen.add(digest)
        result=detector.predict(blob,filename=Path(row[0]).name)
        if result.status.value not in {'SUCCESS','PARTIAL_SUCCESS'}:
            records.append({'label':row[1],'group':row[2],'sha256':digest,'status':result.status.value,'error':result.error_code,'abstained':True})
            continue
        records.append({'label':row[1],'group':row[2],'sha256':digest,'score':result.risk_score/100,
            'verdict':result.verdict,'status':result.status.value,'abstained':result.verdict=='UNCERTAIN',
            'latency_ms':result.processing_time_ms})
    scored=[r for r in records if 'score' in r]
    accepted=[r for r in scored if not r['abstained']]
    def metrics(rows):
        return calculate_metrics([r['label'] for r in rows],[r['score'] for r in rows],threshold=.62) if rows else None
    report={'manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'artifact_sha256':detector.cnn.manifest['weights_sha256'],'policy':'image-screening-v2',
        'counts':dict(Counter(r['status'] for r in records)),
        'abstention_rate':sum(r['abstained'] for r in records)/len(records),
        'score_metrics_all_completed':metrics(scored),'accepted_decision_metrics':metrics(accepted),
        'calibration_available':False,'records':records,
        'limits':'Grouped split/generator independence must be established before supplying this manifest. This command does not certify provenance or fit confidence calibration.'}
    target=Path(output_path)
    if target.exists():raise ValueError('Refusing to overwrite an evaluation report')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();evaluate(args.manifest,args.output)
