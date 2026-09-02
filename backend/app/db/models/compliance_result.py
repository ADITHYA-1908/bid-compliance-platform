"""
Compliance Result Model for Part 6A
Persists rule-by-rule evaluation determinations (PASS, FAIL, REVIEW, NOT_APPLICABLE, PENDING)
for each TenderRequirement against a Bid submission and its verified evidence.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Uuid,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.bid import Bid
    from app.db.models.tender import Tender
    from app.db.models.tender_requirement import TenderRequirement
    from app.db.models.tender_requirement_version import TenderRequirementVersion


class ComplianceStatus:
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"

    ALL = [PASS, FAIL, REVIEW, NOT_APPLICABLE, PENDING, BLOCKED]
    TERMINAL = [PASS, FAIL, REVIEW, NOT_APPLICABLE]


class ComplianceResult(Base, TimestampMixin):
    """
    Stores an individual compliance determination for a specific TenderRequirement
    evaluated against a Bid submission. Preserves snapshot of actual and expected values,
    evidence links, and human-readable justification.
    """
    __tablename__ = "compliance_results"
    __table_args__ = (
        Index("ix_compliance_results_bid_req_current", "bid_id", "tender_requirement_id", "is_current"),
        Index("ix_compliance_results_bid_status", "bid_id", "compliance_status"),
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
    tender_requirement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tender_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rule Version Provenance (Part 15)
    rule_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tender_requirement_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_version_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=1,
    )

    # Compliance Determination
    compliance_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ComplianceStatus.PENDING,
        index=True,
    )

    # Evaluation Snapshots
    actual_value: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
    )
    expected_value: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
    )
    operator: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Reasoning & Evidence Traceability
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    evidence: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
    )
    source_verification_ids: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )

    # Requirement Meta Preserved for Audit
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_critical: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    critical_failure: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )
    weight: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=5, scale=2),
        default=Decimal("10.0"),
        nullable=True,
    )

    # Versioning & Audit
    evaluation_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    bid: Mapped["Bid"] = relationship("Bid")
    tender: Mapped["Tender"] = relationship("Tender")
    tender_requirement: Mapped["TenderRequirement"] = relationship("TenderRequirement")
    rule_version: Mapped[Optional["TenderRequirementVersion"]] = relationship("TenderRequirementVersion")

    def __repr__(self) -> str:
        return (
            f"<ComplianceResult(id={self.id}, bid_id={self.bid_id}, "
            f"requirement_id={self.tender_requirement_id}, rule_v={self.rule_version_number}, "
            f"status='{self.compliance_status}', is_current={self.is_current})>"
        )
