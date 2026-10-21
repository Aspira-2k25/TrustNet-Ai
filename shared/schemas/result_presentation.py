"""Public result contract. Raw detector fields are retained for expert evidence."""
from typing import Any, Literal
from pydantic import BaseModel, Field

VerdictKey = Literal['looks_ai','looks_edited','scam','risky','no_clear_signs','not_sure','incomplete']
SignalLevel = Literal['low','medium','high']


class PublicReason(BaseModel):
    text: str
    evidence_id: str = Field(pattern=r'^/')


class SignalCheck(BaseModel):
    name: str
    state: Literal['warning', 'uncertain', 'incomplete']
    text: str
    evidence_id: str = Field(pattern=r'^/')


class LocalizedResult(BaseModel):
    verdict_key: VerdictKey
    headline: str
    reasons: list[PublicReason]
    next_steps: list[str]
    level: dict[str, SignalLevel]
    limits: list[str]
    checks: list[SignalCheck] = Field(default_factory=list)


class ResultPresentation(LocalizedResult):
    details: dict[str, Any]
    locales: dict[Literal['en','hi'], LocalizedResult]
    contract_version: Literal['1'] = '1'
