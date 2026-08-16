import threading
import asyncio
import json
import time
from typing import Optional
from aiokafka import AIOKafkaConsumer
from shared.constants.topics import Topics
from shared.logging.logger_setup import get_logger
from services.image_deepfake.app.config.settings import settings
from services.image_deepfake.app.worker import worker

logger = get_logger(settings.SERVICE_NAME)

class ImageConsumerThread(threading.Thread):
    """
    Background Kafka consumer thread for Image Deepfake Service.
    Consumes from `detection.requested.image_deepfake`.
    """
    def __init__(self, bootstrap_servers: Optional[str] = None):
        super().__init__(daemon=True, name="ImageDeepfakeKafkaConsumer")
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.group_id = settings.KAFKA_CONSUMER_GROUP
        self._stop_event = threading.Event()

    def run(self):
        logger.info(f"Starting Image Deepfake Kafka Consumer thread for group '{self.group_id}'...", extra={"scan_id": "", "request_id": ""})
        asyncio.run(self._consume_loop())

    async def _consume_loop(self):
        topic = Topics.DETECTION_REQUESTED_IMAGE
        
        while not self._stop_event.is_set():
            consumer = None
            try:
                consumer = AIOKafkaConsumer(
                    topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    request_timeout_ms=5000
                )
                await consumer.start()
                logger.info(f"Kafka consumer successfully connected and subscribed to '{topic}'", extra={"scan_id": "", "request_id": ""})

                while not self._stop_event.is_set():
                    try:
                        msg_batch = await asyncio.wait_for(consumer.getmany(timeout_ms=1000, max_records=10), timeout=2.0)
                        for tp, messages in msg_batch.items():
                            for msg in messages:
                                worker.handle_message(msg.value)
                    except asyncio.TimeoutError:
                        continue
                    except Exception as err:
                        if not self._stop_event.is_set():
                            logger.warning(f"Error fetching Kafka messages: {str(err)}", extra={"scan_id": "", "request_id": ""})
                        break

            except Exception as e:
                if not self._stop_event.is_set():
                    logger.warning(f"Kafka consumer connection to {self.bootstrap_servers} failed ({str(e)}). Retrying in 5s...", extra={"scan_id": "", "request_id": ""})
                    await asyncio.sleep(5.0)
            finally:
                if consumer:
                    try:
                        await consumer.stop()
                    except Exception:
                        pass

    def stop(self):
        logger.info("Stopping Image Deepfake Kafka Consumer thread...", extra={"scan_id": "", "request_id": ""})
        self._stop_event.set()
