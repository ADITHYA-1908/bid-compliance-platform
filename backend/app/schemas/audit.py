"""
Pydantic Schemas for Part 8E Audit Trail & Decision History
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditActorSourceEnum(str, Enum):
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"
    AI_SERVICE = "AI_SERVICE"


class AuditEventTypeEnum(str, Enum):
    # Tender
    TENDER_CREATED = "TENDER_CREATED"
    TENDER_UPDATED = "TENDER_UPDATED"
    TENDER_PUBLISHED = "TENDER_PUBLISHED"
    TENDER_STATUS_CHANGED = "TENDER_STATUS_CHANGED"

    # Bid
    BID_CREATED = "BID_CREATED"
    BID_DOCUMENT_UPLOADED = "BID_DOCUMENT_UPLOADED"
    BID_DOCUMENT_REPLACED = "BID_DOCUMENT_REPLACED"
    BID_SUBMITTED = "BID_SUBMITTED"

    # Document AI
    DOCUMENT_PROCESSING_COMPLETED = "DOCUMENT_PROCESSING_COMPLETED"
    DOCUMENT_CLASSIFIED = "DOCUMENT_CLASSIFIED"
    DOCUMENT_EXTRACTION_COMPLETED = "DOCUMENT_EXTRACTION_COMPLETED"

    # Verification
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    VERIFICATION_UNAVAILABLE = "VERIFICATION_UNAVAILABLE"
    VERIFICATION_RETRIED = "VERIFICATION_RETRIED"

    # Compliance
    COMPLIANCE_EVALUATED = "COMPLIANCE_EVALUATED"
    COMPLIANCE_RE_EVALUATED = "COMPLIANCE_RE_EVALUATED"

    # Scoring & Risk
    SCORE_CALCULATED = "SCORE_CALCULATED"
    SCORE_RECALCULATED = "SCORE_RECALCULATED"
    RISK_CALCULATED = "RISK_CALCULATED"
    RISK_OVERRIDE_APPLIED = "RISK_OVERRIDE_APPLIED"

    # AI Recommendation
    AI_RECOMMENDATION_GENERATED = "AI_RECOMMENDATION_GENERATED"
    AI_RECOMMENDATION_REGENERATED = "AI_RECOMMENDATION_REGENERATED"
    AI_RECOMMENDATION_STALE = "AI_RECOMMENDATION_STALE"

    # Human Review
    HUMAN_REVIEW_STARTED = "HUMAN_REVIEW_STARTED"
    HUMAN_REVIEW_NOTE_ADDED = "HUMAN_REVIEW_NOTE_ADDED"
    HUMAN_REVIEW_RESOLVED = "HUMAN_REVIEW_RESOLVED"
    HUMAN_REVIEW_ESCALATED = "HUMAN_REVIEW_ESCALATED"

    # Shortlisting
    BID_SHORTLISTED = "BID_SHORTLISTED"
    BID_REMOVED_FROM_SHORTLIST = "BID_REMOVED_FROM_SHORTLIST"

    # Final Decision
    BID_DECISION_CREATED = "BID_DECISION_CREATED"
    BID_DECISION_SUPERSEDED = "BID_DECISION_SUPERSEDED"
    BID_DECISION_RECONFIRMED = "BID_DECISION_RECONFIRMED"
    BID_DECISION_STALE = "BID_DECISION_STALE"


class AuditEntityTypeEnum(str, Enum):
    TENDER = "TENDER"
    BID = "BID"
    BID_DOCUMENT = "BID_DOCUMENT"
    VERIFICATION_RECORD = "VERIFICATION_RECORD"
    COMPLIANCE_RESULT = "COMPLIANCE_RESULT"
    SCORE_SNAPSHOT = "SCORE_SNAPSHOT"
    RISK_SNAPSHOT = "RISK_SNAPSHOT"
    AI_RECOMMENDATION = "AI_RECOMMENDATION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BID_SHORTLIST = "BID_SHORTLIST"
    BID_DECISION = "BID_DECISION"


class AuditEventActorSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: Optional[uuid.UUID] = None
    profile_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    role: Optional[str] = None
    source: str = "HUMAN"


class AuditEventItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    tender_id: Optional[uuid.UUID] = None
    bid_id: Optional[uuid.UUID] = None
    tender_number: Optional[str] = None
    bid_number: Optional[str] = None
    bidder_name: Optional[str] = None

    actor: AuditEventActorSummary
    event_type: str
    event_label: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    action: str
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    created_at: datetime


class AuditKPIsResponse(BaseModel):
    total_events: int = 0
    events_today: int = 0
    decisions_recorded: int = 0
    reviews_resolved: int = 0
    ai_events: int = 0
    system_events: int = 0


class AuditListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[AuditEventItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    kpis: AuditKPIsResponse


class RecordAuditEventDTO(BaseModel):
    """Internal DTO passed to AuditService."""
    organization_id: uuid.UUID
    tender_id: Optional[uuid.UUID] = None
    bid_id: Optional[uuid.UUID] = None
    actor_user_id: Optional[uuid.UUID] = None
    actor_profile_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    actor_source: str = "HUMAN"
    event_type: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    action: str
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
