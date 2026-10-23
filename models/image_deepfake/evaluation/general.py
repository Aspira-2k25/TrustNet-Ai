"""Evaluate/select/promote whole-image policies; candidates never auto-activate."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from models.image_deepfake.inference.general_policy import POLICY, digest
from models.image_deepfake.evaluation.benchmark import read_manifest, transform, metric_summary, grouped_intervals
from models.image_deepfake.evaluation.select_policy import wilson_upper


def write(path, value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2)
    return value


def check_report(report,purpose,identity,localizer):
    if (report.get('purpose') != purpose or report.get('policy') != POLICY
            or report.get('identity') != identity or report.get('localizer') != localizer
            or not report.get('manifest_sha256')):
        raise ValueError('Evaluation identity/purpose mismatch')


def independent(first,second):
    for key in ('sha256','pixel_sha256','group','subject_id'):
        a={r[key] for r in first if r.get(key)}
        b={r[key] for r in second if r.get(key)}
        if a & b:
            raise ValueError('Validation/test overlap: '+key)


def budgets(rows,low,high):
    rows=[r for r in rows if r.get('variant','original')=='original']
    if any(type(r.get('label')) is not int or r['label'] not in (0,1)
           or not isinstance(r.get('group'),str) or not r['group']
           or any(not isinstance(r.get(k),str) or len(r[k])!=64 for k in ('sha256','pixel_sha256'))
           or r.get('score') is not None and (isinstance(r['score'],bool)
               or not isinstance(r['score'],(int,float)) or not math.isfinite(r['score']) or not 0<=r['score']<=1)
           for r in rows):
        raise ValueError('Malformed evaluation records')
    if len({r['group'] for r in rows}) != len(rows):
        raise ValueError('Independent source groups required')
    real=[r['score']*100 for r in rows if r['label']==0 and r.get('score') is not None]
    fake=[r['score']*100 for r in rows if r['label']==1 and r.get('score') is not None]
    if min(len(real),len(fake)) < 1000:
        raise ValueError('At least 1000 independently scored sources per class required')
    accepted=sum(s < low or s >= high for s in real+fake)/len(rows)
    if accepted < .9:
        raise ValueError('Accepted coverage below 90%')
    fpr=wilson_upper(sum(s>=high for s in real),len(real))
    fnr=wilson_upper(sum(s<low for s in fake),len(fake))
    if fpr > .01 or fnr > .05:
        raise ValueError('Predeclared error budgets unmet')
    return {'accepted_coverage':accepted,'real_false_positive_upper95':fpr,'fake_false_low_upper95':fnr}


def evaluate(manifest,output,purpose,robustness=False):
    from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
    detector=EfficientNetDetector(policy=POLICY,evaluation_candidate=True)
    source=Path(manifest)
    rows=read_manifest(source,purpose)
    records=[]
    variants=('original','jpeg_75','resize_256') if robustness else ('original',)
    for row in rows:
        blob=Path(row['path']).read_bytes()
        for variant in variants:
            try:
                result=detector.predict(transform(blob,variant))
                score=result.risk_score/100 if result.metadata.get('score_available') else None
                record={**row,'variant':variant,'score':score,'status':result.status.value,
                        'verdict':result.verdict,'scope_state':result.metadata.get('scope_state'),
                        'abstained':result.verdict not in {'LIKELY_AI_MANIPULATED','LOW_MANIPULATION_SIGNAL'},
                        'latency_ms':result.processing_time_ms,'error':result.error_code}
            except Exception:
                record={**row,'variant':variant,'score':None,'status':'FAILED','verdict':'UNKNOWN',
                        'abstained':True,'latency_ms':0,'error':'DECODE_OR_INFERENCE_FAILED'}
            record.pop('path',None)
            records.append(record)
    original=[r for r in records if r['variant']=='original']
    slices={}
    for key in ('source','generator','task','pose','quality'):
        for value in sorted({str(r.get(key,'unknown')) for r in original}):
            slices[key+':'+value]=metric_summary([r for r in original if str(r.get(key,'unknown'))==value])
    return write(output,{'policy':POLICY,'purpose':purpose,'identity':detector.general_client.identity(),
        'localizer':detector.face_analyzer.localizer.identity,'manifest_sha256':digest(source),
        'records':records,'summary':metric_summary(original),'slices':slices,
        'grouped_intervals':grouped_intervals(original),
        'latency_ms':{'p50':float(np.percentile([r['latency_ms'] for r in original],50)),
                      'p95':float(np.percentile([r['latency_ms'] for r in original],95))},
        'limits':'Reference metrics do not validate modern generators. Unknown upstream overlap remains. Independent labels and data provenance require review.'})


def select(report,output):
    path=Path(report).resolve();target=Path(output).resolve()
    value=json.loads(path.read_text());identity=value['identity']
    check_report(value,'validation',identity,value['localizer'])
    if path.parent != target.parent or not identity.get('deployment_pinned') or not identity.get('processor_sha256'):
        raise ValueError('Same-directory evidence and pinned model/processor required')
    rows=[r for r in value['records'] if r.get('variant','original')=='original']
    real=[r['score']*100 for r in rows if r['label']==0 and r.get('score') is not None]
    fake=[r['score']*100 for r in rows if r['label']==1 and r.get('score') is not None]
    if min(len(real),len(fake))<1000:
        raise ValueError('Insufficient independent validation sources')
    choices=sorted(set([0.,100.]+real+fake))
    high=next((t for t in choices if wilson_upper(sum(s>=t for s in real),len(real))<=.01),None)
    lows=[t for t in choices if wilson_upper(sum(s<t for s in fake),len(fake))<=.05]
    if high is None or not lows:
        raise ValueError('No operating point meets error budgets')
    low=min(max(lows),math.nextafter(high,0.))
    if not low<high:
        raise ValueError('No two-boundary operating point')
    results=budgets(rows,low,high)
    return write(target,{'id':POLICY,'validated':True,'release_approved':False,'identity':identity,
        'localizer':value['localizer'],'aggregation':'general_only_face_diagnostic','low':low,'high':high,
        'evaluation_report':path.name,'evaluation_sha256':digest(path),'validation_gates':results})


def promote(candidate,test,output):
    path=Path(candidate).resolve();final=Path(test).resolve();target=Path(output).resolve()
    if len({path.parent,final.parent,target.parent})!=1:
        raise ValueError('Versioned artifacts must share one directory')
    value=json.loads(path.read_text());report=json.loads(final.read_text())
    from models.image_deepfake.inference.general_policy import load,read_evidence
    checked=load(value['identity'],value['localizer'],allow_candidate=True,path=path)
    if not checked['validated']:
        raise ValueError(checked['reason'])
    validation=read_evidence(path.parent,value['evaluation_report'],value['evaluation_sha256'])
    check_report(report,'test',value['identity'],value['localizer'])
    independent(validation['records'],report['records'])
    results=budgets(report['records'],value['low'],value['high'])
    return write(target,{**value,'release_approved':True,'final_test_report':final.name,
                         'final_test_sha256':digest(final),'final_test_gates':results})


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['evaluate','select','promote'])
    parser.add_argument('--manifest');parser.add_argument('--purpose',choices=['validation','test'],default='test')
    parser.add_argument('--report');parser.add_argument('--candidate');parser.add_argument('--test')
    parser.add_argument('--output',required=True);parser.add_argument('--robustness',action='store_true')
    args=parser.parse_args()
    if args.action=='evaluate':evaluate(args.manifest,args.output,args.purpose,args.robustness)
    elif args.action=='select':select(args.report,args.output)
    else:promote(args.candidate,args.test,args.output)
