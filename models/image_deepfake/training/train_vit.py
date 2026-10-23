"""Fine-tune the existing ViT on explicit prepared face manifests; GPU required."""
import argparse
import hashlib
import json
import random
from pathlib import Path
import numpy as np
import torch
from PIL import Image, ImageOps
from torch.utils.data import DataLoader, Dataset
from models.image_deepfake.evaluation.benchmark import read_manifest
from models.image_deepfake.evaluation.data_audit import audit
from models.image_deepfake.evaluation.metrics import calculate_metrics
from models.image_deepfake.inference.vit_policy import MODEL, REVISION


def run(train_manifest, validation_manifest, test_manifest, output, epochs=10, batch_size=16,
        learning_rate=2e-5, seed=42, head_only=False, face_crops_prepared=False):
    from transformers import AutoImageProcessor, AutoModelForImageClassification
    if not torch.cuda.is_available():
        raise ValueError('ViT training requires the selected Kaggle GPU environment')
    if face_crops_prepared is not True:
        raise ValueError('Explicit matching prepared-face-crop confirmation is required')
    if epochs < 1 or batch_size < 1 or learning_rate <= 0:
        raise ValueError('Invalid training settings')
    target = Path(output).resolve()
    if target.exists() and any(target.iterdir()): raise ValueError('Training output must be empty')
    target.mkdir(parents=True, exist_ok=True)
    partitions = {'train': train_manifest, 'validation': validation_manifest, 'test': test_manifest}
    evidence = audit(partitions, target/'split_audit.json')
    if not evidence['passed_exact_checks'] or evidence['near_duplicate_candidates']:
        raise ValueError('Resolve exact leakage and near-duplicate review candidates before training')
    rows = {split: read_manifest(path, split) for split, path in partitions.items()}
    if any({r['label'] for r in split} != {0, 1} for split in rows.values()):
        raise ValueError('Both real and fake classes required in every split')
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False; torch.backends.cudnn.deterministic = True
    processor = AutoImageProcessor.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForImageClassification.from_pretrained(MODEL, revision=REVISION)
    # Reorder existing pretrained output rows into the artifact's explicit label order.
    original = {str(v).lower(): int(k) for k, v in model.config.id2label.items()}
    if set(original) != {'real', 'fake'}: raise ValueError('Unexpected source labels')
    order = [original['real'], original['fake']]
    with torch.no_grad():
        model.classifier.weight.copy_(model.classifier.weight[order].clone())
        model.classifier.bias.copy_(model.classifier.bias[order].clone())
    model.config.id2label = {0: 'real', 1: 'fake'}; model.config.label2id = {'real': 0, 'fake': 1}
    if head_only:
        for parameter in model.parameters(): parameter.requires_grad = False
        for parameter in model.classifier.parameters(): parameter.requires_grad = True
    model = model.to('cuda')

    class Faces(Dataset):
        def __init__(self, split): self.rows = rows[split]
        def __len__(self): return len(self.rows)
        def __getitem__(self, index):
            row = self.rows[index]
            with Image.open(row['path']) as image:
                pixels = processor(images=ImageOps.exif_transpose(image).convert('RGB'), return_tensors='pt')['pixel_values'][0]
            return pixels, row['label']

    generator = torch.Generator().manual_seed(seed)
    loaders = {s: DataLoader(Faces(s), batch_size=batch_size, shuffle=s == 'train', num_workers=0,
                            generator=generator) for s in rows}
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=learning_rate, weight_decay=.01)
    def evaluate(split):
        model.eval(); labels, scores = [], []; loss, count = 0., 0
        with torch.no_grad():
            for pixels, targets in loaders[split]:
                result = model(pixel_values=pixels.to('cuda'), labels=targets.to('cuda'))
                loss += result.loss.item()*len(targets); count += len(targets)
                labels.extend(targets.tolist()); scores.extend(result.logits.softmax(-1)[:, 1].cpu().tolist())
        return loss/count, calculate_metrics(labels, scores)
    best, stale, history = float('inf'), 0, []
    for epoch in range(epochs):
        model.train()
        for pixels, labels in loaders['train']:
            optimizer.zero_grad(set_to_none=True)
            result = model(pixel_values=pixels.to('cuda'), labels=labels.to('cuda'))
            result.loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.); optimizer.step()
        loss, metrics = evaluate('validation'); history.append({'epoch': epoch+1, 'validation_loss': loss, 'metrics': metrics})
        print(json.dumps(history[-1]), flush=True)
        if loss < best:
            best, stale = loss, 0; model.save_pretrained(target, safe_serialization=True); processor.save_pretrained(target)
            torch.save({'optimizer': optimizer.state_dict(), 'epoch': epoch+1, 'seed': seed}, target/'training_state.pt')
        else:
            stale += 1
            if stale >= 3: break
    model = AutoModelForImageClassification.from_pretrained(target, local_files_only=True).to('cuda')
    test_loss, test_metrics = evaluate('test')
    index = [{k: row[k] for k in ('sha256', 'pixel_sha256', 'label', 'group')} | {'split': split}
             for split in rows for row in rows[split]]
    (target/'dataset_index.json').write_text(json.dumps(index, indent=2))
    report = {'seed': seed, 'source_revision': REVISION, 'head_only': head_only,
              'learning_rate': learning_rate, 'batch_size': batch_size, 'history': history,
              'test_loss': test_loss, 'test_metrics': test_metrics, 'calibration_available': False,
              'limits': 'Prepared crops only. End-to-end all-input testing and recent-generator external validation remain required.'}
    (target/'training_report.json').write_text(json.dumps(report, indent=2))
    names = ['config.json', 'preprocessor_config.json', 'model.safetensors', 'dataset_index.json', 'training_report.json']
    files = {n: hashlib.sha256((target/n).read_bytes()).hexdigest() for n in names}
    manifest = {'format_version': 1, 'model_id': MODEL, 'architecture': 'ViTForImageClassification',
                'source_revision': REVISION, 'revision': 'local-'+files['model.safetensors'],
                'labels': {'0': 'real', '1': 'fake'}, 'input_policy': 'detected-box-padding-0-v1',
                'data_kind': 'real', 'release_approved': False, 'files': files}
    (target/'vit_manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for split in ('train', 'validation', 'test'): parser.add_argument('--'+split, required=True)
    parser.add_argument('--output', required=True); parser.add_argument('--head-only', action='store_true')
    parser.add_argument('--prepared-face-crops', action='store_true', required=True)
    parser.add_argument('--epochs', type=int, default=10); args = parser.parse_args()
    run(args.train, args.validation, args.test, args.output, epochs=args.epochs, head_only=args.head_only,
        face_crops_prepared=args.prepared_face_crops)
