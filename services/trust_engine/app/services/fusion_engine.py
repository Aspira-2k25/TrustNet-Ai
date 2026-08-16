import os
import yaml
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from shared.schemas.detection_result import DetectionResult
from shared.schemas.evidence import EvidenceItem
from shared.constants.status import StatusEnum
from shared.logging.logger_setup import get_logger
from services.trust_engine.app.config.settings import settings
from services.trust_engine.app.schemas.trust_schemas import TrustScoreResult, RiskLevelEnum

logger = get_logger(settings.SERVICE_NAME)

class FusionEngine:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or settings.FUSION_WEIGHTS_FILE
        self.weights, self.max_ratio, self.delta_threshold, self.penalty = self._load_config()

    def _load_config(self):
        default_weights = {
            "image_deepfake": 0.25,
            "phishing": 0.25,
            "scam_message": 0.25,
            "fake_review": 0.25,
            "audio_deepfake": 0.25,
            "video_deepfake": 0.25,
            "osint": 0.25
        }
        max_ratio = 0.40
        delta_threshold = 40.0
        penalty = 0.75

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    cfg = yaml.safe_load(f) or {}
                    weights = cfg.get("weights", default_weights)
                    max_ratio = cfg.get("max_single_module_weight_ratio", max_ratio)
                    delta_threshold = cfg.get("contradiction_delta_threshold", delta_threshold)
                    penalty = cfg.get("contradiction_confidence_penalty", penalty)
                    return weights, max_ratio, delta_threshold, penalty
            except Exception as e:
                logger.warning(f"Failed to parse {self.config_path}, using defaults: {str(e)}", extra={"scan_id": "", "request_id": ""})
                
        return default_weights, max_ratio, delta_threshold, penalty

    def fuse(self, results: List[DetectionResult], scan_id: Optional[str] = None) -> TrustScoreResult:
        """
        Executes the 4-step fusion algorithm defined in Master Spec Section 5.2.
        """
        # Step 1: Normalization & Validation Pass
        valid_results = [
            r for r in results
            if r.status in (StatusEnum.SUCCESS, StatusEnum.PARTIAL_SUCCESS) and 0.0 <= r.risk_score <= 100.0
        ]

        if not valid_results:
            target_scan_id = scan_id or (results[0].scan_id if results else "unknown")
            return TrustScoreResult(
                scan_id=target_scan_id,
                trust_risk_score=0.0,
                confidence=0.0,
                risk_level=RiskLevelEnum.LOW,
                contradiction_flag=False,
                contradiction_details="No successful detector reports available for fusion.",
                reporting_modules=[],
                evidence=[],
                explanation="Scan incomplete or all detectors failed.",
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        target_scan_id = scan_id or valid_results[0].scan_id

        # Step 2: Weighted Combination (ADR 0005)
        reporting_modules = [r.module.value if hasattr(r.module, 'value') else str(r.module) for r in valid_results]
        raw_weights = [self.weights.get(m, 0.25) for m in reporting_modules]
        total_raw_weight = sum(raw_weights) or 1.0

        # Normalize weights
        norm_weights = [w / total_raw_weight for w in raw_weights]

        # Apply maximum single module weight rule if multiple modules report
        if len(valid_results) > 1 and self.max_ratio > 0:
            capped_weights = [min(w, self.max_ratio) for w in norm_weights]
            capped_sum = sum(capped_weights) or 1.0
            effective_weights = [w / capped_sum for w in capped_weights]
        else:
            effective_weights = norm_weights

        # Compute fused risk score and raw confidence
        fused_risk = sum(r.risk_score * w for r, w in zip(valid_results, effective_weights))
        fused_risk = round(max(0.0, min(100.0, fused_risk)), 2)
        raw_confidence = sum(r.confidence * w for r, w in zip(valid_results, effective_weights))
        raw_confidence = round(max(0.0, min(1.0, raw_confidence)), 2)

        # Step 3: Contradiction Detection
        contradiction_flag = False
        contradiction_details = None
        confidence = raw_confidence

        if len(valid_results) >= 2:
            scores = [r.risk_score for r in valid_results]
            delta = max(scores) - min(scores)
            if delta >= self.delta_threshold:
                contradiction_flag = True
                confidence = round(raw_confidence * self.penalty, 2)
                contradiction_details = (
                    f"Contradiction detected (score delta={delta:.1f} >= {self.delta_threshold:.1f}). "
                    f"Applied confidence penalty from {raw_confidence:.2f} to {confidence:.2f}."
                )

        # Step 4: Risk Level Mapping (Table 5.1)
        if fused_risk < 25.0:
            risk_level = RiskLevelEnum.LOW
        elif fused_risk < 50.0:
            risk_level = RiskLevelEnum.MEDIUM
        elif fused_risk < 75.0:
            risk_level = RiskLevelEnum.HIGH
        else:
            risk_level = RiskLevelEnum.CRITICAL

        # Evidence Aggregation
        all_evidence: List[EvidenceItem] = []
        for r in valid_results:
            if r.evidence:
                all_evidence.extend(r.evidence)

        # Generate Plain-Language Explanation
        modules_str = ", ".join(reporting_modules)
        explanation = (
            f"Trust Score: {fused_risk:.1f}/100 ({risk_level.value} RISK, confidence: {confidence*100:.0f}%). "
            f"Synthesized across {len(valid_results)} module(s): [{modules_str}]."
        )
        if contradiction_flag:
            explanation += f" Note: {contradiction_details}"

        return TrustScoreResult(
            scan_id=target_scan_id,
            trust_risk_score=fused_risk,
            confidence=confidence,
            risk_level=risk_level,
            contradiction_flag=contradiction_flag,
            contradiction_details=contradiction_details,
            reporting_modules=reporting_modules,
            evidence=all_evidence,
            explanation=explanation,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

fusion_engine = FusionEngine()
