import io
import os
import uuid
from typing import Optional
from services.image_deepfake.app.config.settings import settings
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends, Header
from pydantic import BaseModel
from PIL import Image as PILImage

from shared.schemas.api_response import APIResponse, ResponseMeta
from shared.schemas.detection_result import DetectionResult
from shared.utils.ids import generate_request_id
from services.image_deepfake.app.worker import worker

from starlette.concurrency import run_in_threadpool

def authenticate(authorization: Optional[str] = Header(None)):
    from shared.auth.verify_token import verify_token, TokenVerificationError
    if not authorization:
        raise HTTPException(401, 'Authentication required')
    try:
        return verify_token(authorization, secret_key=settings.JWT_SECRET_KEY,
                            algorithm=settings.JWT_ALGORITHM, expected_type='access')['sub']
    except TokenVerificationError:
        raise HTTPException(401, 'Invalid access token')

router = APIRouter(prefix="", tags=["Inference"], dependencies=[Depends(authenticate)])

class DirectDetectKeyRequest(BaseModel):
    storage_key: str
    scan_id: Optional[str] = None
    enable_explanation: bool = False

@router.post("/detect/file", response_model=APIResponse[DetectionResult])
async def detect_image_file(
    file: UploadFile = File(...),
    scan_id: Optional[str] = Form(None),
    enable_explanation: bool = Form(False)
):
    request_id = generate_request_id()
    image_bytes = await file.read(settings.MAX_IMAGE_SIZE_MB * 1024 * 1024 + 1)
    
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_FILE", "message": "Uploaded file is empty"}
        )
    if len(image_bytes) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": f"File exceeds maximum allowed size of {settings.MAX_IMAGE_SIZE_MB}MB"}
        )
    from models.image_deepfake.preprocessing.validator import ImageValidator
    valid, validation_error = ImageValidator().validate(image_bytes)
    if not valid:
        raise HTTPException(413 if 'exceeds' in str(validation_error).lower() else 400,
            detail={'code':'INVALID_IMAGE_BYTES','message':validation_error})

    safe_filename = os.path.basename(file.filename or "uploaded_media.jpg")

    result = await run_in_threadpool(
        worker.detector.predict,
        image_bytes,
        scan_id=scan_id or str(uuid.uuid4()),
        filename=safe_filename,
        enable_explanation=enable_explanation
    )
    if getattr(result, "status", None) and str(result.status).upper().endswith("FAILED"):
        raise HTTPException(
            status_code=503 if result.error_code == 'INFERENCE_BUSY' else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": result.error_code or "INFERENCE_FAILED",
                "message": result.error_message or "Deepfake detection failed during analysis."
            }
        )
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )

@router.post("/detect/key", response_model=APIResponse[DetectionResult])
async def detect_image_key(
    req: DirectDetectKeyRequest
):
    # Public callers cannot establish ownership of an internal worker storage key.
    raise HTTPException(403, 'Storage-key inference is internal only; upload an image through the authenticated scan route.')
