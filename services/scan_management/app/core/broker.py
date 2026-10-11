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
        if not settings.KAFKA_ENABLED:
            return
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
            if self._producer:
                await self._producer.stop()
            self._producer = None

    async def stop(self):
        if self._producer:
            try:
                await self._producer.stop()
            except Exception:
                pass

    async def publish_detection_requested(self, event, topic=None, routing_key=None) -> bool:
        from fastapi import HTTPException
        if self._producer is None:
            raise HTTPException(503, "Kafka unavailable; asynchronous dispatch not accepted")
        target_topic = topic or routing_key
        if not target_topic:
            raise ValueError("Explicit canonical topic required")
        for attempt in range(3):
            try:
                await asyncio.wait_for(self._producer.send_and_wait(target_topic, key=event.scan_id, value=event.model_dump(mode="json")), 5)
                logger.info("Published scan=%s topic=%s", event.scan_id, target_topic)
                return True
            except Exception:
                if attempt == 2:
                    raise HTTPException(503, "Kafka dispatch failed")
                await asyncio.sleep(.25 * (attempt + 1))

publisher = KafkaEventPublisher()
