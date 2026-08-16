from typing import Optional, Dict
import httpx
from fastapi import Request, HTTPException, status
from fastapi.responses import Response

async def forward_request(
    target_base_url: str,
    target_path: str,
    request: Request,
    extra_headers: Optional[Dict[str, str]] = None
) -> Response:
    """
    Forwards an incoming HTTP request to a downstream microservice.
    """
    url = f"{target_base_url.rstrip('/')}/{target_path.lstrip('/')}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    # Filter out hop-by-hop headers
    excluded_headers = {"host", "content-length", "connection"}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded_headers}
    if extra_headers:
        headers.update(extra_headers)

    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            downstream_res = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body
            )
            
            # Forward response
            return Response(
                content=downstream_res.content,
                status_code=downstream_res.status_code,
                headers=dict(downstream_res.headers),
                media_type=downstream_res.headers.get("content-type")
            )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE", "message": f"Downstream service at {target_base_url} is currently unavailable"}
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "GATEWAY_TIMEOUT", "message": f"Downstream service at {target_base_url} timed out"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "BAD_GATEWAY", "message": f"Proxy request failed: {str(e)}"}
        )
