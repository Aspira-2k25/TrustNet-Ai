import io
import json
from PIL import Image
from models.image_deepfake.inference import forensic_detector as module


def test_quality_gate_does_not_hide_the_experimental_head_disagreement(monkeypatch):
    # Unit fixture reproduces the observed score conflict, not model accuracy.
    model=module.ForensicDetector.__new__(module.ForensicDetector)
    model.config=json.loads((module.ROOT/'calibration/evidence-v2.json').read_text())
    model.modern_head={'fixture':True};model.localizer=None;model.localizer_error='Unit fixture edit check unavailable'
    class Primary:
        def predict(self,*args,**kwargs):return {'embedding':[0.],'ai_score':.0003889915533363819,'model_view_shape':[1,3,384,384]}
    model.global_model=Primary()
    monkeypatch.setattr(module,'head_score',lambda *args:.9582667556832105)
    monkeypatch.setattr(module,'inspect_c2pa',lambda *args:{})
    from models.image_deepfake.forensics import supporting_signals
    monkeypatch.setattr(supporting_signals,'analyze',lambda *args:{'assets':{}})
    image=io.BytesIO();Image.new('RGB',(64,64),'gray').save(image,'JPEG',quality=50)
    result=model.predict(image.getvalue(),scan_id='unit-disagreement')
    analysis=result.metadata['image_analysis']
    assert result.verdict=='INCONCLUSIVE'
    assert analysis['ai_checks_disagree'] is True
    assert analysis['ai_reading_status']=='quality_limited'
    assert any('does not corroborate' in reason for reason in analysis['reasons'])
    assert analysis['ai_raw_score']<.001 and analysis['ai_generated_prob']>.9
