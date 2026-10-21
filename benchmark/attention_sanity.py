"""Matched-area deletion test on already-observed diagnostic images, CPU only."""
import argparse,io,json,sys,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageFilter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from models.image_deepfake.inference.global_classifier import GlobalClassifier
from models.image_deepfake.explainability.grad_cam import generate


def png(array):
    stream=io.BytesIO();Image.fromarray(array).save(stream,'PNG');return stream.getvalue()


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--n',type=int,default=12);a=p.parse_args()
    import torch
    torch.set_num_threads(2)
    model=GlobalClassifier('community',Path(__file__).resolve().parents[1]/'models/image_deepfake/artifacts/global')
    rows=json.loads((a.source/'manifest.json').read_text())['rows'];selected=[]
    for label in [False,True]:selected.extend(sorted([r for r in rows if r['split']=='test' and r['positive']==label],key=lambda r:r['identity'])[:a.n//2])
    results=[]
    for row in selected:
        data=(a.source/row['path']).read_bytes()
        with Image.open(io.BytesIO(data)) as image:rgb=np.asarray(ImageOps.exif_transpose(image).convert('RGB'))
        mapped=generate(model.model,model.processor,data,return_map=True)
        heat=mapped['heatmap'];coverage=mapped['coverage'];h,w=heat.shape
        cells=[]
        for y in range(0,h-31,32):
            for x in range(0,w-31,32):
                if coverage[y:y+32,x:x+32].all():cells.append((x,y,float(heat[y:y+32,x:x+32].mean())))
        if len(cells)<10:continue
        k=max(1,round(len(cells)*.1));top=sorted(cells,key=lambda c:c[2],reverse=True)[:k]
        blurred=np.asarray(Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(12)))
        def deleted(cells):
            pixels=rgb.copy()
            for x,y,_ in cells:pixels[y:y+32,x:x+32]=blurred[y:y+32,x:x+32]
            return model.predict(png(pixels))['ai_score']
        baseline=model.predict(png(rgb))['ai_score'];high_drop=baseline-deleted(top)
        rng=np.random.default_rng(81327);random_drops=[baseline-deleted([cells[i] for i in rng.choice(len(cells),k,replace=False)]) for _ in range(3)]
        record={'identity':row['identity'],'positive':row['positive'],'generator':row['generator'],'source':row['source'],'ai_score':baseline,'selected_cells':k,'cell_size':32,'highlighted_deletion_drop':high_drop,'random_deletion_drop':float(np.mean(random_drops)),'beats_random':bool(high_drop>np.mean(random_drops))}
        results.append(record);print(json.dumps(record),flush=True)
    report={'method':'Original-geometry Grad-CAM; top 10% fully visible 32px cells versus three fixed random equal-area controls; Gaussian blur deletion','scope':'Previously observed diagnostic images; not an accuracy/generalization test','n':len(results),'mean_highlighted_drop':float(np.mean([r['highlighted_deletion_drop'] for r in results])),'mean_random_drop':float(np.mean([r['random_deletion_drop'] for r in results])),'wins':sum(r['beats_random'] for r in results),'rows':results}
    report['passed']=report['mean_highlighted_drop']>report['mean_random_drop'] and report['wins']>len(results)/2
    a.output.write_text(json.dumps(report,indent=2));print('SANITY',json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)

if __name__=='__main__':main()
