import io
import uuid
from datetime import datetime, timezone
import pytest
import httpx
from PIL import Image

from services.image_deepfake.app.main import app
from services.image_deepfake.app.worker import worker
from shared.schemas.events import DetectionRequestedEvent, DetectionRequestedPayload, DetectorCompletedEvent
from shared.constants.modules import ModuleEnum
from shared.constants.status import StatusEnum
from shared.constants.native_score_semantics import NativeScoreSemanticsEnum

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c

def create_valid_test_image_bytes() -> bytes:
    img = Image.new("RGB", (100, 100), color=(120, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

@pytest.mark.anyio
async def test_detect_image_file_endpoint(client):
    img_bytes = create_valid_test_image_bytes()
    scan_id = str(uuid.uuid4())
    
    files = {
        "file": ("test_face.jpg", img_bytes, "image/jpeg")
    }
    data = {
        "scan_id": scan_id
    }
    response = await client.post("/detect/file", files=files, data=data)
    assert response.status_code == 200
    
    body = response.json()
    assert body["error"] is None
    assert body["data"]["scan_id"] == scan_id
    assert body["data"]["module"] == "image_deepfake"
    assert body["data"]["status"] == "SUCCESS"
    assert 0.0 <= body["data"]["risk_score"] <= 100.0

def test_worker_process_valid_file(tmp_path):
    img_bytes = create_valid_test_image_bytes()
    test_file = tmp_path / "test_image.jpg"
    test_file.write_bytes(img_bytes)

    scan_id = str(uuid.uuid4())
    event = DetectionRequestedEvent(
        scan_id=scan_id,
        module=ModuleEnum.image_deepfake,
        timestamp=datetime.now(timezone.utc).isoformat(),
        payload=DetectionRequestedPayload(
            object_storage_key=str(test_file)
        )
    )

    completed_event = worker.process_request(event)
    assert isinstance(completed_event, DetectorCompletedEvent)
    assert completed_event.payload.scan_id == scan_id
    assert completed_event.payload.status == StatusEnum.SUCCESS
    assert completed_event.payload.error_code is None
    assert completed_event.payload.native_score_semantics == NativeScoreSemanticsEnum.probability_of_negative_class

def test_worker_process_missing_file():
    scan_id = str(uuid.uuid4())
    event = DetectionRequestedEvent(
        scan_id=scan_id,
        module=ModuleEnum.image_deepfake,
        timestamp=datetime.now(timezone.utc).isoformat(),
        payload=DetectionRequestedPayload(
            object_storage_key="non_existent/path/to/missing_file.jpg"
        )
    )

    completed_event = worker.process_request(event)
    assert isinstance(completed_event, DetectorCompletedEvent)
    assert completed_event.payload.scan_id == scan_id
    assert completed_event.payload.status == StatusEnum.FAILED
    assert completed_event.payload.error_code == "MEDIA_NOT_FOUND"

def test_worker_handle_raw_message(tmp_path):
    img_bytes = create_valid_test_image_bytes()
    test_file = tmp_path / "handled_image.jpg"
    test_file.write_bytes(img_bytes)

    scan_id = str(uuid.uuid4())
    event = DetectionRequestedEvent(
        scan_id=scan_id,
        module=ModuleEnum.image_deepfake,
        timestamp=datetime.now(timezone.utc).isoformat(),
        payload=DetectionRequestedPayload(
            object_storage_key=str(test_file)
        )
    )

    raw_json_bytes = event.model_dump_json().encode("utf-8")
    completed = worker.handle_message(raw_json_bytes)
    assert completed is not None
    assert completed.payload.scan_id == scan_id
    assert completed.payload.status == StatusEnum.SUCCESS
