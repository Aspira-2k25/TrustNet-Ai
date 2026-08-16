import pytest
from shared.schemas.events import DetectionRequestedEvent, DetectionRequestedPayload, DetectorCompletedEvent
from shared.constants.modules import ModuleEnum
from shared.schemas.detection_result import DetectionResult
from shared.tests.test_detection_result import get_base_valid_data

def test_detection_requested_event():
    payload = DetectionRequestedPayload(object_storage_key="test/image.jpg")
    event = DetectionRequestedEvent(
        scan_id="scan-123",
        module=ModuleEnum.image_deepfake,
        timestamp="2026-08-15T18:00:00Z",
        payload=payload
    )
    assert event.scan_id == "scan-123"
    assert event.module == ModuleEnum.image_deepfake
    assert event.payload.object_storage_key == "test/image.jpg"
    assert event.schema_version == 1

def test_detector_completed_event():
    result_data = get_base_valid_data()
    result = DetectionResult(**result_data)
    
    event = DetectorCompletedEvent(
        payload=result
    )
    
    # event_id should be auto-generated via shared.utils.ids
    assert event.event_id is not None
    assert len(event.event_id) > 0
    assert event.schema_version == 1
    assert event.payload.scan_id == result.scan_id
