"""
Document Duplicate Match Model for Part 10: Duplicate / Reuse Document Detection
Stores multi-signal comparison telemetry, match classifications, structured data matches,
similarity scores, and Procurement Officer review states for documents submitted across different bidders.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.organization import Organization
    from app.db.models.tender import Tender
    from app.db.models.bid import Bid
    from app.db.models.bid_document import BidDocument
    from app.db.models.profile import Profile


class DuplicateMatchType:
    EXACT_FILE_DUPLICATE = "EXACT_FILE_DUPLICATE"
    CONTENT_DUPLICATE = "CONTENT_DUPLICATE"
    STRUCTURED_DATA_MATCH = "STRUCTURED_DATA_MATCH"
    HIGH_SIMILARITY = "HIGH_SIMILARITY"
    POSSIBLE_REUSE = "POSSIBLE_REUSE"

    ALL = [
        EXACT_FILE_DUPLICATE,
        CONTENT_DUPLICATE,
        STRUCTURED_DATA_MATCH,
        HIGH_SIMILARITY,
        POSSIBLE_REUSE,
    ]


class DuplicateMatchStatus:
    DETECTED = "DETECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONFIRMED_BENIGN = "CONFIRMED_BENIGN"
    CONFIRMED_REUSE = "CONFIRMED_REUSE"
    DISMISSED = "DISMISSED"

    ALL = [
        DETECTED,
        REVIEW_REQUIRED,
        CONFIRMED_BENIGN,
        CONFIRMED_REUSE,
        DISMISSED,
    ]


class DocumentDuplicateMatch(Base, TimestampMixin):
    """
    Represents a detected potential duplicate or reuse match between two BidDocuments
    submitted by different bidders for the same tender.
    """
    __tablename__ = "document_duplicate_matches"
    __table_args__ = (
        Index("ix_doc_dup_tender_status", "tender_id", "status"),
        Index("ix_doc_dup_org_tender", "organization_id", "tender_id"),
        Index("ix_doc_dup_pair", "document_a_id", "document_b_id", unique=True),
        Index("ix_doc_dup_bids", "bid_a_id", "bid_b_id"),
        Index("ix_doc_dup_match_type", "match_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
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

    # Document A references
    document_a_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bid_a_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Document B references
    document_b_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bid_b_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Match Telemetry & Signals
    match_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DuplicateMatchType.POSSIBLE_REUSE,
        server_default=DuplicateMatchType.POSSIBLE_REUSE,
    )
    file_hash_match: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    content_hash_match: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    structured_field_match_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0.0",
        nullable=False,
    )
    text_similarity_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0.0",
        nullable=False,
    )
    overall_confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0.0",
        nullable=False,
    )

    # Review Lifecycle
    status: Mapped[str] = mapped_column(
        String(50),
        default=DuplicateMatchStatus.REVIEW_REQUIRED,
        server_default=DuplicateMatchStatus.REVIEW_REQUIRED,
        nullable=False,
        index=True,
    )
    review_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # Detailed Evidence Breakdown
    matched_fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    evidence_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Human Review Outcome
    reviewer_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    reviewed_by_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    tender: Mapped["Tender"] = relationship("Tender")
    document_a: Mapped["BidDocument"] = relationship("BidDocument", foreign_keys=[document_a_id])
    document_b: Mapped["BidDocument"] = relationship("BidDocument", foreign_keys=[document_b_id])
    bid_a: Mapped["Bid"] = relationship("Bid", foreign_keys=[bid_a_id])
    bid_b: Mapped["Bid"] = relationship("Bid", foreign_keys=[bid_b_id])
    reviewed_by_profile: Mapped[Optional["Profile"]] = relationship("Profile", foreign_keys=[reviewed_by_profile_id])

    def __repr__(self) -> str:
        return (
            f"<DocumentDuplicateMatch(id={self.id}, tender={self.tender_id}, "
            f"type='{self.match_type}', status='{self.status}', confidence={self.overall_confidence})>"
        )
