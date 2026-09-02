"""
Human Review & Evidence Inspection Models for Part 8C
Represents human review queue items, multi-source evidence snapshots,
audit logs, and reviewer notes for flagged bid submissions and requirement discrepancies.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.organization import Organization
    from app.db.models.tender import Tender
    from app.db.models.bid import Bid
    from app.db.models.tender_requirement import TenderRequirement
    from app.db.models.compliance_result import ComplianceResult
    from app.db.models.verification_record import VerificationRecord
    from app.db.models.bid_document import BidDocument
    from app.db.models.profile import Profile


class ReviewType:
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"
    VERIFICATION_REVIEW = "VERIFICATION_REVIEW"
    DOCUMENT_REVIEW = "DOCUMENT_REVIEW"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PENDING_SOURCE = "PENDING_SOURCE"
    CRITICAL_REVIEW = "CRITICAL_REVIEW"
    POTENTIAL_DOCUMENT_REUSE = "POTENTIAL_DOCUMENT_REUSE"
    POOR_DOCUMENT_QUALITY = "POOR_DOCUMENT_QUALITY"
    OTHER = "OTHER"

    ALL = [
        COMPLIANCE_REVIEW,
        VERIFICATION_REVIEW,
        DOCUMENT_REVIEW,
        IDENTITY_MISMATCH,
        LOW_CONFIDENCE,
        PENDING_SOURCE,
        CRITICAL_REVIEW,
        POTENTIAL_DOCUMENT_REUSE,
        POOR_DOCUMENT_QUALITY,
        OTHER,
    ]


class ReviewSeverity:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    ALL = [LOW, MEDIUM, HIGH, CRITICAL]


class ReviewStatus:
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    SUPERSEDED = "SUPERSEDED"

    ALL = [OPEN, IN_REVIEW, RESOLVED, ESCALATED, SUPERSEDED]


class ReviewResolution:
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    ESCALATED = "ESCALATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONFIRMED_BENIGN = "CONFIRMED_BENIGN"
    CONFIRMED_REUSE = "CONFIRMED_REUSE"
    DISMISSED = "DISMISSED"

    ALL = [
        CONFIRMED,
        REJECTED,
        NEEDS_MORE_EVIDENCE,
        ESCALATED,
        NOT_APPLICABLE,
        CONFIRMED_BENIGN,
        CONFIRMED_REUSE,
        DISMISSED,
    ]


class HumanReviewItem(Base, TimestampMixin):
    """
    Represents an actionable, auditable human review item requiring Procurement Officer inspection.
    Originated from compliance uncertainties, verification anomalies, low-confidence extractions,
    or cross-document mismatches.
    """
    __tablename__ = "human_review_items"
    __table_args__ = (
        Index("ix_human_review_items_org_status", "organization_id", "status"),
        Index("ix_human_review_items_tender_bid", "tender_id", "bid_id"),
        Index("ix_human_review_items_source_key", "tender_id", "bid_id", "source_type", "source_id"),
        Index("ix_human_review_items_severity", "severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Scoping & Multi-Tenancy (Strictly scoped to the Procuring Entity Organization)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bid_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional Linkage to Upstream Core Entities
    compliance_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("compliance_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tender_requirement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tender_requirements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verification_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("verification_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    bid_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Review Classification & State
    review_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ReviewType.COMPLIANCE_REVIEW,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ReviewSeverity.MEDIUM,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ReviewStatus.OPEN,
        index=True,
    )

    # Source Tracking & Idempotency
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="COMPLIANCE_RESULT",
    )
    source_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Factual Presentation
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # System Finding Snapshot (Preserved immutably for audit provenance)
    system_finding: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Resolution Metadata
    resolution: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    resolution_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    effective_compliance_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Assignment & Claim State
    claimed_by_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    tender: Mapped["Tender"] = relationship("Tender")
    bid: Mapped["Bid"] = relationship("Bid")
    compliance_result: Mapped[Optional["ComplianceResult"]] = relationship("ComplianceResult")
    tender_requirement: Mapped[Optional["TenderRequirement"]] = relationship("TenderRequirement")
    verification_record: Mapped[Optional["VerificationRecord"]] = relationship("VerificationRecord")
    bid_document: Mapped[Optional["BidDocument"]] = relationship("BidDocument")
    claimed_by_profile: Mapped[Optional["Profile"]] = relationship("Profile", foreign_keys=[claimed_by_profile_id])
    resolved_by_profile: Mapped[Optional["Profile"]] = relationship("Profile", foreign_keys=[resolved_by_profile_id])
    notes: Mapped[List["HumanReviewNote"]] = relationship(
        "HumanReviewNote",
        back_populates="review_item",
        cascade="all, delete-orphan",
        order_by="HumanReviewNote.created_at.asc()",
    )

    def __repr__(self) -> str:
        return (
            f"<HumanReviewItem(id={self.id}, tender_id={self.tender_id}, bid_id={self.bid_id}, "
            f"type='{self.review_type}', status='{self.status}', severity='{self.severity}')>"
        )


class HumanReviewNote(Base, TimestampMixin):
    """
    Stores an immutable, auditable remark/note entered by a Procurement Officer on a HumanReviewItem.
    """
    __tablename__ = "human_review_notes"
    __table_args__ = (
        Index("ix_human_review_notes_review_created", "review_item_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    review_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("human_review_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    note_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Relationships
    review_item: Mapped["HumanReviewItem"] = relationship("HumanReviewItem", back_populates="notes")
    author_profile: Mapped["Profile"] = relationship("Profile")

    def __repr__(self) -> str:
        return f"<HumanReviewNote(id={self.id}, review_item_id={self.review_item_id}, author={self.author_profile_id})>"
