from pydantic import BaseModel

class EvidenceItem(BaseModel):
    feature_or_region: str
    contribution: float # [TO VERIFY] with the team whether contribution should be bounded (e.g., [0,1] or [-1,1])
    human_readable_note: str
