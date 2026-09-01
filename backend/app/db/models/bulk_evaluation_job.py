"""
Bulk Evaluation Job and Job Item Models for Part 9
Manages batch processing states, lifecycle progression, failure isolation,
diagnostics, and telemetry for multi-bid evaluation runs on tenders.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.organization import Organization
    from app.db.models.tender import Tender
    from app.db.models.bid import Bid
    from app.db.models.profile import Profile


class BulkJobStatus:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ALL = [QUEUED, RUNNING, COMPLETED, PARTIALLY_COMPLETED, FAILED, CANCELLED]


class BulkItemStatus:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    SKIPPED = "SKIPPED"
    ALL = [QUEUED, RUNNING, SUCCESS, FAILED, REVIEW_REQUIRED, SKIPPED]


class BulkStage:
    QUEUED = "QUEUED"
    DOCUMENT_PROCESSING = "DOCUMENT_PROCESSING"
    VERIFICATION = "VERIFICATION"
    COMPLIANCE = "COMPLIANCE"
    SCORING = "SCORING"
    RISK = "RISK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ALL = [
        QUEUED,
        DOCUMENT_PROCESSING,
        VERIFICATION,
        COMPLIANCE,
        SCORING,
        RISK,
        COMPLETED,
        FAILED,
        SKIPPED,
    ]


class BulkEvaluationJob(Base):
    """
    Tracks tender-level batch evaluation runs, summary telemetry, and overall execution status.
    """
    __tablename__ = "bulk_evaluation_jobs"
    __table_args__ = (
        Index("ix_bulk_jobs_tender_status", "tender_id", "status"),
        Index("ix_bulk_jobs_org_created", "organization_id", "created_at"),
    )

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

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=BulkJobStatus.QUEUED,
        index=True,
    )

    total_bids: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_bids: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_bids: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_bids: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_required_bids: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_findings_bids: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    started_by_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    tender: Mapped["Tender"] = relationship("Tender")
    started_by_profile: Mapped[Optional["Profile"]] = relationship("Profile")
    items: Mapped[List["BulkEvaluationJobItem"]] = relationship(
        "BulkEvaluationJobItem",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="BulkEvaluationJobItem.created_at.asc()",
    )


class BulkEvaluationJobItem(Base):
    """
    Per-bid execution item within a bulk evaluation batch.
    Maintains isolated stage diagnostics, outcomes, and failure states.
    """
    __tablename__ = "bulk_evaluation_job_items"
    __table_args__ = (
        Index("ix_bulk_items_job_status", "job_id", "status"),
        Index("ix_bulk_items_bid", "bid_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bulk_evaluation_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bid_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=BulkItemStatus.QUEUED,
        index=True,
    )
    current_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=BulkStage.QUEUED,
    )

    # Stage-level execution status telemetry
    document_processing_status: Mapped[str] = mapped_column(
        String(50),
        default="NONE",
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default="NONE",
        nullable=False,
    )
    compliance_status: Mapped[str] = mapped_column(
        String(50),
        default="NONE",
        nullable=False,
    )
    score_status: Mapped[str] = mapped_column(
        String(50),
        default="NONE",
        nullable=False,
    )
    risk_status: Mapped[str] = mapped_column(
        String(50),
        default="NONE",
        nullable=False,
    )

    # Evaluation results snapshot
    final_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    critical_findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Technical error and retry diagnostics
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_retryable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    job: Mapped["BulkEvaluationJob"] = relationship("BulkEvaluationJob", back_populates="items")
    bid: Mapped["Bid"] = relationship("Bid")
