import pytest
import io
import uuid
import httpx
from PIL import Image
from services.scan_management.app.main import app
from services.scan_management.app.database.session import init_db

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()

@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c

def create_valid_test_image_bytes() -> bytes:
    img = Image.new("RGB", (100, 100), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

@pytest.mark.anyio
async def test_upload_image_scan_success(client):
    img_bytes = create_valid_test_image_bytes()
    files = {
        "file": ("test_avatar.jpg", img_bytes, "image/jpeg")
    }
    data = {
        "modality": "image"
    }
    response = await client.post("/scans/upload", files=files, data=data)
    assert response.status_code == 202
    
    body = response.json()
    assert body["error"] is None
    assert body["data"]["content_type"] == "image"
    assert body["data"]["media_storage_key"].startswith("quarantine/image/")
    assert body["data"]["id"] is not None

@pytest.mark.anyio
async def test_upload_invalid_extension(client):
    files = {
        "file": ("malicious_script.exe", b"malicious binary payload", "application/octet-stream")
    }
    data = {
        "modality": "image"
    }
    response = await client.post("/scans/upload", files=files, data=data)
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_EXTENSION"

@pytest.mark.anyio
async def test_upload_corrupted_image_magic_bytes(client):
    files = {
        "file": ("fake_image.jpg", b"NOT_A_VALID_JPEG_HEADER", "image/jpeg")
    }
    data = {
        "modality": "image"
    }
    response = await client.post("/scans/upload", files=files, data=data)
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_IMAGE_BYTES"

@pytest.mark.anyio
async def test_create_text_scan_success(client):
    payload = {
        "text": "URGENT: Your bank account is locked. Click here to verify your identity."
    }
    response = await client.post("/scans/text", json=payload)
    assert response.status_code == 202
    
    body = response.json()
    assert body["error"] is None
    assert body["data"]["content_type"] == "text"
    assert body["data"]["raw_input"] == payload["text"]

@pytest.mark.anyio
async def test_create_url_scan_success(client):
    payload = {
        "url": "http://secure-login-apple-support-verify.com/login"
    }
    response = await client.post("/scans/url", json=payload)
    assert response.status_code == 202
    
    body = response.json()
    assert body["error"] is None
    assert body["data"]["content_type"] == "url"
    assert body["data"]["raw_input"] == payload["url"]

@pytest.mark.anyio
async def test_get_scan_by_id(client):
    # First create a scan
    payload = {"url": "https://example.org/test"}
    create_res = await client.post("/scans/url", json=payload)
    scan_id = create_res.json()["data"]["id"]
    
    # Retrieve it
    response = await client.get(f"/scans/{scan_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["id"] == scan_id
    assert body["data"]["content_type"] == "url"

@pytest.mark.anyio
async def test_get_nonexistent_scan(client):
    nonexistent_id = str(uuid.uuid4())
    response = await client.get(f"/scans/{nonexistent_id}")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "SCAN_NOT_FOUND"

@pytest.mark.anyio
async def test_list_scans(client):
    response = await client.get("/scans?page=1&limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert "scans" in body["data"]
    assert isinstance(body["data"]["scans"], list)
    assert body["data"]["total"] >= 0
