import io
import uuid
from datetime import datetime, timezone
import pytest
import httpx
from PIL import Image

# Import microservice apps
from services.auth.app.main import app as auth_app
from services.auth.app.database.session import init_db as init_auth_db
from services.scan_management.app.main import app as scan_app
from services.scan_management.app.database.session import init_db as init_scan_db
from services.image_deepfake.app.main import app as image_app
from services.trust_engine.app.main import app as trust_app

# Import ML detector and fusion engine
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from services.trust_engine.app.services.fusion_engine import fusion_engine
from shared.schemas.detection_result import DetectionResult
from shared.schemas.evidence import EvidenceItem
from shared.constants.modules import ModuleEnum
from shared.constants.status import StatusEnum
from shared.constants.native_score_semantics import NativeScoreSemanticsEnum

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
async def setup_databases():
    await init_auth_db()
    await init_scan_db()

def create_valid_test_jpeg() -> bytes:
    img = Image.new("RGB", (224, 224), color=(140, 80, 210))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

@pytest.mark.anyio
async def test_full_end_to_end_multimodal_pipeline():
    """
    E2E Test Scenario 1: Happy Path Multimodal Pipeline
    1. Register user and obtain JWT access token.
    2. Upload image scan request to Scan Management Service.
    3. Execute Image Deepfake inference with Grad-CAM explainability.
    4. Perform calibrated weighted fusion in Trust Score Engine.
    5. Verify cross-cutting traceability (scan_id, evidence items, risk level).
    """
    # Step 1: User Registration & Authentication
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=auth_app), base_url="http://auth") as auth_client:
        email = f"analyst_{uuid.uuid4().hex[:8]}@trustnet.ai"
        reg_res = await auth_client.post(
            "/auth/register",
            json={"email": email, "password": "SecurePassword123!", "role": "researcher"}
        )
        assert reg_res.status_code == 201
        auth_data = reg_res.json()["data"]
        access_token = auth_data["access_token"]
        user_id = auth_data["user_id"]

    # Step 2: Upload Scan Request
    headers = {"Authorization": f"Bearer {access_token}"}
    image_bytes = create_valid_test_jpeg()
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=scan_app), base_url="http://scans") as scan_client:
        upload_res = await scan_client.post(
            "/scans/upload",
            headers=headers,
            files={"file": ("suspect_face.jpg", image_bytes, "image/jpeg")},
            data={"modality": "image"}
        )
        assert upload_res.status_code == 202
        scan_data = upload_res.json()["data"]
        scan_id = scan_data["id"]
        storage_key = scan_data["media_storage_key"]
        assert scan_data["user_id"] == user_id

    # Step 3: Image Deepfake Worker Inference (with Grad-CAM)
    image_detector = EfficientNetDetector(enable_explainability=True)
    image_result = image_detector.predict(image_bytes, scan_id=scan_id)
    
    assert image_result.scan_id == scan_id
    assert image_result.status == StatusEnum.SUCCESS
    assert 0.0 <= image_result.risk_score <= 100.0
    assert image_result.native_score_semantics == NativeScoreSemanticsEnum.probability_of_negative_class
    assert len(image_result.evidence) >= 1
    assert "visual_saliency" in image_result.evidence[0].feature_or_region

    # Step 4: Multi-Module Synthesis in Trust Score Engine
    # (Synthesize image result with accompanying text/context result)
    context_result = DetectionResult(
        scan_id=scan_id,
        module=ModuleEnum.scam_message,
        detector_id="scam_message.baseline.v1",
        model_version="v1",
        preprocessing_version="v1",
        native_score=0.80,
        native_score_semantics=NativeScoreSemanticsEnum.probability_of_positive_class,
        risk_score=80.0,
        confidence=0.85,
        label="scam",
        status=StatusEnum.SUCCESS,
        evidence=[EvidenceItem(
            feature_or_region="suspicious_intent",
            contribution=0.80,
            human_readable_note="Urgent credential harvesting tone detected."
        )],
        processing_time_ms=25,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    # Step 5: Trust Score Engine Multimodal Synthesis & Fusion
    fused_score = fusion_engine.fuse([image_result, context_result], scan_id=scan_id)
    
    assert fused_score.scan_id == scan_id
    assert 0.0 <= fused_score.trust_risk_score <= 100.0
    assert fused_score.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert len(fused_score.reporting_modules) == 2
    assert "image_deepfake" in fused_score.reporting_modules
    assert "scam_message" in fused_score.reporting_modules
    assert len(fused_score.evidence) >= 2
    assert "Trust Score:" in fused_score.explanation

    # Step 6: Verify Trust Engine HTTP Endpoint & Score Retrieval
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=trust_app), base_url="http://trust") as trust_client:
        fuse_http_res = await trust_client.post(
            "/fuse",
            json={"scan_id": scan_id, "results": [image_result.model_dump(), context_result.model_dump()]}
        )
        assert fuse_http_res.status_code == 200
        
        get_score_res = await trust_client.get(f"/scores/{scan_id}")
        assert get_score_res.status_code == 200
        assert get_score_res.json()["data"]["scan_id"] == scan_id

@pytest.mark.anyio
async def test_pipeline_graceful_degradation():
    """
    E2E Test Scenario 2: Graceful Degradation
    When one detector fails, the pipeline still synthesizes the remaining
    detector results without crashing or losing explainability.
    """
    scan_id = str(uuid.uuid4())
    image_detector = EfficientNetDetector(enable_explainability=False)
    
    # Passing corrupted bytes produces a FAILED DetectionResult
    failed_image_result = image_detector.predict(b"corrupted_invalid_data", scan_id=scan_id)
    assert failed_image_result.status == StatusEnum.FAILED
    
    # Valid complementary result
    valid_result = DetectionResult(
        scan_id=scan_id,
        module=ModuleEnum.fake_review,
        detector_id="fake_review.baseline.v1",
        model_version="v1",
        preprocessing_version="v1",
        native_score=0.35,
        native_score_semantics=NativeScoreSemanticsEnum.probability_of_positive_class,
        risk_score=35.0,
        confidence=0.80,
        label="legitimate",
        status=StatusEnum.SUCCESS,
        evidence=[],
        processing_time_ms=30,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    # Fusion engine gracefully filters failed detector and fuses remaining valid results
    fused_score = fusion_engine.fuse([failed_image_result, valid_result], scan_id=scan_id)
    assert fused_score.scan_id == scan_id
    assert fused_score.trust_risk_score == valid_result.risk_score
    assert len(fused_score.reporting_modules) == 1
    assert "fake_review" in fused_score.reporting_modules

@pytest.mark.anyio
async def test_pipeline_security_input_rejection():
    """
    E2E Test Scenario 3: Upload Gateway Security Filtering
    Uploads with unauthorized extensions or payload tampering are blocked at the perimeter.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=scan_app), base_url="http://scans") as scan_client:
        # Rejection of executable payload
        res = await scan_client.post(
            "/scans/upload",
            files={"file": ("exploit.exe", b"MZ\x90\x00\x03\x00", "application/x-dosexec")},
            data={"modality": "image"}
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "INVALID_EXTENSION"
