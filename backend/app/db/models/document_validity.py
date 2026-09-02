"""
Document Validity Record Database Model
Part 14 — Certificate Validity Monitoring for BidVerify AI
Tracks certificate expiry/validity dates, deterministically calculated statuses,
days until expiry, provenance evidence snippets, quality impacts, and replacement history.
"""

from datetime import datetime, timezone
import enum
import uuid
from typing import Optional, Dict, Any

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class ValidityStatus(str, enum.Enum):
    VALID = "VALID"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    NO_EXPIRY = "NO_EXPIRY"
    UNKNOWN = "UNKNOWN"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ValidityDateSource(str, enum.Enum):
    STRUCTURED_EXTRACTION = "STRUCTURED_EXTRACTION"
    VERIFICATION_ADAPTER = "VERIFICATION_ADAPTER"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class DocumentValidityRecord(Base, TimestampMixin):
    """
    Persistent record representing the validity lifecycle state of a BidDocument certificate.
    Maintains historical provenance, evidence snippets, confidence scores, and replacement status.
    """
    __tablename__ = "document_validity_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bid_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bids.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Document & Certificate Classification
    document_type = Column(String(100), nullable=False, default="OTHER", index=True)

    # Extracted Validity Dates
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True, index=True)

    # Calculated Status & Countdown
    validity_status = Column(
        String(50),
        nullable=False,
        default=ValidityStatus.UNKNOWN.value,
        index=True,
    )
    days_until_expiry = Column(Integer, nullable=True)

    # Extraction Provenance & Evidence
    date_source = Column(
        String(50),
        nullable=False,
        default=ValidityDateSource.STRUCTURED_EXTRACTION.value,
    )
    source_page = Column(Integer, nullable=True)
    source_text = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=1.0)

    # Versioning & Replacement
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    submission_validity_status = Column(String(50), nullable=True)

    # Monitoring Telemetry
    last_checked_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    next_check_at = Column(DateTime(timezone=True), nullable=True)

    # Extensible Metadata (threshold configs, quality adjustments, verification comparisons)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    document = relationship("BidDocument", foreign_keys=[document_id], lazy="joined")
    bid = relationship("Bid", foreign_keys=[bid_id], lazy="select")
    organization = relationship("Organization", foreign_keys=[organization_id], lazy="select")

    __table_args__ = (
        Index("ix_doc_validity_org_status", "organization_id", "validity_status"),
        Index("ix_doc_validity_bid_current", "bid_id", "is_current"),
        Index("ix_doc_validity_expiry_status", "expiry_date", "validity_status"),
    )
