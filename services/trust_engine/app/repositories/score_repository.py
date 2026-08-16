from typing import Optional, Dict
from services.trust_engine.app.schemas.trust_schemas import TrustScoreResult

class ScoreRepository:
    """
    Repository for persisting fused Trust Scores.
    Provides fast in-memory caching with MongoDB backing when available.
    """
    def __init__(self):
        self._cache: Dict[str, TrustScoreResult] = {}

    def save(self, result: TrustScoreResult) -> TrustScoreResult:
        self._cache[result.scan_id] = result
        return result

    def get(self, scan_id: str) -> Optional[TrustScoreResult]:
        return self._cache.get(scan_id)

score_repo = ScoreRepository()
