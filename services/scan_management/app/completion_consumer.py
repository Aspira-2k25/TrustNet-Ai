"""Persist validated completion events with first-completion-wins idempotency."""
import asyncio,json,logging,os
from aiokafka import AIOKafkaConsumer,AIOKafkaProducer
from aiokafka.structs import OffsetAndMetadata
from sqlalchemy import select
from services.scan_management.app.config.settings import settings
from services.scan_management.app.database.session import async_session_factory
from services.scan_management.app.db_models.scan import Scan,ScanAssessment
from shared.schemas.events import DetectorCompletedEvent
from shared.constants.topics import Topics,get_dlq_topic
from shared.kafka.reliable_worker import send_bounded
logger=logging.getLogger('trustnet.scan.completion')
async def persist_completion(event,session):
    result=event.payload
    scan=(await session.execute(select(Scan).where(Scan.id==result.scan_id).with_for_update())).scalar_one_or_none()
    if not scan:raise ValueError('Unknown scan')
    expected={'image':'image_deepfake','text':'scam_message','url':'phishing'}.get(scan.content_type)
    if result.module.value!=expected:raise ValueError('Wrong module for scan')
    saved=await session.get(ScanAssessment,scan.id)
    if saved and saved.assessment.get("result"):return False
    if scan.status not in ('QUEUED','PROCESSING'):raise ValueError('Scan is not awaiting inference')
    from services.trust_engine.app.services.fusion_engine import fusion_engine
    trust=fusion_engine.fuse([result],scan.id).model_dump(mode='json')
    trust['module_scores']={result.module.value:result.risk_score if result.status.value == 'SUCCESS' else None};trust['contradiction_detected']=trust['contradiction_flag']
    if result.module.value == 'phishing' and result.status.value == 'PARTIAL_SUCCESS':
        trust['module_scores']['phishing'] = result.risk_score
    assessment = {'result':result.model_dump(mode='json'),'trust_score':trust}
    if saved:
        saved.assessment = {**saved.assessment, **assessment}
    else:
        session.add(ScanAssessment(scan_id=scan.id,assessment=assessment))
    scan.status=result.status.value
    await session.commit();return True
async def consume_completions():
    topics=[Topics.DETECTOR_IMAGE_COMPLETED,Topics.DETECTOR_SCAM_COMPLETED,Topics.DETECTOR_PHISHING_COMPLETED]
    while True:
        consumer=None;producer=None
        try:
            producer=AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,value_serializer=lambda v:json.dumps(v).encode(),key_serializer=lambda k:k.encode() if k else None)
            consumer=AIOKafkaConsumer(*topics,bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,group_id=os.getenv('SCAN_COMPLETION_GROUP','trustnet_scan_completion'),enable_auto_commit=False,auto_offset_reset='earliest',request_timeout_ms=5000)
            await producer.start();await consumer.start()
            async for msg in consumer:
                from aiokafka.structs import TopicPartition
                try:
                    event=DetectorCompletedEvent.model_validate_json(msg.value)
                    if msg.key!=event.payload.scan_id.encode() or msg.topic!='detector.'+event.payload.module.value+'.completed':raise ValueError('Event association mismatch')
                    async with async_session_factory() as session:await persist_completion(event,session)
                except ValueError:
                    await send_bounded(producer,get_dlq_topic(msg.topic),None,{'error':'INVALID_COMPLETION','partition':msg.partition,'offset':msg.offset})
                await consumer.commit({TopicPartition(msg.topic,msg.partition):OffsetAndMetadata(msg.offset+1,'')})
        except asyncio.CancelledError:raise
        except Exception as exc:
            logger.warning('Completion persistence/connection failed type=%s',type(exc).__name__);await asyncio.sleep(3)
        finally:
            if consumer:await consumer.stop()
            if producer:await producer.stop()
