"""
Clarification Request & Response Models for Part 16
Provides auditable communication, evidence clarification, and document replacement
workflows between Procurement Officers and Bidders.
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
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.organization import Organization
    from app.db.models.tender import Tender
    from app.db.models.bid import Bid
    from app.db.models.profile import Profile
    from app.db.models.bid_document import BidDocument
    from app.db.models.tender_requirement import TenderRequirement
    from app.db.models.tender_requirement_version import TenderRequirementVersion
    from app.db.models.verification_record import VerificationRecord
    from app.db.models.compliance_result import ComplianceResult
    from app.db.models.human_review import HumanReviewItem
    from app.db.models.document_duplicate_match import DocumentDuplicateMatch


class ClarificationStatus:
    DRAFT = "DRAFT"
    SENT = "SENT"
    VIEWED = "VIEWED"
    RESPONDED = "RESPONDED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

    ALL = [
        DRAFT,
        SENT,
        VIEWED,
        RESPONDED,
        UNDER_REVIEW,
        RESOLVED,
        CLOSED,
        EXPIRED,
        CANCELLED,
    ]


class ClarificationPriority:
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"

    ALL = [LOW, NORMAL, HIGH, URGENT]


class ClarificationType:
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    UNCLEAR_DOCUMENT = "UNCLEAR_DOCUMENT"
    LOW_OCR_CONFIDENCE = "LOW_OCR_CONFIDENCE"
    VERIFICATION_MISMATCH = "VERIFICATION_MISMATCH"
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"
    DUPLICATE_REUSE_EXPLANATION = "DUPLICATE_REUSE_EXPLANATION"
    CERTIFICATE_VALIDITY = "CERTIFICATE_VALIDITY"
    CONFLICTING_INFORMATION = "CONFLICTING_INFORMATION"
    ADDITIONAL_EVIDENCE = "ADDITIONAL_EVIDENCE"
    OTHER = "OTHER"

    ALL = [
        MISSING_DOCUMENT,
        UNCLEAR_DOCUMENT,
        LOW_OCR_CONFIDENCE,
        VERIFICATION_MISMATCH,
        COMPLIANCE_REVIEW,
        DUPLICATE_REUSE_EXPLANATION,
        CERTIFICATE_VALIDITY,
        CONFLICTING_INFORMATION,
        ADDITIONAL_EVIDENCE,
        OTHER,
    ]


class ClarificationRequest(Base, TimestampMixin):
    """
    Clarification Request entity initiated by a Procurement Officer toward a Bidder
    to resolve discrepancies, obtain replacement scans, or request supporting evidence.
    """
    __tablename__ = "clarification_requests"
    __table_args__ = (
        Index("ix_clarification_requests_tender_status", "tender_id", "status"),
        Index("ix_clarification_requests_bid_status", "bid_id", "status"),
        Index("ix_clarification_requests_tender_org", "tender_organization_id", "status"),
        Index("ix_clarification_requests_bidder_org", "bidder_organization_id", "status"),
        Index("ix_clarification_requests_due_date", "due_date"),
        Index("ix_clarification_requests_type", "clarification_type"),
        Index("ix_clarification_requests_priority", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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
    tender_organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bidder_organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_by_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assigned_bidder_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Core message content
    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    clarification_type: Mapped[str] = mapped_column(
        String(50),
        default=ClarificationType.OTHER,
        server_default=ClarificationType.OTHER,
        nullable=False,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        default=ClarificationPriority.NORMAL,
        server_default=ClarificationPriority.NORMAL,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default=ClarificationStatus.SENT,
        server_default=ClarificationStatus.SENT,
        nullable=False,
        index=True,
    )

    # Lifecycle Timestamps & Deadlines
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    viewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Related Context Links (Provenance)
    related_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_requirement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tender_requirements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_rule_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tender_requirement_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_rule_version_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    related_verification_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("verification_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_compliance_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("compliance_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_review_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("human_review_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_duplicate_match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_duplicate_matches.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Resolution Metadata
    resolved_by_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolution_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # Relationships
    tender: Mapped["Tender"] = relationship(
        "Tender",
        foreign_keys=[tender_id],
        lazy="select",
    )
    bid: Mapped["Bid"] = relationship(
        "Bid",
        foreign_keys=[bid_id],
        lazy="select",
    )
    tender_organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[tender_organization_id],
        lazy="select",
    )
    bidder_organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[bidder_organization_id],
        lazy="select",
    )
    created_by: Mapped["Profile"] = relationship(
        "Profile",
        foreign_keys=[created_by_profile_id],
        lazy="joined",
    )
    assigned_bidder: Mapped[Optional["Profile"]] = relationship(
        "Profile",
        foreign_keys=[assigned_bidder_profile_id],
        lazy="select",
    )
    resolved_by: Mapped[Optional["Profile"]] = relationship(
        "Profile",
        foreign_keys=[resolved_by_profile_id],
        lazy="select",
    )
    related_document: Mapped[Optional["BidDocument"]] = relationship(
        "BidDocument",
        foreign_keys=[related_document_id],
        lazy="select",
    )
    related_requirement: Mapped[Optional["TenderRequirement"]] = relationship(
        "TenderRequirement",
        foreign_keys=[related_requirement_id],
        lazy="select",
    )
    related_rule_version: Mapped[Optional["TenderRequirementVersion"]] = relationship(
        "TenderRequirementVersion",
        foreign_keys=[related_rule_version_id],
        lazy="select",
    )
    related_verification_record: Mapped[Optional["VerificationRecord"]] = relationship(
        "VerificationRecord",
        foreign_keys=[related_verification_record_id],
        lazy="select",
    )
    related_compliance_result: Mapped[Optional["ComplianceResult"]] = relationship(
        "ComplianceResult",
        foreign_keys=[related_compliance_result_id],
        lazy="select",
    )
    related_review_item: Mapped[Optional["HumanReviewItem"]] = relationship(
        "HumanReviewItem",
        foreign_keys=[related_review_item_id],
        lazy="select",
    )
    related_duplicate_match: Mapped[Optional["DocumentDuplicateMatch"]] = relationship(
        "DocumentDuplicateMatch",
        foreign_keys=[related_duplicate_match_id],
        lazy="select",
    )
    responses: Mapped[List["ClarificationResponse"]] = relationship(
        "ClarificationResponse",
        back_populates="clarification_request",
        cascade="all, delete-orphan",
        order_by="ClarificationResponse.created_at.asc()",
        lazy="selectin",
    )


class ClarificationResponse(Base, TimestampMixin):
    """
    Response record provided by a Bidder answering a Clarification Request.
    Supports textual explanation, supporting evidence, and replacement document linkage.
    """
    __tablename__ = "clarification_responses"
    __table_args__ = (
        Index("ix_clarification_responses_request_id", "clarification_request_id"),
        Index("ix_clarification_responses_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    clarification_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("clarification_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    responded_by_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    response_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    attached_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_replacement_document: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    replaced_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    clarification_request: Mapped["ClarificationRequest"] = relationship(
        "ClarificationRequest",
        back_populates="responses",
        foreign_keys=[clarification_request_id],
        lazy="select",
    )
    responded_by: Mapped["Profile"] = relationship(
        "Profile",
        foreign_keys=[responded_by_profile_id],
        lazy="joined",
    )
    attached_document: Mapped[Optional["BidDocument"]] = relationship(
        "BidDocument",
        foreign_keys=[attached_document_id],
        lazy="select",
    )
    replaced_document: Mapped[Optional["BidDocument"]] = relationship(
        "BidDocument",
        foreign_keys=[replaced_document_id],
        lazy="select",
    )
