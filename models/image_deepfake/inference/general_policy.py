"""Whole-image decisions require matching independent validation and final-test evidence."""
import hashlib
import json
import math
import os
from pathlib import Path

POLICY = 'image-general-v4'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_evidence(root, name, expected):
    path = (root / name).resolve()
    if not path.is_relative_to(root) or digest(path) != expected:
        raise ValueError('Policy evidence integrity mismatch')
    return json.loads(path.read_text())


def load(identity, localizer, allow_candidate=False, path=None):
    default = {'id': POLICY, 'validated': False, 'reason': 'Whole-image operating point is not independently validated; manual review required.'}
    selected = path or os.getenv('IMAGE_GENERAL_POLICY_FILE')
    if not selected:
        return default
    try:
        source = Path(selected).resolve()
        value = json.loads(source.read_text())
        if (value.get('id') != POLICY or value.get('identity') != identity or value.get('localizer') != localizer
                or not identity.get('deployment_pinned') or not identity.get('processor_sha256')
                or value.get('validated') is not True or value.get('aggregation') != 'general_only_face_diagnostic'):
            raise ValueError('Model/backend/processor/localizer identity mismatch or unpinned deployment')
        low, high = value['low'], value['high']
        if any(isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n) for n in (low,high)) or not 0 <= low < high <= 100:
            raise ValueError('Invalid operating boundaries')
        validation = read_evidence(source.parent, value['evaluation_report'], value['evaluation_sha256'])
        from models.image_deepfake.evaluation.general import check_report, budgets
        check_report(validation, 'validation', identity, localizer)
        budgets(validation['records'], low, high)
        if not allow_candidate:
            if value.get('release_approved') is not True:
                raise ValueError('Independent final-test promotion incomplete')
            final = read_evidence(source.parent, value['final_test_report'], value['final_test_sha256'])
            check_report(final, 'test', identity, localizer)
            budgets(final['records'], low, high)
            from models.image_deepfake.evaluation.general import independent
            independent(validation['records'],final['records'])
        return {**value, 'reason': 'Independent operating-point gates passed; scores remain uncalibrated.'}
    except Exception as error:
        return {**default, 'reason': 'Policy unavailable: '+str(error)}
