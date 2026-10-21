"""Fit portable native-feature heads, then evaluate one frozen choice once.

Calibration and threshold/mixture selection use development partitions only.
This tool never deploys weights. AI-stream success does not certify the entire
image pipeline or unsupported manipulation types.
"""
import argparse,hashlib,json,sys,time
from pathlib import Path
from dataclasses import asdict
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark.coverage_train import select_threshold
from benchmark.real_photo_guard import wilson
from models.image_deepfake.inference.native_features import CropContract


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def features(source,cache,names,test=False):
    doc=json.loads((source/'manifest.json').read_text());rows=[r for r in doc['rows'] if (r['split']=='test' if test else r['split'] in {'train','calibration','threshold'})]
    vectors=[]
    for name in names:
        contract=json.loads((cache/(name+'-contract.json')).read_text())
        if contract['manifest_sha256']!=digest(source/'manifest.json') or contract['crops']!=asdict(CropContract()):raise ValueError('Incompatible feature cache')
        records={r['identity']:r for r in read(cache/(name+'-features.jsonl'))}
        missing=[r['identity'] for r in rows if r['identity'] not in records]
        if missing:raise ValueError(f'{name}: {len(missing)} source features are not complete')
        for row in rows:
            if records[row['identity']]['sha256']!=row['sha256']:raise ValueError('Source bytes changed')
        vectors.append(np.asarray([records[r['identity']]['embedding'] for r in rows],np.float32))
    return rows,np.concatenate(vectors,axis=1)


def primary_scores(source,rows,target):
    existing={r['identity']:r for r in read(target)} if target.exists() else {}
    pending=[r for r in rows if r['identity'] not in existing]
    if pending:
        import torch
        from PIL import Image,ImageOps
        from models.image_deepfake.inference.global_classifier import GlobalClassifier
        torch.set_num_threads(4);model=GlobalClassifier('community',Path(__file__).resolve().parents[1]/'models/image_deepfake/artifacts/global')
        for start in range(0,len(pending),8):
            group=pending[start:start+8];images=[]
            for row in group:
                data=(source/row['path']).read_bytes()
                if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Source bytes changed')
                import io
                with Image.open(io.BytesIO(data)) as image:images.append(ImageOps.exif_transpose(image).convert('RGB'))
            batch=model.processor(images=images,return_tensors='pt')
            with torch.inference_mode():scores=model.model(**batch).logits[:,0].sigmoid().cpu().tolist()
            with target.open('a') as stream:
                for row,score in zip(group,scores):
                    record={'identity':row['identity'],'sha256':row['sha256'],'score':score};existing[row['identity']]=record;stream.write(json.dumps(record)+'\n')
            if start%128==0:print('Paired primary',start+len(group),'/',len(pending),flush=True)
    for row in rows:
        if existing[row['identity']]['sha256']!=row['sha256']:raise ValueError('Primary cache source changed')
    return np.array([existing[r['identity']]['score'] for r in rows])


def fit(source,cache,holdout,names):
    target=cache/'candidate.json'
    if target.exists():
        head=json.loads(target.read_text())
        if head['development_manifest_sha256']!=digest(source/'manifest.json') or head['holdout_manifest_sha256']!=digest(holdout/'manifest.json') or head['backbones']!=names:raise ValueError('Frozen candidate contract changed')
        return head
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.isotonic import IsotonicRegression
    rows,x=features(source,cache,names);y=np.array([r['positive'] for r in rows]);splits=np.array([r['split'] for r in rows]);tr=splits=='train';ca=splits=='calibration';th=splits=='threshold'
    if min(sum(tr&y),sum(tr&~y))<2000:raise ValueError('At least 2000 original files per training class are required')
    augmented_rows=[r for r in rows if r['split']=='train' and int(r['sha256'][:8],16)%4==0];augmented_vectors=[]
    for name in names:
        records={r['identity']:r for r in read(cache/(name+'-augmented.jsonl'))}
        if any(r['identity'] not in records or records[r['identity']]['sha256']!=r['sha256'] for r in augmented_rows):raise ValueError('Training stress views are incomplete or changed')
        augmented_vectors.append(np.asarray([records[r['identity']]['embedding'] for r in augmented_rows],np.float32))
    xtrain=np.vstack([x[tr],np.concatenate(augmented_vectors,axis=1)]);ytrain=np.r_[y[tr],[r['positive'] for r in augmented_rows]]
    scaler=StandardScaler().fit(xtrain);model=LogisticRegression(C=1,class_weight='balanced',max_iter=1500,random_state=81327).fit(scaler.transform(xtrain),ytrain);raw=model.predict_proba(scaler.transform(x))[:,1]
    if max(model.n_iter_)>=1500:raise ValueError('Linear head did not converge; do not freeze or evaluate it')
    selected_rows=[r for r in rows if r['split']!='train'];primary=primary_scores(source,selected_rows,cache/'primary-development.jsonl');raw_dev=raw[~tr];y_dev=y[~tr];ca_dev=splits[~tr]=='calibration';th_dev=~ca_dev
    options=[]
    for name,pred in [('native_head',raw_dev),('primary_native_mean',.5*(primary+raw_dev))]:
        iso=IsotonicRegression(out_of_bounds='clip').fit(pred[ca_dev],y_dev[ca_dev]);scores=iso.predict(pred[th_dev]);threshold=select_threshold(y_dev[th_dev],scores,target=.01)
        options.append({'name':name,'isotonic_x':iso.X_thresholds_.tolist(),'isotonic_y':iso.y_thresholds_.tolist(),'threshold':threshold,'selection_recall':float(np.mean(scores[y_dev[th_dev]]>=threshold)),'selection_real_fpr':float(np.mean(scores[~y_dev[th_dev]]>=threshold))})
    choice=max(options,key=lambda item:(item['selection_recall'],-item['selection_real_fpr'],item['name']=='native_head'))
    # Verify a metadata shortcut on the ACTUAL crop input. Also report original
    # source metadata separately; constant crop geometry cannot exclude JPEG history.
    from sklearn.metrics import roc_auc_score
    controls=[]
    for row in rows:
        path=source/row['path']
        with path.open('rb') as stream:jpeg=stream.read(2)==b'\xff\xd8'
        controls.append([row['width'],row['height'],path.stat().st_size,int(jpeg)])
    controls=np.asarray(controls)
    control_scaler=StandardScaler().fit(controls[tr]);control=LogisticRegression(max_iter=1500,class_weight='balanced').fit(control_scaler.transform(controls[tr]),y[tr])
    auc=float(roc_auc_score(y[ca],control.predict_proba(control_scaler.transform(controls[ca]))[:,1]))
    head={'version':'native-crops-head-v1','backbones':names,'crop_contract':asdict(CropContract()),'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'coef':model.coef_[0].tolist(),'intercept':float(model.intercept_[0]),'choice':choice,'development_options':options,'development_manifest_sha256':digest(source/'manifest.json'),'holdout_manifest_sha256':digest(holdout/'manifest.json'),'original_metadata_shortcut_auc':auc,'input_metadata_note':'Native crops are RGB tensors of the same dimensions; original container metadata is not a model input. Source compression/content shortcuts may remain.','training_originals':{'real':int(sum(tr&~y)),'fake':int(sum(tr&y))},'training_stress_views':len(augmented_rows),'promotion':'Not deployed. Require independent AI-stream and full-pipeline real-photo guard checks.'}
    target.write_text(json.dumps(head,indent=2));print('FROZEN',digest(target),choice,flush=True);return head


def evaluate(source,cache,head,output):
    from scipy.special import expit
    from sklearn.metrics import roc_auc_score
    if digest(source/'manifest.json')!=head['holdout_manifest_sha256']:raise ValueError('Frozen candidate does not match this test manifest')
    rows,x=features(source,cache,head['backbones'],test=True);raw=expit(((x-head['mean'])/head['scale'])@head['coef']+head['intercept']);primary=primary_scores(source,rows,cache/'primary-test.jsonl');choice=head['choice'];mixed=raw if choice['name']=='native_head' else .5*(primary+raw);scores=np.interp(mixed,choice['isotonic_x'],choice['isotonic_y']);y=np.array([r['positive'] for r in rows],dtype=bool);pred=scores>=choice['threshold'];baseline=primary>=.3546251223812103
    if not np.isfinite(scores).all() or not np.isfinite(primary).all():raise ValueError('Nonfinite model output; evaluation invalid')
    def metrics(alerts,index,readings):
        truth=y[index];values=alerts[index];real=int(sum(~truth));fake=int(sum(truth));fp=int(sum(values&~truth));tp=int(sum(values&truth))
        fn=fake-tp;tn=real-fp
        return {'n':len(truth),'real_n':real,'fake_n':fake,'tp':tp,'fp':fp,'tn':tn,'fn':fn,'accuracy':(tp+tn)/len(truth),'precision':tp/(tp+fp) if tp+fp else None,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,'roc_auc':float(roc_auc_score(truth,readings[index])) if real and fake else None,'recall':tp/fake if fake else None,'real_fpr':fp/real if real else None,'real_fpr_wilson95':wilson(fp,real) if real else None,'ai_stream_inconclusive_rate':float(np.mean(~values))}
    indexes=np.ones(len(y),bool);report={'candidate_content_sha256':hashlib.sha256(json.dumps(head,sort_keys=True).encode()).hexdigest(),'test_manifest_sha256':digest(source/'manifest.json'),'baseline':metrics(baseline,indexes,primary),'candidate':metrics(pred,indexes,scores),'per_generator':{g:{'baseline':metrics(baseline,np.array([r['generator']==g for r in rows]),primary),'candidate':metrics(pred,np.array([r['generator']==g for r in rows]),scores)} for g in sorted({r['generator'] for r in rows if r['positive']})},'limits':['AI stream only, not combined manipulation false alerts or a four-verdict authenticity accuracy.','Accuracy/F1 treat no alert as negative for binary evaluation; runtime no-alert results remain uncertain, not authenticated real.','Test image identities are fresh, but generator identities were observed in a prior experiment.','No GPT-image/Imagen accuracy claim. No test tuning.']}
    report['ai_stream_gate_passed']=report['candidate']['real_fpr_wilson95'][1]<=.02 and report['candidate']['recall']>report['baseline']['recall']
    shortcut_auc=head.get('original_metadata_shortcut_auc')
    report['source_metadata_shortcut_gate_passed']=shortcut_auc is not None and abs(shortcut_auc-.5)<=.05
    report['promotion_eligible']=False
    report['promotion_blockers']=['Full-pipeline real-photo guard and runtime parity/latency verification remain required.']
    if not report['source_metadata_shortcut_gate_passed']:
        report['promotion_blockers'].append('Source-file metadata predicts the development labels above the near-chance target. Resolve source/format/size and compression-history confounds with controlled-input evaluation before deployment; crop geometry alone is not proof.')
    if not report['ai_stream_gate_passed']:report['promotion_blockers'].append('Independent AI-stream recall/FPR promotion gate failed.')
    report['deployed']=False
    output.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--holdout',type=Path);p.add_argument('--candidate',type=Path);p.add_argument('--backbones',nargs='+',default=['community','dino','openclip']);p.add_argument('--evaluate',action='store_true');a=p.parse_args()
    if a.evaluate:evaluate(a.source,a.cache,json.loads(a.candidate.read_text()),a.cache/'holdout-report.json')
    else:fit(a.source,a.cache,a.holdout,a.backbones)

if __name__=='__main__':main()
