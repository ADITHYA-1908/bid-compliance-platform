"""
Procurement Dashboard Schemas for Part 8A: Procurement Evaluation Dashboard Foundation
Defines Pydantic response models for high-level dashboard summaries, tender evaluation progress,
and paginated bid evaluation listings with search, filter, and sorting metadata.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProcurementDashboardCounts(BaseModel):
    """Aggregated KPI counts for the procurement officer dashboard."""
    model_config = ConfigDict(from_attributes=True)

    active_tenders: int = Field(default=0, description="Total active tenders owned by organization")
    open_tenders: int = Field(default=0, description="Tenders currently open for bidding")
    closed_under_evaluation: int = Field(default=0, description="Tenders closed and under evaluation")
    total_submitted_bids: int = Field(default=0, description="Total submitted bids across all tenders")
    bids_requiring_review: int = Field(default=0, description="Bids with human review required flags")
    critical_risk_bids: int = Field(default=0, description="Bids evaluated with CRITICAL adjusted risk")
    pending_evaluations: int = Field(default=0, description="Bids with incomplete / provisional evaluations")
    evaluation_completed_bids: int = Field(default=0, description="Bids where deterministic evaluation is complete")


class TenderEvaluationOverviewItem(BaseModel):
    """Overview of a single tender and its aggregate evaluation progress."""
    model_config = ConfigDict(from_attributes=True)

    tender_id: uuid.UUID
    tender_number: str
    title: str
    category: Optional[str] = None
    department: Optional[str] = None
    status: str
    estimated_value: Optional[Decimal] = None
    currency: str = "INR"
    submission_end_date: Optional[datetime] = None
    total_submitted_bids: int = 0
    evaluated_bids: int = 0
    pending_bids: int = 0
    review_required_bids: int = 0
    critical_risk_bids: int = 0
    evaluation_progress_percentage: float = 0.0
    created_at: datetime


class ProcurementDashboardSummaryResponse(BaseModel):
    """Top-level procurement officer dashboard response."""
    model_config = ConfigDict(from_attributes=True)

    counts: ProcurementDashboardCounts
    tenders: List[TenderEvaluationOverviewItem]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class BidEvaluationListItem(BaseModel):
    """Summarized bid evaluation item for tender bid evaluation listings."""
    model_config = ConfigDict(from_attributes=True)

    bid_id: uuid.UUID
    tender_id: uuid.UUID
    bid_number: str
    bidder_organization_id: uuid.UUID
    bidder_legal_name: str
    trade_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    quoted_amount: Optional[Decimal] = None
    currency: str = "INR"
    is_shortlisted: bool = False

    # Compliance & Scoring
    compliance_score: Optional[float] = None
    is_score_provisional: bool = False
    
    # Risk Assessment
    base_risk_score: Optional[float] = None
    base_risk_level: Optional[str] = None
    adjusted_risk_score: Optional[float] = None
    adjusted_risk_level: Optional[str] = None
    is_risk_provisional: bool = False

    # Defects & Reviews
    mandatory_failures_count: int = 0
    critical_failures_count: int = 0
    review_items_count: int = 0
    has_critical_findings: bool = False
    critical_findings_count: int = 0
    human_review_required: bool = False

    # AI Recommendation
    ai_recommendation: Optional[str] = None
    ai_status: str = Field(default="NOT_GENERATED", description="CURRENT, STALE, UNAVAILABLE, or NOT_GENERATED")
    
    # Derived Evaluation Status
    evaluation_status: str = Field(
        default="NOT_STARTED",
        description="NOT_STARTED, PROCESSING, PROVISIONAL, REVIEW_REQUIRED, EVALUATION_COMPLETE, or AI_STALE"
    )
    is_evaluation_complete: bool = False
    stale_components: List[str] = Field(default_factory=list)

    # Human Decision Status (Part 8D)
    human_decision_status: str = Field(
        default="NOT_DECIDED",
        description="Authoritative human qualification decision: NOT_DECIDED, UNDER_REVIEW, QUALIFIED, DISQUALIFIED"
    )


class TenderBidEvaluationsListResponse(BaseModel):
    """Paginated list of submitted bids for a tender with full evaluation matrices."""
    model_config = ConfigDict(from_attributes=True)

    tender_id: uuid.UUID
    tender_number: str
    tender_title: str
    tender_status: str
    procurement_organization_name: str
    submission_end_date: Optional[datetime] = None
    total_submitted_bids: int = 0
    evaluated_bids: int = 0
    
    bids: List[BidEvaluationListItem]
    total_count: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 1
    generated_at: datetime = Field(default_factory=datetime.utcnow)
