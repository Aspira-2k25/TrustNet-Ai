import logging
import json
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "unknown"),
            "message": record.getMessage(),
        }
        
        # NOTE: request_id and scan_id are passed as structured `extra` fields on each log call.
        # This choice is explicit to avoid global mutable state. Request-scoped context 
        # propagation across async services requires contextvars or similar, 
        # which adds complexity. Passing as `extra` ensures clean, stateless propagation.
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "scan_id"):
            log_record["scan_id"] = record.scan_id
            
        if hasattr(record, "error_code"):
            log_record["error_code"] = record.error_code
        if hasattr(record, "error_message"):
            log_record["error_message"] = record.error_message
            
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

class ServiceInjectFilter(logging.Filter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def filter(self, record):
        record.service = self.service_name
        return True

def get_logger(service_name: str) -> logging.Logger:
    logger = logging.getLogger(service_name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        
        # Inject service name into every log record
        logger.addFilter(ServiceInjectFilter(service_name))
        
        logger.addHandler(handler)
        logger.propagate = False
        
    return logger
