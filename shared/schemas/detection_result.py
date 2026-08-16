from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, Dict, Any, List
import re
from datetime import datetime

from shared.constants.modules import ModuleEnum
from shared.constants.status import StatusEnum
from shared.constants.native_score_semantics import NativeScoreSemanticsEnum
from shared.constants.schema_version import CURRENT_SCHEMA_VERSION
from shared.schemas.evidence import EvidenceItem

class DetectionResult(BaseModel):
    scan_id: str
    module: ModuleEnum
    detector_id: str
    model_version: str
    preprocessing_version: str
    native_score: float
    native_score_semantics: NativeScoreSemanticsEnum
    risk_score: float = Field(..., ge=0.0, le=100.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    label: str
    status: StatusEnum
    evidence: List[EvidenceItem] = Field(default_factory=list)
    analyzers: List[Dict[str, Any]] = Field(default_factory=list)
    has_face: Optional[bool] = None
    verdict: Optional[str] = None
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: int = Field(default=0, ge=0)
    timestamp: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION)

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError("Timestamp must be a valid ISO-8601 UTC datetime string")

    @model_validator(mode='after')
    def validate_status_and_errors(self) -> 'DetectionResult':
        if self.status in (StatusEnum.SUCCESS, StatusEnum.PARTIAL_SUCCESS):
            if self.error_code is not None or self.error_message is not None:
                raise ValueError("error_code and error_message MUST be null on SUCCESS or PARTIAL_SUCCESS")
        elif self.status in (StatusEnum.FAILED, StatusEnum.TIMEOUT, StatusEnum.UNAVAILABLE):
            if self.error_code is None:
                raise ValueError(f"error_code MUST be set when status is {self.status}")
        return self
