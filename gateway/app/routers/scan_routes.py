from typing import Dict, Any
from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from gateway.app.core.proxy_client import forward_request
from gateway.app.middleware.auth_middleware import get_authenticated_user
from gateway.app.config.settings import settings

router = APIRouter(prefix="/api/v1/scans", tags=["Scan Proxy"])

@router.api_route("", methods=["GET", "POST"])
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_scan_requests(
    request: Request,
    path: str = "",
    user: Dict[str, Any] = Depends(get_authenticated_user)
) -> Response:
    target_path = f"scans/{path}" if path else "scans"
    # Forward verified user ID in custom header
    extra_headers = {
        "x-user-id": user.get("sub", ""),
        "x-user-role": user.get("role", "user")
    }
    return await forward_request(
        target_base_url=settings.SCAN_SERVICE_URL,
        target_path=target_path,
        request=request,
        extra_headers=extra_headers
    )
