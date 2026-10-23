"""Evaluate annotated face boxes; absence of annotations is not negative ground truth."""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from models.image_deepfake.preprocessing.validator import canonical_bytes
from models.image_deepfake.forensics.face_analyzer import FaceAnalyzer


def iou(a, b):
    x, y = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[0]+a[2], b[0]+b[2]), min(a[1]+a[3], b[1]+b[3])
    overlap = max(0, right-x)*max(0, bottom-y)
    return overlap/max(1, a[2]*a[3]+b[2]*b[3]-overlap)


def evaluate(manifest, output):
    path, target = Path(manifest).resolve(), Path(output)
    if target.exists(): raise ValueError('Refusing to overwrite localization report')
    rows = json.loads(path.read_text()); analyzer = FaceAnalyzer(); records = []
    if not rows: raise ValueError('Annotated manifest cannot be empty')
    for row in rows:
        if 'boxes' not in row or row.get('coordinate_space') != 'exif_oriented_rgb':
            raise ValueError('Explicit boxes and EXIF-oriented coordinate space are required')
        expected = row['boxes']
        if any(not isinstance(b, list) or len(b) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in b) or min(b[2:]) <= 0 for b in expected):
            raise ValueError('Invalid annotation box')
        result = analyzer.analyze(canonical_bytes((path.parent/row['path']).read_bytes()))
        detected = result.get('bounding_boxes', []); matched = set(); true_positive = 0
        for box in detected:
            choices = [(iou(box, target), index) for index, target in enumerate(expected) if index not in matched]
            if choices:
                score, index = max(choices)
                if score >= .5: matched.add(index); true_positive += 1
        records.append({'pose': row.get('pose', 'unknown'), 'quality': row.get('quality', 'unknown'),
                        'tp': true_positive, 'fp': len(detected)-true_positive,
                        'fn': len(expected)-true_positive, 'status': result.get('status')})
    def summarize(items):
        tp, fp, fn = (sum(r[k] for r in items) for k in ('tp', 'fp', 'fn'))
        return {'count': len(items), 'tp': tp, 'fp': fp, 'fn': fn,
                'precision': tp/(tp+fp) if tp+fp else None, 'recall': tp/(tp+fn) if tp+fn else None,
                'runtime_unavailable': sum(r['status'] not in {'APPLIED', 'SKIPPED'} for r in items)}
    report = {'iou_threshold': .5, 'summary': summarize(records),
              'slices': {field: {value: summarize([r for r in records if r[field] == value])
                                 for value in {r[field] for r in records}} for field in ('pose', 'quality')},
              'records': records, 'limits': 'Annotation completeness and coordinate correctness require manual verification.'}
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--manifest', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); evaluate(args.manifest, args.output)
