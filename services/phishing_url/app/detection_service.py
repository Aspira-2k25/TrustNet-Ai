from shared.constants.modules import ModuleEnum
from shared.constants.schema_version import CURRENT_SCHEMA_VERSION
from shared.schemas.events import DetectionRequestedEvent, DetectorCompletedEvent

class DetectionService:
    def __init__(self, detector):
        self.detector = detector

    def handle(self, data):
        import time
        started = time.monotonic()
        event = DetectionRequestedEvent.model_validate(data)
        self.validate(event)
        try:
            result = self.detector.predict({"scan_id": event.scan_id, "url": event.payload.url})
        except (RuntimeError, ValueError) as exc:
            from shared.schemas.detection_result import DetectionResult
            from datetime import datetime, timezone
            result = DetectionResult(scan_id=event.scan_id, module="phishing", detector_id="phishing.worker", model_version="unavailable", preprocessing_version="unavailable", native_score=0, native_score_semantics="probability_of_positive_class", risk_score=0, confidence=0, label="unknown", status="FAILED", error_code="INFERENCE_FAILED", error_message=f"Phishing inference failed ({type(exc).__name__})", timestamp=datetime.now(timezone.utc).isoformat())
            from models.phishing_url.inference.forensics import apply_policy
            from models.phishing_url.preprocessing.url_parser import parse_url
            try:
                parse_url(event.payload.url)
            except ValueError:
                result.error_code = 'INVALID_URL'
            else:
                result = apply_policy(result, event.payload.url)
        import os
        from models.phishing_url.preprocessing.link_input import inspect_input
        try:link=inspect_input(event.payload.url)
        except ValueError:link={'kind':'invalid'}
        collector_url=os.getenv("PHISHING_COLLECTOR_URL")
        if collector_url and result.error_code != 'INVALID_URL' and link['kind']=='web':
            import httpx
            try:
                response=httpx.post(collector_url.rstrip('/')+'/collect',json={"url":link['normalized'],"include_html":True},headers={"x-collector-token":os.getenv("PHISHING_COLLECTOR_TOKEN","")},timeout=30)
                response.raise_for_status()
                result.metadata["collected_observations"]=response.json()
                result.metadata["metadata_used_by_model"]=False
                from models.phishing_url.inference.forensics import apply_policy
                result=apply_policy(result,event.payload.url,result.metadata.get('threshold'),response.json())
            except (httpx.HTTPError, ValueError, TypeError):
                result.metadata["collection_status"]="unavailable"
                from models.phishing_url.inference.forensics import apply_policy
                result=apply_policy(result,event.payload.url,result.metadata.get('threshold'),{'signals':{}})
        result.metadata['model_inference_ms'] = result.processing_time_ms
        result.processing_time_ms = round((time.monotonic()-started)*1000)
        result.metadata['processing_time_definition'] = 'Total phishing pipeline including collection; excludes Kafka queue delay.'
        return DetectorCompletedEvent(payload=result)

    @staticmethod
    def validate(event):
        if event.module != ModuleEnum.phishing or event.schema_version != CURRENT_SCHEMA_VERSION:
            raise ValueError("Unsupported phishing request module/schema")
        if not isinstance(event.payload.url,str) or not event.payload.url:
            raise ValueError("Phishing URL payload required")
