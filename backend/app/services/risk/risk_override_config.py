"""
Centralized Risk Override Configuration for Part 7D: Critical Overrides & Risk Adjustment Logic
Defines deterministic override types, minimum risk floors, risk penalties, priority ordering,
and formula versioning under Deterministic Risk Override Model v1.
"""

from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from app.services.risk.risk_config import RiskConfig, RiskLevel


class RiskOverrideType(str, Enum):
    """Canonical override mechanisms for deterministic risk adjustment."""
    RISK_FLOOR = "RISK_FLOOR"
    RISK_INCREMENT = "RISK_INCREMENT"
    LEVEL_FLOOR = "LEVEL_FLOOR"
    SCORE_CAP = "SCORE_CAP"
    REVIEW_ESCALATION = "REVIEW_ESCALATION"


class OverrideSeverity(str, Enum):
    """Severity classification for applied risk overrides."""
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskOverrideConfig:
    """
    Centralized configuration container for deterministic risk overrides and floors.
    All floors, increments, and thresholds are Decimal-safe and fully auditable.
    """

    OVERRIDE_FORMULA_VERSION: str = "v1"
    MODEL_NAME: str = "Deterministic Risk Override Model v1"

    # -------------------------------------------------------------------------
    # Confirmed Exclusion / Integrity Overrides (Development Baseline Policy)
    # Note: These values represent development risk calibration baselines.
    # -------------------------------------------------------------------------
    # Confirmed Active Blacklisting (Tender requirement FAIL on NOT_BLACKLISTED)
    FLOOR_ACTIVE_BLACKLISTING: Decimal = Decimal("90.00")
    LEVEL_ACTIVE_BLACKLISTING: RiskLevel = RiskLevel.CRITICAL

    # Confirmed Active Debarment at tender date
    FLOOR_ACTIVE_DEBARMENT: Decimal = Decimal("90.00")
    LEVEL_ACTIVE_DEBARMENT: RiskLevel = RiskLevel.CRITICAL

    # -------------------------------------------------------------------------
    # Critical Requirement Failure Floors (is_critical=True, status=FAIL)
    # -------------------------------------------------------------------------
    # Single Critical Requirement Failure (e.g. Critical OEM, BIS, Statutory, Financial, etc.)
    FLOOR_SINGLE_CRITICAL_FAIL: Decimal = Decimal("70.00")
    LEVEL_SINGLE_CRITICAL_FAIL: RiskLevel = RiskLevel.HIGH

    # Multiple Critical Requirement Failures (>= 2 critical fails)
    FLOOR_MULTIPLE_CRITICAL_FAIL: Decimal = Decimal("80.00")
    LEVEL_MULTIPLE_CRITICAL_FAIL: RiskLevel = RiskLevel.CRITICAL
    MULTIPLE_CRITICAL_THRESHOLD: int = 2

    # -------------------------------------------------------------------------
    # Severe Identifier / Structural Identity Mismatches
    # -------------------------------------------------------------------------
    # Severe exact structural PAN/GST or PAN/CIN mismatch
    FLOOR_STRONG_IDENTITY_MISMATCH: Decimal = Decimal("75.00")
    LEVEL_STRONG_IDENTITY_MISMATCH: RiskLevel = RiskLevel.HIGH

    # Non-critical / partial mismatch adjustments (e.g. address or name variations)
    INCREMENT_PARTIAL_IDENTITY_MISMATCH: Decimal = Decimal("5.00")

    # -------------------------------------------------------------------------
    # Critical Review & Pending Uncertainty Escalations
    # -------------------------------------------------------------------------
    # Critical rule in REVIEW state (provisional uncertainty)
    FLOOR_CRITICAL_REVIEW: Decimal = Decimal("50.00")
    LEVEL_CRITICAL_REVIEW: RiskLevel = RiskLevel.HIGH

    # -------------------------------------------------------------------------
    # Override Priority & Execution Ordering
    # Standard Order:
    #   1. Start with base risk score
    #   2. Apply cumulative increments and clamp [0.00, 100.00]
    #   3. Apply highest applicable minimum risk floor: max(score, highest_floor)
    #   4. Clamp to [0.00, 100.00]
    #   5. Recalculate level using centralized 7C thresholds
    #   6. Apply minimum level floor (never downgrade risk)
    # -------------------------------------------------------------------------
    EXECUTION_ORDER_DESCRIPTION: str = (
        "Base Score -> Increments -> Highest Applicable Floor -> "
        "Score Clamp [0..100] -> Threshold Recalculation -> Level Floor Enforcement"
    )

    @classmethod
    def compare_risk_levels(cls, level_a: RiskLevel, level_b: RiskLevel) -> int:
        """
        Compares two risk levels by severity:
        LOW < MEDIUM < HIGH < CRITICAL.
        Returns:
          -1 if level_a < level_b
           0 if level_a == level_b
           1 if level_a > level_b
        """
        hierarchy = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }
        val_a = hierarchy.get(level_a, 0)
        val_b = hierarchy.get(level_b, 0)
        if val_a < val_b:
            return -1
        elif val_a > val_b:
            return 1
        return 0

    @classmethod
    def max_risk_level(cls, level_a: Optional[RiskLevel], level_b: Optional[RiskLevel]) -> Optional[RiskLevel]:
        """Returns the higher of two risk levels."""
        if level_a is None:
            return level_b
        if level_b is None:
            return level_a
        return level_a if cls.compare_risk_levels(level_a, level_b) >= 0 else level_b
