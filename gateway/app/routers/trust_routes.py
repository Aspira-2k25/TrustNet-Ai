from fastapi import APIRouter, Request
from fastapi.responses import Response
from gateway.app.core.proxy_client import forward_request
from gateway.app.config.settings import settings

router = APIRouter(prefix="/api/v1/trust", tags=["Trust Engine Proxy"])

@router.api_route("", methods=["GET", "POST"])
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_trust_requests(request: Request, path: str = "") -> Response:
    target_path = path if path else ""
    return await forward_request(
        target_base_url=settings.TRUST_ENGINE_SERVICE_URL,
        target_path=target_path,
        request=request
    )
