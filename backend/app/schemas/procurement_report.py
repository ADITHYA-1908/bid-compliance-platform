"""
Pydantic Schemas for Part 8E Procurement Reports (Tender Summary & Bid Evaluation)
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReportTenderInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tender_id: uuid.UUID
    tender_number: str
    title: str
    status: str
    organization_name: str
    category: Optional[str] = None
    procurement_type: Optional[str] = None
    currency: str = "INR"
    estimated_value: Optional[float] = None
    published_at: Optional[datetime] = None
    submission_end_date: Optional[datetime] = None


class ReportBidderInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: uuid.UUID
    name: str
    pan_number: Optional[str] = None
    gstin: Optional[str] = None
    udyam_number: Optional[str] = None
    business_type: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None


class ReportBidInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bid_id: uuid.UUID
    bid_number: str
    status: str
    submitted_at: Optional[datetime] = None
    quoted_amount: Optional[float] = None
    currency: str = "INR"
    is_shortlisted: bool = False
    shortlist_reason: Optional[str] = None


class ReportComplianceSection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evaluation_complete: bool = False
    evaluation_version: int = 1
    total_requirements: int = 0
    passed_count: int = 0
    failed_count: int = 0
    review_count: int = 0
    pending_count: int = 0
    not_applicable_count: int = 0
    mandatory_failures_count: int = 0
    critical_failures_count: int = 0


class ReportScoreSection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overall_compliance_score: Optional[float] = None
    score_type: str = "FINAL"
    scoring_complete: bool = False
    earned_weight: float = 0.0
    eligible_weight: float = 0.0
    category_scores: Dict[str, Any] = Field(default_factory=dict)
    scoring_version: int = 1
    is_stale: bool = False


class ReportRiskSection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    base_risk_score: Optional[float] = None
    base_risk_level: Optional[str] = None
    adjusted_risk_score: Optional[float] = None
    adjusted_risk_level: Optional[str] = None
    override_applied: bool = False
    applied_overrides: List[Dict[str, Any]] = Field(default_factory=list)
    risk_complete: bool = False
    risk_version: int = 1
    is_stale: bool = False


class ReportDefectItem(BaseModel):
    requirement_code: str
    requirement_name: str
    category: str
    compliance_status: str
    is_mandatory: bool
    is_critical: bool
    reason: Optional[str] = None


class ReportHumanReviewItem(BaseModel):
    id: uuid.UUID
    review_type: str
    severity: str
    status: str
    resolution: Optional[str] = None
    reason: Optional[str] = None
    resolved_by_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    notes_count: int = 0


class ReportAISection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recommendation: Optional[str] = None
    recommendation_reason: Optional[str] = None
    summary: Optional[str] = None
    strengths: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    guardrail_applied: bool = False
    guardrail_reason: Optional[str] = None
    confidence_label: Optional[str] = None
    is_stale: bool = False
    advisory_disclaimer: str = (
        "AI evaluation recommendation is strictly advisory assistance grounded in deterministic facts. "
        "AI does not make qualification, selection, or tender award decisions."
    )


class ReportFinalDecisionSection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision: str = "NOT_DECIDED"
    reason: Optional[str] = None
    decision_summary: Optional[str] = None
    category: Optional[str] = None
    decided_by_name: Optional[str] = None
    decided_by_role: Optional[str] = None
    decided_at: Optional[datetime] = None
    decision_version: int = 0
    is_current: bool = True
    is_stale: bool = False
    stale_reason: Optional[str] = None


class ReportDecisionHistoryItem(BaseModel):
    decision_version: int
    decision: str
    reason: str
    decision_summary: Optional[str] = None
    decided_by_name: Optional[str] = None
    decided_at: datetime
    is_current: bool
    superseded_at: Optional[datetime] = None


class ReportAuditEventSummaryItem(BaseModel):
    event_type: str
    event_label: str
    action: str
    actor_name: str
    actor_source: str
    summary: str
    created_at: datetime


class BidEvaluationReportResponse(BaseModel):
    """
    Comprehensive, auditable Bid Compliance & Decision Dossier.
    """
    model_config = ConfigDict(from_attributes=True)

    report_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    report_title: str = "Bid Compliance Verification & Evaluation Report"
    generated_at: datetime
    generated_by: str

    tender: ReportTenderInfo
    bidder: ReportBidderInfo
    bid: ReportBidInfo

    compliance: ReportComplianceSection
    score: ReportScoreSection
    risk: ReportRiskSection

    mandatory_failures: List[ReportDefectItem] = Field(default_factory=list)
    critical_findings: List[ReportDefectItem] = Field(default_factory=list)
    human_reviews: List[ReportHumanReviewItem] = Field(default_factory=list)

    ai_recommendation: Optional[ReportAISection] = None
    final_human_decision: ReportFinalDecisionSection
    decision_history: List[ReportDecisionHistoryItem] = Field(default_factory=list)

    stale_warnings: List[str] = Field(default_factory=list)
    mock_verification_disclaimer: Optional[str] = None
    audit_timeline: List[ReportAuditEventSummaryItem] = Field(default_factory=list)


class TenderSummaryBidItem(BaseModel):
    bid_id: uuid.UUID
    bid_number: str
    bidder_name: str
    quoted_amount: Optional[float] = None
    compliance_score: Optional[float] = None
    adjusted_risk_level: Optional[str] = None
    human_decision_status: str
    is_shortlisted: bool = False
    critical_defects_count: int = 0
    open_reviews_count: int = 0


class TenderReportResponse(BaseModel):
    """
    Comprehensive Tender Evaluation Summary Report for Procurement Officers & Review Committees.
    """
    model_config = ConfigDict(from_attributes=True)

    report_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    report_title: str = "Tender Compliance Evaluation Summary Report"
    generated_at: datetime
    generated_by: str

    tender: ReportTenderInfo

    # Key Aggregates
    total_bids_submitted: int = 0
    total_bids_evaluated: int = 0
    total_qualified: int = 0
    total_disqualified: int = 0
    total_under_review: int = 0
    total_not_decided: int = 0
    total_shortlisted: int = 0

    # Risk Distribution
    risk_distribution: Dict[str, int] = Field(
        default_factory=lambda: {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    )

    # Compliance Overview
    average_compliance_score: Optional[float] = None
    total_critical_defects: int = 0
    total_open_reviews: int = 0

    # Itemized Bids
    bids: List[TenderSummaryBidItem] = Field(default_factory=list)
