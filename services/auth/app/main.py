from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from shared.schemas.api_response import APIResponse, ResponseMeta, ErrorDetail
from shared.utils.ids import generate_request_id
from shared.logging.logger_setup import get_logger
from services.auth.app.config.settings import settings
from services.auth.app.database.session import init_db
from services.auth.app.routers.auth_router import router as auth_router

logger = get_logger(settings.SERVICE_NAME)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables for Auth Service...")
    await init_db()
    logger.info("Auth Service initialized successfully.")
    yield
    logger.info("Auth Service shutting down...")

app = FastAPI(
    title="TrustNet Auth Service",
    description="Authentication and User Management Service for TrustNet AI",
    version="1.0.0",
    lifespan=lifespan
)

# Include Auth Router
app.include_router(auth_router)

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
        data={"status": "ok", "service": "auth_service"},
        meta=ResponseMeta(request_id=request_id)
    )
