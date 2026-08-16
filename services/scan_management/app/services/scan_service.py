import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.scan_management.app.repositories.scan_repository import ScanRepository
from services.scan_management.app.db_models.scan import Scan
from services.scan_management.app.schemas.scan_schemas import (
    ScanResponse,
    ScanListResponse
)
from services.scan_management.app.validators.upload_validator import validate_and_sanitize_upload
from services.scan_management.app.core.broker import publisher
from services.scan_management.app.config.settings import settings
from shared.schemas.events import DetectionRequestedEvent, DetectionRequestedPayload
from shared.constants.modules import ModuleEnum
from shared.constants.topics import Topics
from shared.constants.status import StatusEnum

class ScanService:
    def __init__(self, session: AsyncSession):
        self.repo = ScanRepository(session)

    async def create_file_scan(
        self,
        user_id: str,
        file_bytes: bytes,
        original_filename: str,
        declared_content_type: str,
        modality: str
    ) -> ScanResponse:
        storage_key, sanitized_filename, file_size = validate_and_sanitize_upload(
            file_bytes=file_bytes,
            original_filename=original_filename,
            declared_content_type=declared_content_type,
            expected_modality=modality
        )

        # Save to local storage prefix (fallback/emulated Object Storage)
        local_path = os.path.join(settings.STORAGE_DIR, storage_key.replace("/", os.sep))
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(file_bytes)

        scan_id = str(uuid.uuid4())
        scan = Scan(
            id=scan_id,
            user_id=user_id,
            status=StatusEnum.SUCCESS.value,
            content_type=modality,
            media_storage_key=storage_key,
            filename=sanitized_filename,
            file_size_bytes=file_size,
            mime_type=declared_content_type
        )
        created_scan = await self.repo.create(scan)

        # Map modality to module enum and routing key
        mod_map = {
            "image": (ModuleEnum.image_deepfake, Topics.DETECTION_REQUESTED_IMAGE),
            "audio": (ModuleEnum.audio_deepfake, Topics.DETECTION_REQUESTED_AUDIO),
            "video": (ModuleEnum.video_deepfake, Topics.DETECTION_REQUESTED_VIDEO),
        }
        
        module_enum, routing_key = mod_map.get(modality, (ModuleEnum.image_deepfake, Topics.DETECTION_REQUESTED_IMAGE))

        # Publish DetectionRequestedEvent
        event = DetectionRequestedEvent(
            scan_id=scan_id,
            module=module_enum,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=DetectionRequestedPayload(
                object_storage_key=storage_key,
                metadata={"original_filename": original_filename, "file_size_bytes": file_size}
            )
        )
        publisher.publish_detection_requested(event, routing_key=routing_key)

        return self._to_response(created_scan)

    async def create_text_scan(self, user_id: str, text: str) -> ScanResponse:
        scan_id = str(uuid.uuid4())
        scan = Scan(
            id=scan_id,
            user_id=user_id,
            status=StatusEnum.SUCCESS.value,
            content_type="text",
            raw_input=text,
            file_size_bytes=len(text.encode("utf-8"))
        )
        created_scan = await self.repo.create(scan)

        # Publish to both scam and review detection
        event = DetectionRequestedEvent(
            scan_id=scan_id,
            module=ModuleEnum.scam_message,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=DetectionRequestedPayload(
                raw_text=text,
                metadata={}
            )
        )
        publisher.publish_detection_requested(event, routing_key=Topics.DETECTION_REQUESTED_TEXT)

        return self._to_response(created_scan)

    async def create_url_scan(self, user_id: str, url: str) -> ScanResponse:
        scan_id = str(uuid.uuid4())
        scan = Scan(
            id=scan_id,
            user_id=user_id,
            status=StatusEnum.SUCCESS.value,
            content_type="url",
            raw_input=url,
            file_size_bytes=len(url.encode("utf-8"))
        )
        created_scan = await self.repo.create(scan)

        event = DetectionRequestedEvent(
            scan_id=scan_id,
            module=ModuleEnum.phishing,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=DetectionRequestedPayload(
                url=url,
                metadata={}
            )
        )
        publisher.publish_detection_requested(event, routing_key=Topics.DETECTION_REQUESTED_URL)

        return self._to_response(created_scan)

    async def get_scan(self, scan_id: str, user_id: Optional[str] = None) -> ScanResponse:
        scan = await self.repo.get_by_id(scan_id)
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "SCAN_NOT_FOUND", "message": f"Scan '{scan_id}' does not exist"}
            )
        if user_id and scan.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ACCESS_DENIED", "message": "You do not have permission to view this scan"}
            )
        return self._to_response(scan)

    async def list_scans(self, user_id: str, page: int = 1, limit: int = 20) -> ScanListResponse:
        offset = (page - 1) * limit
        scans, total = await self.repo.list_by_user(user_id, offset=offset, limit=limit)
        return ScanListResponse(
            scans=[self._to_response(s) for s in scans],
            total=total,
            page=page,
            limit=limit
        )

    def _to_response(self, scan: Scan) -> ScanResponse:
        return ScanResponse(
            id=scan.id,
            user_id=scan.user_id,
            status=scan.status,
            content_type=scan.content_type,
            media_storage_key=scan.media_storage_key,
            raw_input=scan.raw_input,
            filename=scan.filename,
            file_size_bytes=scan.file_size_bytes,
            created_at=scan.created_at.isoformat(),
            updated_at=scan.updated_at.isoformat()
        )
