from shared.kafka.reliable_worker import run_worker
from services.scam_message.app.config.settings import settings
from shared.schemas.message_input import MessageInput
from models.scam_message.presentation import enrich
from services.scam_message.app.optional_explanation import explain
async def consume(runner):
    async def predict(event):
        request=MessageInput(text=event.payload.raw_text or '',**event.payload.metadata.get('message_context',{}))
        result=enrich(await runner.predict(request.canonical_text(),event.scan_id),request)
        from services.scam_message.app.link_fusion import fuse_links
        result=await fuse_links(result,request,settings.PHISHING_SERVICE_URL)
        result.metadata['optional_explanation']=await explain(result,request.optional_analysis)
        return result
    await run_worker('scam_message',settings.KAFKA_BOOTSTRAP_SERVERS,predict)
