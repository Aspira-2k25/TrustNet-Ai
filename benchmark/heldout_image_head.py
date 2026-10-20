"""Score frozen, previously unused adaptation and high-resolution holdouts."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evaluation-root',type=Path,required=True)
    a=p.parse_args();repo=Path(__file__).resolve().parents[1]
    import torch
    torch.set_num_threads(2)
    from models.image_deepfake.inference.global_classifier import GlobalClassifier
    from models.image_deepfake.inference.feature_head import head_score,policy_score
    cfgpath=repo/'models/image_deepfake/calibration/evidence-v2.json'
    cfg=json.loads(cfgpath.read_text(encoding='utf-8'))
    head=json.loads((repo/'models/image_deepfake/calibration/modern-feature-head.json').read_text(encoding='utf-8'))
    fingerprint=hashlib.sha256(cfgpath.read_bytes()).hexdigest()
    target=a.evaluation_root/'adaptation/heldout-predictions.jsonl'
    existing=[json.loads(l) for l in target.read_text(encoding='utf-8').splitlines()] if target.exists() else []
    assert all(r['config_sha256']==fingerprint for r in existing),'Configuration changed after holdout scoring; do not silently retune.'
    seen={r['sha256'] for r in existing};model=None
    for folder in ['adaptation','real-high-resolution']:
        rows=json.loads((a.evaluation_root/folder/'manifest.json').read_text(encoding='utf-8'))['rows']
        for row in rows:
            if row['split']!='test' or row['sha256'] in seen:continue
            if model is None:model=GlobalClassifier('community',repo/'models/image_deepfake/artifacts/global')
            result=model.predict((a.evaluation_root/folder/row['path']).read_bytes(),return_embedding=True)
            modern=head_score(result.pop('embedding'),head)
            score=policy_score(result['ai_score'],modern,cfg['ai'])
            value={**row,**result,'head_raw':modern,'policy_score':score,'alert':score>=cfg['ai']['raw_alert'],'cohort':folder,'config_sha256':fingerprint}
            with target.open('a',encoding='utf-8') as f:f.write(json.dumps(value)+'\n')
            existing.append(value);print(folder,len(existing),'ai',row['ai'],'alert',value['alert'],flush=True)
    report={}
    from sklearn.metrics import roc_auc_score
    for cohort in ['adaptation','real-high-resolution']:
        group=[r for r in existing if r['cohort']==cohort];real=[r for r in group if not r['ai']];fake=[r for r in group if r['ai']]
        report[cohort]={'n':len(group),'real_alerts':sum(r['alert'] for r in real),'real_n':len(real),'positive_alerts':sum(r['alert'] for r in fake),'positive_n':len(fake),'roc_auc':roc_auc_score([r['ai'] for r in group],[r['policy_score'] for r in group]) if real and fake else None}
    report['scope']='AI classifier stream only. No claim about full detector accuracy or localization. Fixed boundaries; never tune using these scores.'
    target.with_suffix('.metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
