import hashlib
import json
import numpy as np
import pytest
from benchmark import native_head


def test_frozen_evaluation_reports_misses_and_false_alerts_without_tuning(tmp_path,monkeypatch):
    manifest=tmp_path/'manifest.json';manifest.write_text('{"fixture":true}')
    rows=[{'positive':False,'generator':'real'},{'positive':False,'generator':'real'},
          {'positive':True,'generator':'held-out-A'},{'positive':True,'generator':'held-out-B'}]
    head={'holdout_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
          'backbones':['fixture'],'mean':[0.],'scale':[1.],'coef':[1.],'intercept':0.,
          'choice':{'name':'native_head','isotonic_x':[0.,1.],'isotonic_y':[0.,1.],'threshold':.5}}
    frozen=json.dumps(head,sort_keys=True)
    monkeypatch.setattr(native_head,'features',lambda *a,**k:(rows,np.array([[-5.],[2.],[3.],[-2.]])))
    monkeypatch.setattr(native_head,'primary_scores',lambda *a:np.array([.1,.2,.7,.8]))
    output=tmp_path/'report.json';native_head.evaluate(tmp_path,tmp_path,head,output)
    result=json.loads(output.read_text())
    assert result['candidate']['tp']==1 and result['candidate']['fp']==1
    assert result['candidate']['tn']==1 and result['candidate']['fn']==1
    assert result['candidate']['precision']==.5 and result['candidate']['f1']==.5
    assert result['baseline']['recall']==1 and result['baseline']['real_fpr']==0
    assert result['candidate']['ai_stream_inconclusive_rate']==.5
    assert result['ai_stream_gate_passed'] is False and result['deployed'] is False
    assert result['source_metadata_shortcut_gate_passed'] is False
    assert result['promotion_eligible'] is False
    assert any('Source-file metadata' in reason for reason in result['promotion_blockers'])
    assert json.dumps(head,sort_keys=True)==frozen


def test_an_unmatched_holdout_is_rejected_before_any_model_prediction(tmp_path):
    (tmp_path/'manifest.json').write_text('{}')
    with pytest.raises(ValueError,match='test manifest'):
        native_head.evaluate(tmp_path,tmp_path,{'holdout_manifest_sha256':'wrong'},tmp_path/'out.json')
