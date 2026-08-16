from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from shared.schemas.api_response import APIResponse, ResponseMeta, ErrorDetail
from shared.utils.ids import generate_request_id
from shared.logging.logger_setup import get_logger
from gateway.app.config.settings import settings
from gateway.app.middleware.rate_limiter import rate_limit_middleware
from gateway.app.routers.auth_routes import router as auth_proxy_router
from gateway.app.routers.scan_routes import router as scan_proxy_router

logger = get_logger(settings.SERVICE_NAME)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing TrustNet API Gateway...")
    yield
    logger.info("TrustNet API Gateway shutdown complete.")

app = FastAPI(
    title="TrustNet API Gateway",
    description="Unified API Gateway and reverse proxy for TrustNet AI Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration for React/Vite Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Apply Rate Limiting Middleware
app.middleware("http")(rate_limit_middleware)

# Register Proxy Routers
app.include_router(auth_proxy_router)
app.include_router(scan_proxy_router)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", generate_request_id())
    
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "ERROR")
        message = exc.detail.get("message", "An error occurred")
        details = exc.detail.get("details", None)
    else:
        code = "HTTP_ERROR"
        message = str(exc.detail)
        details = None
        
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            data=None,
            error=ErrorDetail(code=code, message=message, details=details),
            meta=ResponseMeta(request_id=request_id)
        ).model_dump(mode="json")
    )

@app.get("/health", response_model=APIResponse[dict])
async def health_check():
    request_id = generate_request_id()
    logger.info("Health check endpoint called", extra={"request_id": request_id, "scan_id": ""})
    return APIResponse(
        data={"status": "ok", "service": "gateway_service"},
        meta=ResponseMeta(request_id=request_id)
    )
