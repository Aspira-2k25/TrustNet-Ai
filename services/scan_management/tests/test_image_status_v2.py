import io
from unittest.mock import AsyncMock
from types import SimpleNamespace
import pytest
from PIL import Image
from starlette.datastructures import UploadFile
from services.scan_management.app.routers import scan_router
from shared.schemas.detection_result import DetectionResult

@pytest.fixture
def anyio_backend():return 'asyncio'

@pytest.mark.anyio
async def test_direct_image_keeps_partial_status_and_hash(monkeypatch):
    result=DetectionResult(scan_id='fixture',module='image_deepfake',detector_id='fixture',model_version='v2',
        preprocessing_version='v2',native_score=.5,native_score_semantics='anomaly_score',risk_score=50,
        confidence=0,status='PARTIAL_SUCCESS',label='uncertain',verdict='UNCERTAIN',timestamp='2026-10-20T00:00:00Z',
        metadata={'assessment_policy':'image-screening-v2','input_sha256':'a'*64,'confidence_available':False})
    monkeypatch.setattr(scan_router,'image_detector',lambda:SimpleNamespace(predict=lambda *args,**kwargs:result))
    class Database:
        def __init__(self):self.rows=[];self.commit=AsyncMock();self.rollback=AsyncMock()
        def add(self,row):self.rows.append(row)
    database=Database();stream=io.BytesIO();Image.new('RGB',(32,32),'blue').save(stream,format='PNG');stream.seek(0)
    response=await scan_router.analyze_image_direct(UploadFile(filename='fixture.png',file=stream),False,'owner',database)
    assert response.data['status']=='PARTIAL_SUCCESS'
    assert database.rows[0].status=='PARTIAL_SUCCESS'
    assert response.data['result']['metadata']['input_sha256']=='a'*64


@pytest.mark.anyio
async def test_vit_unsupported_persists_no_trust_score(monkeypatch):
    result=DetectionResult(scan_id='fixture',module='image_deepfake',detector_id='vit',model_version='v3',
        preprocessing_version='v3',native_score=0,native_score_semantics='anomaly_score',risk_score=0,
        confidence=0,status='PARTIAL_SUCCESS',label='unknown',verdict='UNSUPPORTED',timestamp='2026-10-20T00:00:00Z',
        metadata={'assessment_policy':'image-vit-v3','score_available':False})
    monkeypatch.setattr(scan_router,'image_detector',lambda:SimpleNamespace(predict=lambda *args,**kwargs:result))
    database=SimpleNamespace(add=lambda row:None,commit=AsyncMock(),rollback=AsyncMock())
    stream=io.BytesIO();Image.new('RGB',(32,32),'blue').save(stream,format='PNG');stream.seek(0)
    response=await scan_router.analyze_image_direct(UploadFile(filename='fixture.png',file=stream),False,'owner',database)
    assert response.data['trust_score']['trust_risk_score'] is None
    assert response.data['trust_score']['module_scores']['image_deepfake'] is None
    assert response.data['trust_score']['risk_level']=='UNKNOWN'
