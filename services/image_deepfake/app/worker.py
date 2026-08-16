import os
import json
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional, Tuple
from aiokafka import AIOKafkaProducer

from shared.schemas.events import DetectionRequestedEvent, DetectorCompletedEvent
from shared.schemas.detection_result import DetectionResult
from shared.constants.modules import ModuleEnum
from shared.constants.status import StatusEnum
from shared.constants.native_score_semantics import NativeScoreSemanticsEnum
from shared.constants.topics import Topics
from shared.logging.logger_setup import get_logger
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from services.image_deepfake.app.config.settings import settings

logger = get_logger(settings.SERVICE_NAME)

class ImageDeepfakeWorker:
    def __init__(self):
        self.detector = EfficientNetDetector()
        self.storage_dir = settings.STORAGE_DIR
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self._producer: Optional[AIOKafkaProducer] = None

    def resolve_image_bytes(self, storage_key: Optional[str]) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Loads image bytes from storage key.
        Checks local storage filesystem fallback (e.g. storage_uploads/quarantine/image/...).
        """
        if not storage_key:
            return None, "Storage key is missing in event payload"

        # Check local storage directory
        local_path = os.path.join(self.storage_dir, storage_key.replace("/", os.sep))
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read(), None

        # If direct path
        if os.path.exists(storage_key):
            with open(storage_key, "rb") as f:
                return f.read(), None

        return None, f"Image file not found for key: {storage_key}"

    def process_request(self, event: DetectionRequestedEvent) -> DetectorCompletedEvent:
        """
        Processes a DetectionRequestedEvent through the ML model and produces a DetectorCompletedEvent.
        """
        start_time = time.time()
        scan_id = event.scan_id
        storage_key = event.payload.object_storage_key

        logger.info(f"Processing image deepfake detection for scan {scan_id}", extra={"scan_id": scan_id, "request_id": ""})

        image_bytes, error_err = self.resolve_image_bytes(storage_key)
        if error_err:
            processing_time_ms = int((time.time() - start_time) * 1000)
            result = DetectionResult(
                scan_id=scan_id,
                module=ModuleEnum.image_deepfake,
                detector_id="image_deepfake.efficientnet_b0.v1",
                model_version="v1",
                preprocessing_version="v1",
                native_score=0.0,
                native_score_semantics=NativeScoreSemanticsEnum.probability_of_negative_class,
                risk_score=0.0,
                confidence=0.0,
                label="error",
                status=StatusEnum.FAILED,
                evidence=[],
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_code="MEDIA_NOT_FOUND",
                error_message=error_err
            )
        else:
            result = self.detector.predict(image_bytes, scan_id=scan_id)

        completed_event = DetectorCompletedEvent(
            payload=result
        )

        return completed_event

    def publish_completed(self, event: DetectorCompletedEvent) -> bool:
        """
        Publishes a DetectorCompletedEvent to Kafka topic `detector.image.completed`.
        """
        topic = Topics.DETECTOR_IMAGE_COMPLETED
        scan_id = event.payload.scan_id
        payload_dict = event.model_dump(mode="json")

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running() and self._producer:
                loop.create_task(
                    self._producer.send_and_wait(
                        topic,
                        key=scan_id,
                        value=payload_dict
                    )
                )
        except Exception as e:
            logger.debug(f"Async Kafka send deferred: {str(e)}", extra={"scan_id": scan_id, "request_id": ""})

        logger.info(
            f"Published DetectorCompletedEvent to Kafka topic '{topic}' (scan_id: {scan_id})",
            extra={"scan_id": scan_id, "request_id": ""}
        )
        return True

    def handle_message(self, message_body: bytes) -> Optional[DetectorCompletedEvent]:
        """
        Full end-to-end message handler: parse JSON -> predict -> publish completion.
        """
        try:
            data = json.loads(message_body.decode("utf-8"))
            event = DetectionRequestedEvent.model_validate(data)
            completed_event = self.process_request(event)
            self.publish_completed(completed_event)
            return completed_event
        except Exception as e:
            logger.error(f"Failed to handle image detection message: {str(e)}", extra={"scan_id": "", "request_id": ""})
            return None

worker = ImageDeepfakeWorker()
