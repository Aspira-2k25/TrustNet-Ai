import pytest
from pydantic import ValidationError
from shared.schemas.detection_result import DetectionResult, ModuleEnum, NativeScoreSemanticsEnum, StatusEnum

def get_base_valid_data():
    return {
        "scan_id": "123e4567-e89b-12d3-a456-426614174000",
        "module": ModuleEnum.image_deepfake,
        "detector_id": "image_deepfake.efficientnet_b0.v1",
        "model_version": "v1.0",
        "preprocessing_version": "v1.0",
        "native_score": 0.95,
        "native_score_semantics": NativeScoreSemanticsEnum.probability_of_positive_class,
        "risk_score": 5.0,
        "confidence": 0.99,
        "label": "REAL",
        "status": StatusEnum.SUCCESS,
        "evidence": [],
        "processing_time_ms": 150,
        "timestamp": "2026-08-15T18:00:00Z"
    }

def test_valid_detection_result_success():
    data = get_base_valid_data()
    result = DetectionResult(**data)
    assert result.status == StatusEnum.SUCCESS
    assert result.error_code is None

def test_valid_detection_result_failure():
    data = get_base_valid_data()
    data["status"] = StatusEnum.FAILED
    data["error_code"] = "MODEL_TIMEOUT"
    result = DetectionResult(**data)
    assert result.status == StatusEnum.FAILED
    assert result.error_code == "MODEL_TIMEOUT"

def test_risk_score_below_zero_rejected():
    data = get_base_valid_data()
    data["risk_score"] = -1.0
    with pytest.raises(ValidationError):
        DetectionResult(**data)

def test_risk_score_above_100_rejected():
    data = get_base_valid_data()
    data["risk_score"] = 101.0
    with pytest.raises(ValidationError):
        DetectionResult(**data)

def test_confidence_out_of_range_rejected():
    data = get_base_valid_data()
    data["confidence"] = 1.5
    with pytest.raises(ValidationError):
        DetectionResult(**data)

def test_invalid_status_rejected():
    data = get_base_valid_data()
    data["status"] = "MAYBE"
    with pytest.raises(ValidationError):
        DetectionResult(**data)

def test_invalid_module_rejected():
    data = get_base_valid_data()
    data["module"] = "not_a_real_module"
    with pytest.raises(ValidationError):
        DetectionResult(**data)

def test_success_with_error_code_rejected():
    data = get_base_valid_data()
    data["status"] = StatusEnum.SUCCESS
    data["error_code"] = "SOME_ERROR"
    with pytest.raises(ValidationError):
        DetectionResult(**data)

def test_failed_without_error_code_rejected():
    data = get_base_valid_data()
    data["status"] = StatusEnum.FAILED
    data["error_code"] = None
    with pytest.raises(ValidationError):
        DetectionResult(**data)

def test_schema_version_default():
    data = get_base_valid_data()
    if "schema_version" in data:
        del data["schema_version"]
    result = DetectionResult(**data)
    assert result.schema_version == 1

def test_timestamp_format():
    data = get_base_valid_data()
    data["timestamp"] = "not-a-timestamp"
    with pytest.raises(ValidationError):
        DetectionResult(**data)
