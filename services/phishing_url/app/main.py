"""Internal contract development API; browser traffic must use Gateway."""
import os
import asyncio
from contextlib import suppress
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from models.phishing_url.inference.phishing_detector import PhishingDetector

@asynccontextmanager
async def lifespan(app):
    manifest=os.getenv("PHISHING_MODEL_MANIFEST")
    if os.getenv("PHISHING_MODEL_S3_URI"):
        from services.phishing_url.app.services.artifact_store import download
        manifest=await asyncio.to_thread(download,os.environ["PHISHING_MODEL_S3_URI"],os.getenv("PHISHING_MODEL_CACHE","runtime_state/phishing_models"),os.environ["PHISHING_MANIFEST_SHA256"])
    app.state.detector = PhishingDetector(manifest)
    app.state.worker_state = {"broker_ready": False}
    task, repository = None, None
    if os.getenv("PHISHING_KAFKA_ENABLED", "false").lower() == "true":
        from services.phishing_url.app.repositories.result_repository import ResultRepository
        from services.phishing_url.app.core.consumer import run_worker
        from services.phishing_url.app.detection_service import DetectionService
        repository = ResultRepository(os.getenv("PHISHING_MONGODB_URI", "mongodb://localhost:27017"))
        task = asyncio.create_task(run_worker(os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094"), "trustnet_phishing_v1", DetectionService(app.state.detector), repository, app.state.worker_state))
    try:
        yield
    finally:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        if repository:
            repository.close()

app = FastAPI(title="TrustNet Phishing Detection", lifespan=lifespan)

class InferenceRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scan_id: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2048)

@app.post('/infer')
async def infer(req: InferenceRequest):
    """Loopback/internal inference. Never navigate to submitted links."""
    if app.state.detector.model is None:
        raise HTTPException(503, 'Phishing model unavailable')
    # Per-process bound prevents concurrent requests growing without limit.
    if not hasattr(app.state, 'inference_slots'):
        app.state.inference_slots = asyncio.Semaphore(2)
    try:
        await asyncio.wait_for(app.state.inference_slots.acquire(), timeout=1)
    except asyncio.TimeoutError:
        raise HTTPException(429, 'Phishing inference busy')
    try:
        result = await asyncio.to_thread(app.state.detector.predict, {'scan_id': req.scan_id, 'url': req.url})
        result.metadata['embedded_scan_mode'] = 'offline_url_model_and_link_policy'
        from urllib.parse import urlparse
        from models.phishing_url.inference.forensics import registered_domain
        host = urlparse(req.url).hostname or req.url
        try:
            reg_dom = registered_domain(host)
        except Exception:
            reg_dom = host
        result.metadata['domain_intel'] = {
            'domain': reg_dom,
            'domain_age_days': None,
            'registration_date': None,
            'ssl_status': 'UNVERIFIED_SSL' if req.url.lower().startswith('https://') else 'UNENCRYPTED_HTTP',
            'ssl_issuer': None,
            'has_password_form': False,
            'final_url': req.url
        }
        return {'data': result.model_dump(mode='json')}
    finally:
        app.state.inference_slots.release()

@app.post('/inspect')
async def inspect(req: InferenceRequest):
    """Explicit internal website inspection using the existing isolated collector."""
    if app.state.detector.model is None:
        raise HTTPException(503, 'Phishing model unavailable')
    if not hasattr(app.state, 'inspection_slots'):
        app.state.inspection_slots = asyncio.Semaphore(2)
    try:
        await asyncio.wait_for(app.state.inspection_slots.acquire(), timeout=1)
    except asyncio.TimeoutError:
        raise HTTPException(429, 'Website inspection busy')
    try:
        from datetime import datetime, timezone
        from services.phishing_url.app.detection_service import DetectionService
        event = {'scan_id': req.scan_id, 'module': 'phishing',
                 'timestamp': datetime.now(timezone.utc).isoformat(), 'payload': {'url': req.url}}
        completed = await asyncio.to_thread(DetectionService(app.state.detector).handle, event)
        completed.payload.metadata['inspection_mode'] = 'explicit_website_inspection'
        return {'data': completed.payload.model_dump(mode='json')}
    finally:
        app.state.inspection_slots.release()


@app.get("/health")
def health():
    return {"status": "ok", "module": "phishing"}

@app.get("/ready")
def ready():
    from fastapi.responses import JSONResponse
    loaded = app.state.detector.model is not None
    kafka=os.getenv("PHISHING_KAFKA_ENABLED", "false").lower()=="true"
    return JSONResponse({"ready":loaded,"model_ready":loaded,"kafka_enabled":kafka,
        "worker_ready":bool(loaded and app.state.worker_state['broker_ready']) if kafka else None},status_code=200 if loaded else 503)


@app.get('/ready/worker')
def worker_ready():
    from fastapi.responses import JSONResponse
    ready=bool(app.state.detector.model is not None and app.state.worker_state['broker_ready'])
    return JSONResponse({'ready':ready},status_code=200 if ready else 503)
