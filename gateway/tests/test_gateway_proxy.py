import time
import pytest
import jwt
import httpx
from gateway.app.main import app
from gateway.app.config.settings import settings

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c

def create_valid_test_token(sub="test_user_123", role="user") -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "role": role,
        "token_type": "access",
        "iat": now,
        "exp": now + 3600
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

@pytest.mark.anyio
async def test_unauthenticated_scan_request_rejected(client):
    response = await client.get("/api/v1/scans")
    assert response.status_code == 401
    
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "TOKEN_MISSING"
    assert "request_id" in body["meta"]

@pytest.mark.anyio
async def test_invalid_token_scan_request_rejected(client):
    response = await client.get("/api/v1/scans", headers={"Authorization": "Bearer invalid.malformed.token"})
    assert response.status_code == 401
    
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "INVALID_TOKEN"

@pytest.mark.anyio
async def test_downstream_unavailable_returns_503(client, monkeypatch):
    token = create_valid_test_token()
    monkeypatch.setattr(settings, "SCAN_SERVICE_URL", "http://127.0.0.1:59999")
    response = await client.get("/api/v1/scans", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503
    
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "request_id" in body["meta"]

@pytest.mark.anyio
async def test_auth_proxy_downstream_unavailable(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_SERVICE_URL", "http://127.0.0.1:59999")
    response = await client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "Password123!"})
    assert response.status_code == 503
    
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
