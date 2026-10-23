import json
import io
from PIL import Image
from models.image_deepfake.training.prepare_kaggle import prepare

def test_publisher_splits_labels_crops_and_duplicate_exclusions(tmp_path,monkeypatch):
    class FixtureDetector:
        cascades=[True]
        eye_cascade=object()
        def analyze(self, blob):
            if Image.open(io.BytesIO(blob)).getpixel((0,0))==(11,222,33):return {'bounding_boxes':[]}
            return {'bounding_boxes':[(2,2,60,60)]}
    import models.image_deepfake.forensics.face_analyzer as module
    monkeypatch.setattr(module,'FaceAnalyzer',FixtureDetector)
    root=tmp_path/'dataset'
    for index,(split,label) in enumerate((s,c) for s in ('train','valid','test') for c in ('real','fake')):
        folder=root/split/label;folder.mkdir(parents=True)
        Image.new('RGB',(64,64),(30+index*25,50,100)).save(folder/'one.png')
    (root/'valid/real/duplicate.png').write_bytes((root/'train/real/one.png').read_bytes())
    Image.new('RGB',(64,64),(11,222,33)).save(root/'test/real/missed-face.png')
    out=tmp_path/'prepared';report=prepare(root,out)
    assert len(report['excluded_duplicates'])==1
    assert 'subject identities' in report['grouping']
    assert report['input_policy']=='haar-eye-pair-crop-v1'
    for split in ('train','validation','test'):
        rows=json.loads((out/(split+'.json')).read_text())
        assert {row[1] for row in rows}=={0,1}
        assert all(Image.open(row[0]).size==(60,60) for row in rows)
    assert len(json.loads((out/'policy_test.json').read_text()))==3
    assert report['exclusion_counts']['one usable detected face required']==1
