"""
Risk Domain Models & Data Structures for Part 7C & 7D: Deterministic Risk & Overrides Engine
Typed Pydantic models for internal risk pipeline, feature representation, auditable contributions,
risk overrides, and adjusted risk assessment results.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.services.risk.risk_config import RiskIndicator, RiskLevel
from app.services.risk.risk_override_config import OverrideSeverity, RiskOverrideType


class RiskContribution(BaseModel):
    """
    Auditable record of an individual risk indicator's contribution to the base risk score.
    """
    model_config = ConfigDict(from_attributes=True)

    indicator: RiskIndicator
    name: str
    raw_value: str
    normalized_value: Decimal
    weight: Decimal
    weighted_contribution: Decimal
    reason: str


class RiskOverride(BaseModel):
    """
    Auditable record of a single deterministic risk override or floor applied in Part 7D.
    """
    model_config = ConfigDict(from_attributes=True)

    rule_code: Optional[str] = None
    override_type: RiskOverrideType
    trigger: str
    source_result_id: Optional[str] = None
    source_requirement_id: Optional[str] = None

    previous_score: Optional[Decimal] = None
    new_score: Optional[Decimal] = None

    previous_level: Optional[str] = None
    new_level: Optional[str] = None

    risk_floor: Optional[Decimal] = None
    risk_increment: Optional[Decimal] = None
    minimum_level: Optional[RiskLevel] = None

    reason: str
    severity: OverrideSeverity = OverrideSeverity.HIGH


class RiskFeatures(BaseModel):
    """
    Normalized feature vector extracted from Part 6 compliance findings and Part 7B score snapshots.
    """
    model_config = ConfigDict(from_attributes=True)

    overall_compliance_score: Optional[Decimal] = None
    total_rules: int = 0
    applicable_rules: int = 0
    passed_count: int = 0
    fail_count: int = 0
    review_count: int = 0
    pending_count: int = 0
    not_applicable_count: int = 0

    mandatory_rules_count: int = 0
    mandatory_failure_count: int = 0
    critical_failure_count: int = 0

    integrity_rules_count: int = 0
    integrity_fail_count: int = 0
    integrity_review_count: int = 0
    cross_document_mismatch_count: int = 0
    low_confidence_count: int = 0

    scoring_complete: bool = True
    human_review_required: bool = False


class RiskAssessment(BaseModel):
    """
    Full risk assessment result for a bid submission containing both Part 7C Base Risk
    and Part 7D Adjusted Risk after deterministic critical overrides.
    """
    model_config = ConfigDict(from_attributes=True)

    bid_id: str
    tender_id: str
    risk_version: int = 1
    risk_formula_version: str = "v1"
    override_formula_version: str = "v1"

    # Part 7C: Pure Mathematical Base Risk
    base_risk_score: Optional[Decimal] = None
    base_risk_level: Optional[RiskLevel] = None

    # Part 7D: Deterministic Adjusted Risk post-overrides
    adjusted_risk_score: Optional[Decimal] = None
    adjusted_risk_level: Optional[RiskLevel] = None

    # Overrides State
    override_applied: bool = False
    override_count: int = 0
    applied_overrides: List[RiskOverride] = Field(default_factory=list)

    # Readiness & Operational Flags
    risk_complete: bool = True
    is_provisional: bool = False
    human_review_required: bool = False

    # Auditable Signals & Reasons
    features: RiskFeatures
    contributions: List[RiskContribution] = Field(default_factory=list)
    summary_reasons: List[str] = Field(default_factory=list)
    calculation_details: Dict[str, Any] = Field(default_factory=dict)
    calculated_at: Optional[datetime] = None
