"""Strict training-to-serving contract. Missing weights never become ImageNet votes."""
import hashlib
import json
import os
from pathlib import Path
import torch
from models.image_deepfake.preprocessing.transforms import process_image_bytes

PREPROCESSING = 'exif-rgb-still-resize224-imagenet-v2'
LABELS = {'0': 'real', '1': 'fake'}

def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

class TrainedImageModel:
    def __init__(self, directory=None):
        self.model = None
        self.error = None
        self.manifest = {}
        self.dataset_index = []
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        root = Path(directory or os.getenv('IMAGE_MODEL_DIR', str(Path(__file__).resolve().parents[1] / 'artifacts'))).resolve()
        try:
            manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
            if (manifest.get('format_version') != 1 or manifest.get('architecture') != 'efficientnet_b0'
                    or manifest.get('labels') != LABELS or manifest.get('preprocessing') != PREPROCESSING
                    or manifest.get('deployable') is not True or manifest.get('data_kind') != 'real'
                    or manifest.get('scope') not in {'face', 'general_image'}):
                raise ValueError('Unsupported, untrained, or incompatible image artifact manifest')
            policy = 'haar-eye-pair-crop-v1' if manifest['scope']=='face' else 'decoded_rgb_full_frame_v1'
            if manifest.get('input_policy') != policy:
                raise ValueError('Incompatible training/serving input policy')
            index_path = root / 'dataset_index.json'
            if sha256(index_path) != manifest.get('dataset_index_sha256'):
                raise ValueError('Dataset provenance index hash mismatch')
            index = json.loads(index_path.read_text(encoding='utf-8'))
            for split in ('train', 'validation', 'test'):
                if {row.get('label') for row in index if row.get('split') == split} != {0, 1}:
                    raise ValueError('Artifact requires both classes in all held-out splits')
            digests = [row['sha256'] for row in index]
            if len(digests) != len(set(digests)):
                raise ValueError('Duplicate dataset content in artifact provenance')
            groups = {}
            for row in index:
                group = row['group_sha256']
                if group in groups and groups[group] != row['split']:
                    raise ValueError('Cross-split source group in artifact provenance')
                groups[group] = row['split']
            weights = root / 'best_model.pt'
            if sha256(weights) != manifest.get('weights_sha256'):
                raise ValueError('Image checkpoint hash mismatch')
            from models.image_deepfake.training.train import build_model
            model = build_model(num_classes=2, pretrained=False)
            model.load_state_dict(torch.load(weights, map_location='cpu', weights_only=True), strict=True)
            model.eval().to(self.device)
            self.model, self.manifest, self.dataset_index = model, manifest, index
        except Exception as error:
            self.error = str(error)

    @property
    def ready(self):
        return self.model is not None

    def predict(self, blob):
        if not self.ready:
            return {'status': 'UNAVAILABLE', 'risk_score': None, 'reason': self.error}
        with torch.inference_mode():
            output = self.model(process_image_bytes(blob, validated=True).to(self.device))
            if output.shape != (1, 2) or not torch.isfinite(output).all():
                raise ValueError('Invalid trained CNN output')
            score = float(torch.softmax(output, dim=1)[0, 1].item()) * 100
        return {'status': 'APPLIED', 'risk_score': round(score, 2),
                'model_name': 'efficientnet_b0', 'weights_sha256': self.manifest['weights_sha256']}
