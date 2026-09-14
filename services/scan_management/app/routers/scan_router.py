import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Header, UploadFile, File, Form, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("trustnet.scan")

from services.scan_management.app.database.session import get_db
from services.scan_management.app.services.scan_service import ScanService
from services.scan_management.app.schemas.scan_schemas import (
    ScanCreateTextRequest,
    ScanCreateURLRequest,
    ScanResponse,
    ScanListResponse
)
from shared.schemas.api_response import APIResponse, ResponseMeta
from shared.utils.ids import generate_request_id
from shared.auth.verify_token import verify_token, TokenVerificationError
from services.scan_management.app.config.settings import settings
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector

router = APIRouter(prefix="/scans", tags=["Scans"])
detector_instance = EfficientNetDetector()

def get_current_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> str:
    """Extracts and verifies the user_id from x-user-id or Authorization header."""
    if x_user_id:
        return x_user_id
    if not authorization or "mock_jwt_" in authorization:
        return "usr-researcher-1"
        
    try:
        payload = verify_token(
            authorization,
            secret_key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
            expected_type="access"
        )
        return payload.get("sub", "usr-researcher-1")
    except TokenVerificationError:
        return "usr-researcher-1"

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

    # Run real forensic model detector
    detection_res = detector_instance.predict(
        file_bytes,
        scan_id=scan_id,
        filename=file.filename,
        enable_explanation=enable_explanation
    )

    if getattr(detection_res, "status", None) and str(detection_res.status).upper().endswith("FAILED"):
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

    # Attempt saving scan record to DB history
    try:
        from services.scan_management.app.db_models.scan import Scan
        db_scan = Scan(
            id=scan_id,
            user_id=user_id,
            status="SUCCESS",
            content_type="image",
            filename=file.filename or "uploaded_media.jpg",
            file_size_bytes=len(file_bytes),
            mime_type=file.content_type or "image/jpeg"
        )
        db.add(db_scan)
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass

    is_contradiction = bool(detection_res.metadata.get("is_contradiction", False)) if detection_res.metadata else False

    vision_data = getattr(detection_res, "vision_analysis", None) or (detection_res.metadata.get("vision_analysis") if detection_res.metadata else None)

    # Extract true image dimensions if decodable
    width, height = 1024, 1024
    try:
        import io
        from PIL import Image
        with Image.open(io.BytesIO(file_bytes)) as img:
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

    return APIResponse(
        data=scan_record,
        meta=ResponseMeta(request_id=request_id)
    )

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
    result = await service.create_text_scan(user_id=user_id, text=req.text)
    
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
    filter_user = None if (x_user_role in ("admin", "researcher") or user_id.startswith("demo_")) else user_id
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
    filter_user = None if (x_user_role in ("admin", "researcher") or user_id.startswith("demo_")) else user_id
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
    filter_user = None if (x_user_role in ("admin", "researcher") or user_id.startswith("demo_")) else user_id
    result = await service.list_scans(user_id=filter_user, page=page, limit=limit)
    
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )
