"""
Pydantic Schemas for Part 8C: Human Review & Evidence Inspection Workflow
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReviewTypeEnum(str, Enum):
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"
    VERIFICATION_REVIEW = "VERIFICATION_REVIEW"
    DOCUMENT_REVIEW = "DOCUMENT_REVIEW"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PENDING_SOURCE = "PENDING_SOURCE"
    CRITICAL_REVIEW = "CRITICAL_REVIEW"
    OTHER = "OTHER"


class ReviewSeverityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReviewStatusEnum(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    SUPERSEDED = "SUPERSEDED"


class ReviewResolutionEnum(str, Enum):
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    ESCALATED = "ESCALATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# -------------------------------------------------------------------------
# Queue Item & KPI Schemas
# -------------------------------------------------------------------------

class ReviewQueueItemResponse(BaseModel):
    id: uuid.UUID
    tender_id: uuid.UUID
    tender_number: str
    tender_title: str
    bid_id: uuid.UUID
    bid_number: str
    bidder_name: str
    bidder_pan: Optional[str] = None
    bidder_gstin: Optional[str] = None
    requirement_code: Optional[str] = None
    requirement_name: Optional[str] = None
    category: Optional[str] = None
    review_type: ReviewTypeEnum
    severity: ReviewSeverityEnum
    status: ReviewStatusEnum
    source_type: str
    title: str
    reason: str
    is_critical: bool = False
    is_mandatory: bool = False
    claimed_by_name: Optional[str] = None
    resolved_by_name: Optional[str] = None
    resolution: Optional[ReviewResolutionEnum] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class ReviewQueueKPIs(BaseModel):
    total_open: int = 0
    critical_open: int = 0
    in_review: int = 0
    resolved_today: int = 0
    escalated: int = 0


class ReviewQueueResponse(BaseModel):
    kpis: ReviewQueueKPIs
    items: List[ReviewQueueItemResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


# -------------------------------------------------------------------------
# Notes & Actions
# -------------------------------------------------------------------------

class ReviewNoteItem(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    author_email: str
    author_role: str
    note_text: str
    created_at: datetime


class AddReviewNoteRequest(BaseModel):
    note_text: str = Field(..., min_length=2, max_length=5000, description="Reviewer remark or audit note")


class ResolveReviewRequest(BaseModel):
    resolution: ReviewResolutionEnum
    reason: str = Field(..., min_length=5, max_length=5000, description="Mandatory factual justification for review resolution")
    effective_compliance_status: Optional[str] = Field(
        None,
        description="Optional effective compliance status (PASS, FAIL, NOT_APPLICABLE) when resolving a compliance discrepancy",
    )


class StartReviewRequest(BaseModel):
    pass


# -------------------------------------------------------------------------
# Evidence Inspection Detail Sections
# -------------------------------------------------------------------------

class ReviewRequirementSection(BaseModel):
    requirement_id: Optional[uuid.UUID] = None
    code: str
    name: str
    category: Optional[str] = None
    requirement_type: Optional[str] = None
    expected_value: Any = None
    operator: Optional[str] = None
    is_mandatory: bool = True
    is_critical: bool = False
    weight: Optional[float] = 10.0


class ReviewActualEvidenceSection(BaseModel):
    claimed_value: Any = None
    verified_value: Any = None
    match_status: Optional[str] = None
    extraction_confidence: Optional[float] = None
    field_confidence: Optional[str] = None
    compliance_status: Optional[str] = None
    system_reason: Optional[str] = None


class ReviewSourceDocumentSection(BaseModel):
    document_id: Optional[uuid.UUID] = None
    document_name: Optional[str] = None
    document_type: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    processing_status: Optional[str] = None
    page_number: Optional[int] = None
    extracted_text_snippet: Optional[str] = None
    ocr_confidence: Optional[float] = None
    secure_download_url: Optional[str] = None


class ReviewVerificationEvidenceSection(BaseModel):
    verification_record_id: Optional[uuid.UUID] = None
    verification_type: Optional[str] = None
    verification_status: Optional[str] = None
    registry_status: Optional[str] = None
    match_status: Optional[str] = None
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    is_mock: bool = False
    is_available: bool = True
    confidence_score: Optional[float] = None
    evidence_payload: Optional[Dict[str, Any]] = None


class ReviewComplianceEvidenceSection(BaseModel):
    compliance_result_id: Optional[uuid.UUID] = None
    compliance_status: Optional[str] = None
    expected_value: Any = None
    actual_value: Any = None
    operator: Optional[str] = None
    reason: Optional[str] = None
    is_mandatory: bool = True
    is_critical: bool = False
    effective_compliance_status: Optional[str] = None
    human_resolution: Optional[str] = None
    human_reason: Optional[str] = None


class CrossDocumentComparisonRow(BaseModel):
    field_name: str
    pan_doc_value: Optional[str] = None
    gst_doc_value: Optional[str] = None
    mca_doc_value: Optional[str] = None
    other_doc_value: Optional[str] = None
    is_match: bool = True
    discrepancy_note: Optional[str] = None


class ReviewAICitationItem(BaseModel):
    citation_id: str
    source_type: str
    title: str
    page: Optional[int] = None
    snippet: Optional[str] = None


class ReviewAIExplanationSection(BaseModel):
    recommendation: Optional[str] = None
    confidence_label: Optional[str] = None
    summary: Optional[str] = None
    strengths: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    review_items: List[str] = Field(default_factory=list)
    grounded_citations: List[ReviewAICitationItem] = Field(default_factory=list)
    disclaimer: str = "AI explanation is advisory assistance and does not resolve this review item or make procurement decisions."
    is_stale: bool = False
    is_available: bool = True


# -------------------------------------------------------------------------
# Full Review Detail Workspace Response
# -------------------------------------------------------------------------

class ReviewDetailResponse(BaseModel):
    review_id: uuid.UUID
    organization_id: uuid.UUID
    tender_id: uuid.UUID
    tender_number: str
    tender_title: str
    bid_id: uuid.UUID
    bid_number: str
    bidder_legal_name: str
    trade_name: Optional[str] = None
    bidder_pan: Optional[str] = None
    bidder_gstin: Optional[str] = None
    review_type: ReviewTypeEnum
    severity: ReviewSeverityEnum
    status: ReviewStatusEnum
    title: str
    reason: str
    system_finding: Dict[str, Any] = Field(default_factory=dict)
    resolution: Optional[ReviewResolutionEnum] = None
    resolution_reason: Optional[str] = None
    effective_compliance_status: Optional[str] = None
    claimed_by_name: Optional[str] = None
    claimed_by_id: Optional[uuid.UUID] = None
    resolved_by_name: Optional[str] = None
    resolved_by_id: Optional[uuid.UUID] = None
    resolved_at: Optional[datetime] = None
    version: int = 1
    created_at: datetime
    updated_at: datetime

    requirement_section: Optional[ReviewRequirementSection] = None
    actual_evidence_section: Optional[ReviewActualEvidenceSection] = None
    source_document_section: Optional[ReviewSourceDocumentSection] = None
    verification_section: Optional[ReviewVerificationEvidenceSection] = None
    compliance_section: Optional[ReviewComplianceEvidenceSection] = None
    cross_document_section: List[CrossDocumentComparisonRow] = Field(default_factory=list)
    ai_explanation_section: Optional[ReviewAIExplanationSection] = None
    notes_history: List[ReviewNoteItem] = Field(default_factory=list)
