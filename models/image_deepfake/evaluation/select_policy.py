"""Select a candidate face operating point from validation data only."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from models.image_deepfake.inference.vit_policy import MODEL, REVISION, POLICY


def wilson_upper(errors, count):
    if not count: return 1.0
    z = 1.959963984540054; p = errors / count
    return (p + z*z/(2*count) + z*math.sqrt(p*(1-p)/count + z*z/(4*count*count))) / (1 + z*z/count)


def select(report_path, output, max_fpr=.01, max_fnr=.05, min_per_class=1000):
    source = Path(report_path).resolve(); target = Path(output).resolve()
    if target.exists(): raise ValueError('Refusing to overwrite policy')
    if source.parent != target.parent: raise ValueError('Policy and evaluation report must share a version directory')
    report = json.loads(source.read_text())
    if (report.get('purpose') != 'validation' or report.get('mode') != 'vit_policy'
            or report.get('model_id') != MODEL or not report.get('model_revision')
            or report.get('strategy') != 'face_max' or report.get('crop_padding') != 0.0
            or not report.get('processor', {}).get('sha256')):
        raise ValueError('Requires matching ViT policy validation evidence with processor identity')
    if not 0 < max_fpr < 1 or not 0 < max_fnr < 1 or min_per_class < 1000:
        raise ValueError('Invalid acceptance budget; at least 1000 independent sources per class required')
    rows = [r for r in report['records'] if r['variant'] == 'original']
    if len({r['group'] for r in rows}) != len(rows):
        raise ValueError('Selection requires independent source groups, not correlated copies')
    real = [r['score'] for r in rows if r['label'] == 0 and r.get('score') is not None]
    fake = [r['score'] for r in rows if r['label'] == 1 and r.get('score') is not None]
    if min(len(real), len(fake)) < min_per_class:
        raise ValueError('Insufficient independently scored validation sources')
    coverage = (len(real)+len(fake))/len(rows)
    if coverage < .9: raise ValueError('Scoring coverage below 90%; fix coverage before threshold selection')
    candidates = sorted(set([0.0, 1.0] + real + fake))
    high = next((t for t in candidates if wilson_upper(sum(s >= t for s in real), len(real)) <= max_fpr), None)
    lows = [t for t in candidates if wilson_upper(sum(s < t for s in fake), len(fake)) <= max_fnr]
    low = min(max(lows), math.nextafter(high, 0.0)) if lows and high is not None else None
    if high is None or low is None or not low < high:
        raise ValueError('No reliable two-boundary operating point meets the declared budgets')
    candidate = {'id': POLICY, 'validated': True, 'release_approved': False,
        'model_id': MODEL, 'model_revision': report['model_revision'], 'processor_sha256': report['processor']['sha256'],
        'aggregation': 'face_max', 'crop_padding': 0.0, 'low': low*100, 'high': high*100,
        'evaluation_report': source.name, 'evaluation_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'max_fpr': max_fpr, 'max_fnr': max_fnr, 'scoring_coverage': coverage,
        'limits': 'Validation-selected candidate. Independent final test and human promotion review still required; no confidence calibration.'}
    target.write_text(json.dumps(candidate, indent=2)); return candidate


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--report', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); select(args.report, args.output)
