"""
Pydantic API Schemas for Part 7A Scoring Foundation
Response models for scoring readiness, weight totals, rule contributions, and audit snapshots.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RuleScoreContributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    compliance_result_id: Optional[str] = None
    requirement_id: str
    requirement_code: str
    requirement_name: str
    category: str
    status: str

    weight: Decimal
    score_factor: Decimal
    earned_weight: Decimal
    eligible_weight: Decimal

    is_mandatory: bool
    is_critical: bool
    critical_failure: bool

    excluded_from_score: bool
    exclusion_reason: Optional[str] = None


class ScoringReadinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scoring_ready: bool
    scoring_complete: bool
    human_review_required: bool
    scoring_status: str

    total_rules: int
    passed_rules: int
    failed_rules: int
    review_rules: int
    pending_rules: int
    not_applicable_rules: int
    mandatory_failures: int
    critical_failures: int


class CategoryScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    display_name: str

    total_rules: int
    passed_rules: int
    failed_rules: int
    review_rules: int
    pending_rules: int
    not_applicable_rules: int
    mandatory_failures: int
    critical_failures: int

    earned_weight: Decimal
    eligible_weight: Decimal

    raw_score: Optional[Decimal] = None
    display_score: Optional[Decimal] = None

    scoring_complete: bool
    human_review_required: bool
    is_provisional: bool
    rule_contributions: List[RuleScoreContributionResponse] = Field(default_factory=list)


class BidScoringFoundationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bid_id: str
    tender_id: str
    scoring_version: int
    scoring_formula_version: str

    readiness: ScoringReadinessResponse
    earned_weight: Decimal
    eligible_weight: Decimal

    overall_score: Optional[Decimal] = None
    is_provisional: bool = False

    category_scores: Dict[str, CategoryScoreResponse] = Field(default_factory=dict)
    rule_contributions: List[RuleScoreContributionResponse] = Field(default_factory=list)
    calculation_details: Dict[str, Any] = Field(default_factory=dict)
    calculated_at: Optional[datetime] = None

