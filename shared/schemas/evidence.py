from pydantic import BaseModel, Field

class EvidenceItem(BaseModel):
    feature_or_region: str
    contribution: float = Field(allow_inf_nan=False)  # Signed attribution in the detector-declared units.
    human_readable_note: str
