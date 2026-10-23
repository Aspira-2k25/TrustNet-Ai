"""ViT-only baseline and end-to-end evaluation, including failed localizations."""
import argparse
import hashlib
import io
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image
from models.image_deepfake.preprocessing.validator import canonical_bytes
from models.image_deepfake.evaluation.metrics import calculate_metrics, compute_confusion_matrix
from models.image_deepfake.inference.vit_policy import MODEL, REVISION


def read_manifest(path, purpose):
    path = Path(path).resolve()
    rows = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(rows, list) or not rows:
        raise ValueError('Manifest must be a nonempty list')
    records, seen, pixels, groups = [], set(), set(), {}
    for index, row in enumerate(rows):
        if isinstance(row, list) and len(row) == 3:
            row = dict(path=row[0], label=row[1], group=row[2], split=purpose)
        if (not isinstance(row, dict) or type(row.get('label')) is not int or row['label'] not in (0, 1)
                or not isinstance(row.get('group'), str) or not row['group']
                or not isinstance(row.get('path'), str)):
            raise ValueError(f'Invalid manifest row {index}')
        if row.get('split', purpose) != purpose:
            raise ValueError('Manifest split does not match evaluation purpose')
        source = (path.parent / row['path']).resolve()
        blob = source.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        # Exact source and decoded-pixel duplicates must not inflate metrics.
        try:
            canonical = canonical_bytes(blob)
            pixel_hash = hashlib.sha256(canonical).hexdigest()
        except Exception:
            # Malformed inputs remain in end-to-end denominators as failures.
            pixel_hash = 'invalid:' + digest
        if digest in seen or pixel_hash in pixels:
            raise ValueError('Duplicate image bytes or canonical pixels in manifest')
        seen.add(digest); pixels.add(pixel_hash)
        if row.get('subject_id'):
            previous = groups.setdefault(row['subject_id'], row['group'])
            if previous != row['group']:
                raise ValueError('Known subject identity must share one source group')
        records.append({**row, 'path': str(source), 'sha256': digest, 'pixel_sha256': pixel_hash})
    return records


def transform(blob, name):
    canonical = canonical_bytes(blob)
    if name == 'original':
        return canonical
    image = Image.open(io.BytesIO(canonical)).convert('RGB')
    stream = io.BytesIO()
    if name.startswith('jpeg_'):
        image.save(stream, format='JPEG', quality=int(name.split('_')[1]))
    elif name == 'resize_256':
        image.thumbnail((256, 256), Image.Resampling.LANCZOS); image.save(stream, format='PNG')
    elif name == 'screenshot_proxy':
        image.thumbnail((768, 768), Image.Resampling.BILINEAR)
        image.save(stream, format='JPEG', quality=85)
    else:
        raise ValueError('Unknown transform')
    return stream.getvalue()


def metric_summary(rows, threshold=.5):
    scored = [r for r in rows if r.get('score') is not None]
    accepted = [r for r in scored if not r['abstained']]
    def metrics(items):
        if not items:
            return None
        labels, scores = [r['label'] for r in items], [r['score'] for r in items]
        return {**calculate_metrics(labels, scores, threshold=threshold),
                'confusion_matrix': compute_confusion_matrix(labels, [int(s >= threshold) for s in scores]),
                'count': len(items)}
    decisions = [r for r in accepted if r.get('verdict') in {'LOW_MANIPULATION_SIGNAL', 'LIKELY_AI_MANIPULATED'}]
    actual_decisions = None
    if decisions:
        actual_decisions = compute_confusion_matrix([r['label'] for r in decisions],
            [int(r['verdict'] == 'LIKELY_AI_MANIPULATED') for r in decisions])
    return {'count': len(rows), 'scored': len(scored), 'accepted': len(accepted),
            'coverage': len(accepted) / len(rows) if rows else 0,
            'abstention_rate': sum(r['abstained'] for r in rows) / len(rows) if rows else 0,
            'all_scored_at_reference_threshold': metrics(scored),
            'accepted_at_reference_threshold': metrics(accepted),
            'actual_accepted_decision_confusion': actual_decisions,
            'failure_count': sum(r['status'] == 'FAILED' for r in rows),
            'unsupported_count': sum(r.get('scope_state') == 'NO_ASSESSABLE_FACE' for r in rows)}


def grouped_intervals(rows, repeats=200, seed=42):
    """Resample source groups, never individual crops/derived images."""
    groups = sorted({r['group'] for r in rows})
    if len(groups) < 2 or not repeats:
        return {'available': False, 'reason': 'At least two independent groups required'}
    mapping = {g: [] for g in groups}
    for row in rows:
        mapping[row['group']].append(row)
    rng = np.random.default_rng(seed); values = {'coverage': [], 'auc_roc': [], 'false_positive_rate': []}
    for _ in range(repeats):
        sample = [r for g in rng.choice(groups, len(groups), replace=True) for r in mapping[g]]
        summary = metric_summary(sample)
        values['coverage'].append(summary['coverage'])
        for key in ('auc_roc', 'false_positive_rate'):
            value = (summary['all_scored_at_reference_threshold'] or {}).get(key)
            if value is not None:
                values[key].append(value)
    return {'available': True, 'method': 'source-group bootstrap percentile 95%', 'repeats': repeats,
            'intervals': {k: [float(x) for x in np.quantile(v, [.025, .975])] if v else None for k, v in values.items()}}


def evaluate(manifest, output, mode='vit_policy', purpose='test', variants=('original',), bootstrap=200):
    if mode not in {'vit_direct', 'vit_policy'} or purpose not in {'validation', 'calibration', 'test'}:
        raise ValueError('Invalid evaluation mode or purpose')
    output = Path(output)
    if output.exists():
        raise ValueError('Refusing to overwrite evaluation report')
    samples = read_manifest(manifest, purpose)
    if mode == 'vit_policy':
        from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
        detector = EfficientNetDetector(policy='image-vit-v3', evaluation_candidate=True)
        vit = detector.local_vit
    else:
        from models.image_deepfake.inference.local_vit_detector import LocalViTDeepfakeDetector
        vit = LocalViTDeepfakeDetector(); detector = None
    if getattr(vit, 'artifact_directory', None):
        from models.image_deepfake.inference.vit_artifact import validate
        validate(vit.artifact_directory)
        index = json.loads((Path(vit.artifact_directory)/'dataset_index.json').read_text())
        forbidden = [r for r in index if r['split'] in ({'train'} if purpose == 'validation' else {'train', 'validation'})]
        for field in ('sha256', 'pixel_sha256', 'group'):
            known = {r[field] for r in forbidden if r.get(field)}
            if known.intersection(r[field] for r in samples if r.get(field)):
                raise ValueError('Evaluation overlaps candidate training/model-selection data: '+field)
    records = []
    for sample in samples:
        for variant in variants:
            started = time.monotonic()
            row = {k: v for k, v in sample.items() if k != 'path'}
            row.update(variant=variant, score=None, abstained=True, status='FAILED')
            try:
                blob = transform(Path(sample['path']).read_bytes(), variant)
                if mode == 'vit_policy':
                    result = detector.predict(blob, filename=Path(sample['path']).name)
                    row.update(score=result.risk_score / 100 if result.metadata.get('score_available') else None,
                        status=result.status.value, verdict=result.verdict, abstained=result.verdict not in {'LOW_MANIPULATION_SIGNAL', 'LIKELY_AI_MANIPULATED'},
                        scope_state=result.metadata.get('scope_state'), views=result.metadata.get('model_views'),
                        reasons=result.metadata.get('why_reasons'), error=result.error_code)
                else:
                    result = vit.predict(blob)
                    if result.get('is_hf_applied'):
                        row.update(score=result['hf_risk_score'] / 100, status='SUCCESS', abstained=False)
                    else:
                        row['error'] = result.get('note')
            except Exception as error:
                row['error'] = str(error)
            row['latency_ms'] = int((time.monotonic() - started) * 1000)
            records.append(row)
    originals = [r for r in records if r['variant'] == 'original']
    slices = {}
    for field in ('generator', 'source', 'task', 'pose', 'quality'):
        slices[field] = {str(value): metric_summary([r for r in originals if r.get(field, 'unknown') == value])
                         for value in sorted({r.get(field, 'unknown') for r in originals}, key=str)}
    latencies = [r['latency_ms'] for r in records]
    report = {'format_version': 1, 'mode': mode, 'purpose': purpose,
        'model_id': vit.model_name, 'model_revision': vit.revision,
        'processor': vit.processor_identity, 'policy': 'image-vit-v3' if detector else 'direct-full-frame-diagnostic',
        'decision_policy': __import__('models.image_deepfake.inference.vit_policy', fromlist=['load_policy']).load_policy(allow_candidate=True, expected_revision=vit.revision) if detector else None,
        'strategy': 'face_max' if detector else 'full_frame', 'crop_padding': 0.0,
        'manifest_sha256': hashlib.sha256(Path(manifest).read_bytes()).hexdigest(),
        'summary': metric_summary(originals), 'reference_threshold': .5,
        'status_counts': dict(Counter(r['status'] for r in originals)), 'slices': slices,
        'variants': {v: metric_summary([r for r in records if r['variant'] == v]) for v in variants},
        'group_intervals': grouped_intervals(originals, bootstrap),
        'latency_ms': {'p50': float(np.percentile(latencies, 50)), 'p95': float(np.percentile(latencies, 95))},
        'records': records, 'calibration_available': False,
        'limits': ['Unknown upstream training membership; source groups do not prove subject independence.',
                   'Reference-threshold metrics are diagnostic, not deployed decision metrics.',
                   'Derived transforms share labels/groups; screenshot proxy is not a real messaging-app benchmark.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--mode', choices=['vit_direct', 'vit_policy'], default='vit_policy')
    parser.add_argument('--purpose', choices=['validation', 'calibration', 'test'], default='test')
    parser.add_argument('--robustness', action='store_true')
    args = parser.parse_args()
    evaluate(args.manifest, args.output, args.mode, args.purpose,
             ('original', 'jpeg_95', 'jpeg_75', 'jpeg_50', 'resize_256', 'screenshot_proxy') if args.robustness else ('original',))
