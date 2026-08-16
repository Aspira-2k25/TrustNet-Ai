import pytest
import torch
from models.image_deepfake.training.dataset import DeepfakeDataset, verify_zero_identity_leakage
from models.image_deepfake.training.train import build_model, train_one_epoch, evaluate_model
from torch.utils.data import DataLoader
import torch.nn as nn

def test_dataset_item_and_shape():
    samples = [
        ("dummy1.jpg", 0, "person_1"),
        ("dummy2.jpg", 1, "person_2"),
    ]
    ds = DeepfakeDataset(samples)
    assert len(ds) == 2
    tensor, label, identity = ds[0]
    assert tensor.shape == (3, 224, 224)
    assert label == 0
    assert identity == "person_1"

def test_zero_identity_leakage_detection():
    # Valid disjoint sets
    train_samples = [("a.jpg", 0, "id_1"), ("b.jpg", 1, "id_2")]
    val_samples = [("c.jpg", 0, "id_3")]
    assert verify_zero_identity_leakage(train_samples, val_samples, []) is True

    # Leaking identity between train and val
    leaking_val = [("d.jpg", 1, "id_1")]
    with pytest.raises(ValueError, match="Identity leakage detected"):
        verify_zero_identity_leakage(train_samples, leaking_val, [])

def test_training_step_execution():
    device = torch.device("cpu")
    model = build_model(num_classes=2, pretrained=False).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()

    samples = [
        ("dummy1.jpg", 0, "p1"),
        ("dummy2.jpg", 1, "p2"),
    ]
    loader = DataLoader(DeepfakeDataset(samples), batch_size=2)
    loss = train_one_epoch(model, loader, optimizer, criterion, device)
    assert isinstance(loss, float)
    assert loss > 0.0

    metrics = evaluate_model(model, loader, criterion, device)
    assert "accuracy" in metrics
    assert "auc" in metrics
