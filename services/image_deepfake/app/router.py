import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel

from shared.schemas.api_response import APIResponse, ResponseMeta
from shared.schemas.detection_result import DetectionResult
from shared.utils.ids import generate_request_id
from services.image_deepfake.app.worker import worker

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
    
    result = worker.detector.predict(
        image_bytes,
        scan_id=scan_id or str(uuid.uuid4()),
        filename=file.filename,
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
        
    result = worker.detector.predict(
        image_bytes,
        scan_id=scan_id,
        enable_explanation=req.enable_explanation
    )
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )
