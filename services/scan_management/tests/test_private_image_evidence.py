"""HTTP/storage ownership contracts. Model inference is tested separately."""
import base64
import hashlib
import io
from datetime import datetime,timezone
import httpx
import jwt
from PIL import Image
import pytest
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from services.scan_management.app.main import app
from services.scan_management.app.database.session import Base,get_db
from services.scan_management.app.config.settings import settings


@pytest.fixture
def anyio_backend():return 'asyncio'


@pytest.mark.anyio
async def test_original_bytes_history_and_every_asset_require_the_scan_owner(tmp_path,monkeypatch):
    secret='private-image-test-secret-at-least-32-characters'
    monkeypatch.setenv('ALLOW_MOCK_AUTH','false')
    monkeypatch.setattr(settings,'JWT_SECRET_KEY',secret)
    monkeypatch.setattr(settings,'STORAGE_DIR',str(tmp_path/'uploads'))
    engine=create_async_engine('sqlite+aiosqlite:///'+str(tmp_path/'scans.sqlite'))
    async with engine.begin() as connection:await connection.run_sync(Base.metadata.create_all)
    factory=async_sessionmaker(engine,expire_on_commit=False)
    async def database():
        async with factory() as session:yield session
    app.dependency_overrides[get_db]=database
    def token(user):
        value=jwt.encode({'sub':user,'token_type':'access','exp':datetime.now(timezone.utc).timestamp()+300},secret,algorithm='HS256')
        return {'Authorization':'Bearer '+value}
    image=Image.new('RGB',(300,350),(70,110,130));buffer=io.BytesIO();image.save(buffer,'PNG',pnginfo=None)
    original=buffer.getvalue()
    # An explicit HTTP service seam; no fake model-accuracy claim.
    class ModelClient:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,files,data):
            assert files['file'][1]==original
            result=dict(scan_id=data['scan_id'],module='image_deepfake',detector_id='image_deepfake.evidence.v2',
                model_version='contract fixture',preprocessing_version='original-bytes',native_score=.01,
                native_score_semantics='anomaly_score',risk_score=1.,confidence=0,label='INCONCLUSIVE',
                verdict='INCONCLUSIVE',status='SUCCESS',timestamp=datetime.now(timezone.utc).isoformat(),
                metadata={'image_analysis':{'source_sha256':hashlib.sha256(original).hexdigest()},
                    'score_semantics':'independent readings','image_assets_base64':{'mask':base64.b64encode(original).decode(),'ela':base64.b64encode(original).decode()}})
            return httpx.Response(200,json={'data':result})
    real_client=httpx.AsyncClient
    try:
        async with real_client(transport=httpx.ASGITransport(app=app),base_url='http://scan') as client:
            monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:ModelClient())
            response=await client.post('/scans/analyze',headers=token('owner-a'),files={'file':('camera.png',original,'image/png')})
            assert response.status_code==200,response.text
            record=response.json()['data'];identifier=record['id']
            assert 'image_assets_base64' not in record['result']['metadata']
            for kind in ['original','mask','ela']:
                route=f'/scans/{identifier}/image/{kind}'
                own=await client.get(route,headers=token('owner-a'))
                assert own.status_code==200 and own.content==original
                assert own.headers['x-content-type-options']=='nosniff'
                assert (await client.get(route,headers=token('owner-b'))).status_code==404
                assert (await client.get(route)).status_code==401
            history=await client.get('/scans/'+identifier,headers=token('owner-a'))
            assert history.status_code==200
            saved=history.json()['data']['result']['metadata']['image_analysis']
            assert saved['source_sha256']==hashlib.sha256(original).hexdigest()
            assert saved['assets']['mask'].endswith('/mask')
            assert (await client.get(f'/scans/{identifier}/image/unknown',headers=token('owner-a'))).status_code==404
    finally:
        app.dependency_overrides.pop(get_db,None)
        await engine.dispose()
