import io
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Header, UploadFile, File, Form, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image as PILImage
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger("trustnet.scan")

from services.scan_management.app.database.session import get_db
from services.scan_management.app.services.scan_service import ScanService
from services.scan_management.app.schemas.scan_schemas import (
    ScanCreateTextRequest,
    ScanCreateURLRequest,
    ScanResponse,
    ScanListResponse
)
from shared.constants.modules import ModuleEnum
from shared.constants.status import StatusEnum
from shared.schemas.api_response import APIResponse, ResponseMeta
from shared.utils.ids import generate_request_id
from shared.auth.verify_token import verify_token, TokenVerificationError
from services.scan_management.app.config.settings import settings

router = APIRouter(prefix="/scans", tags=["Scans"])
detector_instance = None

def image_detector():
    global detector_instance
    if detector_instance is None:
        try:
            from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
        except ImportError:
            raise HTTPException(503, 'Image inference dependencies are unavailable in this scam-only runtime')
        detector_instance = EfficientNetDetector()
    return detector_instance

def get_current_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> str:
    """Derive ownership from the signed token, never caller-supplied identity headers."""
    if authorization:
        try:
            payload = verify_token(
                authorization,
                secret_key=settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM,
                expected_type="access"
            )
            return payload["sub"]
        except TokenVerificationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": e.error_code, "message": e.message}
            )

    env = os.getenv("ENVIRONMENT", "dev").strip().lower()
    allow_mock = os.getenv("ALLOW_MOCK_AUTH", "false").strip().lower() in ("true", "1", "yes")
    if env in ("dev", "test") and allow_mock:
        return "usr-researcher-1"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "TOKEN_MISSING", "message": "Authentication required"}
    )

@router.get("/limits")
async def scan_limits(user_id: str = Depends(get_current_user_id)):
    return APIResponse(data={"image_mb": settings.MAX_IMAGE_SIZE_MB, "audio_mb": settings.MAX_AUDIO_SIZE_MB, "video_mb": settings.MAX_VIDEO_SIZE_MB, "message_characters": 10000}, meta=ResponseMeta(request_id=generate_request_id()))

@router.post("/analyze", response_model=APIResponse[Dict[str, Any]])
async def analyze_image_direct(
    file: UploadFile = File(...),
    enable_explanation: bool = Form(False),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Direct synchronous deepfake forensic analysis endpoint.
    Executes actual EfficientNet-B0 convolutional inference, 2D Fourier (FFT) spectrum analysis,
    Error Level Analysis (ELA), and sensor noise evaluation on the uploaded image.
    """
    request_id = generate_request_id()
    scan_id = f"scan-{uuid.uuid4().hex[:10]}"
    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_FILE", "message": "Uploaded file is empty"}
        )
    max_size = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": f"File exceeds maximum allowed size of {settings.MAX_IMAGE_SIZE_MB}MB"}
        )
    try:
        img_check = PILImage.open(io.BytesIO(file_bytes))
        img_check.verify()
    except Exception as e:
        logger.error(f"[SCAN ROUTER] Image verification failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_IMAGE_BYTES", "message": "File header/magic bytes do not match a valid image"}
        )

    safe_filename = os.path.basename(file.filename or "uploaded_media.jpg")

    # Run real forensic model detector
    detection_res = await run_in_threadpool(
        image_detector().predict,
        file_bytes,
        scan_id=scan_id,
        filename=safe_filename,
        enable_explanation=enable_explanation
    )

    if getattr(detection_res.status, "value", str(detection_res.status)) not in ("SUCCESS", "PARTIAL_SUCCESS"):
        logger.error(f"[SCAN ROUTER] Forensic detection failed for scan {scan_id}: {detection_res.error_code} - {detection_res.error_message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": detection_res.error_code or "INFERENCE_FAILED",
                "message": detection_res.error_message or "Deepfake detection failed during analysis."
            }
        )
    
    risk_score = detection_res.risk_score
    risk_level = "CRITICAL" if risk_score >= 75 else ("HIGH" if risk_score >= 50 else ("MEDIUM" if risk_score >= 25 else "LOW"))

    is_contradiction = bool(detection_res.metadata.get("is_contradiction", False)) if detection_res.metadata else False

    vision_data = getattr(detection_res, "vision_analysis", None) or (detection_res.metadata.get("vision_analysis") if detection_res.metadata else None)

    # Extract true image dimensions if decodable
    width, height = 1024, 1024
    try:
        with PILImage.open(io.BytesIO(file_bytes)) as img:
            width, height = img.size
    except Exception:
        pass

    trust_score_data = {
        "scan_id": scan_id,
        "trust_risk_score": risk_score,
        "risk_level": risk_level,
        "reporting_modules": ["image_deepfake"],
        "module_scores": {"image_deepfake": risk_score},
        "confidence": detection_res.confidence,
        "contradiction_detected": is_contradiction,
        "contradiction_flag": is_contradiction,
        "contradiction_details": "Conflicting evidence detected between model and forensic engines." if is_contradiction else None,
        "evidence": [item.model_dump() for item in detection_res.evidence],
        "explanation": detection_res.explanation,
        "vision_analysis": vision_data,
        "metadata": {"vision_analysis": vision_data} if vision_data else {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    scan_record = {
        "id": scan_id,
        "user_id": user_id,
        "status": "SUCCESS",
        "content_type": "image",
        "filename": file.filename or "uploaded_media.jpg",
        "file_size_bytes": len(file_bytes),
        "mime_type": file.content_type or "image/jpeg",
        "dimensions": {"width": width, "height": height},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": detection_res.model_dump(),
        "vision_analysis": vision_data,
        "trust_score": trust_score_data
    }

    from services.scan_management.app.db_models.scan import Scan, ScanAssessment
    db.add(Scan(id=scan_id, user_id=user_id, status="SUCCESS", content_type="image",
                filename=safe_filename, file_size_bytes=len(file_bytes), mime_type=file.content_type))
    db.add(ScanAssessment(scan_id=scan_id, assessment={"result": detection_res.model_dump(mode="json"), "trust_score": trust_score_data, "dimensions": {"width": width, "height": height}}))
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.error("Image persistence failed scan=%s", scan_id)
        raise HTTPException(503, "Analysis completed but could not be saved; retry later")

    return APIResponse(
        data=scan_record,
        meta=ResponseMeta(request_id=request_id)
    )

@router.post("/scam/analyze", response_model=APIResponse[Dict[str, Any]])
async def analyze_scam(req: ScanCreateTextRequest, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    import httpx
    from shared.schemas.detection_result import DetectionResult
    from services.scan_management.app.db_models.scan import Scan, ScanAssessment
    from services.trust_engine.app.services.fusion_engine import fusion_engine
    scan_id = str(uuid.uuid4())
    try:
        async with httpx.AsyncClient(timeout=settings.SCAM_SERVICE_TIMEOUT_SECONDS) as client:
            response = await client.post(settings.SCAM_SERVICE_URL.rstrip("/") + "/infer", json={**req.model_dump(mode='json'), "scan_id": scan_id})
        if response.status_code != 200:
            raise HTTPException(response.status_code, response.json().get("detail", "Scam service unavailable"))
        result = DetectionResult.model_validate(response.json()["data"])
        if result.scan_id != scan_id or result.module != ModuleEnum.scam_message:
            raise ValueError("Mismatched scam service response")
        if result.status not in (StatusEnum.SUCCESS, StatusEnum.PARTIAL_SUCCESS):
            raise HTTPException(503, "Scam assessment failed or unavailable")
    except httpx.TimeoutException:
        raise HTTPException(504, "Scam service timeout")
    except httpx.RequestError:
        raise HTTPException(503, "Scam service unavailable")
    except (ValueError, KeyError):
        raise HTTPException(502, "Invalid scam service response")
    trust = fusion_engine.fuse([result], scan_id).model_dump(mode="json")
    trust["module_scores"] = {"scam_message": result.risk_score}
    trust["contradiction_detected"] = trust["contradiction_flag"]
    assessment = {"raw_input": req.canonical_text(), "result": result.model_dump(mode="json"), "trust_score": trust}
    scan = Scan(id=scan_id, user_id=user_id, status="SUCCESS", content_type="text", raw_input=req.text[:4096], filename="message.txt", mime_type="text/plain", file_size_bytes=len(req.text.encode("utf-8")))
    db.add(scan); db.add(ScanAssessment(scan_id=scan_id, assessment=assessment))
    try:
        await db.commit(); await db.refresh(scan)
    except Exception:
        await db.rollback()
        logger.error("Scam persistence failed scan=%s", scan_id)
        raise HTTPException(503, "Assessment could not be saved; retry later")
    scan.saved_assessment = assessment
    return APIResponse(data=ScanService(db)._to_response(scan).model_dump(), meta=ResponseMeta(request_id=generate_request_id()))

@router.post("/upload", response_model=APIResponse[ScanResponse], status_code=status.HTTP_202_ACCEPTED)
async def create_file_scan(
    file: UploadFile = File(...),
    modality: str = Form(..., description="Modality of upload: 'image', 'audio', or 'video'"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    request_id = generate_request_id()
    file_bytes = await file.read()
    
    service = ScanService(db)
    result = await service.create_file_scan(
        user_id=user_id,
        file_bytes=file_bytes,
        original_filename=file.filename or f"upload.{modality}",
        declared_content_type=file.content_type or "application/octet-stream",
        modality=modality
    )
    
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )

@router.post("/text", response_model=APIResponse[ScanResponse], status_code=status.HTTP_202_ACCEPTED)
async def create_text_scan(
    req: ScanCreateTextRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    request_id = generate_request_id()
    service = ScanService(db)
    result = await service.create_text_scan(user_id=user_id, text=req.text, message_context=req.model_dump(mode='json',exclude={'text'}))
    
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )

@router.post("/url", response_model=APIResponse[ScanResponse], status_code=status.HTTP_202_ACCEPTED)
async def create_url_scan(
    req: ScanCreateURLRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    request_id = generate_request_id()
    if not settings.KAFKA_ENABLED:
        # Same local phishing runtime also powers embedded-message link checks.
        import httpx
        from shared.schemas.detection_result import DetectionResult
        from services.scan_management.app.db_models.scan import Scan, ScanAssessment
        from services.trust_engine.app.services.fusion_engine import fusion_engine
        scan_id = str(uuid.uuid4())
        try:
            async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
                response = await client.post(settings.PHISHING_SERVICE_URL.rstrip('/') + '/infer', json={'scan_id':scan_id, 'url':req.url})
                response.raise_for_status()
                detection = DetectionResult.model_validate(response.json()['data'])
            if detection.scan_id != scan_id or detection.module.value != 'phishing':
                raise ValueError('Mismatched phishing result')
        except (httpx.HTTPError, ValueError, KeyError):
            raise HTTPException(503, 'Phishing service unavailable or returned an invalid result')
        trust = fusion_engine.fuse([detection], scan_id).model_dump(mode='json')
        trust['module_scores'] = {'phishing':detection.risk_score if detection.status in (StatusEnum.SUCCESS, StatusEnum.PARTIAL_SUCCESS) else None}
        trust['contradiction_detected'] = trust['contradiction_flag']
        assessment = {'result':detection.model_dump(mode='json'), 'trust_score':trust}
        scan = Scan(id=scan_id, user_id=user_id, status=detection.status.value, content_type='url', raw_input=req.url,
                    filename='url.txt', mime_type='text/plain', file_size_bytes=len(req.url.encode()))
        db.add(scan); db.add(ScanAssessment(scan_id=scan_id, assessment=assessment))
        try:
            await db.commit(); await db.refresh(scan)
        except Exception:
            await db.rollback()
            raise HTTPException(503, 'URL assessment could not be saved')
        scan.saved_assessment = assessment
        return APIResponse(data=ScanService(db)._to_response(scan), meta=ResponseMeta(request_id=request_id))
    service = ScanService(db)
    result = await service.create_url_scan(user_id=user_id, url=req.url)
    
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )

@router.get("/{scan_id}/status", response_model=APIResponse[dict])
async def get_scan_status(
    scan_id: str,
    user_id: str = Depends(get_current_user_id),
    x_user_role: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    request_id = generate_request_id()
    service = ScanService(db)
    filter_user = user_id
    scan = await service.get_scan(scan_id=scan_id, user_id=filter_user)
    
    return APIResponse(
        data={"scan_id": scan.id, "status": scan.status, "content_type": scan.content_type},
        meta=ResponseMeta(request_id=request_id)
    )

@router.get("/{scan_id}", response_model=APIResponse[ScanResponse])
async def get_scan_by_id(
    scan_id: str,
    user_id: str = Depends(get_current_user_id),
    x_user_role: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    request_id = generate_request_id()
    service = ScanService(db)
    filter_user = user_id
    result = await service.get_scan(scan_id=scan_id, user_id=filter_user)
    
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )

@router.get("", response_model=APIResponse[ScanListResponse])
async def list_scans(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    x_user_role: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    request_id = generate_request_id()
    service = ScanService(db)
    filter_user = user_id
    result = await service.list_scans(user_id=filter_user, page=page, limit=limit)
    
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )
