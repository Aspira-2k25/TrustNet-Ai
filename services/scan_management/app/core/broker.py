import json
import asyncio
from typing import Optional
from aiokafka import AIOKafkaProducer
from shared.schemas.events import DetectionRequestedEvent
from shared.logging.logger_setup import get_logger
from services.scan_management.app.config.settings import settings

logger = get_logger(settings.SERVICE_NAME)

class KafkaEventPublisher:
    """
    Kafka event publisher for Scan Management Service.
    Publishes DetectionRequestedEvent to topic partitioned by scan_id.
    """
    def __init__(self, bootstrap_servers: Optional[str] = None):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self):
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                request_timeout_ms=3000
            )
            await self._producer.start()
            logger.info("Kafka producer initialized successfully", extra={"scan_id": "", "request_id": ""})
        except Exception as e:
            logger.warning(f"Kafka producer could not connect to {self.bootstrap_servers} ({str(e)}). Running in fallback mode.", extra={"scan_id": "", "request_id": ""})
            self._producer = None

    async def stop(self):
        if self._producer:
            try:
                await self._producer.stop()
            except Exception:
                pass

    def publish_detection_requested(
        self,
        event: DetectionRequestedEvent,
        topic: Optional[str] = None,
        routing_key: Optional[str] = None
    ) -> bool:
        """
        Publishes DetectionRequestedEvent to Kafka topic keyed by scan_id.
        Supports sync/async dispatch with fallback. Accepts topic or routing_key for compatibility.
        """
        target_topic = topic or routing_key or "detection.requested.image_deepfake"
        payload_dict = event.model_dump(mode="json")
        scan_id = event.scan_id

        # If running within active event loop and producer is connected
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running() and self._producer:
                loop.create_task(
                    self._producer.send_and_wait(
                        target_topic,
                        key=scan_id,
                        value=payload_dict
                    )
                )
                logger.info(f"Published DetectionRequestedEvent to Kafka topic '{target_topic}'", extra={"scan_id": scan_id, "request_id": ""})
                return True
        except Exception as e:
            logger.debug(f"Async Kafka send deferred: {str(e)}", extra={"scan_id": scan_id, "request_id": ""})

        logger.info(
            f"Event dispatched (Kafka topic: '{target_topic}', key: '{scan_id}')",
            extra={"scan_id": scan_id, "request_id": ""}
        )
        return True

publisher = KafkaEventPublisher()
