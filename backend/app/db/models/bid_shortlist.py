"""
Bid Shortlist Model for Part 8B: Bid Comparison & Shortlisting View
Stores human-controlled shortlisting state, timestamp, and optional rationale
for bid proposals evaluated by authorized Procurement Officers.
"""

import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.bid import Bid
    from app.db.models.tender import Tender
    from app.db.models.user import User


class BidShortlist(Base, TimestampMixin):
    """
    Persists human-controlled shortlisting decisions by Procurement Officers.
    Shortlisting indicates selection for further detailed evaluation/review.
    It does NOT represent final qualification, award, or winner selection.
    """
    __tablename__ = "bid_shortlists"
    __table_args__ = (
        UniqueConstraint("tender_id", "bid_id", name="uq_bid_shortlists_tender_bid"),
        Index("ix_bid_shortlists_tender_id", "tender_id"),
        Index("ix_bid_shortlists_bid_id", "bid_id"),
        Index("ix_bid_shortlists_shortlisted", "tender_id", "is_shortlisted"),
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
    )

    bid_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=False,
    )

    is_shortlisted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="True if proposal is currently shortlisted by procurement officer",
    )

    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Procurement officer rationale for shortlisting or removing from shortlist",
    )

    shortlisted_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID of Procurement Officer who set current shortlist state",
    )

    # Relationships
    tender: Mapped["Tender"] = relationship("Tender")
    bid: Mapped["Bid"] = relationship("Bid")
    shortlisted_by: Mapped[Optional["User"]] = relationship("User")
