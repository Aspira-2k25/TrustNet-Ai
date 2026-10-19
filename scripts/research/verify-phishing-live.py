"""Real Kafka + Mongo replay smoke test; no external URL is fetched."""
import asyncio
from contextlib import suppress
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import uuid
from aiokafka import AIOKafkaProducer,AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient,NewTopic
from aiokafka.errors import TopicAlreadyExistsError
from shared.constants.topics import Topics
from shared.schemas.events import DetectionRequestedEvent
from services.phishing_url.app.core.consumer import run_worker
from services.phishing_url.app.detection_service import DetectionService
from services.phishing_url.app.repositories.result_repository import ResultRepository
from models.phishing_url.inference.phishing_detector import PhishingDetector

async def main():
    scan_id='phishing-smoke-'+str(uuid.uuid4())
    admin=AIOKafkaAdminClient(bootstrap_servers='localhost:9094');await admin.start()
    try:
        for topic in (Topics.DETECTION_REQUESTED_PHISHING,Topics.DETECTOR_PHISHING_COMPLETED,Topics.DETECTION_REQUESTED_PHISHING+'.dlq'):
            try:await admin.create_topics([NewTopic(topic,num_partitions=1,replication_factor=1)])
            except TopicAlreadyExistsError:pass
    finally:await admin.close()
    repository=ResultRepository('mongodb://localhost:27017');repository.ping()
    service=DetectionService(PhishingDetector('models/phishing_url/checkpoints/baseline/rf.json'))
    state={};worker=asyncio.create_task(run_worker('localhost:9094','phishing-smoke-'+scan_id,service,repository,state))
    consumer=AIOKafkaConsumer(Topics.DETECTOR_PHISHING_COMPLETED,bootstrap_servers='localhost:9094',group_id=scan_id,auto_offset_reset='earliest')
    producer=AIOKafkaProducer(bootstrap_servers='localhost:9094')
    try:
        await consumer.start();await producer.start()
        for _ in range(60):
            if state.get('broker_ready'):break
            await asyncio.sleep(.25)
        if not state.get('broker_ready'):raise RuntimeError('Worker not ready')
        event=DetectionRequestedEvent(scan_id=scan_id,module='phishing',timestamp=datetime.now(timezone.utc).isoformat(),payload={'url':'https://example.com/account'})
        completions=[]
        for attempt in range(2):
            await producer.send_and_wait(Topics.DETECTION_REQUESTED_PHISHING,key=scan_id.encode(),value=event.model_dump_json().encode())
            async def matching():
                async for message in consumer:
                    value=json.loads(message.value)
                    if value['payload']['scan_id']==scan_id:return value
            completions.append(await asyncio.wait_for(matching(),60))
        assert completions[0]==completions[1], 'Replay changed completion identity'
        assert repository.collection.find_one({'_id':scan_id})['completion']==completions[0]
        result=completions[0]['payload']
        report={'scan_id':scan_id,'real_kafka':True,'real_mongodb':True,'duplicate_completion_identical':True,'result':result,'model':'trained RF lexical baseline','external_collection':False}
        Path('models/phishing_url/research/live_worker_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({key:report[key] for key in ('scan_id','real_kafka','real_mongodb','duplicate_completion_identical')},indent=2))
    finally:
        worker.cancel()
        with suppress(asyncio.CancelledError):await worker
        await producer.stop();await consumer.stop();repository.close()
asyncio.run(main())
