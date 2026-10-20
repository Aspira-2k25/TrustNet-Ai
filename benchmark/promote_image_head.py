"""Freeze conservative AI decision boundaries and calibration using validation only."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from models.image_deepfake.inference.feature_head import head_score,policy_score,logit


def read(path):return [json.loads(l) for l in path.read_text().splitlines() if l]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evaluation-root',type=Path,required=True)
    a=p.parse_args();repo=Path(__file__).resolve().parents[1]
    folder=a.evaluation_root/'adaptation';head=json.loads((folder/'candidate-head.json').read_text())
    old=json.loads((a.evaluation_root/'images/manifest-controls.json').read_text())
    wanted=[r for r in old['rows'] if r['split']=='validation']
    cache=folder/'old-generator-validation.jsonl'
    existing=read(cache) if cache.exists() else []
    seen={r['sha256'] for r in existing}
    pending=[r for r in wanted if r['sha256'] not in seen]
    if pending:
        import torch
        torch.set_num_threads(2)
        from models.image_deepfake.inference.global_classifier import GlobalClassifier
        model=GlobalClassifier('community',repo/'models/image_deepfake/artifacts/global')
        for index,row in enumerate(pending):
            result=model.predict((a.evaluation_root/'images'/row['path']).read_bytes(),return_embedding=True)
            value={**row,**result,'head_raw':head_score(result['embedding'],head)}
            value.pop('embedding')
            with cache.open('a') as f:f.write(json.dumps(value)+'\n')
            existing.append(value)
            if index%16==0:print('Existing-generator validation',index+1,'/',len(pending),flush=True)
    rows=read(folder/'real-validation-challenge.jsonl')+existing
    for row in read(folder/'features.jsonl'):
        if row['split']=='validation':rows.append({**row,'head_raw':head_score(row['embedding'],head)})
    rows+=read(a.evaluation_root/'real-high-resolution/validation.jsonl')
    # These matched controls include real JPEG degradations missing from the
    # native-photo guard. Reuse their existing primary predictions, calculating
    # head features only where the native records do not provide them.
    assert all(r['split']=='validation' for r in rows)
    real=[r for r in rows if not r['ai']]
    guard=dict(primary_raw_alert=max(r['ai_score'] for r in real)+1e-6,
               modern_raw_alert=max(r['head_raw'] for r in real)+1e-6)
    if max(guard.values())>=1:raise ValueError('A real validation photo saturates a head; candidate cannot be promoted safely')
    scores=np.array([policy_score(r['ai_score'],r['head_raw'],guard) for r in rows])
    labels=np.array([bool(r['ai']) for r in rows])
    families=Counter(r['family'] for r in rows)
    weights=np.array([1/families[r['family']] for r in rows])
    for label in [False,True]:weights[labels==label]*=len(rows)/2/weights[labels==label].sum()
    calibrator=LogisticRegression(C=1.,random_state=42).fit(np.array([logit(v) for v in scores]).reshape(-1,1),labels,sample_weight=weights)
    observed_fp=int(sum(scores[~labels]>=.5))
    if observed_fp:raise ValueError('Validation-relative boundary unexpectedly flags a real image')
    stats=dict(n=len(rows),real_families=len({r['family'] for r in real}),
        positive_alert_recall=float(np.mean(scores[labels]>=.5)),real_alerts=observed_fp,
        roc_auc=float(roc_auc_score(labels,scores,sample_weight=weights)),
        probability_scope='Platt calibration on balanced, family-weighted validation collections; deployment prevalence and unseen generators are not calibrated.')
    config_path=repo/'models/image_deepfake/calibration/evidence-v2.json'
    config=json.loads(config_path.read_text())
    config['primary_candidate_validation']=config.get('primary_candidate_validation',config['ai'])
    config['ai']={**guard,'kind':'platt_logit','coef':float(calibrator.coef_[0,0]),
        'intercept':float(calibrator.intercept_[0]),'raw_alert':.5,
        'coordinate_definition':'Sigmoid of maximum logit excess over validation-real maxima plus an epsilon guard; 0.5 is the derived boundary, not an arbitrary raw-model threshold.',
        'validation':stats}
    config['version']='evidence-v2-modern-guard-1'
    config['ai_alert']=.5
    config['ai_authentic']=max(0.,min(float(min(scores[labels])),float(np.median(scores[~labels])))-1e-6)
    localization=read(a.evaluation_root/'localizer-native-validation/predictions.jsonl')
    config['manipulation_authentic']=max(0.,min(min(r['raw_score'] for r in localization if r['manipulation']),float(np.median([r['raw_score'] for r in localization if not r['manipulation']])))-1e-6)
    config['authenticity_enabled']=False
    config['authenticity_limit']='Broad edit coverage, including generative fill, inpainting and face swap, is not established. Low model readings cannot establish authenticity.'
    head['promoted']=True;head['version']='community-modern-feature-head-1'
    head_path=repo/'models/image_deepfake/calibration/modern-feature-head.json'
    head_path.write_text(json.dumps(head,indent=2),encoding='utf-8')
    config['modern_head_sha256']=hashlib.sha256(head_path.read_bytes()).hexdigest()
    config['limits'].append('Modern feature head trained on 96 matched images from COCO and SafeIMG. Public-safety/document domains may introduce content bias; fresh OpenAI cases are diagnostics, not an independent benchmark.')
    config_path.write_text(json.dumps(config,indent=2),encoding='utf-8')
    (folder/'selected-validation-metrics.json').write_text(json.dumps(stats,indent=2))
    print(json.dumps({**stats,**guard,'ai_authentic_policy_boundary':config['ai_authentic'],
        'manipulation_authentic_raw_boundary':config['manipulation_authentic']},indent=2))


if __name__=='__main__':main()
