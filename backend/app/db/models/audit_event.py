"""
Audit Event Model
Tamper-resistant, append-only chronological log of all significant procurement actions,
decisions, state changes, AI syntheses, human reviews, and verifications.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.organization import Organization
    from app.db.models.tender import Tender
    from app.db.models.bid import Bid
    from app.db.models.user import User
    from app.db.models.profile import Profile


class AuditActorSource:
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"
    AI_SERVICE = "AI_SERVICE"
    ALL = [HUMAN, SYSTEM, AI_SERVICE]


class AuditEventType:
    # Tender Lifecycle
    TENDER_CREATED = "TENDER_CREATED"
    TENDER_UPDATED = "TENDER_UPDATED"
    TENDER_PUBLISHED = "TENDER_PUBLISHED"
    TENDER_STATUS_CHANGED = "TENDER_STATUS_CHANGED"

    # Bid Lifecycle
    BID_CREATED = "BID_CREATED"
    BID_DOCUMENT_UPLOADED = "BID_DOCUMENT_UPLOADED"
    BID_DOCUMENT_REPLACED = "BID_DOCUMENT_REPLACED"
    BID_SUBMITTED = "BID_SUBMITTED"

    # Document AI Processing
    DOCUMENT_PROCESSING_COMPLETED = "DOCUMENT_PROCESSING_COMPLETED"
    DOCUMENT_CLASSIFIED = "DOCUMENT_CLASSIFIED"
    DOCUMENT_EXTRACTION_COMPLETED = "DOCUMENT_EXTRACTION_COMPLETED"

    # Verification Engine
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    VERIFICATION_UNAVAILABLE = "VERIFICATION_UNAVAILABLE"
    VERIFICATION_RETRIED = "VERIFICATION_RETRIED"

    # Compliance Engine
    COMPLIANCE_EVALUATED = "COMPLIANCE_EVALUATED"
    COMPLIANCE_RE_EVALUATED = "COMPLIANCE_RE_EVALUATED"

    # Score & Risk
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

    # Final Human Decision
    BID_DECISION_CREATED = "BID_DECISION_CREATED"
    BID_DECISION_SUPERSEDED = "BID_DECISION_SUPERSEDED"
    BID_DECISION_RECONFIRMED = "BID_DECISION_RECONFIRMED"
    BID_DECISION_STALE = "BID_DECISION_STALE"

    # Bulk Evaluation (Part 9)
    BULK_EVALUATION_STARTED = "BULK_EVALUATION_STARTED"
    BULK_EVALUATION_COMPLETED = "BULK_EVALUATION_COMPLETED"
    BULK_EVALUATION_PARTIALLY_COMPLETED = "BULK_EVALUATION_PARTIALLY_COMPLETED"
    BULK_EVALUATION_FAILED = "BULK_EVALUATION_FAILED"
    BULK_EVALUATION_CANCELLED = "BULK_EVALUATION_CANCELLED"
    BULK_EVALUATION_RETRY = "BULK_EVALUATION_RETRY"

    # Duplicate & Reuse Detection (Part 10)
    DOCUMENT_DUPLICATE_DETECTED = "DOCUMENT_DUPLICATE_DETECTED"
    DOCUMENT_DUPLICATE_REVIEWED = "DOCUMENT_DUPLICATE_REVIEWED"
    DOCUMENT_DUPLICATE_DISMISSED = "DOCUMENT_DUPLICATE_DISMISSED"
    DOCUMENT_REUSE_CONFIRMED = "DOCUMENT_REUSE_CONFIRMED"

    # Document Quality Diagnostics (Part 11)
    DOCUMENT_QUALITY_CHECK_COMPLETED = "DOCUMENT_QUALITY_CHECK_COMPLETED"
    DOCUMENT_QUALITY_REVIEW_REQUIRED = "DOCUMENT_QUALITY_REVIEW_REQUIRED"
    DOCUMENT_QUALITY_UNUSABLE = "DOCUMENT_QUALITY_UNUSABLE"

    # Notification Center (Part 12)
    NOTIFICATION_CREATED = "NOTIFICATION_CREATED"
    NOTIFICATION_READ = "NOTIFICATION_READ"
    NOTIFICATIONS_ALL_READ = "NOTIFICATIONS_ALL_READ"

    # Certificate Validity Monitoring (Part 14)
    CERTIFICATE_VALIDITY_CHECKED = "CERTIFICATE_VALIDITY_CHECKED"
    CERTIFICATE_EXPIRING = "CERTIFICATE_EXPIRING"
    CERTIFICATE_EXPIRED = "CERTIFICATE_EXPIRED"
    CERTIFICATE_VALIDITY_REVIEW_REQUIRED = "CERTIFICATE_VALIDITY_REVIEW_REQUIRED"
    CERTIFICATE_REPLACED = "CERTIFICATE_REPLACED"

    # Compliance Rule Version History (Part 15)
    COMPLIANCE_RULE_VERSION_CREATED = "COMPLIANCE_RULE_VERSION_CREATED"
    COMPLIANCE_RULE_CHANGED = "COMPLIANCE_RULE_CHANGED"
    COMPLIANCE_RULE_REEVALUATION_REQUESTED = "COMPLIANCE_RULE_REEVALUATION_REQUESTED"

    # Clarification Request Workflow (Part 16)
    CLARIFICATION_CREATED = "CLARIFICATION_CREATED"
    CLARIFICATION_SENT = "CLARIFICATION_SENT"
    CLARIFICATION_VIEWED = "CLARIFICATION_VIEWED"
    CLARIFICATION_RESPONDED = "CLARIFICATION_RESPONDED"
    CLARIFICATION_UNDER_REVIEW = "CLARIFICATION_UNDER_REVIEW"
    CLARIFICATION_RESOLVED = "CLARIFICATION_RESOLVED"
    CLARIFICATION_REOPENED = "CLARIFICATION_REOPENED"
    CLARIFICATION_CANCELLED = "CLARIFICATION_CANCELLED"
    CLARIFICATION_EXPIRED = "CLARIFICATION_EXPIRED"


class AuditEntityType:
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
    BULK_EVALUATION_JOB = "BULK_EVALUATION_JOB"
    DOCUMENT_DUPLICATE_MATCH = "DOCUMENT_DUPLICATE_MATCH"
    DOCUMENT_QUALITY_RESULT = "DOCUMENT_QUALITY_RESULT"
    NOTIFICATION = "NOTIFICATION"
    DOCUMENT_VALIDITY_RECORD = "DOCUMENT_VALIDITY_RECORD"
    TENDER_REQUIREMENT_VERSION = "TENDER_REQUIREMENT_VERSION"
    CLARIFICATION_REQUEST = "CLARIFICATION_REQUEST"
    CLARIFICATION_RESPONSE = "CLARIFICATION_RESPONSE"


class AuditEvent(Base):
    """
    Append-only persistent log of significant actions in the procurement lifecycle.
    Application-level users have no permissions to update or delete rows from this table.
    """
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_org_created", "organization_id", "created_at"),
        Index("ix_audit_events_tender_created", "tender_id", "created_at"),
        Index("ix_audit_events_bid_created", "bid_id", "created_at"),
        Index("ix_audit_events_type_created", "event_type", "created_at"),
        Index("ix_audit_events_actor_created", "actor_user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Multi-Tenant & Scope Isolation
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tender_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    bid_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Actor Identity & Classification
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    actor_role: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    actor_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AuditActorSource.HUMAN,
    )

    # Event Categorization
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Human-Readable Description & Structured Telemetry
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Request / Client Metadata
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Immutable UTC Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    tender: Mapped[Optional["Tender"]] = relationship("Tender")
    bid: Mapped[Optional["Bid"]] = relationship("Bid")
    actor_user: Mapped[Optional["User"]] = relationship("User")
    actor_profile: Mapped[Optional["Profile"]] = relationship("Profile")

    def __repr__(self) -> str:
        return (
            f"<AuditEvent(id={self.id}, type='{self.event_type}', "
            f"actor='{self.actor_name or self.actor_source}', created_at='{self.created_at}')>"
        )
