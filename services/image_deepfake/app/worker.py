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
from models.image_deepfake.inference.forensic_detector import ForensicDetector
from services.image_deepfake.app.config.settings import settings

logger = get_logger(settings.SERVICE_NAME)

class ImageDeepfakeWorker:
    def __init__(self):
        self.detector = None
        self.error = None
        try:self.detector = ForensicDetector()
        except Exception as exc:
            self.error = type(exc).__name__
            logger.exception("Image model failed to load")
        self.storage_dir = settings.STORAGE_DIR
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self._producer: Optional[AIOKafkaProducer] = None

    def resolve_image_bytes(self, storage_key: Optional[str]) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Loads image bytes from storage key.
        Checks local storage filesystem fallback (e.g. storage_uploads/quarantine/image/...).
        Strictly prevents directory traversal attacks.
        """
        if not storage_key:
            return None, "Storage key is missing in event payload"

        # Prevent path traversal
        norm_parts = storage_key.replace("\\", "/").split("/")
        if ".." in norm_parts:
            return None, "Invalid storage key: directory traversal detected"

        from pathlib import Path
        abs_storage_dir=Path(self.storage_dir).resolve()
        local_path=(abs_storage_dir/storage_key).resolve()
        if not local_path.is_relative_to(abs_storage_dir):
            return None,"Image storage key is outside the configured storage directory"

        if os.path.exists(local_path) and os.path.isfile(local_path):
            with open(local_path, "rb") as f:
                data=f.read(settings.MAX_IMAGE_SIZE_MB*1024*1024+1)
            if len(data)>settings.MAX_IMAGE_SIZE_MB*1024*1024:
                return None,'Image storage object exceeds the upload byte limit'
            return data,None

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
        if self.detector is None:error_err="Image model unavailable; run the image artifact installer"
        if error_err:
            processing_time_ms = int((time.time() - start_time) * 1000)
            result = DetectionResult(
                scan_id=scan_id,
                module=ModuleEnum.image_deepfake,
                detector_id="image_deepfake.evidence.v2",
                model_version="v1",
                preprocessing_version="v1",
                native_score=0.0,
                native_score_semantics=NativeScoreSemanticsEnum.anomaly_score,
                risk_score=0.0,
                confidence=0.0,
                label="error",
                status=StatusEnum.FAILED,
                evidence=[],
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_code="MODEL_UNAVAILABLE" if self.detector is None else "MEDIA_NOT_FOUND",
                error_message=error_err
            )
        else:
            filename = None
            enable_explanation = False
            if event.payload.metadata and isinstance(event.payload.metadata, dict):
                filename = event.payload.metadata.get("original_filename")
                enable_explanation = bool(
                    event.payload.metadata.get("enable_explanation", False) or
                    event.payload.metadata.get("enable_deep_vision", False)
                )
            if not filename and storage_key:
                filename = os.path.basename(storage_key)

            result = self.detector.predict(
                image_bytes,
                scan_id=scan_id,
                filename=filename,
                enable_explanation=enable_explanation
            )

        encoded=result.metadata.pop('image_assets_base64',{})
        if result.status==StatusEnum.SUCCESS and result.metadata.get('image_analysis'):
            from shared.utils.image_assets import persist,directory,KINDS
            import hashlib
            target=directory(self.storage_dir,scan_id)
            if target.exists():
                # Idempotent retry: a completed artifact directory is reused only
                # for exactly the same original source. Never overwrite another scan.
                if hashlib.sha256((target/KINDS['original']).read_bytes()).digest()!=hashlib.sha256(image_bytes).digest():
                    raise ValueError('Image evidence identity collision')
                urls={kind:f'/api/v1/scans/{scan_id}/image/{kind}' for kind in encoded if (target/KINDS[kind]).is_file()}
            else:
                _,urls=persist(self.storage_dir,scan_id,image_bytes,encoded)
            result.metadata['image_analysis']['assets']=urls
            result.metadata['image_analysis']['original_url']=f'/api/v1/scans/{scan_id}/image/original'
        completed_event = DetectorCompletedEvent(
            payload=result
        )

        return completed_event

    async def publish_completed(self, event):
        from shared.kafka.reliable_worker import send_bounded
        await send_bounded(self._producer, Topics.DETECTOR_IMAGE_COMPLETED, event.payload.scan_id, event.model_dump(mode="json"))
        return True

    def handle_message(self, message_body: bytes) -> Optional[DetectorCompletedEvent]:
        """
        Full end-to-end message handler: parse JSON -> predict -> publish completion.
        """
        try:
            data = json.loads(message_body.decode("utf-8"))
            event = DetectionRequestedEvent.model_validate(data)
            completed_event = self.process_request(event)
            # Parsing/inference only. Reliable consumer owns awaited publication.
            return completed_event
        except Exception as e:
            logger.error(f"Failed to handle image detection message: {str(e)}", extra={"scan_id": "", "request_id": ""})
            return None

worker = ImageDeepfakeWorker()
