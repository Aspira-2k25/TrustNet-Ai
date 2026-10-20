"""Compare candidates using validation families only, without touching test labels."""
import argparse
import gc
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
    parser.add_argument('--candidate',choices=list(__import__('models.image_deepfake.inference.global_classifier',fromlist=['CANDIDATES']).CANDIDATES))
    args=parser.parse_args()
    import torch
    torch.set_num_threads(2)
    from models.image_deepfake.inference.global_classifier import GlobalClassifier,CANDIDATES
    doc=json.loads(args.manifest.read_text(encoding='utf-8'))
    rows=[r for r in doc['rows'] if r['split']==args.split and not r['manipulation']]
    args.output.mkdir(parents=True,exist_ok=True)
    for name in CANDIDATES:
        if args.candidate and name!=args.candidate:continue
        target=args.output/(name+'.jsonl')
        existing=[json.loads(line) for line in target.read_text().splitlines()] if target.exists() else []
        seen={r['sha256'] for r in existing}
        if len(seen)>=len(rows):
            print(f'{name}: reusing complete validation predictions',flush=True)
            continue
        local=Path(__file__).resolve().parents[1]/'runtime_state/image-candidates'/name
        detector=GlobalClassifier(name,model_path=local if (local/'model.safetensors').exists() else None)
        print(name,'label mapping',detector.labels,flush=True)
        for index,row in enumerate(rows):
            if row['sha256'] in seen:
                continue
            data=(args.manifest.parent/row['path']).read_bytes()
            assert hashlib.sha256(data).hexdigest()==row['sha256']
            started=time.monotonic()
            prediction=detector.predict(data)
            record={**row,**prediction,'ms':round((time.monotonic()-started)*1000)}
            with target.open('a',encoding='utf-8') as stream:
                stream.write(json.dumps(record)+'\n')
            if index%32==0:
                print(name,index+1,len(rows),'shape',prediction['original_shape'],prediction['model_view_shape'],flush=True)
        del detector
        gc.collect()


if __name__=='__main__':
    main()
