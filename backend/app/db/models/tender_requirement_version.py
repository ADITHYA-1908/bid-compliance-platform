"""
Tender Requirement Version Model for Part 15: Compliance Rule Version History
Persists immutable snapshots of tender eligibility criteria and compliance rules
to ensure complete auditability, provenance tracking, and evaluation reproducibility.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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
    from app.db.models.tender_requirement import TenderRequirement
    from app.db.models.profile import Profile


class TenderRequirementVersion(Base, TimestampMixin):
    """
    Immutable historical snapshot of a TenderRequirement version.
    Records the exact criteria parameters, change reason, actor, and effective period.
    """
    __tablename__ = "tender_requirement_versions"
    __table_args__ = (
        Index("ix_tender_req_ver_req_id", "tender_requirement_id"),
        Index("ix_tender_req_ver_tender_id", "tender_id"),
        Index("ix_tender_req_ver_num", "tender_requirement_id", "version_number", unique=True),
        Index("ix_tender_req_ver_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tender_requirement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tender_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # Core Requirement Definition
    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="STATUTORY",
    )
    requirement_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="BOOLEAN",
    )
    operator: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="EQUALS",
    )
    expected_value: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
    )
    unit: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    is_critical: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    weight: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=True,
        default=Decimal("10.0"),
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Clause / Corrigendum Source
    source_clause: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    source_page: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    corrigendum_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Effective Dates
    effective_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    effective_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Audit & Provenance
    change_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    changed_by_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    change_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Relationships
    tender_requirement: Mapped["TenderRequirement"] = relationship(
        "TenderRequirement",
        back_populates="versions",
    )
    tender: Mapped["Tender"] = relationship(
        "Tender",
    )
    changed_by_profile: Mapped[Optional["Profile"]] = relationship(
        "Profile",
    )

    def __repr__(self) -> str:
        return (
            f"<TenderRequirementVersion(id={self.id}, req_id={self.tender_requirement_id}, "
            f"version={self.version_number}, code='{self.code}')>"
        )
