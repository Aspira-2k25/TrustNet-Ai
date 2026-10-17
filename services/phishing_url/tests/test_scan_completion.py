import unittest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from services.scan_management.app.database.session import Base
from services.scan_management.app.db_models.scan import Scan, ScanAssessment
from services.scan_management.app.completion_consumer import persist_completion
from services.scan_management.app.services.scan_service import ScanService
from services.phishing_url.app.detection_service import DetectionService
from models.phishing_url.inference.phishing_detector import PhishingDetector
from fastapi import HTTPException

class CompletionTests(unittest.IsolatedAsyncioTestCase):
    async def test_phishing_completion_persistence_and_owner(self):
        engine=create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
        factory=async_sessionmaker(engine,expire_on_commit=False)
        async with factory() as session:
            session.add(Scan(id="phish-test",user_id="owner",content_type="url",raw_input="https://example.com",status="QUEUED"));await session.commit()
            event=DetectionService(PhishingDetector()).handle({"scan_id":"phish-test","module":"phishing","timestamp":"2026-10-12T00:00:00Z","payload":{"url":"https://example.com"}})
            self.assertTrue(await persist_completion(event,session));self.assertFalse(await persist_completion(event,session))
            saved=await session.get(ScanAssessment,"phish-test")
            self.assertEqual(saved.assessment["result"]["scan_id"],"phish-test")
            self.assertIsNone(saved.assessment["trust_score"]["trust_risk_score"])
            with self.assertRaises(HTTPException) as denied: await ScanService(session).get_scan("phish-test","other")
            self.assertEqual(denied.exception.status_code,403)
        await engine.dispose()
