import uuid
from datetime import datetime, timezone
import pytest
import httpx

from services.trust_engine.app.main import app
from services.trust_engine.app.services.fusion_engine import FusionEngine
from services.trust_engine.app.schemas.trust_schemas import RiskLevelEnum
from shared.schemas.detection_result import DetectionResult
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

def make_mock_result(module: ModuleEnum, risk_score: float, confidence: float = 0.85, scan_id: str = None) -> DetectionResult:
    valid_scan_id = scan_id or str(uuid.uuid4())
    return DetectionResult(
        scan_id=valid_scan_id,
        module=module,
        detector_id=f"{module.value}.mock.v1",
        model_version="v1",
        preprocessing_version="v1",
        native_score=risk_score / 100.0,
        native_score_semantics=NativeScoreSemanticsEnum.probability_of_positive_class,
        risk_score=risk_score,
        confidence=confidence,
        label="test",
        status=StatusEnum.SUCCESS,
        evidence=[],
        processing_time_ms=50,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

def test_single_detector_fusion():
    engine = FusionEngine()
    res = make_mock_result(ModuleEnum.image_deepfake, risk_score=80.0, confidence=0.90)
    
    fused = engine.fuse([res])
    assert fused.trust_risk_score == 80.0
    assert fused.confidence == 0.90
    assert fused.risk_level == RiskLevelEnum.CRITICAL
    assert fused.contradiction_flag is False

def test_multi_detector_consistent_fusion():
    engine = FusionEngine()
    scan_id = str(uuid.uuid4())
    r1 = make_mock_result(ModuleEnum.image_deepfake, risk_score=70.0, confidence=0.80, scan_id=scan_id)
    r2 = make_mock_result(ModuleEnum.phishing, risk_score=80.0, confidence=0.90, scan_id=scan_id)
    
    fused = engine.fuse([r1, r2])
    # Average of 70 and 80 is 75.0 (CRITICAL)
    assert 74.0 <= fused.trust_risk_score <= 76.0
    assert fused.risk_level == RiskLevelEnum.CRITICAL
    assert fused.contradiction_flag is False

def test_contradiction_detection_applies_penalty():
    engine = FusionEngine()
    scan_id = str(uuid.uuid4())
    # Image detector says fake (risk=90), but text detector says authentic (risk=10) -> delta=80 >= 40
    r1 = make_mock_result(ModuleEnum.image_deepfake, risk_score=90.0, confidence=0.80, scan_id=scan_id)
    r2 = make_mock_result(ModuleEnum.scam_message, risk_score=10.0, confidence=0.80, scan_id=scan_id)
    
    fused = engine.fuse([r1, r2])
    assert fused.contradiction_flag is True
    assert fused.contradiction_details is not None
    # 0.80 * 0.75 penalty = 0.60
    assert fused.confidence == 0.60
    # Average is 50.0 (HIGH)
    assert fused.risk_level == RiskLevelEnum.HIGH

def test_empty_results_fallback():
    engine = FusionEngine()
    fused = engine.fuse([])
    assert fused.trust_risk_score == 0.0
    assert fused.confidence == 0.0
    assert fused.risk_level == RiskLevelEnum.LOW

@pytest.mark.anyio
async def test_fuse_http_endpoint(client):
    scan_id = str(uuid.uuid4())
    r1 = make_mock_result(ModuleEnum.image_deepfake, risk_score=60.0, scan_id=scan_id)
    payload = {
        "scan_id": scan_id,
        "results": [r1.model_dump()]
    }
    response = await client.post("/fuse", json=payload)
    assert response.status_code == 200
    
    body = response.json()
    assert body["error"] is None
    assert body["data"]["scan_id"] == scan_id
    assert body["data"]["trust_risk_score"] == 60.0
    assert body["data"]["risk_level"] == "HIGH"

@pytest.mark.anyio
async def test_get_fused_score_endpoint(client):
    scan_id = str(uuid.uuid4())
    r1 = make_mock_result(ModuleEnum.phishing, risk_score=30.0, scan_id=scan_id)
    await client.post("/fuse", json={"scan_id": scan_id, "results": [r1.model_dump()]})
    
    response = await client.get(f"/scores/{scan_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["scan_id"] == scan_id
    assert body["data"]["risk_level"] == "MEDIUM"
