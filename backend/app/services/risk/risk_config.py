"""
Centralized Risk Configuration & Thresholds for Part 7C: Deterministic Risk Assessment Engine
Defines risk levels, indicator weights, threshold boundaries, rounding precision,
and formula versioning under Development Risk Model v1.
"""

from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, Tuple


class RiskLevel(str, Enum):
    """Canonical risk classification levels for bid compliance risk."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskIndicator(str, Enum):
    """Deterministic risk factor indicators evaluated in Part 7C."""
    COMPLIANCE_DEFICIT = "COMPLIANCE_DEFICIT"
    RULE_FAILURES = "RULE_FAILURES"
    REVIEW_UNCERTAINTY = "REVIEW_UNCERTAINTY"
    PENDING_UNCERTAINTY = "PENDING_UNCERTAINTY"
    MANDATORY_FAILURES = "MANDATORY_FAILURES"
    INTEGRITY_CONCERNS = "INTEGRITY_CONCERNS"


class RiskConfig:
    """
    Centralized configuration container for deterministic base risk calculation.
    All weights and thresholds are Decimal-safe and fully auditable.
    """

    # Formula Versioning for auditability
    RISK_FORMULA_VERSION: str = "v1"
    MODEL_NAME: str = "Development Risk Model v1"

    # Decimal Precision & Rounding Policy
    INTERNAL_PRECISION: Decimal = Decimal("0.0001")
    DISPLAY_PRECISION: Decimal = Decimal("0.01")
    ROUNDING_MODE: str = ROUND_HALF_UP

    # -------------------------------------------------------------------------
    # Baseline Risk Indicator Weights (Development Risk Model v1)
    # Total Maximum Score = 40 + 20 + 15 + 10 + 10 + 5 = 100.00
    # -------------------------------------------------------------------------
    WEIGHT_COMPLIANCE_DEFICIT: Decimal = Decimal("40.0000")
    WEIGHT_RULE_FAILURES: Decimal = Decimal("20.0000")
    WEIGHT_REVIEW_UNCERTAINTY: Decimal = Decimal("15.0000")
    WEIGHT_PENDING_UNCERTAINTY: Decimal = Decimal("10.0000")
    WEIGHT_MANDATORY_FAILURES: Decimal = Decimal("10.0000")
    WEIGHT_INTEGRITY_CONCERNS: Decimal = Decimal("5.0000")

    # -------------------------------------------------------------------------
    # Risk Level Threshold Boundaries
    # [0.00, 25.00)   -> LOW
    # [25.00, 50.00)  -> MEDIUM
    # [50.00, 75.00)  -> HIGH
    # [75.00, 100.00] -> CRITICAL
    # -------------------------------------------------------------------------
    THRESHOLD_LOW_MAX: Decimal = Decimal("25.00")
    THRESHOLD_MEDIUM_MAX: Decimal = Decimal("50.00")
    THRESHOLD_HIGH_MAX: Decimal = Decimal("75.00")
    THRESHOLD_CRITICAL_MAX: Decimal = Decimal("100.00")

    @classmethod
    def clamp_score(cls, score: Decimal) -> Decimal:
        """Clamps score within strictly valid [0.00, 100.00] bounds."""
        if score < Decimal("0.00"):
            return Decimal("0.00")
        if score > Decimal("100.00"):
            return Decimal("100.00")
        return score.quantize(cls.DISPLAY_PRECISION, rounding=cls.ROUNDING_MODE)

    @classmethod
    def get_risk_level(cls, score: Decimal) -> RiskLevel:
        """
        Determines the risk classification level from a numerical score using
        exact half-open boundary intervals:
          0.00 <= score < 25.00  -> LOW
          25.00 <= score < 50.00 -> MEDIUM
          50.00 <= score < 75.00 -> HIGH
          75.00 <= score <= 100.00 -> CRITICAL
        """
        clamped = cls.clamp_score(score)

        if clamped < cls.THRESHOLD_LOW_MAX:
            return RiskLevel.LOW
        if clamped < cls.THRESHOLD_MEDIUM_MAX:
            return RiskLevel.MEDIUM
        if clamped < cls.THRESHOLD_HIGH_MAX:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL

    @classmethod
    def get_indicator_metadata(cls, indicator: RiskIndicator) -> Dict[str, str]:
        """Provides human-readable display names and descriptions for risk indicators."""
        meta = {
            RiskIndicator.COMPLIANCE_DEFICIT: {
                "name": "Compliance Deficit",
                "description": "Risk contribution from unearned requirement compliance weight.",
            },
            RiskIndicator.RULE_FAILURES: {
                "name": "Rule Failures",
                "description": "Normalized failure rate across all applicable requirements.",
            },
            RiskIndicator.REVIEW_UNCERTAINTY: {
                "name": "Review Uncertainty",
                "description": "Uncertainty penalty arising from unresolved human review items.",
            },
            RiskIndicator.PENDING_UNCERTAINTY: {
                "name": "Pending Uncertainty",
                "description": "Uncertainty penalty arising from unexecuted verification checks.",
            },
            RiskIndicator.MANDATORY_FAILURES: {
                "name": "Mandatory Failures",
                "description": "Additional risk penalty for non-compliance with mandatory clauses.",
            },
            RiskIndicator.INTEGRITY_CONCERNS: {
                "name": "Integrity & Identity Concerns",
                "description": "Signal from debarment, blacklisting, or cross-document identity mismatches.",
            },
        }
        return meta.get(indicator, {"name": indicator.value, "description": ""})
