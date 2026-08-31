"""
Bid Model
Represents a bidder application/response to a published procurement opportunity (Tender).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.organization import Organization
    from app.db.models.profile import Profile
    from app.db.models.tender import Tender
    from app.db.models.bid_document import BidDocument
    from app.db.models.verification_record import VerificationRecord



class Bid(Base, TimestampMixin):
    """
    Bid entity representing a bidder's commercial, technical, and compliance submission
    for a specific Tender. Initially created as DRAFT until finalized and submitted.
    """
    __tablename__ = "bids"
    __table_args__ = (
        UniqueConstraint(
            "tender_id",
            "bidder_organization_id",
            name="uq_bids_tender_organization",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenders.id", ondelete="RESTRICT"),
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

    bid_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        server_default="DRAFT",
        nullable=False,
        index=True,
    )

    quoted_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        server_default="INR",
        nullable=False,
    )

    technical_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    commercial_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    submitted_by_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    declaration_accepted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    declaration_accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    submission_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        index=True,
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
    tender: Mapped["Tender"] = relationship(
        "Tender",
        back_populates="bids",
    )
    bidder_organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="bids",
    )
    created_by_profile: Mapped["Profile"] = relationship(
        "Profile",
        foreign_keys=[created_by_profile_id],
        back_populates="created_bids",
    )
    submitted_by_profile: Mapped[Optional["Profile"]] = relationship(
        "Profile",
        foreign_keys=[submitted_by_profile_id],
        back_populates="submitted_bids",
    )
    documents: Mapped[List["BidDocument"]] = relationship(
        "BidDocument",
        back_populates="bid",
        cascade="all, delete-orphan",
    )
    verifications: Mapped[List["VerificationRecord"]] = relationship(
        "VerificationRecord",
        back_populates="bid",
        cascade="all, delete-orphan",
    )
