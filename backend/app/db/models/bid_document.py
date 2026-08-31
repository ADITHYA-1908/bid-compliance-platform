"""
Bid Document Model for Part 3D: Bid Document Upload
Represents uploaded statutory, technical, and commercial compliance evidence
attached to a specific Bid and optionally linked to a TenderRequirement.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.bid import Bid
    from app.db.models.profile import Profile
    from app.db.models.tender_requirement import TenderRequirement
    from app.db.models.document_processing import DocumentProcessing
    from app.db.models.verification_record import VerificationRecord


class BidDocument(Base, TimestampMixin):
    """
    Bid Document entity representing a file uploaded by a bidder as part of their
    bid package (e.g. GST certificate, PAN, OEM authorization, financial statement).
    Stored in private storage with metadata in PostgreSQL.
    """
    __tablename__ = "bid_documents"

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
    tender_requirement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tender_requirements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    uploaded_by_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    document_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    document_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="UPLOADED",
        server_default="UPLOADED",
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
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
        back_populates="documents",
    )
    tender_requirement: Mapped[Optional["TenderRequirement"]] = relationship(
        "TenderRequirement",
        back_populates="bid_documents",
    )
    uploaded_by_profile: Mapped["Profile"] = relationship(
        "Profile",
        back_populates="uploaded_documents",
    )
    processing: Mapped[Optional["DocumentProcessing"]] = relationship(
        "DocumentProcessing",
        back_populates="bid_document",
        uselist=False,
        cascade="all, delete-orphan",
    )
    verifications: Mapped[List["VerificationRecord"]] = relationship(
        "VerificationRecord",
        back_populates="bid_document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BidDocument(id={self.id}, bid_id={self.bid_id}, type='{self.document_type}', filename='{self.original_filename}', active={self.is_active})>"
