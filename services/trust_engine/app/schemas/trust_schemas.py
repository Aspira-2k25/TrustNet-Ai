from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from shared.schemas.evidence import EvidenceItem

class RiskLevelEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class TrustScoreResult(BaseModel):
    scan_id: str
    trust_risk_score: float = Field(..., ge=0.0, le=100.0, description="Universal risk score [0, 100]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in combined assessment [0, 1]")
    risk_level: RiskLevelEnum
    contradiction_flag: bool = Field(default=False)
    contradiction_details: Optional[str] = None
    reporting_modules: List[str]
    evidence: List[EvidenceItem] = Field(default_factory=list)
    explanation: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
