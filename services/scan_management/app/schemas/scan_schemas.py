from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from shared.schemas.message_input import MessageInput

class ScanCreateTextRequest(MessageInput):
    pass

class ScanCreateURLRequest(BaseModel):
    url: str = Field(..., min_length=4, max_length=2048, description="The URL to scan for phishing")

class ScanResponse(BaseModel):
    id: str
    user_id: str
    status: str
    content_type: str
    media_storage_key: Optional[str] = None
    raw_input: Optional[str] = None
    filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    trust_score: Optional[Dict[str, Any]] = None
    dimensions: Optional[Dict[str, int]] = None
    mime_type: Optional[str] = None

class ScanListResponse(BaseModel):
    scans: List[ScanResponse]
    total: int
    page: int
    limit: int
