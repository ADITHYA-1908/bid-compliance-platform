"""
Scoring Domain Models & Data Structures for Part 7A
Typed Pydantic models for internal scoring pipeline, rule contributions, readiness, and calculation results.
"""

import uuid
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ScoringStatus(str, Enum):
    READY = "READY"
    INCOMPLETE = "INCOMPLETE"
    BLOCKED = "BLOCKED"
    NO_SCORABLE_REQUIREMENTS = "NO_SCORABLE_REQUIREMENTS"


class RuleScoreInput(BaseModel):
    """Normalized input representation of a single requirement and its compliance result."""
    model_config = ConfigDict(from_attributes=True)

    compliance_result_id: Optional[uuid.UUID] = None
    requirement_id: uuid.UUID
    requirement_code: str
    requirement_name: str
    category: str
    status: str
    weight: Optional[Decimal] = None
    is_mandatory: bool = True
    is_critical: bool = False
    critical_failure: bool = False
    review_required: bool = False
    review_reason: Optional[str] = None


class RuleScoreContribution(BaseModel):
    """Computed score contribution for an individual requirement clause."""
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

    is_mandatory: bool = True
    is_critical: bool = False
    critical_failure: bool = False

    excluded_from_score: bool = False
    exclusion_reason: Optional[str] = None


class CategoryScore(BaseModel):
    """Aggregated compliance score and weight metrics for a specific category domain."""
    model_config = ConfigDict(from_attributes=True)

    category: str
    display_name: str

    total_rules: int = 0
    passed_rules: int = 0
    failed_rules: int = 0
    review_rules: int = 0
    pending_rules: int = 0
    not_applicable_rules: int = 0
    mandatory_failures: int = 0
    critical_failures: int = 0

    earned_weight: Decimal = Decimal("0.0000")
    eligible_weight: Decimal = Decimal("0.0000")

    raw_score: Optional[Decimal] = None
    display_score: Optional[Decimal] = None

    scoring_complete: bool = True
    human_review_required: bool = False
    is_provisional: bool = False
    rule_contributions: List[RuleScoreContribution] = Field(default_factory=list)


class ScoringReadiness(BaseModel):
    """Scoring readiness and rule status counts."""
    model_config = ConfigDict(from_attributes=True)

    scoring_ready: bool
    scoring_complete: bool
    human_review_required: bool
    scoring_status: ScoringStatus

    total_rules: int = 0
    passed_rules: int = 0
    failed_rules: int = 0
    review_rules: int = 0
    pending_rules: int = 0
    not_applicable_rules: int = 0
    mandatory_failures: int = 0
    critical_failures: int = 0


class ScoringCalculationResult(BaseModel):
    """Full foundation scoring result for a bid including category and overall scores."""
    model_config = ConfigDict(from_attributes=True)

    bid_id: str
    tender_id: str
    scoring_version: int = 1
    scoring_formula_version: str = "v1.0"

    readiness: ScoringReadiness
    earned_weight: Decimal
    eligible_weight: Decimal

    overall_score: Optional[Decimal] = None
    is_provisional: bool = False

    category_scores: Dict[str, CategoryScore] = Field(default_factory=dict)
    rule_contributions: List[RuleScoreContribution] = Field(default_factory=list)
    calculation_details: Dict[str, Any] = Field(default_factory=dict)

