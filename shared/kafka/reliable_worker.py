"""At-least-once Kafka worker: durable idempotency, bounded retries, manual commits."""
import asyncio,json,logging,sqlite3,hashlib,os
from pathlib import Path
from datetime import datetime,timezone
from aiokafka import AIOKafkaProducer,AIOKafkaConsumer
from aiokafka.structs import TopicPartition,OffsetAndMetadata
from shared.schemas.events import DetectionRequestedEvent,DetectorCompletedEvent
from shared.schemas.detection_result import DetectionResult
from shared.constants.topics import get_detection_requested_topic,get_detector_completed_topic,get_dlq_topic
logger=logging.getLogger('trustnet.kafka')

def failed_result(scan_id,module,code):
    return DetectionResult(scan_id=scan_id,module=module,detector_id=module+'.worker',model_version='unavailable',preprocessing_version='unavailable',native_score=0,native_score_semantics='probability_of_positive_class',risk_score=0,confidence=0,label='unknown',verdict='UNKNOWN',status='FAILED',timestamp=datetime.now(timezone.utc).isoformat(),error_code=code,error_message='Inference unavailable or failed; no safety assessment')

async def send_bounded(producer,topic,key,value):
    if producer is None:raise RuntimeError('Kafka producer unavailable')
    for attempt in range(3):
        try:
            await asyncio.wait_for(producer.send_and_wait(topic,key=key,value=value),5)
            return
        except Exception:
            if attempt==2:raise
            await asyncio.sleep(.25*(attempt+1))

def cache_connection(module):
    root=Path(os.getenv('WORKER_STATE_DIR','./runtime_state'));root.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(root/(module+'.sqlite'))
    db.execute('CREATE TABLE IF NOT EXISTS completions (scan_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, event TEXT NOT NULL)');return db

async def run_worker(module,bootstrap,predict,stop=None,group=None):
    request_topic=get_detection_requested_topic(module); completed_topic=get_detector_completed_topic(module)
    db=cache_connection(module)
    try:
        while not stop or not stop.is_set():
            producer=None;consumer=None
            try:
                producer=AIOKafkaProducer(bootstrap_servers=bootstrap,value_serializer=lambda v:json.dumps(v).encode(),key_serializer=lambda k:k.encode() if k else None,enable_idempotence=True,request_timeout_ms=5000)
                consumer=AIOKafkaConsumer(request_topic,bootstrap_servers=bootstrap,group_id=group or 'trustnet_'+module,enable_auto_commit=False,auto_offset_reset='earliest',request_timeout_ms=5000,max_poll_interval_ms=600000)
                await producer.start();await consumer.start()
                while not stop or not stop.is_set():
                    batches=await consumer.getmany(timeout_ms=1000,max_records=1)
                    for tp,messages in batches.items():
                        for msg in messages:
                            try:
                                event=DetectionRequestedEvent.model_validate_json(msg.value)
                                if event.module.value!=module or msg.key!=event.scan_id.encode():raise ValueError('Event association mismatch')
                            except Exception:
                                await send_bounded(producer,get_dlq_topic(request_topic),None,{'error':'INVALID_EVENT','topic':request_topic,'partition':msg.partition,'offset':msg.offset})
                                await consumer.commit({tp:OffsetAndMetadata(msg.offset+1,'')});continue
                            fingerprint=hashlib.sha256(event.model_dump_json().encode()).hexdigest()
                            saved=db.execute('SELECT fingerprint,event FROM completions WHERE scan_id=?',(event.scan_id,)).fetchone()
                            if saved and saved[0]!=fingerprint:
                                await send_bounded(producer,get_dlq_topic(request_topic),event.scan_id,{'scan_id':event.scan_id,'error':'CONFLICTING_RETRY'})
                            else:
                                if saved:completed=json.loads(saved[1])
                                else:
                                    try:
                                        result=await predict(event)
                                        if result.scan_id!=event.scan_id or result.module.value!=module:
                                            raise ValueError('Inference result association mismatch')
                                    except Exception as exc:
                                        logger.warning('Inference failed scan=%s type=%s',event.scan_id,type(exc).__name__)
                                        result=failed_result(event.scan_id,module,'INFERENCE_FAILED')
                                    completed=DetectorCompletedEvent(payload=result).model_dump(mode='json')
                                    db.execute('INSERT INTO completions VALUES (?,?,?)',(event.scan_id,fingerprint,json.dumps(completed)));db.commit()
                                await send_bounded(producer,completed_topic,event.scan_id,completed)
                            await consumer.commit({tp:OffsetAndMetadata(msg.offset+1,'')})
            except asyncio.CancelledError:raise
            except Exception as exc:
                logger.warning('Kafka worker disconnected type=%s; reconnecting',type(exc).__name__)
                await asyncio.sleep(3)
            finally:
                if consumer:await consumer.stop()
                if producer:await producer.stop()
    finally:db.close()
