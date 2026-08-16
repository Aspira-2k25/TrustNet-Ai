import pytest
from typing import Any
from shared.interfaces.detector_base import BaseDetector
from shared.schemas.detection_result import DetectionResult
from shared.tests.test_detection_result import get_base_valid_data

def test_base_detector_cannot_be_instantiated():
    with pytest.raises(TypeError) as excinfo:
        BaseDetector()
    assert "Can't instantiate abstract class BaseDetector" in str(excinfo.value)

class DummyDetector(BaseDetector):
    def predict(self, input_data: Any) -> DetectionResult:
        result_data = get_base_valid_data()
        return DetectionResult(**result_data)

def test_concrete_detector_can_be_instantiated_and_called():
    detector = DummyDetector()
    result = detector.predict("some arbitrary input")
    
    assert isinstance(result, DetectionResult)
    assert result.scan_id == "123e4567-e89b-12d3-a456-426614174000"
