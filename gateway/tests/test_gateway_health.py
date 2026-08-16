import pytest
import httpx
from gateway.app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.anyio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "data" in data
    assert data["data"]["status"] == "ok"
    assert data["data"]["service"] == "gateway_service"
    assert "error" in data
    assert data["error"] is None
    assert "meta" in data
    assert "request_id" in data["meta"]
    assert len(data["meta"]["request_id"]) > 0
