import io
import os
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel
from PIL import Image as PILImage

from shared.schemas.api_response import APIResponse, ResponseMeta
from shared.schemas.detection_result import DetectionResult
from shared.utils.ids import generate_request_id
from services.image_deepfake.app.worker import worker

from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="", tags=["Inference"])

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
    image_bytes = await file.read()
    
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_FILE", "message": "Uploaded file is empty"}
        )
    if len(image_bytes) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": "File exceeds maximum allowed size of 15MB"}
        )
    try:
        img_check = PILImage.open(io.BytesIO(image_bytes))
        img_check.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_IMAGE_BYTES", "message": "File header/magic bytes do not match a valid image"}
        )

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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
    request_id = generate_request_id()
    scan_id = req.scan_id or str(uuid.uuid4())
    
    image_bytes, error_err = worker.resolve_image_bytes(req.storage_key)
    if error_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FILE_NOT_FOUND", "message": error_err}
        )
        
    result = await run_in_threadpool(
        worker.detector.predict,
        image_bytes,
        scan_id=scan_id,
        enable_explanation=req.enable_explanation
    )
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )
