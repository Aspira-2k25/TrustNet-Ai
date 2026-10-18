"""Fine-tune BERT classification head and encoder on frozen URL partitions.

Defaults use the full training partition. --max-train-rows is explicitly a
development experiment; its artifact is tagged and cannot be called a full run.
Downloads must be performed explicitly into a local source directory first.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import time
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from models.phishing_url.preprocessing.bert_tokenizer import BERT_MODEL, BERT_REVISION, BERT_PREPROCESSING, MAX_LENGTH, serialize_url
from models.phishing_url.evaluation.metrics import metrics

class URLDataset(Dataset):
    def __init__(self, rows, tokenizer):
        self.rows, self.tokenizer = rows, tokenizer
    def __len__(self):
        return len(self.rows)
    def __getitem__(self, index):
        row = self.rows[index]
        tokens = self.tokenizer(serialize_url(row["url"]), truncation=True, padding="max_length", max_length=MAX_LENGTH, return_tensors="pt")
        return {**{k: v.squeeze(0) for k, v in tokens.items()}, "labels": torch.tensor(int(row["label"]))}

def predict(model, tokenizer, rows, device, batch_size=8):
    model.eval()
    values = []
    with torch.no_grad():
        for batch in DataLoader(URLDataset(rows, tokenizer), batch_size=batch_size):
            batch.pop("labels")
            logits = model(**{k: v.to(device) for k, v in batch.items()}).logits
            values.extend(torch.softmax(logits, dim=1)[:, 1].cpu().tolist())
    return np.array(values)

def train(dataset, source, output, epochs=3, batch_size=8, max_train_rows=None, resume=False, checkpoint_steps=500):
    from models.phishing_url.training.train_baselines import load_rows
    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    torch.set_num_threads(4)
    rows = load_rows(dataset)
    training = [r for r in rows if r["split"] == "train"]
    validation = [r for r in rows if r["split"] == "validation"]
    selection = [r for r in validation if int(hashlib.sha256(r["domain_group"].encode()).hexdigest()[:8],16)%3 == 0]
    if epochs < 1 or batch_size < 1 or checkpoint_steps < 1 or {r["label"] for r in selection} != {"0","1"}:
        raise ValueError("Invalid training settings or selection validation")
    if max_train_rows:
        random.Random(42).shuffle(training)
        training = training[:max_train_rows]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(source, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(source, num_labels=2, local_files_only=True).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    best_loss, stale, history = float("inf"), 0, []
    from .checkpoint import save, restore
    signature={'dataset_sha256':hashlib.sha256(Path(dataset).read_bytes()).hexdigest(),'revision':BERT_REVISION,'epochs':epochs,'batch_size':batch_size,'max_train_rows':max_train_rows,'max_length':MAX_LENGTH}
    checkpoint=output/'resume.pt'
    progress={'epoch':0,'next_step':0,'loss_sum':0.,'loss_count':0,'best_loss':best_loss,'stale':stale,'history':history}
    if resume:
        if not checkpoint.exists():raise ValueError('Resume checkpoint missing')
        progress=restore(checkpoint,model,optimizer,signature,device)
        best_loss,stale,history=progress['best_loss'],progress['stale'],progress['history']
    started = time.monotonic()
    total_steps=(len(training)+batch_size-1)//batch_size
    print(json.dumps({'stage':'training_ready','training_rows':len(training),'steps_per_epoch':total_steps,'resumed':resume}),flush=True)
    for epoch in range(progress['epoch'],epochs):
        if stale>=2:break
        model.train()
        next_step=progress['next_step'] if epoch==progress['epoch'] else 0
        loss_sum=progress['loss_sum'] if next_step else 0.
        loss_count=progress['loss_count'] if next_step else 0
        order=torch.randperm(len(training),generator=torch.Generator().manual_seed(42+epoch)).tolist()
        remaining=torch.utils.data.Subset(URLDataset(training,tokenizer),order[next_step*batch_size:])
        loader=DataLoader(remaining,batch_size=batch_size,generator=torch.Generator().manual_seed(142+epoch))
        for step, batch in enumerate(loader,start=next_step):
            optimizer.zero_grad()
            loss = model(**{k: v.to(device) for k, v in batch.items()}).loss
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1); optimizer.step()
            current_loss=float(loss.detach().cpu());loss_sum+=current_loss;loss_count+=1
            if step % 100 == 0:
                status={"epoch":epoch+1,"step":step+1,"steps_per_epoch":total_steps,"training_percent":round(100*(epoch*total_steps+step+1)/(epochs*total_steps),2),"loss":current_loss,"elapsed_seconds":time.monotonic()-started}
                (output/'progress.json').write_text(json.dumps(status),encoding='utf-8')
                print(json.dumps(status),flush=True)
            if (step+1)%checkpoint_steps==0:
                save(checkpoint,model,optimizer,signature,{'epoch':epoch,'next_step':step+1,'loss_sum':loss_sum,'loss_count':loss_count,'best_loss':best_loss,'stale':stale,'history':history})
        p = predict(model, tokenizer, selection, device, batch_size)
        y = np.array([int(r["label"]) for r in selection])
        clipped = np.clip(p, 1e-7, 1 - 1e-7)
        val_loss = float(-(y * np.log(clipped) + (1-y) * np.log(1-clipped)).mean())
        history.append({"epoch": epoch+1, "train_loss": loss_sum/max(loss_count,1), "validation_log_loss": val_loss})
        if val_loss < best_loss:
            best_loss, stale = val_loss, 0
            model.save_pretrained(output / "bert", safe_serialization=True)
            tokenizer.save_pretrained(output / "bert")
        else:
            stale += 1
        save(checkpoint,model,optimizer,signature,{'epoch':epoch+1,'next_step':0,'loss_sum':0.,'loss_count':0,'best_loss':best_loss,'stale':stale,'history':history})
    model = AutoModelForSequenceClassification.from_pretrained(output / "bert", local_files_only=True).to(device)
    p = predict(model, tokenizer, validation, device, batch_size)
    y = np.array([int(r["label"]) for r in validation])
    with (output / "validation_predictions.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target); writer.writerow(["url", "domain_group", "label", "probability"])
        writer.writerows((r["url"], r["domain_group"], r["label"], float(prob)) for r, prob in zip(validation, p))
    manifest = dict(model_id=BERT_MODEL, source_revision=BERT_REVISION, license="Apache-2.0", preprocessing_version=BERT_PREPROCESSING, max_length=MAX_LENGTH, representation="original parsed URL, without HTML", seed=42, device=str(device), training_rows=len(training), full_training_partition=max_train_rows is None, dataset_sha256=hashlib.sha256(Path(dataset).read_bytes()).hexdigest(), history=history, validation_metrics=metrics(y, p), elapsed_seconds=time.monotonic()-started, files={str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (output / "bert").iterdir() if path.is_file()})
    (output / "bert_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("dataset"); parser.add_argument("source"); parser.add_argument("output")
    parser.add_argument("--epochs", type=int, default=3); parser.add_argument("--batch-size", type=int, default=8); parser.add_argument("--max-train-rows", type=int)
    parser.add_argument('--resume',action='store_true');parser.add_argument('--checkpoint-steps',type=int,default=500)
    args = parser.parse_args()
    print(json.dumps(train(args.dataset, args.source, args.output, args.epochs, args.batch_size, args.max_train_rows,args.resume,args.checkpoint_steps), indent=2))
