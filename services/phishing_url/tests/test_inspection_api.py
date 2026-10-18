"""Inspection delegates to the protected pipeline and bounds concurrent work."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from services.phishing_url.app.main import app
from shared.schemas.detection_result import DetectionResult


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
async def test_inspection_delegates_to_existing_collection_pipeline(monkeypatch):
    monkeypatch.setattr(app.state, 'detector', SimpleNamespace(model=object()), raising=False)
    monkeypatch.setattr(app.state, 'inspection_slots', asyncio.Semaphore(2), raising=False)
    def handle(service, event):
        assert event['payload'] == {'url': 'https://example.com/'}
        return SimpleNamespace(payload=DetectionResult(scan_id=event['scan_id'], module='phishing',
            detector_id='fixture', model_version='fixture', preprocessing_version='fixture',
            native_score=.2, native_score_semantics='probability_of_positive_class', risk_score=20,
            confidence=0, label='legitimate', status='PARTIAL_SUCCESS',
            timestamp=datetime.now(timezone.utc).isoformat()))
    with patch('services.phishing_url.app.detection_service.DetectionService.handle', handle):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post('/inspect', json={'scan_id':'saved-link', 'url':'https://example.com/'})
    assert response.status_code == 200
    assert response.json()['data']['metadata']['inspection_mode'] == 'explicit_website_inspection'
    assert app.state.inspection_slots._value == 2


@pytest.mark.anyio
async def test_missing_model_and_busy_inspection_return_explicit_failure(monkeypatch):
    monkeypatch.setattr(app.state, 'detector', SimpleNamespace(model=None), raising=False)
    monkeypatch.setattr(app.state, 'inspection_slots', asyncio.Semaphore(0), raising=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        request = {'scan_id':'saved-link', 'url':'https://example.com/'}
        assert (await client.post('/inspect', json=request)).status_code == 503
        app.state.detector.model = object()
        assert (await client.post('/inspect', json=request)).status_code == 429
        assert (await client.post('/inspect', json={**request, 'proxy':'http://invalid/'})).status_code == 422
