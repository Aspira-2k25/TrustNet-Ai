import pytest
import torch
from models.image_deepfake.training.dataset import DeepfakeDataset, verify_zero_identity_leakage
from models.image_deepfake.training.train import build_model, train_one_epoch, evaluate_model
from torch.utils.data import DataLoader
import torch.nn as nn
from PIL import Image

def training_samples(tmp_path):
    samples=[]
    for i in range(2):
        path=tmp_path/f'fixture-{i}.jpg'
        Image.new('RGB',(240,240),(60+80*i,100,150)).save(path)
        samples.append((str(path),i,f'person_{i+1}'))
    return samples

def test_dataset_item_and_shape(tmp_path):
    samples = training_samples(tmp_path)
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

def test_training_step_execution(tmp_path):
    device = torch.device("cpu")
    model = build_model(num_classes=2, pretrained=False).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()

    samples = training_samples(tmp_path)
    loader = DataLoader(DeepfakeDataset(samples), batch_size=2)
    loss = train_one_epoch(model, loader, optimizer, criterion, device)
    assert isinstance(loss, float)
    assert loss > 0.0

    metrics = evaluate_model(model, loader, criterion, device)
    assert "accuracy" in metrics
    assert "auc" in metrics
