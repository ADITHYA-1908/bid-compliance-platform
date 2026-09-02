"""
Verification Record Model for Part 5A
Tracks individual claim verification results, match classifications, source telemetry,
evidence payloads, retry history, and execution state.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin
from app.verification.types import (
    VerificationClaimSource,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationTriggerSource,
)

if TYPE_CHECKING:
    from app.db.models.bid import Bid
    from app.db.models.bid_document import BidDocument
    from app.db.models.document_processing import DocumentProcessing
    from app.db.models.profile import Profile


class VerificationRecord(Base, TimestampMixin):
    """
    VerificationRecord entity storing the execution result and evidence of a claim verification.
    Traceable to Bid, BidDocument, and DocumentProcessing records.
    """
    __tablename__ = "verification_records"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bid_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bid_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_processing_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_processing.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    verification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default=VerificationStatus.PENDING,
        server_default=VerificationStatus.PENDING,
        nullable=False,
        index=True,
    )

    source_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        default=VerificationSourceType.MOCK,
        server_default=VerificationSourceType.MOCK,
        nullable=False,
    )
    claim_source: Mapped[str] = mapped_column(
        String(50),
        default=VerificationClaimSource.DOCUMENT,
        server_default=VerificationClaimSource.DOCUMENT,
        nullable=False,
    )

    claimed_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    verified_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    match_status: Mapped[str] = mapped_column(
        String(50),
        default=VerificationMatchStatus.UNKNOWN,
        server_default=VerificationMatchStatus.UNKNOWN,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        server_default="1.0",
        nullable=False,
    )

    evidence: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    request_payload: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    response_payload: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    error_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )

    triggered_by_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    trigger_source: Mapped[str] = mapped_column(
        String(50),
        default=VerificationTriggerSource.SYSTEM,
        server_default=VerificationTriggerSource.SYSTEM,
        nullable=False,
    )

    verification_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verification_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        index=True,
    )

    # Relationships
    bid: Mapped["Bid"] = relationship(
        "Bid",
        back_populates="verifications",
    )
    bid_document: Mapped[Optional["BidDocument"]] = relationship(
        "BidDocument",
        back_populates="verifications",
    )
    document_processing: Mapped[Optional["DocumentProcessing"]] = relationship(
        "DocumentProcessing",
        back_populates="verifications",
    )
    triggered_by_profile: Mapped[Optional["Profile"]] = relationship(
        "Profile",
        foreign_keys=[triggered_by_profile_id],
    )

    def __repr__(self) -> str:
        return (
            f"<VerificationRecord(id={self.id}, type='{self.verification_type}', "
            f"status='{self.verification_status}', match='{self.match_status}', "
            f"source='{self.source_name}', claim='{self.claimed_value}')>"
        )
