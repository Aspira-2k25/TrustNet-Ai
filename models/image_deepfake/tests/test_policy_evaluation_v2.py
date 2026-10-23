import hashlib
import json
from types import SimpleNamespace
import pytest
from models.image_deepfake.evaluation import run

def test_evaluation_rejects_known_training_source_group(tmp_path,monkeypatch):
    image=tmp_path/'image.jpg';image.write_bytes(b'harmless fixture')
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps([['image.jpg',0,'known-train-group']]))
    detector=SimpleNamespace(readiness=lambda:{'ready':True},cnn=SimpleNamespace(manifest={'weights_sha256':'a'*64},
        dataset_index=[{'sha256':'b'*64,'split':'train','group_sha256':hashlib.sha256(b'known-train-group').hexdigest()}]))
    monkeypatch.setattr(run,'EfficientNetDetector',lambda **kwargs:detector)
    with pytest.raises(ValueError,match='leaks'):
        run.evaluate(manifest,tmp_path/'report.json')
    assert not (tmp_path/'report.json').exists()
