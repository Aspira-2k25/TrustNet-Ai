import io
import uuid
import pytest
import httpx
from pathlib import Path
from PIL import Image

from services.image_deepfake.app.main import app
from services.image_deepfake.app.worker import worker

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.anyio
async def test_empty_file_upload_rejected(client):
    files = {"file": ("empty.jpg", b"", "image/jpeg")}
    response = await client.post("/detect/file", files=files, data={"scan_id": str(uuid.uuid4())})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "EMPTY_FILE"
    assert "empty" in body["error"]["message"].lower()

@pytest.mark.anyio
async def test_oversized_file_upload_rejected(client):
    # 15MB limit + 1 byte
    oversized_bytes = b"0" * (15 * 1024 * 1024 + 10)
    files = {"file": ("huge.jpg", oversized_bytes, "image/jpeg")}
    response = await client.post("/detect/file", files=files, data={"scan_id": str(uuid.uuid4())})
    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "FILE_TOO_LARGE"

@pytest.mark.anyio
async def test_invalid_image_bytes_rejected(client):
    fake_image_bytes = b"MZ\x90\x00\x03\x00\x00\x00ThisIsNotAnImageExecutable"
    files = {"file": ("malicious.jpg", fake_image_bytes, "image/jpeg")}
    response = await client.post("/detect/file", files=files, data={"scan_id": str(uuid.uuid4())})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_IMAGE_BYTES"

def test_path_traversal_detection_in_worker(tmp_path):
    # Attempting to resolve a path outside the storage root should be rejected safely
    worker.storage_dir = str(tmp_path / "storage")
    Path(worker.storage_dir).mkdir(parents=True, exist_ok=True)
    
    malicious_key = "../../etc/passwd"
    bytes_out, err = worker.resolve_image_bytes(malicious_key)
    assert bytes_out is None
    assert err is not None
    assert "directory traversal detected" in err.lower() or "traverses outside" in err.lower()
