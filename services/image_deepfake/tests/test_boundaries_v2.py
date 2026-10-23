import io
import time
import jwt
import pytest
import httpx
from PIL import Image
from services.image_deepfake.app.main import app
from services.image_deepfake.app.worker import worker
from services.image_deepfake.app.config.settings import settings

@pytest.fixture
def anyio_backend(): return 'asyncio'

@pytest.mark.anyio
async def test_unauthenticated_upload_and_key_are_blocked():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post('/detect/key',json={'storage_key':'anything.png'})
        assert response.status_code==401
        response=await client.post('/detect/file',files={'file':('x.png',b'bad','image/png')})
        assert response.status_code==401

@pytest.mark.anyio
async def test_authenticated_public_key_is_forbidden():
    token=jwt.encode({'sub':'test-owner','token_type':'access','exp':int(time.time())+60},settings.JWT_SECRET_KEY,algorithm=settings.JWT_ALGORITHM)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post('/detect/key',json={'storage_key':'anything.png'},headers={'Authorization':'Bearer '+token})
        assert response.status_code==403

def test_worker_rejects_absolute_and_traversal_paths(tmp_path,monkeypatch):
    root=tmp_path/'allowed';root.mkdir()
    outsider=tmp_path/'outside.png';Image.new('RGB',(20,20),'blue').save(outsider)
    monkeypatch.setattr(worker,'storage_dir',str(root))
    assert worker.resolve_image_bytes(str(outsider))[0] is None
    assert worker.resolve_image_bytes('../outside.png')[0] is None
    Image.new('RGB',(20,20),'blue').save(root/'inside.png')
    assert worker.resolve_image_bytes('inside.png')[1] is None

@pytest.mark.anyio
async def test_missing_weights_fail_readiness_but_not_liveness(monkeypatch):
    monkeypatch.setattr(worker.detector, "policy", "image-screening-v2")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        assert (await client.get('/health')).status_code==200
        response=await client.get('/ready')
        assert response.status_code==503
        assert response.json()['trained_cnn'] is False

@pytest.mark.anyio
async def test_body_budget_precedes_multipart_parsing():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post('/detect/file',content=b'x',headers={'Content-Length':str(20*1024*1024)})
        assert response.status_code==413

@pytest.mark.anyio
async def test_streamed_budget_cannot_be_bypassed_by_missing_length():
    from shared.image_body_limit import ImageBodyLimit
    from fastapi import HTTPException
    chunks=iter([{'type':'http.request','body':b'x'*40000,'more_body':True}]*3)
    calls=[]
    async def receive():calls.append(1);return next(chunks)
    async def application(scope,receive,send):
        for _ in range(3):await receive()
    middleware=ImageBodyLimit(application,paths=['/detect/file'],max_bytes=1)
    with pytest.raises(HTTPException) as error:
        await middleware({'type':'http','path':'/detect/file','headers':[]},receive,None)
    assert error.value.status_code==413 and len(calls)==2
