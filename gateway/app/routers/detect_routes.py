from fastapi import APIRouter, Request
from fastapi.responses import Response
from gateway.app.core.proxy_client import forward_request
from gateway.app.config.settings import settings

router = APIRouter(prefix="/api/v1/detect", tags=["Deepfake Detection Proxy"])

@router.api_route("", methods=["GET", "POST"])
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_detect_requests(request: Request, path: str = "") -> Response:
    target_path = f"detect/{path}" if path else "detect"
    return await forward_request(
        target_base_url=settings.IMAGE_DEEPFAKE_SERVICE_URL,
        target_path=target_path,
        request=request
    )
