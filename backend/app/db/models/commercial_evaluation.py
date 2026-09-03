"""
Commercial Evaluation Result Model
Stores deterministic commercial bid evaluation outputs, financial scores,
QCBS final scores, ranking positions, and explainable justifications.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Dict, Any
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.tender import Tender
    from app.db.models.bid import Bid


class CommercialEvaluationResult(Base, TimestampMixin):
    """
    Stores historical and current commercial evaluation snapshots for bids against a tender.
    Supports L1 lowest compliant bid, QCBS technical + financial weighting, and custom weighted formulas.
    """
    __tablename__ = "commercial_evaluation_results"

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

    # Method applied (L1_LOWEST_COMPLIANT_BID, QCBS_TECHNICAL_FINANCIAL, CUSTOM_WEIGHTED)
    evaluation_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Eligibility Gate: ELIGIBLE, INELIGIBLE_MANDATORY_FAILED, REVIEW_REQUIRED, UNKNOWN
    eligibility_status: Mapped[str] = mapped_column(
        String(50),
        default="UNKNOWN",
        server_default="UNKNOWN",
        nullable=False,
        index=True,
    )

    # Commercial values
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

    # Evaluated scores
    technical_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    financial_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    final_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # Ranking & Labels
    commercial_rank: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        index=True,
    )
    rank_label: Mapped[str] = mapped_column(
        String(50),
        default="NOT_RANKED",
        server_default="NOT_RANKED",
        nullable=False,
    )
    is_l1: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    is_tie: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # Risk & Review Blockers
    has_critical_blocker: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    blocker_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Explainable Audit Rationale
    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    formula_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        index=True,
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    tender: Mapped["Tender"] = relationship("Tender")
    bid: Mapped["Bid"] = relationship("Bid")

    def __repr__(self) -> str:
        return (
            f"<CommercialEvaluationResult(tender_id={self.tender_id}, bid_id={self.bid_id}, "
            f"method='{self.evaluation_method}', rank='{self.rank_label}', score={self.final_score})>"
        )
