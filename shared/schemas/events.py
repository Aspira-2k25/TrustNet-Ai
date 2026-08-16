from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from shared.constants.schema_version import CURRENT_SCHEMA_VERSION
from shared.constants.modules import ModuleEnum
from shared.schemas.detection_result import DetectionResult
from shared.utils.ids import generate_event_id

class DetectionRequestedPayload(BaseModel):
    # [TO VERIFY] exact per-modality DetectionRequestedEvent payload fields against Blueprint Part G.
    # [PROPOSED] generic payload fields: object_storage_key for media (image/audio/video), 
    # raw_text or url for NLP modalities (phishing/scam/review/OSINT).
    object_storage_key: Optional[str] = None
    raw_text: Optional[str] = None
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DetectionRequestedEvent(BaseModel):
    scan_id: str
    module: ModuleEnum
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION)
    timestamp: str
    payload: DetectionRequestedPayload

class DetectorCompletedEvent(BaseModel):
    event_id: str = Field(default_factory=generate_event_id)
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION)
    payload: DetectionResult
