"""Paired crop experiments on validation data only; never changes serving policy."""
import argparse
import io
import json
from pathlib import Path
from PIL import Image
from models.image_deepfake.evaluation.benchmark import read_manifest, metric_summary
from models.image_deepfake.forensics.face_analyzer import FaceAnalyzer
from models.image_deepfake.inference.local_vit_detector import LocalViTDeepfakeDetector
from models.image_deepfake.preprocessing.validator import canonical_bytes


def evaluate(manifest, output):
    target = Path(output)
    if target.exists(): raise ValueError('Refusing to overwrite view experiment')
    rows = read_manifest(manifest, 'validation'); analyzer = FaceAnalyzer(); model = LocalViTDeepfakeDetector()
    records = []
    for row in rows:
        canonical = canonical_bytes(Path(row['path']).read_bytes()); image = Image.open(io.BytesIO(canonical))
        face = analyzer.analyze(canonical); boxes = sorted(face.get('bounding_boxes', []), key=lambda b:b[2]*b[3], reverse=True)
        predictions = {'full_frame': model.predict(canonical)}
        for padding in (0.0, 0.1, 0.2):
            scores = []
            for x, y, w, h in boxes[:4]:
                if min(w, h) < 48: continue
                bounds = (max(0, int(x-w*padding)), max(0, int(y-h*padding)),
                          min(image.width, int(x+w*(1+padding))), min(image.height, int(y+h*(1+padding))))
                stream = io.BytesIO(); image.crop(bounds).save(stream, format='PNG')
                value = model.predict(stream.getvalue())
                if value.get('is_hf_applied'): scores.append(value['hf_risk_score'])
            complete = bool(scores) and len(scores) == len(boxes) <= 4
            predictions[f'face_max_padding_{padding}'] = {'is_hf_applied': bool(scores), 'views_complete': complete, 'hf_risk_score': max(scores) if scores else None}
            predictions[f'face_mean_padding_{padding}'] = {'is_hf_applied': bool(scores), 'views_complete': complete, 'hf_risk_score': sum(scores)/len(scores) if scores else None}
        for strategy, value in predictions.items():
            available = value.get('is_hf_applied', False)
            records.append({'group': row['group'], 'label': row['label'], 'sha256': row['sha256'],
                'strategy': strategy, 'score': value['hf_risk_score']/100 if available else None,
                'abstained': not available or not value.get('views_complete', True),
                'status': 'SUCCESS' if available and value.get('views_complete', True) else 'PARTIAL_SUCCESS' if available else 'FAILED', 'detected_faces': len(boxes)})
    report = {'purpose': 'validation', 'model_id': model.model_name, 'model_revision': model.revision,
              'strategies': {s: metric_summary([r for r in records if r['strategy'] == s]) for s in {r['strategy'] for r in records}},
              'records': records, 'limits': 'Paired descriptive experiment. Classifier metrics use reference threshold 0.5; crop failures remain in denominators. No automatic strategy promotion.'}
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(report, indent=2)); return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--manifest', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); evaluate(args.manifest, args.output)
