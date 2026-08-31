"""
Bid Decision Model for Part 8D: Final Human Decision Workflow
Represents authoritative, versioned human-controlled final bid qualification decisions
recorded by Procurement Officers with evaluation snapshot references and audit provenance.
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
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
    from app.db.models.organization import Organization
    from app.db.models.tender import Tender
    from app.db.models.bid import Bid
    from app.db.models.profile import Profile
    from app.db.models.score_snapshot import BidScoreSnapshot
    from app.db.models.risk_snapshot import BidRiskSnapshot
    from app.db.models.ai_recommendation import AIRecommendationRecord


class BidDecisionStatus(str, enum.Enum):
    """
    Centralized status values for human-controlled bid-level qualification decisions.
    """
    NOT_DECIDED = "NOT_DECIDED"
    UNDER_REVIEW = "UNDER_REVIEW"
    QUALIFIED = "QUALIFIED"
    DISQUALIFIED = "DISQUALIFIED"


class DisqualificationReasonCategory(str, enum.Enum):
    """
    Standardized classification categories for bid disqualification reasons.
    """
    MANDATORY_REQUIREMENT_FAILURE = "MANDATORY_REQUIREMENT_FAILURE"
    CRITICAL_REQUIREMENT_FAILURE = "CRITICAL_REQUIREMENT_FAILURE"
    DOCUMENT_INSUFFICIENT = "DOCUMENT_INSUFFICIENT"
    REGISTRATION_NON_COMPLIANCE = "REGISTRATION_NON_COMPLIANCE"
    FINANCIAL_NON_COMPLIANCE = "FINANCIAL_NON_COMPLIANCE"
    TECHNICAL_NON_COMPLIANCE = "TECHNICAL_NON_COMPLIANCE"
    INTEGRITY_CONCERN = "INTEGRITY_CONCERN"
    OTHER = "OTHER"


class BidDecision(Base, TimestampMixin):
    """
    Bid Decision entity capturing an authorized Procurement Officer's qualification
    determination on a submitted bid. Supports strict versioning, historical retention,
    evaluation snapshot linkage, and upstream staleness tracking.
    """
    __tablename__ = "bid_decisions"

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
    bid_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    decision: Mapped[str] = mapped_column(
        String(50),
        default=BidDecisionStatus.NOT_DECIDED.value,
        server_default=BidDecisionStatus.NOT_DECIDED.value,
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    decision_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    decided_by_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Versioning & Snapshot References
    decision_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )
    evaluation_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
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
    ai_recommendation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ai_recommendations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # State & Staleness
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        index=True,
    )
    is_stale: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )
    stale_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Superseding Linkage
    superseded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    superseded_by_decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_decisions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    tender: Mapped["Tender"] = relationship("Tender")
    bid: Mapped["Bid"] = relationship("Bid")
    decided_by_profile: Mapped["Profile"] = relationship("Profile")
    score_snapshot: Mapped[Optional["BidScoreSnapshot"]] = relationship("BidScoreSnapshot")
    risk_snapshot: Mapped[Optional["BidRiskSnapshot"]] = relationship("BidRiskSnapshot")
    ai_recommendation: Mapped[Optional["AIRecommendationRecord"]] = relationship("AIRecommendationRecord")
