import copy
from datetime import datetime, timedelta, timezone
import uuid

import httpx
import pytest

from services.scan_management.app.main import app
from services.scan_management.app.database.session import async_session_factory, init_db
from services.scan_management.app.db_models.scan import Scan, ScanAssessment, LinkInspection
from shared.schemas.detection_result import DetectionResult


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
async def source():
    await init_db()
    scan_id = str(uuid.uuid4())
    original = {'scan_id': scan_id, 'module': 'scam_message', 'risk_score': 21,
                'metadata': {'links': [{'url': 'https://example.com/receipt', 'risk_score': 21}],
                             'fusion': {'combined_score': 21, 'calibrated': False}}}
    async with async_session_factory() as db:
        db.add(Scan(id=scan_id, user_id='usr-researcher-1', status='SUCCESS', content_type='text'))
        db.add(ScanAssessment(scan_id=scan_id, assessment={'result': copy.deepcopy(original)}))
        await db.commit()
    return scan_id, original


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        yield client


def backend(monkeypatch, *, unavailable=False, wrong_id=False, no_live=False):
    requests = []
    original_post = httpx.AsyncClient.post

    async def intercept(client, url, **kwargs):
        if str(url).endswith(':8007/inspect'):
            request = kwargs['json']; requests.append(request)
            if unavailable:
                raise httpx.ConnectError('Fixture collector unavailable')
            result = DetectionResult(scan_id='wrong' if wrong_id else request['scan_id'], module='phishing',
                detector_id='fixture', model_version='fixture', preprocessing_version='fixture',
                native_score=.1, native_score_semantics='probability_of_positive_class', risk_score=12,
                confidence=0, label='legitimate', status='PARTIAL_SUCCESS',
                timestamp=datetime.now(timezone.utc).isoformat(), metadata={'forensics': {
                    'hostname': 'example.com', 'registered_domain': 'example.com',
                    'network': {'signals': {} if no_live else {'dns': {'status': 'observed', 'addresses': ['93.184.216.34']}}}}})
            return httpx.Response(200, json={'data': result.model_dump(mode='json')}, request=httpx.Request('POST', str(url)))
        return await original_post(client, url, **kwargs)
    monkeypatch.setattr(httpx.AsyncClient, 'post', intercept)
    return requests


@pytest.mark.anyio
async def test_saved_inspection_is_owner_scoped_cached_and_keeps_original_score(source, client, monkeypatch):
    scan_id, original = source
    requests = backend(monkeypatch)
    endpoint = f'/scans/{scan_id}/links/0/inspection'
    response = await client.post(endpoint, json={})
    assert response.status_code == 200, response.text
    result = response.json()['data']['result']
    inspection = result['metadata']['links'][0]['inspection']
    assert inspection['status'] == 'COMPLETED'
    assert inspection['summary']['live_checks_observed'] == 1
    assert inspection['result']['risk_score'] == 12
    assert result['risk_score'] == original['risk_score'] == 21
    assert result['metadata']['fusion'] == original['metadata']['fusion']
    assert requests[0]['url'] == 'https://example.com/receipt'
    saved = (await client.get(f'/scans/{scan_id}')).json()['data']['result']
    assert saved == result
    history = (await client.get('/scans?limit=100')).json()['data']['scans']
    assert next(s for s in history if s['id'] == scan_id)['result'] == result
    assert (await client.post(endpoint, json={})).status_code == 200
    assert len(requests) == 1
    # The original assessment JSON is unchanged, including the quick URL result.
    async with async_session_factory() as db:
        assert (await db.get(ScanAssessment, scan_id)).assessment['result'] == original


@pytest.mark.anyio
async def test_inspection_rejects_unauthenticated_other_owner_and_arbitrary_url(source, client, monkeypatch):
    scan_id, _ = source
    requests = backend(monkeypatch)
    endpoint = f'/scans/{scan_id}/links/0/inspection'
    monkeypatch.setenv('ALLOW_MOCK_AUTH', 'false')
    assert (await client.post(endpoint, json={})).status_code == 401
    monkeypatch.setenv('ALLOW_MOCK_AUTH', 'true')
    async with async_session_factory() as db:
        scan = await db.get(Scan, scan_id); scan.user_id = 'different-owner'; await db.commit()
    assert (await client.post(endpoint, json={})).status_code == 403
    assert not requests
    assert (await client.post(endpoint, json={'url': 'http://127.0.0.1/'})).status_code == 422


@pytest.mark.anyio
@pytest.mark.parametrize('mode', ['unavailable', 'wrong_id', 'no_live'])
async def test_failure_is_explicit_and_retryable_without_a_safe_claim(source, client, monkeypatch, mode):
    scan_id, original = source
    backend(monkeypatch, **{mode: True})
    response = await client.post(f'/scans/{scan_id}/links/0/inspection', json={})
    assert response.status_code == 200
    result = response.json()['data']['result']
    inspection = result['metadata']['links'][0]['inspection']
    assert inspection['status'] == 'UNAVAILABLE'
    assert inspection['reason']
    assert result['risk_score'] == original['risk_score']


@pytest.mark.anyio
async def test_inflight_claim_prevents_duplicate_fetch_and_invalid_index(source, client, monkeypatch):
    scan_id, _ = source
    requests = backend(monkeypatch)
    async with async_session_factory() as db:
        db.add(LinkInspection(scan_id=scan_id, link_index=0, status='PROCESSING',
                              updated_at=datetime.now(timezone.utc), assessment={}))
        await db.commit()
    assert (await client.post(f'/scans/{scan_id}/links/0/inspection', json={})).status_code == 409
    assert (await client.post(f'/scans/{scan_id}/links/1/inspection', json={})).status_code == 404
    assert (await client.post(f'/scans/{scan_id}/links/8/inspection', json={})).status_code == 422
    assert not requests


@pytest.mark.anyio
async def test_stale_process_claim_can_recover(source, client, monkeypatch):
    scan_id, _ = source
    backend(monkeypatch)
    async with async_session_factory() as db:
        db.add(LinkInspection(scan_id=scan_id, link_index=0, status='PROCESSING',
                              updated_at=datetime.now(timezone.utc) - timedelta(minutes=3), assessment={}))
        await db.commit()
    response = await client.post(f'/scans/{scan_id}/links/0/inspection', json={})
    assert response.status_code == 200
    assert response.json()['data']['result']['metadata']['links'][0]['inspection']['status'] == 'COMPLETED'


@pytest.mark.anyio
async def test_inspection_rejects_non_web_urls(client):
    await init_db()
    scan_id = str(uuid.uuid4())
    original = {'scan_id': scan_id, 'module': 'scam_message', 'risk_score': 10,
                'metadata': {'links': [{'url': 'mailto:info@example.com', 'risk_score': 0}]}}
    async with async_session_factory() as db:
        db.add(Scan(id=scan_id, user_id='usr-researcher-1', status='SUCCESS', content_type='text'))
        db.add(ScanAssessment(scan_id=scan_id, assessment={'result': original}))
        await db.commit()
    res = await client.post(f'/scans/{scan_id}/links/0/inspection', json={})
    assert res.status_code == 422
    assert 'Only web URLs can be inspected' in res.json()['error']['message']

