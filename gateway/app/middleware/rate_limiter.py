import time
from collections import defaultdict
from fastapi import Request, HTTPException, status
from gateway.app.config.settings import settings

class InMemoryRateLimiter:
    def __init__(self, max_requests_per_minute: int = 120):
        self.max_requests = max_requests_per_minute
        self.requests = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        window_start = now - 60.0
        
        # Clean expired timestamps
        self.requests[client_id] = [t for t in self.requests[client_id] if t > window_start]
        
        if len(self.requests[client_id]) >= self.max_requests:
            return False
            
        self.requests[client_id].append(now)
        return True

limiter = InMemoryRateLimiter(max_requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)

async def rate_limit_middleware(request: Request, call_next):
    # Don't rate limit health checks
    if request.url.path == "/health":
        return await call_next(request)
        
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please slow down."}
        )
        
    return await call_next(request)
