"""Promote only after an independent all-input test meets explicit budgets."""
import argparse
import hashlib
import json
from pathlib import Path
from models.image_deepfake.evaluation.select_policy import wilson_upper


def promote(candidate_path, test_path, output):
    candidate_path, test_path, target = map(lambda p: Path(p).resolve(), (candidate_path, test_path, output))
    if target.exists() or not candidate_path.parent == test_path.parent == target.parent:
        raise ValueError('Use new files inside one version directory')
    candidate = json.loads(candidate_path.read_text()); test = json.loads(test_path.read_text())
    validation = json.loads((candidate_path.parent/candidate['evaluation_report']).read_text())
    if (test.get('purpose') != 'test' or test.get('mode') != 'vit_policy'
            or test.get('model_revision') != candidate['model_revision']
            or (test.get('processor') or {}).get('sha256') != candidate['processor_sha256']
            or (test.get('decision_policy') or {}).get('policy_sha256') != hashlib.sha256(candidate_path.read_bytes()).hexdigest()):
        raise ValueError('Final test did not evaluate this exact candidate')
    validation_rows = [r for r in validation['records'] if r['variant'] == 'original']
    test_rows = [r for r in test['records'] if r['variant'] == 'original']
    for field in ('sha256', 'pixel_sha256', 'group', 'subject_id'):
        known = {r[field] for r in validation_rows if r.get(field)}
        if known.intersection(r[field] for r in test_rows if r.get(field)):
            raise ValueError('Validation/final-test leakage: '+field)
    if len({r['group'] for r in test_rows}) != len(test_rows): raise ValueError('Final test needs independent source groups')
    if not test_rows or sum(not r['abstained'] for r in test_rows)/len(test_rows) < .9:
        raise ValueError('Final accepted coverage below 90%')
    real = [r for r in test_rows if r['label'] == 0]; fake = [r for r in test_rows if r['label'] == 1]
    if min(len(real), len(fake)) < 1000: raise ValueError('Final test needs at least 1000 sources per class')
    fp = sum(r.get('verdict') == 'LIKELY_AI_MANIPULATED' for r in real)
    fn = sum(r.get('verdict') == 'LOW_MANIPULATION_SIGNAL' for r in fake)
    if wilson_upper(fp, len(real)) > candidate['max_fpr'] or wilson_upper(fn, len(fake)) > candidate['max_fnr']:
        raise ValueError('Final test fails declared false-positive/false-negative budgets')
    result = {**candidate, 'release_approved': True, 'final_test_report': test_path.name,
              'final_test_sha256': hashlib.sha256(test_path.read_bytes()).hexdigest(),
              'promotion_definition': 'Independent test software gates passed; unknown upstream identities/generators and label quality remain dataset limitations.'}
    target.write_text(json.dumps(result, indent=2)); return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('candidate', 'test', 'output'): parser.add_argument('--'+name, required=True)
    args = parser.parse_args(); promote(args.candidate, args.test, args.output)
