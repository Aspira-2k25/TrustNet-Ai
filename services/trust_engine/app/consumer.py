import threading
import asyncio
import json
import time
from typing import Optional, Dict, List
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from shared.schemas.events import DetectorCompletedEvent
from shared.constants.topics import Topics
from shared.logging.logger_setup import get_logger
from services.trust_engine.app.config.settings import settings
from services.trust_engine.app.services.fusion_engine import fusion_engine
from services.trust_engine.app.repositories.score_repository import score_repo

logger = get_logger(settings.SERVICE_NAME)

class TrustEngineConsumerThread(threading.Thread):
    """
    Background Kafka consumer thread for Trust Score Engine.
    Subscribes to detector completion topics and publishes to `trust_score.generated`.
    """
    def __init__(self, bootstrap_servers: Optional[str] = None):
        super().__init__(daemon=True, name="TrustEngineKafkaConsumer")
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.group_id = settings.KAFKA_CONSUMER_GROUP
        self._stop_event = threading.Event()
        self._scan_buffer: Dict[str, List] = {}

    def run(self):
        logger.info(f"Starting Trust Engine Kafka Consumer thread for group '{self.group_id}'...", extra={"scan_id": "", "request_id": ""})
        asyncio.run(self._consume_loop())

    async def _consume_loop(self):
        topics = [
            Topics.DETECTOR_IMAGE_COMPLETED,
            Topics.DETECTOR_AUDIO_COMPLETED,
            Topics.DETECTOR_VIDEO_COMPLETED,
            Topics.DETECTOR_PHISHING_COMPLETED,
            Topics.DETECTOR_SCAM_COMPLETED,
            Topics.DETECTOR_REVIEW_COMPLETED,
            Topics.DETECTOR_OSINT_COMPLETED,
        ]

        while not self._stop_event.is_set():
            consumer = None
            producer = None
            try:
                consumer = AIOKafkaConsumer(
                    *topics,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    request_timeout_ms=5000
                )
                producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                    request_timeout_ms=3000
                )
                await consumer.start()
                await producer.start()
                logger.info("Trust Engine consumer & producer initialized successfully", extra={"scan_id": "", "request_id": ""})

                while not self._stop_event.is_set():
                    try:
                        msg_batch = await asyncio.wait_for(consumer.getmany(timeout_ms=1000, max_records=10), timeout=2.0)
                        for tp, messages in msg_batch.items():
                            for msg in messages:
                                await self._handle_message(msg.value, producer)
                    except asyncio.TimeoutError:
                        continue
                    except Exception as err:
                        if not self._stop_event.is_set():
                            logger.warning(f"Error reading detector messages from Kafka: {str(err)}", extra={"scan_id": "", "request_id": ""})
                        break

            except Exception as e:
                if not self._stop_event.is_set():
                    logger.warning(f"Kafka connection to {self.bootstrap_servers} failed ({str(e)}). Retrying in 5s...", extra={"scan_id": "", "request_id": ""})
                    await asyncio.sleep(5.0)
            finally:
                if consumer:
                    try:
                        await consumer.stop()
                    except Exception:
                        pass
                if producer:
                    try:
                        await producer.stop()
                    except Exception:
                        pass

    async def _handle_message(self, message_body: bytes, producer: Optional[AIOKafkaProducer]):
        try:
            data = json.loads(message_body.decode("utf-8") if isinstance(message_body, bytes) else message_body)
            event = DetectorCompletedEvent.model_validate(data)
            scan_id = event.payload.scan_id

            if scan_id not in self._scan_buffer:
                self._scan_buffer[scan_id] = []
            self._scan_buffer[scan_id].append(event.payload)

            # Fuse available reports for this scan
            fused = fusion_engine.fuse(self._scan_buffer[scan_id], scan_id=scan_id)
            score_repo.save(fused)

            # Publish trust_score.generated
            if producer:
                await producer.send_and_wait(
                    Topics.TRUST_SCORE_GENERATED,
                    key=scan_id,
                    value=fused.model_dump(mode="json")
                )
            logger.info(f"Fused Trust Score generated for scan {scan_id}: {fused.trust_risk_score:.1f}", extra={"scan_id": scan_id, "request_id": ""})
        except Exception as e:
            logger.error(f"Failed to process detector completed message: {str(e)}", extra={"scan_id": "", "request_id": ""})

    def stop(self):
        logger.info("Stopping Trust Engine Kafka Consumer thread...", extra={"scan_id": "", "request_id": ""})
        self._stop_event.set()
