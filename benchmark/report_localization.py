"""Held-out, native-resolution IoU and real-photo region false-positive rates."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from models.image_deepfake.forensics.localization_output import pixel_mask


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evaluation-root',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    config=json.loads((root/'models/image_deepfake/calibration/evidence-v2.json').read_text())
    folder=a.evaluation_root/'localizer-native-test'
    rows=[json.loads(l) for l in (folder/'predictions.jsonl').read_text().splitlines()]
    assert len(rows)==96 and all(r['split']=='test' for r in rows)
    output=[]
    for row in rows:
        with np.load(folder/(row['sha256']+'.npz')) as z:
            mask,regions=pixel_mask(z['heatmap'],z['reliability'],config['pixel_threshold'],config['min_reliability'],config['min_area_fraction'])
        covered=row['inference_mode']=='native'
        alert=covered and row['raw_score']>=config['manipulation']['raw_alert'] and bool(regions)
        if not alert:mask[:]=0
        iou=None
        if row['mask']:
            truth=np.asarray(Image.open(a.evaluation_root/'images'/row['mask']))>0
            prediction=mask>0
            assert truth.shape==prediction.shape
            iou=float((truth&prediction).sum()/max(1,(truth|prediction).sum()))
        output.append({**row,'alert':alert,'iou':iou,'probability_calibrated':covered})
    real=[r for r in output if not r['manipulation']];fake=[r for r in output if r['manipulation']]
    report=dict(n=len(output),real_n=len(real),manipulated_n=len(fake),
        positive_recall=sum(r['alert'] for r in fake)/len(fake),
        real_region_false_positives=sum(r['alert'] for r in real),
        real_region_false_positive_rate=sum(r['alert'] for r in real)/len(real),
        mean_iou_all_manipulated=float(np.mean([r['iou'] for r in fake])),
        raw_detection_auc=float(roc_auc_score([r['manipulation'] for r in output],[r['raw_score'] for r in output])),
        per_edit={kind:dict(n=sum(r['variant']==kind for r in fake),mean_iou=float(np.mean([r['iou'] for r in fake if r['variant']==kind]))) for kind in sorted({r['variant'] for r in fake})},
        uncalibrated_tiled_images=sum(not r['probability_calibrated'] for r in output),
        limits=['Synthetic rectangular splice/copy-move only, JPEG quality 70. No independent inpainting, face-swap or object-removal IoU established.',
                'IoU includes missing/unsupported masks as zero. Real-photo false positives are measured, not guaranteed absent.'])
    (a.evaluation_root/'localization-heldout.metrics.json').write_text(json.dumps(report,indent=2))
    (a.evaluation_root/'localization-heldout.rows.json').write_text(json.dumps(output,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
