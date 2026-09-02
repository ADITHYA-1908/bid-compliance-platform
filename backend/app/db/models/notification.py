"""
Notification Database Model
Part 12 — Notification Center for BidVerify AI
Multi-tenant, role-aware, event-driven in-app notifications.
"""

from datetime import datetime, timezone
import enum
import uuid
from typing import Optional, Dict, Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class NotificationSeverity(str, enum.Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class NotificationType(str, enum.Enum):
    BID_SUBMITTED = "BID_SUBMITTED"
    DOCUMENT_MISSING = "DOCUMENT_MISSING"
    DOCUMENT_QUALITY_REVIEW_REQUIRED = "DOCUMENT_QUALITY_REVIEW_REQUIRED"
    DOCUMENT_PROCESSING_COMPLETED = "DOCUMENT_PROCESSING_COMPLETED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    VERIFICATION_REVIEW_REQUIRED = "VERIFICATION_REVIEW_REQUIRED"
    DUPLICATE_DOCUMENT_ALERT = "DUPLICATE_DOCUMENT_ALERT"
    COMPLIANCE_REVIEW_REQUIRED = "COMPLIANCE_REVIEW_REQUIRED"
    CRITICAL_RISK_DETECTED = "CRITICAL_RISK_DETECTED"
    CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"
    CLARIFICATION_RECEIVED = "CLARIFICATION_RECEIVED"
    CERTIFICATE_EXPIRING = "CERTIFICATE_EXPIRING"
    CERTIFICATE_EXPIRED = "CERTIFICATE_EXPIRED"
    CERTIFICATE_VALIDITY_REVIEW_REQUIRED = "CERTIFICATE_VALIDITY_REVIEW_REQUIRED"
    TENDER_DEADLINE_APPROACHING = "TENDER_DEADLINE_APPROACHING"
    BULK_EVALUATION_COMPLETED = "BULK_EVALUATION_COMPLETED"
    BULK_EVALUATION_PARTIAL = "BULK_EVALUATION_PARTIAL"
    FINAL_DECISION_RECORDED = "FINAL_DECISION_RECORDED"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Target recipient profile and tenant organization (strictly scoped)
    recipient_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional business entity references
    tender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    bid_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Categorization and content
    notification_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, default=NotificationSeverity.INFO.value, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # State & action
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    action_url = Column(String(512), nullable=True)

    # Deduplication key to prevent spamming
    dedupe_key = Column(String(255), nullable=True, index=True)
    metadata_json = Column(JSONB, nullable=True)

    # Relationships
    recipient_profile = relationship("Profile", foreign_keys=[recipient_profile_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    tender = relationship("Tender", foreign_keys=[tender_id])
    bid = relationship("Bid", foreign_keys=[bid_id])
    document = relationship("BidDocument", foreign_keys=[document_id])

    __table_args__ = (
        Index("ix_notifications_recipient_unread_created", "recipient_profile_id", "is_read", "created_at"),
    )

    def mark_read(self) -> None:
        self.is_read = True
        self.read_at = datetime.now(timezone.utc)

    def mark_unread(self) -> None:
        self.is_read = False
        self.read_at = None

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type={self.notification_type}, severity={self.severity}, recipient={self.recipient_profile_id}, is_read={self.is_read})>"
