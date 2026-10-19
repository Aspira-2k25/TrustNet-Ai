"""At-least-once phishing worker with durable Mongo completion replay."""
import asyncio
import hashlib
import json
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import OffsetAndMetadata
from shared.constants.topics import Topics, get_dlq_topic
from shared.schemas.events import DetectionRequestedEvent
from shared.kafka.reliable_worker import send_bounded

logger = logging.getLogger("trustnet.phishing.worker")

async def process(event, service, repository):
    fingerprint = hashlib.sha256(event.model_dump_json().encode()).hexdigest()
    saved = await asyncio.to_thread(repository.get, event.scan_id, fingerprint)
    if saved is not None:
        return saved
    completion = await asyncio.to_thread(service.handle, event.model_dump(mode="json"))
    return await asyncio.to_thread(repository.save, event.scan_id, fingerprint, completion.model_dump(mode="json"))

async def run_worker(bootstrap, group, service, repository, state):
    while True:
        producer, consumer = None, None
        state["broker_ready"] = False
        try:
            await asyncio.to_thread(repository.ping)
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap, enable_idempotence=True, value_serializer=lambda value: json.dumps(value).encode(), key_serializer=lambda key: key.encode() if key else None)
            consumer = AIOKafkaConsumer(Topics.DETECTION_REQUESTED_PHISHING, bootstrap_servers=bootstrap, group_id=group, enable_auto_commit=False, auto_offset_reset="earliest", max_poll_interval_ms=600000)
            await producer.start(); await consumer.start()
            state["broker_ready"] = True
            while True:
                batch = await consumer.getmany(timeout_ms=1000, max_records=1)
                for partition, messages in batch.items():
                    for message in messages:
                        try:
                            event = DetectionRequestedEvent.model_validate_json(message.value)
                            if event.module.value != "phishing" or message.key != event.scan_id.encode():
                                raise ValueError("Invalid request association")
                            # Validates module/schema before durable inference.
                            service.validate(event)
                        except ValueError:
                            await send_bounded(producer, get_dlq_topic(message.topic), None, {"error": "INVALID_REQUEST", "partition": message.partition, "offset": message.offset})
                            await consumer.commit({partition: OffsetAndMetadata(message.offset + 1, "")})
                            continue
                        try:
                            completion = await process(event, service, repository)
                        except ValueError:
                            await send_bounded(producer, get_dlq_topic(message.topic), event.scan_id, {"error": "CONFLICTING_REQUEST", "scan_id": event.scan_id})
                        else:
                            # Result is durable before publication; replay uses the same event ID.
                            await send_bounded(producer, Topics.DETECTOR_PHISHING_COMPLETED, event.scan_id, completion)
                        await consumer.commit({partition: OffsetAndMetadata(message.offset + 1, "")})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Phishing worker retry type=%s", type(exc).__name__)
            await asyncio.sleep(3)
        finally:
            state["broker_ready"] = False
            if consumer:
                await consumer.stop()
            if producer:
                await producer.stop()
