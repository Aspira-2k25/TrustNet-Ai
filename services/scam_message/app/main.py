import asyncio, logging
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from pydantic import Field
from shared.schemas.message_input import MessageInput
from models.scam_message.presentation import enrich
from services.scam_message.app.optional_explanation import explain
from models.scam_message.detector import ScamDetector
from shared.schemas.api_response import APIResponse,ResponseMeta
from shared.utils.ids import generate_request_id
from services.scam_message.app.config.settings import settings
logger=logging.getLogger('trustnet.scam')
class InferenceRequest(MessageInput):
    scan_id: str = Field(min_length=1,max_length=100)
class InferenceRunner:
    def __init__(self):
        self.detector=None; self.error=None
        self.pool=ThreadPoolExecutor(max_workers=settings.SCAM_MAX_CONCURRENCY)
        self.active=0
        try:self.detector=ScamDetector()
        except Exception as exc:self.error=type(exc).__name__; logger.exception('Artifact unavailable: %s',exc)
    async def predict(self,text,scan_id):
        if self.detector is None: raise HTTPException(503,'Scam model unavailable')
        if self.active>=settings.SCAM_MAX_CONCURRENCY: raise HTTPException(429,'Scam inference busy; retry later')
        self.active+=1
        future=asyncio.get_running_loop().run_in_executor(self.pool,self.detector.predict,text,scan_id)
        def completed(_):self.active-=1
        future.add_done_callback(completed)
        try:return await asyncio.wait_for(asyncio.shield(future),settings.SCAM_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:raise HTTPException(504,'Scam inference timed out')
        except ValueError as exc:raise HTTPException(422,str(exc))
        except Exception as exc:
            logger.error('Scam inference unavailable scan=%s type=%s',scan_id,type(exc).__name__)
            raise HTTPException(503,'Scam inference unavailable')
runner=None
@asynccontextmanager
async def lifespan(app):
    global runner
    runner=InferenceRunner()
    task=None
    if settings.KAFKA_ENABLED:
        from services.scam_message.app.worker import consume
        task=asyncio.create_task(consume(runner))
    yield
    if task:
        task.cancel()
        try:await task
        except asyncio.CancelledError:pass
    runner.pool.shutdown(wait=True)
app=FastAPI(title='TrustNet Scam Message Service',lifespan=lifespan)
@app.get('/health')
async def health():return {'status':'ok','service':'scam_message'}
@app.get('/ready')
async def ready():
    if not runner or not runner.detector:raise HTTPException(503,'Artifact unavailable')
    return {'status':'ready','model_version':runner.detector.manifest['model_version']}
@app.post('/infer')
async def infer(req:InferenceRequest):
    if not runner: raise HTTPException(503,'Scam service is not ready')
    result=enrich(await runner.predict(req.canonical_text(),req.scan_id),req)
    from services.scam_message.app.link_fusion import fuse_links
    result=await fuse_links(result,req,settings.PHISHING_SERVICE_URL)
    result.metadata['optional_explanation']=await explain(result,req.optional_analysis)
    logger.info('Inference scan=%s status=%s latency_ms=%s',req.scan_id,result.status,result.processing_time_ms)
    return APIResponse(data=result,meta=ResponseMeta(request_id=generate_request_id()))
