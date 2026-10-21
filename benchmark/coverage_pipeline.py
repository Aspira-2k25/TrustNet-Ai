"""Paired actual-pipeline decisions on a fixed untouched, source-stratified subset."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark.coverage_train import read,score,view,digest
from benchmark.real_photo_guard import wilson


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
    if out.is_relative_to(Path(__file__).resolve().parents[1]):raise SystemExit('Research outputs must be external')
    doc=json.loads((out/'manifest.json').read_text());head=json.loads((out/'candidate.json').read_text())
    if head['manifest_sha256']!=digest(out/'manifest.json'):raise ValueError('Candidate manifest changed')
    source={r['identity']:r for r in doc['rows']}
    features=read(out/'test-features.jsonl');feature_map={r['identity']:r for r in features}
    selection=out/'paired-selection.json'
    if selection.exists():selected=json.loads(selection.read_text())
    else:
        selected=[]
        test=[r for r in doc['rows'] if r['split']=='test']
        for generator in sorted({r['generator'] for r in test if r['positive']}):
            selected.extend(r['identity'] for r in sorted([r for r in test if r['generator']==generator],key=lambda r:r['identity'])[:8])
        for name in sorted({r['source'] for r in test if not r['positive']}):
            selected.extend(r['identity'] for r in sorted([r for r in test if r['source']==name and not r['positive']],key=lambda r:r['identity'])[:6])
        selection.write_text(json.dumps(selected,indent=2),encoding='utf-8')
    # No outcome-dependent retries, selection or threshold changes.
    path=out/'paired-pipeline.jsonl';records=read(path) if path.exists() else [];done={r['identity'] for r in records}
    from models.image_deepfake.inference.forensic_detector import ForensicDetector
    from models.image_deepfake.inference.decision import decide
    detector=ForensicDetector();baseline_config_sha=digest(Path(__file__).resolve().parents[1]/'models/image_deepfake/calibration/evidence-v2.json')
    if any(r['candidate_sha256']!=digest(out/'candidate.json') or r['baseline_config_sha256']!=baseline_config_sha for r in records):
        raise ValueError('Saved paired decisions belong to a different candidate or baseline policy')
    for identity in selected:
        if identity in done:continue
        row=source[identity];feature=feature_map[identity];_,sha,data=view(out,row,0,include_bytes=True)
        if feature['view_sha256']!=sha:raise ValueError('Paired bytes differ from holdout feature bytes')
        result=detector.predict(data);analysis=result.metadata['image_analysis'];prob=float(score(head,[feature])[0])
        config={**detector.config,'ai_alert':head['threshold'],'ai_alert_corroboration_required':False,
            'manipulation_alert':detector.config['manipulation']['raw_alert'],'authenticity_enabled':False}
        verdict,reasons=decide(prob,analysis['manipulation_raw_score'],analysis['provenance'],analysis['quality'],analysis['regions'],config)
        record={k:row[k] for k in ['identity','family','source','generator','positive']};record.update(view_sha256=sha,
            baseline_verdict=result.verdict,candidate_verdict=verdict,candidate_probability=prob,
            candidate_reasons=reasons,baseline_config_sha256=baseline_config_sha,candidate_sha256=digest(out/'candidate.json'))
        with path.open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
        records.append(record);print('Paired pipeline',len(records),'/',len(selected),row['generator'],result.verdict,'->',verdict,flush=True)
    def metrics(key):
        real=[r for r in records if not r['positive']];fake=[r for r in records if r['positive']]
        alerts={'LIKELY_AI_GENERATED','LIKELY_MANIPULATED'}
        fp=sum(r[key] in alerts for r in real)
        return {'n':len(records),'real_n':len(real),'generated_n':len(fake),'false_alerts':fp,
            'real_fpr':fp/len(real),'real_fpr_wilson95':wilson(fp,len(real)),
            'ai_generated_recall':sum(r[key]=='LIKELY_AI_GENERATED' for r in fake)/len(fake),
            'any_warning_recall':sum(r[key] in alerts for r in fake)/len(fake),
            'inconclusive_rate':sum(r[key]=='INCONCLUSIVE' for r in records)/len(records),
            'verdict_counts':dict(Counter(r[key] for r in records))}
    report={'baseline':metrics('baseline_verdict'),'candidate':metrics('candidate_verdict'),
        'limits':['Small stratified paired subset; the larger classifier holdout measures AI-stream FPR separately.','Matched JPEG size/quality/filter controls are software proxies, not comprehensive device or app coverage.','Both policies keep authenticity disabled; localization and provenance are reused from the same actual detector run.']}
    (out/'paired-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
