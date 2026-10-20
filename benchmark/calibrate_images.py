"""Fit portable calibration and mask boundaries on validation families only."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from models.image_deepfake.forensics.localization_output import pixel_mask


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def fit(rows, score, target):
    assert all(r['split']=='validation' for r in rows)
    x=np.array([r[score] for r in rows]); y=np.array([bool(r[target]) for r in rows])
    model=IsotonicRegression(out_of_bounds='clip').fit(x,y)
    # A strict boundary above every observed real score. This is an observed
    # validation constraint, not a population false-positive guarantee.
    boundary=float(np.nextafter(max(x[~y]),np.inf))
    calibrated_boundary=float(model.predict([boundary])[0])
    return dict(x=model.X_thresholds_.tolist(),y=model.y_thresholds_.tolist(),
        raw_alert=boundary,alert=calibrated_boundary,n=len(rows),
        real_families=len({r['family'] for r in rows if not r[target]}),
        roc_auc=float(roc_auc_score(y,x)),observed_real_alerts=0,
        recall_above_real_max=float(np.mean(x[y]>=boundary)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    ai=read(a.root/'image-candidates-controlled/community.jsonl')
    locdir=a.root/'localizer-native-validation'
    loc=read(locdir/'predictions.jsonl')
    best=None
    # Coarse, declared grid. Optimize masks independently from global AI scores.
    cached=[]
    for r in loc:
        with np.load(locdir/(r['sha256']+'.npz')) as z:
            heat=z['heatmap'].copy(); reliability=z['reliability'].copy()
        truth=np.asarray(Image.open(a.root/'images'/r['mask']))>0 if r['mask'] else np.zeros(heat.shape,bool)
        cached.append((r,heat,reliability,truth))
    for threshold in [.5,.7,.85,.95,.99]:
        for reliability in [.25,.5,.75]:
            false_masks=0; ious=[]
            for r,h,c,t in cached:
                mask,_=pixel_mask(h,c,threshold,reliability,.001)
                m=mask>0
                if r['manipulation']:
                    ious.append(float((m&t).sum()/max(1,(m|t).sum())))
                elif m.any():false_masks+=1
            candidate=(false_masks<=1,float(np.mean(ious)), -false_masks,threshold,reliability)
            # Feasible candidates first, then average IoU. If none is feasible,
            # report the failure rather than declaring the masks validated.
            if best is None or candidate>best:best=candidate
    passed,iou,negative_fp,threshold,reliability=best
    config=dict(version='evidence-v2-validation-1',calibration_ready=True,
        ai=fit(ai,'ai_score','ai'),manipulation=fit(loc,'raw_score','manipulation'),
        pixel_threshold=threshold,min_reliability=reliability,min_area_fraction=.001,
        mask_validation=dict(passed=passed,mean_iou=iou,real_images_with_regions=-negative_fp),
        ai_authentic=0.,manipulation_authentic=0.,authenticity_enabled=False,
        authenticity_limit='Pixel-only authenticity conclusions disabled: all three tested classifiers missed a fresh OpenAI-generated diagnostic. Low scores cannot rule out modern generators.',
        manipulation_scope='Native single-frame JPEG validation; tiled scores and unseen edit types are not calibrated.',
        limits=['Small validation set and correlated degradation variants; thresholds do not guarantee a population false-positive rate.',
                'No validated GPT-image, Midjourney, Gemini, face-swap or generative-inpainting recall.',
                'Synthetic splice and copy-move masks do not represent every real edit.'],
        inputs={str(f.relative_to(a.root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [a.root/'image-candidates-controlled/community.jsonl',locdir/'predictions.jsonl']})
    config['ai_alert']=config['ai']['alert'];config['manipulation_alert']=config['manipulation']['alert']
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(config,indent=2),encoding='utf-8')
    print(json.dumps(config,indent=2))


if __name__=='__main__':main()
