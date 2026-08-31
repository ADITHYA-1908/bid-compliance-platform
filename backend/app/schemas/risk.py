"""
Risk Schemas for Part 7C & Part 7D: Deterministic Risk & Overrides Engine
Defines Pydantic request and response schemas for Risk APIs.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RiskContributionResponse(BaseModel):
    """Auditable itemized contribution of a single risk indicator."""
    model_config = ConfigDict(from_attributes=True)

    indicator: str
    name: str
    raw_value: str
    normalized_value: Decimal
    weight: Decimal
    weighted_contribution: Decimal
    reason: str


class RiskOverrideResponse(BaseModel):
    """Auditable record of an applied deterministic risk override or floor."""
    model_config = ConfigDict(from_attributes=True)

    rule_code: Optional[str] = None
    override_type: str
    trigger: str
    source_result_id: Optional[str] = None
    source_requirement_id: Optional[str] = None

    previous_score: Optional[Decimal] = None
    new_score: Optional[Decimal] = None

    previous_level: Optional[str] = None
    new_level: Optional[str] = None

    risk_floor: Optional[Decimal] = None
    risk_increment: Optional[Decimal] = None
    minimum_level: Optional[str] = None

    reason: str
    severity: str


class RiskFeaturesResponse(BaseModel):
    """Extracted feature vector metrics used in risk evaluation."""
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


class BidRiskAssessmentResponse(BaseModel):
    """
    Complete risk assessment snapshot response containing:
    - Part 7C Base Risk (pure mathematical calculation)
    - Part 7D Adjusted Risk (post deterministic overrides & floors)
    - Completeness & Provisional flags
    - Feature vector & itemized indicator contributions
    - Applied override audit history and summary reasons
    """
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    bid_id: str
    tender_id: str
    risk_version: int
    risk_formula_version: str
    override_formula_version: str = "v1"

    # Part 7C: Mathematical Base Risk
    base_risk_score: Optional[Decimal] = None
    base_risk_level: Optional[str] = None

    # Part 7D: Deterministic Adjusted Risk
    adjusted_risk_score: Optional[Decimal] = None
    adjusted_risk_level: Optional[str] = None

    # Overrides Applied
    override_applied: bool = False
    override_count: int = 0
    applied_overrides: List[RiskOverrideResponse] = Field(default_factory=list)

    # Operational & Readiness Flags
    risk_complete: bool
    is_provisional: bool
    human_review_required: bool

    # Signals & Explanations
    features: RiskFeaturesResponse
    contributions: List[RiskContributionResponse] = Field(default_factory=list)
    summary_reasons: List[str] = Field(default_factory=list)
    calculation_details: Dict[str, Any] = Field(default_factory=dict)
    calculated_at: Optional[datetime] = None
