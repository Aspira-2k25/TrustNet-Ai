from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List

class ScanCreateTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="The raw message or review text to scan")

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

class ScanListResponse(BaseModel):
    scans: List[ScanResponse]
    total: int
    page: int
    limit: int
