import unittest
from services.phishing_url.app.core.consumer import process
from services.phishing_url.app.detection_service import DetectionService
from models.phishing_url.inference.phishing_detector import PhishingDetector
from shared.schemas.events import DetectionRequestedEvent

class Repository:
    def __init__(self): self.saved = {}
    def get(self, scan_id, fingerprint):
        record = self.saved.get(scan_id)
        if record and record[0] != fingerprint: raise ValueError("Conflicting request")
        return record[1] if record else None
    def save(self, scan_id, fingerprint, completion):
        self.saved.setdefault(scan_id,(fingerprint,completion))
        return self.get(scan_id,fingerprint)
class WorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_replay_retains_completion_identity(self):
        event=DetectionRequestedEvent(scan_id="test",module="phishing",timestamp="2026-10-12T00:00:00Z",payload={"url":"https://example.com"})
        repository=Repository(); service=DetectionService(PhishingDetector())
        first=await process(event,service,repository); second=await process(event,service,repository)
        self.assertEqual(first,second)
        altered=event.model_copy(deep=True); altered.payload.url="https://different.com"
        with self.assertRaises(ValueError): await process(altered,service,repository)
    async def test_inference_failure_is_unknown(self):
        class Broken:
            def predict(self,_): raise RuntimeError("broken")
        result=DetectionService(Broken()).handle({"scan_id":"test","module":"phishing","timestamp":"2026-10-12T00:00:00Z","payload":{"url":"https://example.com"}})
        self.assertEqual(result.payload.status.value,"UNAVAILABLE"); self.assertEqual(result.payload.label,"unknown")
        self.assertEqual(result.payload.error_code,"INFERENCE_FAILED")
        self.assertIn('forensics',result.payload.metadata)
