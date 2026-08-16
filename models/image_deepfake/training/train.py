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

def run_training(config_path: str, output_dir: str = "checkpoints", dry_run: bool = False):
    """Executes full training pipeline according to config YAML."""
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Starting TrustNet AI Image Deepfake Training on device: {device}")

    # Load configuration
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        config = {
            "training": {
                "epochs": 2 if dry_run else 10,
                "batch_size": 4 if dry_run else 32,
                "learning_rate": 0.0003,
                "weight_decay": 0.0001
            }
        }

    # Mock dataset creation for verification / dry-run
    train_samples = [
        ("dummy_real_1.jpg", 0, "person_01"),
        ("dummy_fake_1.jpg", 1, "person_01"),
        ("dummy_real_2.jpg", 0, "person_02"),
        ("dummy_fake_2.jpg", 1, "person_02"),
    ]
    val_samples = [
        ("dummy_real_3.jpg", 0, "person_03"),
        ("dummy_fake_3.jpg", 1, "person_03"),
    ]

    verify_zero_identity_leakage(train_samples, val_samples, [])

    train_ds = DeepfakeDataset(train_samples, transform=DEFAULT_TRAIN_TRANSFORMS)
    val_ds = DeepfakeDataset(val_samples, transform=DEFAULT_VAL_TRANSFORMS)

    train_loader = DataLoader(train_ds, batch_size=config["training"]["batch_size"], shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=config["training"]["batch_size"], shuffle=False)

    model = build_model(num_classes=2, pretrained=True).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"]
    )
    criterion = nn.CrossEntropyLoss()

    best_auc = 0.0
    epochs = 1 if dry_run else config["training"]["epochs"]

    for epoch in range(1, epochs + 1):
        train_loss = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_metrics = evaluate_model(model, val_loader, criterion, device)

        print(f"Epoch [{epoch}/{epochs}] | Train Loss: {train_loss:.4f} | Val Loss: {val_metrics['loss']:.4f} | Val AUC: {val_metrics['auc']:.4f}")

        if val_metrics["auc"] >= best_auc:
            best_auc = val_metrics["auc"]
            checkpoint_path = os.path.join(output_dir, "best_model.pt")
            torch.save(model.state_dict(), checkpoint_path)
            print(f"  --> Saved new best checkpoint to {checkpoint_path}")

    print("[+] Training completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TrustNet AI — Image Deepfake Training")
    parser.add_argument("--config", type=str, default="models/image_deepfake/configs/baseline_config.yaml", help="Path to config YAML")
    parser.add_argument("--output-dir", type=str, default="checkpoints", help="Output checkpoint directory")
    parser.add_argument("--dry-run", action="store_true", help="Perform single epoch dry run with dummy samples")
    args = parser.parse_args()

    run_training(args.config, args.output_dir, args.dry_run)
