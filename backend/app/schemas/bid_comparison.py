"""
Bid Comparison and Shortlisting Schemas for Part 8B
Defines Pydantic models for comparative bid evaluation across the same tender,
category scores comparison, requirement-by-requirement determinations,
and human-controlled shortlisting actions.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BidComparisonRequest(BaseModel):
    """Payload to request side-by-side comparison of 2 to 5 submitted bids."""
    bid_ids: List[uuid.UUID] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="List of 2 to 5 unique bid UUIDs to compare",
    )


class ShortlistActionRequest(BaseModel):
    """Payload to add, update, or remove a bid from the shortlist with optional rationale."""
    reason: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Procurement officer rationale for shortlisting action",
    )


class ShortlistRecordResponse(BaseModel):
    """Response representing a bid's shortlist status."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tender_id: uuid.UUID
    bid_id: uuid.UUID
    is_shortlisted: bool
    reason: Optional[str] = None
    shortlisted_by_id: Optional[uuid.UUID] = None
    shortlisted_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CriticalFindingComparisonItem(BaseModel):
    """Itemized critical defect or finding for a compared bid."""
    model_config = ConfigDict(from_attributes=True)

    requirement_code: str
    requirement_name: str
    category: str
    compliance_status: str
    is_mandatory: bool = True
    is_critical: bool = True
    risk_override: Optional[str] = None
    finding_reason: str


class CategoryScoreComparisonValue(BaseModel):
    """Per-bid performance values for a specific requirement category."""
    model_config = ConfigDict(from_attributes=True)

    category: str
    score: Optional[float] = None
    earned_weight: float = 0.0
    eligible_weight: float = 0.0
    is_na: bool = False
    total_rules: int = 0
    passed_rules: int = 0
    failed_rules: int = 0
    review_rules: int = 0
    pending_rules: int = 0


class CategoryComparisonRow(BaseModel):
    """A single category comparison row across all compared bids."""
    model_config = ConfigDict(from_attributes=True)

    category_code: str
    display_name: str
    bid_scores: Dict[str, CategoryScoreComparisonValue] = Field(
        default_factory=dict,
        description="Map of bid_id string to category performance values",
    )
    all_match: bool = False


class RequirementBidResultItem(BaseModel):
    """Evaluation determination of a single requirement for a single bid."""
    model_config = ConfigDict(from_attributes=True)

    bid_id: uuid.UUID
    compliance_status: str = Field(
        default="NOT_EVALUATED",
        description="PASS, FAIL, REVIEW, NOT_APPLICABLE, PENDING, or NOT_EVALUATED",
    )
    actual_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    operator: Optional[str] = None
    reason: Optional[str] = None
    evidence_summary: Optional[str] = None
    has_evidence: bool = False
    source_verification_ids: List[str] = Field(default_factory=list)


class RequirementComparisonRow(BaseModel):
    """Side-by-side comparison row for a single tender requirement."""
    model_config = ConfigDict(from_attributes=True)

    requirement_id: uuid.UUID
    code: str
    name: str
    category: str
    requirement_type: str
    is_mandatory: bool = True
    is_critical: bool = False
    weight: float = 10.0
    expected_value: Optional[Any] = None
    operator: Optional[str] = None
    bid_results: Dict[str, RequirementBidResultItem] = Field(
        default_factory=dict,
        description="Map of bid_id string to requirement evaluation determination",
    )
    all_match: bool = False
    has_failure: bool = False
    has_review: bool = False
    has_critical_issue: bool = False


class BidComparisonItem(BaseModel):
    """Full comparative metrics for a single bidder in the comparison matrix."""
    model_config = ConfigDict(from_attributes=True)

    bid_id: uuid.UUID
    bid_number: str
    bidder_organization_id: uuid.UUID
    bidder_legal_name: str
    trade_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    quoted_amount: Optional[Decimal] = None
    currency: str = "INR"

    # Shortlist Status
    is_shortlisted: bool = False
    shortlist_reason: Optional[str] = None
    shortlisted_at: Optional[datetime] = None

    # Overall Compliance Score
    overall_score: Optional[float] = None
    is_score_provisional: bool = False
    scoring_complete: bool = False
    earned_weight: float = 0.0
    eligible_weight: float = 0.0

    # Risk Assessment & Overrides
    base_risk_score: Optional[float] = None
    base_risk_level: Optional[str] = None
    adjusted_risk_score: Optional[float] = None
    adjusted_risk_level: Optional[str] = None
    override_applied: bool = False
    applied_overrides: List[Dict[str, Any]] = Field(default_factory=list)
    is_risk_provisional: bool = False
    risk_complete: bool = False

    # Defects & Reviews
    mandatory_failure_count: int = 0
    mandatory_failures: List[str] = Field(default_factory=list)
    critical_failure_count: int = 0
    critical_findings: List[CriticalFindingComparisonItem] = Field(default_factory=list)
    review_count: int = 0
    review_items: List[str] = Field(default_factory=list)
    pending_count: int = 0
    pending_items: List[str] = Field(default_factory=list)

    # AI Recommendation
    ai_recommendation: Optional[str] = None
    ai_status: str = Field(default="NOT_GENERATED", description="CURRENT, STALE, UNAVAILABLE, or NOT_GENERATED")
    ai_summary: Optional[str] = None
    ai_confidence: Optional[str] = None

    # Derived Evaluation Status
    evaluation_status: str = Field(
        default="NOT_STARTED",
        description="NOT_STARTED, PROCESSING, PROVISIONAL, REVIEW_REQUIRED, EVALUATION_COMPLETE, or AI_STALE",
    )
    is_evaluation_complete: bool = False
    stale_components: List[str] = Field(default_factory=list)

    # Category Scores Mapping
    category_scores: Dict[str, CategoryScoreComparisonValue] = Field(default_factory=dict)

    # Human Decision Status (Part 8D)
    human_decision_status: str = Field(
        default="NOT_DECIDED",
        description="Authoritative human qualification decision: NOT_DECIDED, UNDER_REVIEW, QUALIFIED, DISQUALIFIED",
    )

    # Commercial Evaluation & Ranking (Tender Method Configuration)
    eligibility_status: str = Field(
        default="ELIGIBLE",
        description="ELIGIBLE, INELIGIBLE_MANDATORY_FAILED, REVIEW_REQUIRED",
    )
    commercial_rank: Optional[int] = None
    rank_label: Optional[str] = None
    is_l1: bool = False
    is_tie: bool = False
    financial_score: Optional[float] = None
    final_score: Optional[float] = None
    has_critical_blocker: bool = False
    blocker_reason: Optional[str] = None
    commercial_explanation: Optional[str] = None


class ComparisonHighlights(BaseModel):
    """Informational markers for prominent comparison metrics (non-binding)."""
    model_config = ConfigDict(from_attributes=True)

    highest_compliance_score_bid_id: Optional[uuid.UUID] = None
    lowest_risk_score_bid_id: Optional[uuid.UUID] = None
    lowest_quoted_amount_bid_id: Optional[uuid.UUID] = None
    top_ranked_bid_id: Optional[uuid.UUID] = None


class BidComparisonResponse(BaseModel):
    """Complete response payload for a side-by-side tender bid comparison session."""
    model_config = ConfigDict(from_attributes=True)

    tender_id: uuid.UUID
    tender_number: str
    tender_title: str
    tender_status: str
    procurement_organization_name: str
    evaluation_method: str = "L1_LOWEST_COMPLIANT_BID"
    technical_weight: Optional[float] = 70.0
    financial_weight: Optional[float] = 30.0
    submission_end_date: Optional[datetime] = None
    total_compared_bids: int = 0
    bids: List[BidComparisonItem] = Field(default_factory=list)
    categories: List[CategoryComparisonRow] = Field(default_factory=list)
    requirements: List[RequirementComparisonRow] = Field(default_factory=list)
    highlights: ComparisonHighlights = Field(default_factory=ComparisonHighlights)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

