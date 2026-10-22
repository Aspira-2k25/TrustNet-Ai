import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import os
import uuid
from typing import Optional
from services.image_deepfake.app.config.settings import settings
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel
from PIL import Image as PILImage

from shared.schemas.api_response import APIResponse, ResponseMeta
from shared.schemas.detection_result import DetectionResult
from shared.utils.ids import generate_request_id
from services.image_deepfake.app.worker import worker

from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="", tags=["Inference"])
pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='image-inference')
active=0

async def run_image(data,scan_id,filename=None,enable_explanation=False):
    global active
    if worker.detector is None:raise HTTPException(503,'Image model is not installed or failed integrity validation')
    if active:raise HTTPException(429,'Image analysis busy; retry later')
    active+=1
    loop=asyncio.get_running_loop()
    future=loop.run_in_executor(pool,lambda:worker.detector.predict(data,scan_id=scan_id,filename=filename,enable_explanation=enable_explanation))
    def finished(_):
        global active
        active-=1
    future.add_done_callback(finished)
    try:return await asyncio.wait_for(asyncio.shield(future),29)
    except asyncio.TimeoutError:raise HTTPException(504,'Image analysis timed out; computation remains bounded to one active request')
    except (ValueError,OSError) as exc:raise HTTPException(400,{'code':'INVALID_IMAGE_BYTES','message':str(exc)})
    except Exception:raise HTTPException(503,'Image inference failed; check service logs')

@router.get('/ready')
async def ready():
    if worker.detector is None:raise HTTPException(503,'Image classifier unavailable; run image setup')
    return {'status':'ready','classifier':worker.detector.global_model.spec['id'],
        'model_selection':worker.detector.model_name,
        'localizer_ready':worker.detector.localizer is not None and getattr(worker.detector.localizer,'ready',True),
        'calibration_version':worker.detector.config['version'],
        'authenticity_enabled':worker.detector.config['authenticity_enabled']}


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
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": f"File exceeds maximum allowed size of {settings.MAX_IMAGE_SIZE_MB}MB"}
        )
    from models.image_deepfake.forensics.source_evidence import inspect_source
    try:inspect_source(image_bytes)
    except (ValueError,OSError) as exc:raise HTTPException(400,{'code':'INVALID_IMAGE_BYTES','message':str(exc)})

    safe_filename = os.path.basename(file.filename or "uploaded_media.jpg")

    result = await run_image(image_bytes,scan_id or str(uuid.uuid4()),safe_filename,enable_explanation)
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
        
    result = await run_image(image_bytes,scan_id,enable_explanation=req.enable_explanation)
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )
