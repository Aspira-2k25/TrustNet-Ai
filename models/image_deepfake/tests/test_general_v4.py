"""Contract fixtures test routing and failures; they are not accuracy measurements."""
import io
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from PIL import Image

from models.image_deepfake.inference.general_image_client import GeneralConfig, GeneralImageClient, MODEL, REVISION, parse_distribution
from models.image_deepfake.inference.face_localizer import FaceLocalizer
from models.image_deepfake.inference.general_policy import load, digest
from models.image_deepfake.evaluation.general import select, promote, budgets, independent


def blob():
    stream=io.BytesIO();Image.new('RGB',(100,100),'blue').save(stream,format='PNG');return stream.getvalue()


def config(backend='hosted'):
    return GeneralConfig(MODEL,REVISION,backend,False,True,False,'hf_contract_fixture')


@pytest.mark.parametrize('value',[None,[],[{'label':'ai','score':.9}],
    [{'label':'fake','score':.9},{'label':'real','score':.1}],
    [{'label':'ai','score':True},{'label':'hum','score':0}],
    [{'label':'ai','score':float('nan')},{'label':'hum','score':.1}],
    [{'label':'ai','score':.9},{'label':'hum','score':.9}]])
def test_reject_malformed_distribution(value):
    with pytest.raises((ValueError,TypeError)):
        parse_distribution(value)


def test_registered_label_mapping_and_key_redaction():
    assert parse_distribution([{'label':'ai','score':.8},{'label':'hum','score':.2}])==80
    assert 'hf_contract_fixture' not in repr(config())


@pytest.mark.parametrize('status,code',[(401,'PROVIDER_UNAUTHORIZED'),(402,'PROVIDER_BILLING_REQUIRED'),
    (403,'PROVIDER_FORBIDDEN'),(404,'MODEL_NOT_SERVED'),(429,'PROVIDER_RATE_LIMITED'),(503,'PROVIDER_UNAVAILABLE')])
def test_hosted_failure_no_implicit_fallback(monkeypatch,status,code):
    calls=[]
    real=httpx.Client
    def response(request):
        calls.append(request);return httpx.Response(status,text='private provider diagnostics must not escape')
    monkeypatch.setattr('models.image_deepfake.inference.general_image_client.httpx.Client',lambda **kw:real(transport=httpx.MockTransport(response),**kw))
    client=GeneralImageClient(config());client._load=Mock(side_effect=AssertionError('no fallback'))
    result=client.predict(blob())
    assert result['risk_score'] is None and result['reason']==code
    assert len(calls)==(2 if status==429 or status>=500 else 1)
    assert 'private provider' not in json.dumps(result)
    client._load.assert_not_called()


def test_hosted_success_explicit_unpinned_identity(monkeypatch):
    real=httpx.Client
    monkeypatch.setattr('models.image_deepfake.inference.general_image_client.httpx.Client',lambda **kw:real(
        transport=httpx.MockTransport(lambda _:httpx.Response(200,json=[{'label':'ai','score':.8},{'label':'hum','score':.2}])),**kw))
    client=GeneralImageClient(config());assert not client.readiness()['ready']
    result=client.predict(blob())
    assert result['status']=='APPLIED' and result['risk_score']==80
    assert result['model_revision'] is None and not result['deployment_pinned']
    assert client.readiness()['connectivity_verified']
    assert 'hf_contract_fixture' not in json.dumps(result)


def test_hosted_timeout(monkeypatch):
    real=httpx.Client
    def timeout(_):raise httpx.ReadTimeout('secret diagnostics')
    monkeypatch.setattr('models.image_deepfake.inference.general_image_client.httpx.Client',lambda **kw:real(transport=httpx.MockTransport(timeout),**kw))
    assert GeneralImageClient(config()).predict(blob())['reason']=='PROVIDER_TIMEOUT'


@pytest.mark.parametrize('change,reason',[
    ({'allow_hosted':False},'HOSTED_UPLOAD_NOT_ENABLED'),({'key':''},'CREDENTIAL_NOT_CONFIGURED'),
    ({'model':'unregistered/model'},'MODEL_NOT_REGISTERED'),({'revision':'changed'},'MODEL_NOT_REGISTERED'),
    ({'backend':'automatic'},'INVALID_BACKEND')])
def test_configuration_does_not_call_network(monkeypatch,change,reason):
    monkeypatch.setattr(httpx,'Client',Mock(side_effect=AssertionError('no network')))
    client=GeneralImageClient(replace(config(),**change))
    assert client.predict(blob())['reason']==reason
    assert not client.readiness()['ready']


def test_landmark_validation_rejects_bad_geometry():
    row=[10,10,100,100,35,40,85,40,60,65,40,90,80,90,.95]
    assert FaceLocalizer.valid(row,200,200)
    for index,value in [(14,.2),(0,-1),(4,float('nan')),(11,20)]:
        changed=row.copy();changed[index]=value;assert not FaceLocalizer.valid(changed,200,200)


def identity():
    return {'model_id':MODEL,'model_revision':REVISION,'deployment_pinned':True,'processor_sha256':'contract-fixture'}


def records(prefix):
    import hashlib
    return [{'label':label,'score':.01 if label==0 else .99,'group':f'{prefix}-{label}-{i}',
             'sha256':hashlib.sha256(f'{prefix}-{label}-{i}'.encode()).hexdigest(),
             'pixel_sha256':hashlib.sha256(f'pixels-{prefix}-{label}-{i}'.encode()).hexdigest(),
             'variant':'original'} for label in (0,1) for i in range(1000)]


def test_policy_requires_independent_final_promotion(tmp_path):
    data={'policy':'image-general-v4','purpose':'validation','identity':identity(),'localizer':{'strategy':'fixture'},
          'manifest_sha256':'fixture-validation','records':records('validation')}
    validation=tmp_path/'validation.json';validation.write_text(json.dumps(data))
    candidate=tmp_path/'candidate.json';select(validation,candidate)
    assert not load(identity(),data['localizer'],path=candidate)['validated']
    assert load(identity(),data['localizer'],allow_candidate=True,path=candidate)['validated']
    final=tmp_path/'test.json';final.write_text(json.dumps({**data,'purpose':'test','manifest_sha256':'fixture-test','records':records('test')}))
    released=tmp_path/'released.json';promote(candidate,final,released)
    assert load(identity(),data['localizer'],path=released)['validated']
    assert not load({**identity(),'processor_sha256':'changed'},data['localizer'],path=released)['validated']
    final.write_text('{}');assert not load(identity(),data['localizer'],path=released)['validated']


def test_reject_overlap_insufficient_data_and_unpinned_identity(tmp_path):
    rows=records('overlap')
    with pytest.raises(ValueError,match='overlap'):independent(rows,rows)
    with pytest.raises(ValueError,match='1000'):budgets(rows[:5],10,90)
    assert not load({**identity(),'deployment_pinned':False},None,path=tmp_path/'missing.json')['validated']


@pytest.mark.parametrize('score,status,verdict',[(90,'APPLIED','UNCERTAIN'),(None,'UNAVAILABLE','UNKNOWN')])
def test_general_branch_independent_of_faces_and_metadata(monkeypatch,score,status,verdict):
    from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
    detector=EfficientNetDetector(policy='image-general-v4')
    for name in ['scene_analyzer','metadata_analyzer','watermark_analyzer','recompression_analyzer','face_analyzer',
                 'freq_analyzer','pixel_analyzer','gabor_analyzer','ela_analyzer','noise_analyzer','stego_analyzer']:
        obj=getattr(detector,name)
        monkeypatch.setattr(obj,'analyze',lambda *args:{'status':'SKIPPED','has_face':False,'face_count':0,
            'bounding_boxes':[],'localization_available':True,'has_unverified_generator_clue':True,'generator_name':'Fixture',
            'finding':'Editable fixture clue'})
    detector.general_client.predict=Mock(return_value={'status':status,'risk_score':score,'reason':'FIXTURE_UNAVAILABLE' if score is None else None})
    detector.local_vit.predict=Mock(side_effect=AssertionError('must not infer a face'))
    result=detector.predict(blob())
    assert result.verdict==verdict and result.metadata['score_available']==(score is not None)
    assert result.metadata['branches']['general']['risk_score']==score
    detector.general_client.predict.assert_called_once();detector.local_vit.predict.assert_not_called()
    assert result.status.value==('SUCCESS' if score is not None else 'UNAVAILABLE')
