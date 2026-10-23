"""
TrustNet AI — EfficientNet-B0 Deepfake Training Pipeline
Per Master Spec Section 4.2.
"""
import os
import argparse
import yaml
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import models

from models.image_deepfake.training.dataset import (
    DeepfakeDataset,
    DEFAULT_TRAIN_TRANSFORMS,
    DEFAULT_VAL_TRANSFORMS,
    verify_zero_identity_leakage
)
from models.image_deepfake.evaluation.metrics import calculate_metrics

def build_model(num_classes: int = 2, pretrained: bool = True) -> nn.Module:
    """Builds EfficientNet-B0 with custom binary classification head."""
    weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
    model = models.efficientnet_b0(weights=weights)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3, inplace=True),
        nn.Linear(in_features, num_classes)
    )
    return model

def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device
) -> float:
    """Trains the model for one epoch and returns average loss."""
    model.train()
    total_loss = 0.0
    total_samples = 0

    for batch in dataloader:
        images, labels, _ = batch
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()

        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item() * images.size(0)
        total_samples += images.size(0)

    return total_loss / max(1, total_samples)

@torch.no_grad()
def evaluate_model(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> dict:
    """Evaluates the model and computes accuracy, loss, and AUC-ROC."""
    model.eval()
    total_loss = 0.0
    all_targets = []
    all_probs = []

    for batch in dataloader:
        images, labels, _ = batch
        images = images.to(device)
        labels = labels.to(device)

        outputs = model(images)
        loss = criterion(outputs, labels)
        probs = torch.softmax(outputs, dim=1)[:, 1] # Probability of FAKE class

        total_loss += loss.item() * images.size(0)
        all_probs.extend(probs.cpu().tolist())
        all_targets.extend(labels.cpu().tolist())

    metrics = calculate_metrics(y_true=all_targets, y_pred_prob=all_probs)
    metrics["loss"] = total_loss / max(1, len(all_targets))
    return metrics

def run_training(config_path: str, output_dir: str = 'checkpoints', dry_run: bool = False):
    import json, random, hashlib
    import numpy as np
    from pathlib import Path
    from datetime import datetime, timezone
    from models.image_deepfake.inference.artifact import PREPROCESSING, LABELS, sha256
    config_file = Path(config_path).resolve()
    if not config_file.is_file():
        raise ValueError('Training configuration does not exist')
    config = yaml.safe_load(config_file.read_text(encoding='utf-8'))
    settings = config.get('training', {})
    required = {'batch_size','epochs','learning_rate','weight_decay','seed','early_stopping_patience'}
    if not required.issubset(settings) or set(settings) - required:
        raise ValueError('training must define only: ' + ', '.join(sorted(required)))
    if (settings['batch_size'] < 2 or settings['epochs'] < 1 or settings['learning_rate'] <= 0
            or settings['weight_decay'] < 0 or settings['early_stopping_patience'] < 1):
        raise ValueError('Invalid training hyperparameters')
    scope = config.get('data', {}).get('scope')
    if scope not in {'face', 'general_image'}:
        raise ValueError('data.scope must be face or general_image')
    target = Path(output_dir).resolve()
    deployed = Path(__file__).resolve().parents[1]
    if deployed == target or deployed in target.parents:
        raise ValueError('Training output must be outside deployed image artifacts')
    if target.exists() and any(target.iterdir()):
        raise ValueError('Output directory must be empty; preserve existing training artifacts')
    seed = int(settings['seed'])
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    if not dry_run and scope == 'face' and config.get('data',{}).get('face_crops_prepared') is not True:
        raise ValueError('Face training requires explicit face_crops_prepared=true and the serving crop policy')
    hashes, manifest_hashes, index = {}, {}, []
    if dry_run:
        partitions = [[('__dry_run__', label, split+str(label)) for label in (0,1)] for split in ('train','validation','test')]
    else:
        partitions = []
        for split in ('train','validation','test'):
            key = split + '_manifest'
            name = config.get('data', {}).get(key)
            if not name:
                raise ValueError('Real training requires train, validation and test manifests')
            manifest_path = (config_file.parent / name).resolve()
            raw = manifest_path.read_bytes(); manifest_hashes[split] = hashlib.sha256(raw).hexdigest()
            rows = json.loads(raw)
            if not isinstance(rows,list) or not rows:
                raise ValueError('Empty or invalid training manifest')
            samples=[]
            for row in rows:
                if not isinstance(row,list) or len(row)!=3 or type(row[1]) is not int or row[1] not in (0,1) or not isinstance(row[2],str) or not row[2]:
                    raise ValueError('Each manifest row must be [path, binary_label, source_or_identity_group]')
                image_path=(manifest_path.parent / row[0]).resolve()
                digest=sha256(image_path)
                if digest in hashes:
                    raise ValueError('Duplicate image bytes in manifests: ' + str(image_path))
                from models.image_deepfake.preprocessing.validator import ImageValidator
                with image_path.open('rb') as stream:
                    valid, error = ImageValidator().validate(stream.read(ImageValidator().max_size_bytes + 1))
                if not valid: raise ValueError(f'Invalid training image: {error}')
                hashes[digest]=split
                index.append({'sha256':digest,'split':split,'label':row[1],
                              'group_sha256':hashlib.sha256(row[2].encode()).hexdigest()})
                samples.append((str(image_path),row[1],row[2]))
            if {row[1] for row in samples} != {0,1}:
                raise ValueError('Each real-data split must contain both classes')
            partitions.append(samples)
    verify_zero_identity_leakage(*partitions)
    target.mkdir(parents=True,exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    train_ds = DeepfakeDataset(partitions[0], transform=DEFAULT_TRAIN_TRANSFORMS, dry_run=dry_run)
    val_ds = DeepfakeDataset(partitions[1], transform=DEFAULT_VAL_TRANSFORMS, dry_run=dry_run)
    test_ds = DeepfakeDataset(partitions[2], transform=DEFAULT_VAL_TRANSFORMS, dry_run=dry_run)
    generator = torch.Generator().manual_seed(seed)
    train_loader=DataLoader(train_ds,batch_size=settings['batch_size'],shuffle=True,generator=generator,num_workers=0)
    val_loader=DataLoader(val_ds,batch_size=settings['batch_size'],num_workers=0)
    test_loader=DataLoader(test_ds,batch_size=settings['batch_size'],num_workers=0)
    model=build_model(num_classes=2,pretrained=not dry_run).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=settings['learning_rate'],weight_decay=settings['weight_decay'])
    criterion=nn.CrossEntropyLoss()
    best, stale, history = -1., 0, []
    for epoch in range(1, (1 if dry_run else settings['epochs'])+1):
        loss=train_one_epoch(model,train_loader,optimizer,criterion,device)
        metrics=evaluate_model(model,val_loader,criterion,device)
        auc=metrics['auc']
        print(f'Epoch {epoch}: loss={loss:.4f}; validation AUC={auc if auc is not None else "unavailable"}')
        history.append({'epoch':epoch,'train_loss':loss,'validation':metrics})
        selection=auc if auc is not None else -metrics['loss']
        if selection > best or epoch == 1:
            best, stale = selection, 0
            torch.save(model.state_dict(),target/'best_model.pt')
            torch.save({'epoch':epoch,'optimizer':optimizer.state_dict(),'seed':seed},target/'training_state.pt')
        else:
            stale+=1
        if stale>=settings['early_stopping_patience']: break
    model.load_state_dict(torch.load(target/'best_model.pt',map_location=device,weights_only=True))
    test_metrics=evaluate_model(model,test_loader,criterion,device)
    (target/'dataset_index.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
    manifest={'dataset_index_sha256':sha256(target/'dataset_index.json'),'format_version':1,'architecture':'efficientnet_b0','labels':LABELS,'preprocessing':PREPROCESSING,
              'weights_sha256':sha256(target/'best_model.pt'),'deployable':not dry_run,
              'data_kind':'smoke' if dry_run else 'real','scope':scope,
              'input_policy':'haar-eye-pair-crop-v1' if scope=='face' else 'decoded_rgb_full_frame_v1','seed':seed,
              'created_at':datetime.now(timezone.utc).isoformat(),'manifest_hashes':manifest_hashes,
              'test_metrics':test_metrics,'config':config,'torch_version':str(torch.__version__)}
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (target/'training_report.json').write_text(json.dumps({'history':history,'held_out_test':test_metrics,
        'data_kind':manifest['data_kind'],'artifact_sha256':manifest['weights_sha256'],
        'split_counts':dict(zip(('train','validation','test'),map(len,partitions)))},indent=2),encoding='utf-8')
    print('Saved smoke artifact (not deployable).' if dry_run else 'Saved versioned training artifact; deployment validation remains required.')
    return manifest

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Train the image binary classifier; manifests use 0=real, 1=fake.')
    parser.add_argument('--config',default='models/image_deepfake/configs/baseline_config.yaml')
    parser.add_argument('--output-dir',default='checkpoints')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    run_training(args.config,args.output_dir,args.dry_run)
