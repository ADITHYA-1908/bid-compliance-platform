"""
AI Recommendation Model for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
Persists non-binding AI-generated recommendations, executive summaries, strengths, concerns,
review items, grounded evidence citations, limitations, and staleness tracking for Bid submissions.
"""

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.bid import Bid
    from app.db.models.risk_snapshot import BidRiskSnapshot
    from app.db.models.score_snapshot import BidScoreSnapshot


class AIRecommendationRecord(Base, TimestampMixin):
    """
    Stores an evidence-grounded, non-binding AI evaluation recommendation and executive summary
    for a specific Bid submission, tied to upstream compliance, score, and risk snapshots.
    """
    __tablename__ = "ai_recommendations"
    __table_args__ = (
        Index("ix_ai_recommendations_bid_stale", "bid_id", "is_stale"),
        Index("ix_ai_recommendations_bid_created", "bid_id", "created_at"),
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

    score_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_score_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )

    risk_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_risk_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )

    compliance_evaluation_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    recommendation: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="PROCEED, PROCEED_WITH_REVIEW, REVIEW_REQUIRED, DO_NOT_PROCEED_WITHOUT_REVIEW, INSUFFICIENT_EVIDENCE",
    )

    recommendation_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Direct, factual rationale for the recommendation based on deterministic evidence",
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Executive summary of the proposal's compliance, risk, and verification posture",
    )

    strengths: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Itemized key strengths grounded in verified facts",
    )

    concerns: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Itemized concerns, failures, and risks",
    )

    review_items: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Items requiring manual Procurement Officer inspection",
    )

    evidence_refs: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="List of validated evidence citations (source_type, source_id, title, page, summary)",
    )

    limitations: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Factual boundaries and data limitations (e.g. pending checks, mock sources)",
    )

    confidence_label: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="MEDIUM",
        comment="HIGH, MEDIUM, LOW based on evidence completeness",
    )

    model_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="local_fallback",
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="default",
    )

    prompt_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="v1",
    )

    guardrail_applied: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if recommendation was adjusted by deterministic guardrail",
    )

    guardrail_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    is_stale: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if upstream compliance/score/risk has changed since generation",
    )

    # Relationships
    bid: Mapped["Bid"] = relationship("Bid")
    score_snapshot: Mapped[Optional["BidScoreSnapshot"]] = relationship("BidScoreSnapshot")
    risk_snapshot: Mapped[Optional["BidRiskSnapshot"]] = relationship("BidRiskSnapshot")
