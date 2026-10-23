"""Versioned face-screening contract. Model readiness is not policy validation."""
import hashlib
import json
import math
import os
from pathlib import Path

POLICY = 'image-vit-v3'
MODEL = 'dima806/deepfake_vs_real_image_detection'
REVISION = '29e4cf9efc543845610045f6ba7e88e5cf9d9301'


def load_policy(path=None, allow_candidate=False, expected_revision=REVISION):
    """Only an evaluated, matching policy artifact may emit threshold decisions."""
    policy = {'id': POLICY, 'validated': False, 'aggregation': 'face_max',
              'crop_padding': 0.0, 'low': None, 'high': None,
              'reason': 'No validated operating point installed; manual review required.'}
    selected = path or os.getenv('IMAGE_VIT_POLICY_FILE')
    if not selected:
        return policy
    try:
        source = Path(selected).resolve()
        candidate = json.loads(source.read_text(encoding='utf-8'))
        if (candidate.get('id') != POLICY or candidate.get('validated') is not True
                or candidate.get('model_revision') != expected_revision
                or candidate.get('model_id') != MODEL
                or candidate.get('aggregation') != 'face_max'
                or candidate.get('crop_padding') != 0.0):
            raise ValueError('Incompatible ViT policy identity or input strategy')
        low, high = candidate['low'], candidate['high']
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (low, high)) or not 0 <= low < high <= 100:
            raise ValueError('Invalid decision boundaries')
        report = (source.parent / candidate['evaluation_report']).resolve()
        if not report.is_relative_to(source.parent):
            raise ValueError('Evaluation report must be inside policy directory')
        if hashlib.sha256(report.read_bytes()).hexdigest() != candidate['evaluation_sha256']:
            raise ValueError('Evaluation report hash mismatch')
        evidence = json.loads(report.read_text(encoding='utf-8'))
        if (evidence.get('purpose') != 'validation' or evidence.get('mode') != 'vit_policy'
                or evidence.get('model_revision') != expected_revision
                or evidence.get('model_id') != MODEL
                or evidence.get('strategy') != 'face_max'
                or evidence.get('crop_padding') != 0.0
                or not evidence.get('manifest_sha256')):
            raise ValueError('Evaluation evidence does not match the policy')
        if candidate.get('processor_sha256') != (evidence.get('processor') or {}).get('sha256'):
            raise ValueError('Processor identity does not match validation evidence')
        if not allow_candidate and candidate.get('release_approved') is not True:
            return {**policy, 'reason': 'Validation candidate exists but independent final-test promotion is incomplete.'}
        if not allow_candidate:
            final_path = (source.parent/candidate['final_test_report']).resolve()
            if not final_path.is_relative_to(source.parent) or hashlib.sha256(final_path.read_bytes()).hexdigest() != candidate['final_test_sha256']:
                raise ValueError('Independent final-test evidence hash mismatch')
        # This validates compatibility/provenance, not the truth of human labels.
        return {**candidate, 'policy_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'reason': 'Validation-selected boundaries; scores remain uncalibrated.'}
    except Exception as error:
        return {**policy, 'reason': f'Policy artifact unavailable: {error}'}


def scope_state(face):
    if face.get('status') not in {'APPLIED', 'SKIPPED'} or not face.get('localization_available'):
        return 'LOCALIZATION_UNAVAILABLE'
    return 'SUPPORTED' if face.get('has_face') and face.get('bounding_boxes') else 'NO_ASSESSABLE_FACE'
