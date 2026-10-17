"""Internal contract development API; browser traffic must use Gateway."""
import os
import asyncio
from contextlib import suppress
from contextlib import asynccontextmanager
from fastapi import FastAPI
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

@app.get("/health")
def health():
    return {"status": "ok", "module": "phishing"}

@app.get("/ready")
def ready():
    from fastapi.responses import JSONResponse
    loaded = app.state.detector.model is not None
    if os.getenv("PHISHING_KAFKA_ENABLED", "false").lower() == "true":
        loaded = loaded and app.state.worker_state["broker_ready"]
    return JSONResponse({"ready": loaded}, status_code=200 if loaded else 503)
