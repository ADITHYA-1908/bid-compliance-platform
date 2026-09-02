"""
Bid Score Snapshot Model for Part 7A
Stores immutable versioned scoring foundation snapshots for Bids against published Tenders.
Captures resolved weights, normalized contributions, earned/eligible weight totals,
readiness flags, and detailed telemetry without early risk or recommendation decisions.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Uuid,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.bid import Bid
    from app.db.models.tender import Tender


class ScoringStatusEnum:
    READY = "READY"
    INCOMPLETE = "INCOMPLETE"
    BLOCKED = "BLOCKED"
    NO_SCORABLE_REQUIREMENTS = "NO_SCORABLE_REQUIREMENTS"

    ALL = [READY, INCOMPLETE, BLOCKED, NO_SCORABLE_REQUIREMENTS]


class BidScoreSnapshot(Base, TimestampMixin):
    """
    Persists deterministic scoring calculation snapshots for audit and history tracking.
    """
    __tablename__ = "bid_score_snapshots"
    __table_args__ = (
        Index("ix_bid_score_snapshots_bid_current", "bid_id", "is_current"),
        Index("ix_bid_score_snapshots_tender_id", "tender_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bid_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=False,
    )
    tender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Scoring Meta & Formula Versioning
    scoring_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    scoring_formula_version: Mapped[str] = mapped_column(
        String(50),
        default="v1.0",
        nullable=False,
    )
    scoring_status: Mapped[str] = mapped_column(
        String(50),
        default=ScoringStatusEnum.INCOMPLETE,
        nullable=False,
    )
    scoring_complete: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    human_review_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Weight Totals (Decimal precision 10,4)
    earned_weight: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    eligible_weight: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=4),
        default=Decimal("0.0000"),
        nullable=False,
    )

    # Rule Counts Summary
    total_rules_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    passed_rules_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_rules_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    review_rules_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    pending_rules_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    not_applicable_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    mandatory_failures_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    critical_failures_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Granular Rule Contributions & Detailed Audit Telemetry
    rule_contributions: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    category_scores: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    calculation_details: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Computed Overall Compliance Score (Part 7B)
    overall_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=True,
    )
    is_provisional: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )


    # Audit & Versioning
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    bid: Mapped["Bid"] = relationship("Bid")
    tender: Mapped["Tender"] = relationship("Tender")

    def __repr__(self) -> str:
        return (
            f"<BidScoreSnapshot(id={self.id}, bid_id={self.bid_id}, "
            f"version={self.scoring_version}, status='{self.scoring_status}', "
            f"earned={self.earned_weight}/{self.eligible_weight}, is_current={self.is_current})>"
        )
