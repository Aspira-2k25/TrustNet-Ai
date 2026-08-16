import json
import logging
import io
from shared.logging.logger_setup import get_logger

def test_json_formatter():
    logger = get_logger("test_service")
    
    log_capture_string = io.StringIO()
    handler = logging.StreamHandler(log_capture_string)
    
    # Borrow the formatter from the existing handler
    original_handler = logger.handlers[0]
    handler.setFormatter(original_handler.formatter)
    
    logger.addHandler(handler)
    
    try:
        logger.info("Test message", extra={"request_id": "req-123", "scan_id": "scan-456"})
        
        log_output = log_capture_string.getvalue().strip()
        log_dict = json.loads(log_output)
        
        assert "timestamp" in log_dict
        assert log_dict["level"] == "INFO"
        assert log_dict["service"] == "test_service"
        assert log_dict["message"] == "Test message"
        assert log_dict["request_id"] == "req-123"
        assert log_dict["scan_id"] == "scan-456"
        
        # Test error fields
        logger.error("Error occurred", extra={"error_code": "ERR_01", "error_message": "Something failed"})
        error_output = log_capture_string.getvalue().strip().split('\n')[-1]
        error_dict = json.loads(error_output)
        
        assert error_dict["level"] == "ERROR"
        assert error_dict["error_code"] == "ERR_01"
        assert error_dict["error_message"] == "Something failed"
    finally:
        logger.removeHandler(handler)
