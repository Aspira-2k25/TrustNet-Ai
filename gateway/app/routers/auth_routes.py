from fastapi import APIRouter, Request
from fastapi.responses import Response
from gateway.app.core.proxy_client import forward_request
from gateway.app.config.settings import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Auth Proxy"])

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_auth_requests(path: str, request: Request) -> Response:
    return await forward_request(
        target_base_url=settings.AUTH_SERVICE_URL,
        target_path=f"auth/{path}",
        request=request
    )
