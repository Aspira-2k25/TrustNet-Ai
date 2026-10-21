"""One frozen ViT head, disjoint calibration/threshold data and sealed generator tests."""
import argparse
from collections import Counter,defaultdict
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import numpy as np
from PIL import Image,ImageOps,ImageFilter,ImageEnhance
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark.real_photo_guard import wilson

PROTOCOL={
    'version':'coverage-v3-head-224-2','backbone':'buildborderless/CommunityForensics-DeepfakeDet-ViT',
    'revision':'ac6ee457bea904a373065754107451793b56db00','feature_size':224,'seed':81327,
    'classifier':{'standardize':True,'algorithm':'LogisticRegression','C':1,'max_iter':1500},
    'training_views':2,'matched_jpeg_bytes':1048576,'calibrator':'IsotonicRegression on calibration partition only',
    'threshold':'Lowest tie-safe boundary with at most 1% threshold-partition real alerts',
    'test_policy':'Test opened only after candidate SHA/threshold freeze. No retuning after test.',
    'promotion':'Real-image test FPR <=2%, Wilson upper bound <=2%, and paired decision coverage improves without additional real alerts.',
    'authenticity':'Disabled unless separately validated manipulation coverage and all evidence gates pass.',
}

def read(path):return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def schedules(out):
    selection=json.loads((out/'source-selection.json').read_text(encoding='utf-8'))
    groups=defaultdict(list)
    for row in selection['rows']:
        identity=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
        groups[row['split'],row['positive']].append(identity)
    return {identity:index for group in groups.values() for index,identity in enumerate(sorted(group))}

def prepare(out):
    target=out/'manifest.json'
    if target.exists():return json.loads(target.read_text(encoding='utf-8'))
    # Concurrent acquisition phases may append the same completed identity; a
    # repeated cache record never becomes an extra training example.
    rows=list({r['identity']:r for r in read(out/'acquired.jsonl')}.values())
    import re
    for row in rows:
        match=re.search(r'(?:COCO_val2014_)?(\d+)\.(?:jpg|png)$',row['family'],re.I)
        if row['source'] in {'COCO','TGIF','DiTFake'}:
            token=row['family'].split(':',1)[1]
            if token.isdigit():row['family']='coco:'+str(int(token))
            elif match:row['family']='coco:'+str(int(match.group(1)))
    families=defaultdict(set);hashes=defaultdict(set)
    for row in rows:
        families[row['family']].add(row['split']);hashes[row['sha256']].add(row['split'])
    bad_family={k for k,v in families.items() if len(v)>1};bad_hash={k for k,v in hashes.items() if len(v)>1}
    rejected=[r for r in rows if r['family'] in bad_family or r['sha256'] in bad_hash]
    rows=[r for r in rows if r['family'] not in bad_family and r['sha256'] not in bad_hash]
    # Near-duplicate screen before fitting or outcomes. This is a heuristic and
    # cannot certify semantic independence or unknown upstream training batches.
    phash_path=out/'perceptual-hashes.json'
    phashes=json.loads(phash_path.read_text()) if phash_path.exists() else {}
    from scipy.fft import dctn
    for index,row in enumerate(rows):
        if row['sha256'] in phashes:continue
        with Image.open(out/row['path']) as image:
            pixels=np.asarray(image.convert('L').resize((32,32)),dtype=float)
        values=dctn(pixels,norm='ortho')[:8,:8].flatten()[1:]
        bits=values>np.median(values);phashes[row['sha256']]=int(sum(int(b)<<i for i,b in enumerate(bits)))
        if index%500==0:print('Pre-fit duplicate screen',index,'/',len(rows),flush=True)
    phash_path.write_text(json.dumps(phashes),encoding='utf-8')
    buckets=defaultdict(list);near_bad=set();near_pairs=[]
    for row_index,row in enumerate(rows):
        value=phashes[row['sha256']];candidates={i for band in range(8) for i in buckets[band,(value>>(8*band))&255]}
        for index in candidates:
            other=rows[index]
            if row['split']==other['split']:continue
            distance=(value^phashes[other['sha256']]).bit_count()
            if distance<=4:
                near_bad.update([row['identity'],other['identity']]);near_pairs.append([row['identity'],other['identity'],distance])
        for band in range(8):buckets[band,(value>>(8*band))&255].append(row_index)
    rejected.extend(r for r in rows if r['identity'] in near_bad)
    rows=[r for r in rows if r['identity'] not in near_bad]
    # Stable matching is independent of image content: both classes receive the
    # same file-type, size, quality and processing schedule within each split.
    processed=[]
    schedule=schedules(out)
    for split in ['train','calibration','threshold','test','seen_test']:
        groups={label:sorted([r for r in rows if r['split']==split and r['positive']==label],key=lambda r:r['identity']) for label in [False,True]}
        if split in {'train','calibration','threshold'}:
            count=min(len(items) for items in groups.values())
            groups={label:items[:count] for label,items in groups.items()}
        for label,items in groups.items():
            for index,row in enumerate(items):processed.append({**row,'schedule':schedule[row['identity']],'views':2 if split=='train' else 1})
    counts=Counter((r['split'],r['positive']) for r in processed)
    if min(counts['train',False],counts['train',True])<2000:raise ValueError('Fewer than 2000 acquired distinct original photos per training class')
    heldout=set(json.loads((out/'source-selection.json').read_text())['heldout_generators'])
    if any(r['generator'] in heldout and r['split']!='test' for r in processed):raise ValueError('Held-out generator leaked into development')
    doc={'protocol':PROTOCOL,'rows':processed,'counts':{str(k):v for k,v in counts.items()},'quarantined':rejected,'perceptual_cross_split_pairs':near_pairs,'source_selection_sha256':digest(out/'source-selection.json'),'limitations':['Class counts are original files, not independent scenes; SIDD scenes stay together.','Upstream ViT pretraining overlap is not known. Unseen refers to this adaptation.','Exact bytes, declared source identities and a pHash distance <=4 screen exclude cross-split duplicates; semantic independence is not guaranteed.']}
    target.write_text(json.dumps(doc,indent=2),encoding='utf-8');print('Frozen manifest',doc['counts'],'quarantine',len(rejected),flush=True);return doc

def view(out,row,augmentation,include_bytes=False):
    seed=PROTOCOL['seed']+row['schedule']*13+augmentation*100003
    rng=np.random.default_rng(seed)
    with Image.open(out/row['path']) as original:image=ImageOps.exif_transpose(original).convert('RGB')
    # All generated and real sources pass the identical transformation schedule.
    base=[384,448,512][row['schedule']%3]
    image=ImageOps.fit(image,(base,base),method=Image.Resampling.LANCZOS)
    scale=float(rng.uniform(.5,1.)) if augmentation else 1.
    size=max(192,round(base*scale));image=image.resize((size,size),Image.Resampling.LANCZOS)
    variant=row['schedule']%6 if not augmentation else int(rng.integers(0,6))
    if variant==1:image=image.filter(ImageFilter.GaussianBlur(.45 if not augmentation else float(rng.uniform(.2,1.2))))
    elif variant==2:
        arr=np.asarray(image,dtype=np.float32);image=Image.fromarray(np.clip(arr+rng.normal(0,2 if not augmentation else 4,arr.shape),0,255).astype(np.uint8))
    elif variant==3:image=ImageEnhance.Color(image).enhance(.8)
    elif variant==4:image=ImageEnhance.Brightness(image).enhance(.65)
    elif variant==5:
        canvas=Image.new('RGB',(size,size+32),'#ececec');canvas.paste(image,(0,32));image=canvas
    buffer=io.BytesIO();image.save(buffer,'JPEG',quality=int(rng.integers(40,96)),subsampling=2)
    data=buffer.getvalue()
    if len(data)>PROTOCOL['matched_jpeg_bytes']:raise ValueError('Matched JPEG control exceeds its byte budget')
    data+=b'\0'*(PROTOCOL['matched_jpeg_bytes']-len(data))
    result=(Image.open(io.BytesIO(data)).convert('RGB'),hashlib.sha256(data).hexdigest())
    return (*result,data) if include_bytes else result

def feature_batch(processor, images):
    batch=processor(images=images,size={'shortest_edge':224},crop_size={'height':224,'width':224},return_tensors='pt')
    if tuple(batch['pixel_values'].shape[-2:]) != (224,224):
        raise ValueError('Feature processor did not produce the declared 224 pixel view')
    return batch


def features(out,doc,test=False,model=None):
    import torch
    from models.image_deepfake.inference.global_classifier import GlobalClassifier
    torch.set_num_threads(4)
    contract={'source_selection_sha256':digest(out/'source-selection.json'),'protocol':PROTOCOL}
    contract_path=out/'feature-cache-contract.json'
    if contract_path.exists() and json.loads(contract_path.read_text())!=contract:raise ValueError('Feature-cache contract changed; do not reuse incompatible features')
    if not contract_path.exists():contract_path.write_text(json.dumps(contract,indent=2),encoding='utf-8')
    path=out/('test-features.jsonl' if test else 'development-features.jsonl')
    allowed={r['identity']:r for r in doc['rows']}
    existing=[r for r in read(path) if r['identity'] in allowed] if path.exists() else []
    for record in existing:
        row=allowed[record['identity']]
        if record['schedule']!=row['schedule']:raise ValueError('Cached feature augmentation schedule changed')
        record['family']=row['family']
    seen={(r['identity'],r['view']) for r in existing}
    splits={'test','seen_test'} if test else {'train','calibration','threshold'}
    pending=[(r,v) for r in doc['rows'] if r['split'] in splits for v in range(r['views']) if (r['identity'],v) not in seen]
    if not pending:return existing
    if model is None:model=GlobalClassifier('community',Path(__file__).resolve().parents[1]/'models/image_deepfake/artifacts/global')
    started=time.monotonic()
    for start in range(0,len(pending),16):
        group=pending[start:start+16];images=[view(out,row,v) for row,v in group]
        batch=feature_batch(model.processor,[x[0] for x in images])
        with torch.inference_mode():
            emb=model.model.vit(**batch,interpolate_pos_encoding=True).last_hidden_state[:,0].cpu().numpy()
            baseline=None
            if test:
                original_view=model.processor(images=[x[0] for x in images],return_tensors='pt')
                baseline=torch.sigmoid(model.model(**original_view).logits[:,0]).cpu().numpy()
        with path.open('a',encoding='utf-8') as stream:
            for index,((row,v),(image,sha),vector) in enumerate(zip(group,images,emb)):
                record={k:row[k] for k in ['identity','family','split','source','generator','positive','schedule']};record.update(view=v,view_sha256=sha,embedding=vector.tolist())
                record['control_features']=[image.width,image.height,PROTOCOL['matched_jpeg_bytes'],1]
                if baseline is not None:record['baseline_primary_raw']=float(baseline[index])
                stream.write(json.dumps(record)+'\n');existing.append(record)
        if start%128==0:print('Frozen features',start+len(group),'/',len(pending),'elapsed',round(time.monotonic()-started),'seconds',flush=True)
    return existing

def select_threshold(labels,scores,target=.01):
    labels=np.asarray(labels,dtype=bool);scores=np.asarray(scores,dtype=float)
    if not (~labels).any():raise ValueError('Threshold selection requires real negatives')
    choices=np.unique(np.r_[scores,np.nextafter(max(scores),np.inf)])
    return float(next(t for t in choices if np.mean(scores[~labels]>=t)<=target))

def train(out,doc):
    target=out/'candidate.json'
    if target.exists():
        head=json.loads(target.read_text(encoding='utf-8'))
        if head['manifest_sha256']!=digest(out/'manifest.json') or head['protocol']!=PROTOCOL:raise ValueError('Frozen candidate does not match this dataset/protocol')
        return head
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import roc_auc_score
    data=features(out,doc)
    tr=[r for r in data if r['split']=='train'];ca=[r for r in data if r['split']=='calibration'];th=[r for r in data if r['split']=='threshold']
    by_id={r['identity']:r for r in doc['rows']}
    for row in tr+ca:
        if 'control_features' not in row:
            image,_=view(out,by_id[row['identity']],row['view'])
            row['control_features']=[image.width,image.height,PROTOCOL['matched_jpeg_bytes'],1]
    x=np.asarray([r['embedding'] for r in tr]);y=np.asarray([r['positive'] for r in tr])
    scaler=StandardScaler().fit(x);model=LogisticRegression(C=1,max_iter=1500,class_weight='balanced',random_state=81327).fit(scaler.transform(x),y)
    shortcut=None
    if all('control_features' in r for r in tr+ca):
        from sklearn.pipeline import make_pipeline
        control=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=1500,random_state=81327))
        control.fit([r['control_features'] for r in tr],y)
        shortcut={'features':['encoded_width','encoded_height','padded_file_bytes','jpeg_flag'],
            'calibration_roc_auc':float(roc_auc_score([r['positive'] for r in ca],control.predict_proba([r['control_features'] for r in ca])[:,1])),
            'note':'Development-only shortcut check. Original container/size labels are removed by matched JPEG encoding; this does not exclude every content shortcut.'}
    def predict(rows):return model.predict_proba(scaler.transform([r['embedding'] for r in rows]))[:,1]
    iso=IsotonicRegression(out_of_bounds='clip').fit(predict(ca),[r['positive'] for r in ca])
    probabilities=iso.predict(predict(th));threshold=select_threshold([r['positive'] for r in th],probabilities)
    record={'version':PROTOCOL['version'],'feature_input_size':224,'feature':'ViT CLS with bicubic position interpolation at 224 pixels','backbone_revision':PROTOCOL['revision'],'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'coef':model.coef_[0].tolist(),'intercept':float(model.intercept_[0]),'isotonic_x':iso.X_thresholds_.tolist(),'isotonic_y':iso.y_thresholds_.tolist(),'threshold':threshold,'manifest_sha256':digest(out/'manifest.json'),'protocol':PROTOCOL,'training_originals':Counter(str(r['positive']) for r in doc['rows'] if r['split']=='train'),'training_views':len(tr),'calibration_n':len(ca),'threshold_n':len(th),'threshold_real_fpr':float(np.mean(probabilities[np.array([not r['positive'] for r in th])]>=threshold)),'promoted':False}
    record['shortcut_control']=shortcut
    target.write_text(json.dumps(record,indent=2),encoding='utf-8');print('FROZEN candidate',digest(target),'threshold',threshold,'validation FPR',record['threshold_real_fpr'],flush=True);return record

def score(head,rows):
    from scipy.special import expit
    raw=expit(((np.array([r['embedding'] for r in rows])-head['mean'])/head['scale'])@head['coef']+head['intercept'])
    return np.interp(raw,head['isotonic_x'],head['isotonic_y'])

def evaluate(out,doc,head):
    # This function cannot fit, calibrate or select thresholds.
    data=features(out,doc,test=True);prob=score(head,data);threshold=head['threshold']
    def summary(rows,scores):
        y=np.array([r['positive'] for r in rows]);pred=scores>=threshold;real=int(sum(~y));fp=int(sum(pred&~y));tp=int(sum(pred&y));n=len(rows)
        return {'n':n,'real':real,'generated':int(sum(y)),'tp':tp,'fp':fp,'recall':tp/int(sum(y)) if any(y) else None,'real_fpr':fp/real if real else None,'real_fpr_wilson95':wilson(fp,real),'ai_stream_inconclusive_rate':float(np.mean(~pred)),'note':'AI-stream coverage only; low scores remain Inconclusive, not authentic.'}
    results={}
    for split in ['test','seen_test']:
        indexes=np.array([r['split']==split for r in data]);group=[r for r in data if r['split']==split]
        results[split]=summary(group,prob[indexes]);results[split]['by_generator']={g:summary([r for r in group if r['generator']==g],prob[np.array([r['split']==split and r['generator']==g for r in data])]) for g in sorted({r['generator'] for r in group})};results[split]['by_real_source']={g:summary([r for r in group if r['source']==g and not r['positive']],prob[np.array([r['split']==split and r['source']==g and not r['positive'] for r in data])]) for g in sorted({r['source'] for r in group if not r['positive']})}
        if split=='test':
            from sklearn.metrics import roc_auc_score,precision_score,recall_score,f1_score,accuracy_score
            labels=[r['positive'] for r in group];scores=prob[indexes];alerts=scores>=threshold
            results[split]['binary_ai_alarm_metrics']={'roc_auc':float(roc_auc_score(labels,scores)),
                'precision':float(precision_score(labels,alerts,zero_division=0)),
                'recall':float(recall_score(labels,alerts,zero_division=0)),
                'f1':float(f1_score(labels,alerts,zero_division=0)),
                'accuracy':float(accuracy_score(labels,alerts)),
                'scope':'Binary AI alarm metrics, not four-verdict authenticity accuracy; below threshold remains Inconclusive.'}
            results[split]['by_processing_proxy']={str(v):summary([r for r in group if r['schedule']%6==v],scores[np.array([r['schedule']%6==v for r in group])]) for v in range(6)}
    baseline_threshold=.3546251223812103
    baseline=np.asarray([r['baseline_primary_raw']>=baseline_threshold for r in data]);test_indexes=np.array([r['split']=='test' for r in data]);truth=np.array([r['positive'] for r in data]);real=test_indexes&~truth;fake=test_indexes&truth
    prior={'real_fpr':float(np.mean(baseline[real])),'real_fpr_wilson95':wilson(int(sum(baseline[real])),int(sum(real))),'generated_recall':float(np.mean(baseline[fake])),'ai_stream_inconclusive_rate':float(np.mean(~baseline[test_indexes])),'scope':'Frozen existing primary-model alert boundary, generation stream only. Manipulation/provenance/authenticity decisions require separate paired pipeline checks.'}
    report={'candidate_sha256':digest(out/'candidate.json'),'manifest_sha256':digest(out/'manifest.json'),'threshold':threshold,'baseline_ai_stream':prior,'results':results,'limits':doc['limitations']+['Wilson assumes independent photos; correlated camera/scene captures weaken that assumption.','No deployment promotion or authenticity enablement follows from classifier metrics alone.']}
    (out/'holdout-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)
    target=out/'holdout-predictions.jsonl'
    with target.open('w',encoding='utf-8') as stream:
        for row,p in zip(data,prob):stream.write(json.dumps({k:v for k,v in row.items() if k!='embedding'}|{'probability':float(p),'alert':bool(p>=threshold)})+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--evaluate',action='store_true');p.add_argument('--prefetch',action='store_true');a=p.parse_args();out=a.output.resolve()
    if out.is_relative_to(Path(__file__).resolve().parents[1]):raise SystemExit('Research outputs must stay outside the application')
    if a.prefetch:
        from models.image_deepfake.inference.global_classifier import GlobalClassifier
        import torch
        torch.set_num_threads(4)
        model=GlobalClassifier('community',Path(__file__).resolve().parents[1]/'models/image_deepfake/artifacts/global');schedule=schedules(out)
        while True:
            rows=list({r['identity']:r for r in read(out/'acquired.jsonl')}.values())
            pending=[{**r,'schedule':schedule[r['identity']],'views':2 if r['split']=='train' else 1} for r in rows if r['split'] not in {'test','seen_test'}]
            features(out,{'rows':pending},model=model)
            print('Prefetch caught up with acquired development sources:',len(pending),flush=True)
            time.sleep(15)
    doc=prepare(out);head=train(out,doc)
    if a.evaluate:evaluate(out,doc,head)

if __name__=='__main__':main()
