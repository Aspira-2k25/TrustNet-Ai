from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from shared.schemas.api_response import APIResponse, ResponseMeta
from shared.schemas.detection_result import DetectionResult
from shared.utils.ids import generate_request_id
from services.trust_engine.app.services.fusion_engine import fusion_engine
from services.trust_engine.app.repositories.score_repository import score_repo
from services.trust_engine.app.schemas.trust_schemas import TrustScoreResult

router = APIRouter(prefix="", tags=["Trust Engine"])

class FuseRequest(BaseModel):
    scan_id: Optional[str] = None
    results: List[DetectionResult]

@router.post("/fuse", response_model=APIResponse[TrustScoreResult])
async def fuse_detection_results(req: FuseRequest):
    request_id = generate_request_id()
    if not req.results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_RESULTS", "message": "At least one DetectionResult is required for fusion"}
        )

    fused = fusion_engine.fuse(req.results, scan_id=req.scan_id)
    score_repo.save(fused)

    return APIResponse(
        data=fused,
        meta=ResponseMeta(request_id=request_id)
    )

@router.get("/scores/{scan_id}", response_model=APIResponse[TrustScoreResult])
async def get_fused_score(scan_id: str):
    request_id = generate_request_id()
    result = score_repo.get(scan_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SCORE_NOT_FOUND", "message": f"No fused trust score found for scan_id: '{scan_id}'"}
        )

    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )
