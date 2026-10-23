import json
from types import SimpleNamespace
import pytest
from PIL import Image
from models.image_deepfake.evaluation.benchmark import evaluate, read_manifest
from models.image_deepfake.evaluation.data_audit import audit
from models.image_deepfake.evaluation.select_policy import select


def samples(tmp_path):
    for name, color in [('real', 'blue'), ('fake', 'red')]:
        Image.new('RGB', (64, 64), color).save(tmp_path/(name+'.png'))
    (tmp_path/'bad.png').write_bytes(b'invalid image')
    path = tmp_path/'manifest.json'
    path.write_text(json.dumps([['real.png', 0, 'r'], ['fake.png', 1, 'f'], ['bad.png', 0, 'bad']]))
    return path


def test_vit_direct_does_not_require_cnn_and_keeps_failed_denominator(tmp_path, monkeypatch):
    import models.image_deepfake.inference.local_vit_detector as module
    detector = SimpleNamespace(model_name='fixture', revision='fixture', processor_identity={},
                               predict=lambda _: {'is_hf_applied': True, 'hf_risk_score': 75})
    monkeypatch.setattr(module, 'LocalViTDeepfakeDetector', lambda: detector)
    report = evaluate(samples(tmp_path), tmp_path/'report.json', mode='vit_direct', bootstrap=0)
    assert report['summary']['count'] == 3
    assert report['summary']['scored'] == 2
    assert report['summary']['failure_count'] == 1
    assert report['summary']['abstention_rate'] == pytest.approx(1/3)


def test_canonical_duplicate_is_rejected(tmp_path):
    Image.new('RGB', (64, 64), 'blue').save(tmp_path/'a.png')
    Image.new('RGB', (64, 64), 'blue').save(tmp_path/'b.bmp')
    path = tmp_path/'manifest.json'; path.write_text(json.dumps([['a.png', 0, 'a'], ['b.bmp', 1, 'b']]))
    with pytest.raises(ValueError, match='Duplicate'):
        read_manifest(path, 'test')


def test_source_group_and_subject_leakage_are_reported(tmp_path):
    paths = {}
    for split, color in [('train', 'blue'), ('test', 'red')]:
        Image.new('RGB', (64, 64), color).save(tmp_path/(split+'.png'))
        path = tmp_path/(split+'.json'); paths[split] = path
        path.write_text(json.dumps([{'path': split+'.png', 'label': 0, 'group': 'same-source', 'subject_id': 'known-person'}]))
    report = audit(paths, tmp_path/'audit.json')
    assert not report['passed_exact_checks']
    assert {'group', 'subject'} <= {r['kind'] for r in report['cross_split_collisions']}


def test_policy_selection_rejects_test_data(tmp_path):
    path = tmp_path/'report.json'; path.write_text(json.dumps({'purpose': 'test'}))
    with pytest.raises(ValueError, match='validation'):
        select(path, tmp_path/'policy.json')


def test_selection_and_independent_promotion_gate(tmp_path):
    import hashlib
    from models.image_deepfake.inference.vit_policy import MODEL, REVISION, load_policy
    from models.image_deepfake.evaluation.promote_policy import promote
    rows = [{'group': f'g{i}', 'label': i % 2, 'score': .95 if i % 2 else .05,
             'variant': 'original', 'sha256': f'image{i}', 'pixel_sha256': f'pixels{i}', 'abstained': True}
            for i in range(2000)]
    report = {'purpose': 'validation', 'mode': 'vit_policy', 'model_id': MODEL, 'model_revision': REVISION,
              'strategy': 'face_max', 'crop_padding': 0., 'processor': {'sha256': 'processor'},
              'manifest_sha256': 'manifest', 'records': rows}
    path = tmp_path/'validation.json'; path.write_text(json.dumps(report))
    candidate_path = tmp_path/'candidate.json'; candidate = select(path, candidate_path)
    assert candidate['low'] < candidate['high']
    assert not load_policy(candidate_path)['validated']
    assert load_policy(candidate_path, allow_candidate=True)['validated']
    test = {**report, 'purpose': 'test', 'decision_policy': {'policy_sha256': hashlib.sha256(candidate_path.read_bytes()).hexdigest()},
            'records': [{**r, 'group': 'test'+r['group'], 'sha256': 'test'+r['sha256'],
                         'pixel_sha256': 'test'+r['pixel_sha256'], 'abstained': False,
                         'verdict': 'LIKELY_AI_MANIPULATED' if r['label'] else 'LOW_MANIPULATION_SIGNAL'} for r in rows]}
    test_path = tmp_path/'test.json'; test_path.write_text(json.dumps(test))
    released = tmp_path/'released.json'; promote(candidate_path, test_path, released)
    assert load_policy(released)['validated']
    test_path.write_text('{}')
    assert not load_policy(released)['validated']
