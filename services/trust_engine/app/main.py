from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from shared.schemas.api_response import APIResponse, ResponseMeta, ErrorDetail
from shared.utils.ids import generate_request_id
from shared.logging.logger_setup import get_logger
from services.trust_engine.app.config.settings import settings
from services.trust_engine.app.consumer import TrustEngineConsumerThread
from services.trust_engine.app.routers.trust_router import router as trust_router

logger = get_logger(settings.SERVICE_NAME)

consumer_thread: TrustEngineConsumerThread = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_thread
    logger.info("Initializing Trust Score Engine Service...")
    
    if settings.ENABLE_KAFKA_CONSUMER:
        consumer_thread = TrustEngineConsumerThread()
        consumer_thread.start()
        
    yield
    
    if consumer_thread:
        consumer_thread.stop()
        consumer_thread.join(timeout=2.0)
    logger.info("Trust Score Engine Service shutdown complete.")

app = FastAPI(
    title="TrustNet Trust Score Engine",
    description="Multimodal score synthesis and calibrated Trust Score fusion engine",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(trust_router)

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
        data={"status": "ok", "service": "trust_engine_service"},
        meta=ResponseMeta(request_id=request_id)
    )
