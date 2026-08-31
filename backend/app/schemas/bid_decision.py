"""
Pydantic Schemas for Part 8D: Final Human Decision Workflow
Defines request and response structures for decision readiness checks,
authoritative decision recording, and historical decision versioning.
"""

import enum
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BidDecisionStatusEnum(str, enum.Enum):
    """
    Status values for human-controlled final bid decisions.
    """
    NOT_DECIDED = "NOT_DECIDED"
    UNDER_REVIEW = "UNDER_REVIEW"
    QUALIFIED = "QUALIFIED"
    DISQUALIFIED = "DISQUALIFIED"


class DisqualificationReasonCategoryEnum(str, enum.Enum):
    """
    Standardized classification categories for disqualification rationales.
    """
    MANDATORY_REQUIREMENT_FAILURE = "MANDATORY_REQUIREMENT_FAILURE"
    CRITICAL_REQUIREMENT_FAILURE = "CRITICAL_REQUIREMENT_FAILURE"
    DOCUMENT_INSUFFICIENT = "DOCUMENT_INSUFFICIENT"
    REGISTRATION_NON_COMPLIANCE = "REGISTRATION_NON_COMPLIANCE"
    FINANCIAL_NON_COMPLIANCE = "FINANCIAL_NON_COMPLIANCE"
    TECHNICAL_NON_COMPLIANCE = "TECHNICAL_NON_COMPLIANCE"
    INTEGRITY_CONCERN = "INTEGRITY_CONCERN"
    OTHER = "OTHER"


class DecisionReadinessResponse(BaseModel):
    """
    Comprehensive decision readiness assessment evaluated by backend safeguards.
    """
    can_qualify: bool = Field(..., description="Whether the bid satisfies all preconditions for qualification")
    can_disqualify: bool = Field(True, description="Whether the bid may be disqualified with recorded justification")
    can_defer: bool = Field(True, description="Whether the bid decision may be deferred or kept under review")
    blocking_reasons: List[str] = Field(default_factory=list, description="List of strict blockers preventing qualification")
    warnings: List[str] = Field(default_factory=list, description="Advisory warnings requiring officer acknowledgement")

    # Evaluation state metrics
    evaluation_complete: bool = Field(..., description="Whether all requirements have completed compliance determinations")
    evaluation_version: int = Field(1, description="Latest compliance evaluation version")
    open_review_count: int = Field(0, description="Total active unresolved human review items")
    critical_open_review_count: int = Field(0, description="Critical unresolved human review items")
    mandatory_failures_count: int = Field(0, description="Number of failed mandatory requirements")
    critical_failures_count: int = Field(0, description="Number of failed critical requirements")
    has_pending_critical_verifications: bool = Field(False, description="Whether critical third-party verifications are pending")

    # Snapshot metrics
    overall_score: Optional[float] = Field(None, description="Current deterministic compliance score percentage")
    adjusted_risk_level: Optional[str] = Field(None, description="Adjusted risk level (LOW, MEDIUM, HIGH, CRITICAL)")
    adjusted_risk_score: Optional[float] = Field(None, description="Adjusted risk score value (0-100)")
    ai_recommendation: Optional[str] = Field(None, description="Advisory AI recommendation outcome")

    # Staleness flags
    is_score_stale: bool = Field(False, description="Whether the scoring snapshot is out of date")
    is_risk_stale: bool = Field(False, description="Whether the risk snapshot is out of date")
    is_ai_stale: bool = Field(False, description="Whether the AI recommendation is out of date")


class RecordBidDecisionRequest(BaseModel):
    """
    Payload submitted by an authorized Procurement Officer to record or change a bid decision.
    """
    decision: BidDecisionStatusEnum = Field(..., description="Decision outcome (QUALIFIED, DISQUALIFIED, UNDER_REVIEW)")
    reason: str = Field(..., min_length=10, max_length=2000, description="Mandatory factual justification for the decision")
    decision_summary: Optional[str] = Field(None, max_length=500, description="Optional brief summary")
    category: Optional[DisqualificationReasonCategoryEnum] = Field(None, description="Standardized disqualification category if applicable")


class DecidedByProfileSummary(BaseModel):
    """
    Identity summary of the officer who recorded the decision.
    """
    profile_id: uuid.UUID
    full_name: str
    role_name: str
    organization_name: Optional[str] = None


class EvaluationSnapshotReference(BaseModel):
    """
    Provenance references capturing the exact evaluation state reviewed by the officer.
    """
    evaluation_version: int
    score_snapshot_id: Optional[uuid.UUID] = None
    overall_score: Optional[float] = None
    risk_snapshot_id: Optional[uuid.UUID] = None
    adjusted_risk_score: Optional[float] = None
    adjusted_risk_level: Optional[str] = None
    ai_recommendation_id: Optional[uuid.UUID] = None
    ai_recommendation: Optional[str] = None


class BidDecisionResponse(BaseModel):
    """
    Authoritative response representing a bid's current qualification decision.
    """
    id: uuid.UUID
    organization_id: uuid.UUID
    tender_id: uuid.UUID
    bid_id: uuid.UUID
    bid_number: Optional[str] = None
    bidder_name: Optional[str] = None
    decision: BidDecisionStatusEnum
    reason: str
    decision_summary: Optional[str] = None
    category: Optional[str] = None
    decided_at: datetime
    decision_version: int
    decided_by: DecidedByProfileSummary
    is_current: bool
    is_stale: bool
    stale_reason: Optional[str] = None
    snapshot_reference: EvaluationSnapshotReference
    readiness: Optional[DecisionReadinessResponse] = None


class BidDecisionHistoryItem(BaseModel):
    """
    Historical decision record for auditability and timeline inspection.
    """
    id: uuid.UUID
    decision_version: int
    decision: BidDecisionStatusEnum
    reason: str
    decision_summary: Optional[str] = None
    category: Optional[str] = None
    decided_at: datetime
    decided_by_name: str
    decided_by_role: str
    is_current: bool
    is_stale: bool
    stale_reason: Optional[str] = None
    superseded_at: Optional[datetime] = None
