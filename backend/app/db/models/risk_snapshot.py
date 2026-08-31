"""
Bid Risk Snapshot Model for Part 7C & 7D: Deterministic Risk & Overrides Engine
Stores immutable versioned base and adjusted risk snapshots for Bids against published Tenders.
Captures extracted feature vectors, itemized auditable risk contributions, summary reasons,
deterministic base risk, and applied critical override history without AI recommendations.
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


class BidRiskSnapshot(Base, TimestampMixin):
    """
    Persists deterministic base and adjusted risk calculation snapshots for audit, telemetry, and history tracking.
    """
    __tablename__ = "bid_risk_snapshots"
    __table_args__ = (
        Index("ix_bid_risk_snapshots_bid_current", "bid_id", "is_current"),
        Index("ix_bid_risk_snapshots_tender_id", "tender_id"),
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
        index=True,
    )
    tender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Risk Snapshot Meta & Formula Versioning
    risk_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    risk_formula_version: Mapped[str] = mapped_column(
        String(50),
        default="v1",
        nullable=False,
    )
    override_formula_version: Mapped[str] = mapped_column(
        String(50),
        default="v1",
        nullable=False,
    )

    # Computed Deterministic Base Risk (0.00 - 100.00)
    base_risk_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=True,
    )
    base_risk_level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Computed Deterministic Adjusted Risk (0.00 - 100.00) post-overrides
    adjusted_risk_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=True,
    )
    adjusted_risk_level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Overrides State
    override_applied: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    override_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    applied_overrides: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Completeness & Readiness Flags
    risk_complete: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_provisional: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    human_review_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Granular Feature Snapshot, Itemized Contributions & Summaries
    feature_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    contribution_details: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    summary_reasons: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    calculation_details: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
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
            f"<BidRiskSnapshot(id={self.id}, bid_id={self.bid_id}, "
            f"version={self.risk_version}, base_score={self.base_risk_score}, "
            f"adjusted_score={self.adjusted_risk_score}, "
            f"adjusted_level='{self.adjusted_risk_level}', is_current={self.is_current})>"
        )
