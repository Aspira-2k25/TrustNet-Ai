"""Cache genuine native segmentation outputs for calibration and held-out IoU."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--split',choices=['validation','test'],default='validation')
    parser.add_argument('--limit',type=int)
    args=parser.parse_args()
    import torch
    torch.set_num_threads(2)
    import numpy as np
    from models.image_deepfake.inference.localizer import TruForLocalizer
    doc=json.loads(args.manifest.read_text(encoding='utf-8'))
    rows=[r for r in doc['rows'] if r['split']==args.split]
    if args.limit:rows=rows[:args.limit]
    args.output.mkdir(parents=True,exist_ok=True)
    pending=[r for r in rows if not (args.output/(r['sha256']+'.npz')).exists()]
    if not pending:
        print('All segmentation outputs already cached; no inference repeated.')
        return
    detector=TruForLocalizer()
    for index,row in enumerate(pending):
        data=(args.manifest.parent/row['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==row['sha256']
        started=time.monotonic()
        result=detector.predict(data)
        np.savez_compressed(args.output/(row['sha256']+'.npz'),heatmap=result.pop('heatmap'),
                            reliability=result.pop('reliability'))
        record={**row,**result,'ms':round((time.monotonic()-started)*1000)}
        with (args.output/'predictions.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(record)+'\n')
        print(f"{index+1}/{len(pending)} {row['variant']} raw={result['raw_score']:.5f} tiles={result['tiles']} native={result['width']}x{result['height']} ms={record['ms']}",flush=True)


if __name__=='__main__':
    main()
