"""
Organization Identity Assessment & Duplicate Entity Match Models
BidVerify AI — Integrated Bid Compliance Verification Platform for GeM Procurement

Provides deterministic legal entity identity evaluation, cross-document statutory consistency tracking,
and duplicate/shared identifier detection across organization profiles.
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
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.organization import Organization
    from app.db.models.bid import Bid
    from app.db.models.user import User
    from app.db.models.tender import Tender


class IdentityMatchStatus:
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISMATCH = "MISMATCH"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"

    ALL = [MATCH, PARTIAL_MATCH, MISMATCH, NOT_APPLICABLE, UNKNOWN]


class OrganizationIdentityStatus:
    VERIFIED = "VERIFIED"
    CONSISTENT = "CONSISTENT"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    MISMATCH = "MISMATCH"
    POTENTIAL_DUPLICATE = "POTENTIAL_DUPLICATE"
    UNKNOWN = "UNKNOWN"

    ALL = [
        VERIFIED,
        CONSISTENT,
        PARTIAL_MATCH,
        REVIEW_REQUIRED,
        MISMATCH,
        POTENTIAL_DUPLICATE,
        UNKNOWN,
    ]


class OrganizationDuplicateMatchType:
    SAME_LEGAL_ENTITY = "SAME_LEGAL_ENTITY"
    SAME_PAN = "SAME_PAN"
    SAME_GSTIN = "SAME_GSTIN"
    SAME_CIN = "SAME_CIN"
    SAME_UDYAM = "SAME_UDYAM"
    SAME_NAME_DIFFERENT_IDENTITY = "SAME_NAME_DIFFERENT_IDENTITY"
    HIGH_NAME_SIMILARITY = "HIGH_NAME_SIMILARITY"

    ALL = [
        SAME_LEGAL_ENTITY,
        SAME_PAN,
        SAME_GSTIN,
        SAME_CIN,
        SAME_UDYAM,
        SAME_NAME_DIFFERENT_IDENTITY,
        HIGH_NAME_SIMILARITY,
    ]


class OrganizationDuplicateMatchStatus:
    DETECTED = "DETECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONFIRMED_SAME_ENTITY = "CONFIRMED_SAME_ENTITY"
    CONFIRMED_DISTINCT = "CONFIRMED_DISTINCT"
    DISMISSED = "DISMISSED"

    ALL = [
        DETECTED,
        REVIEW_REQUIRED,
        CONFIRMED_SAME_ENTITY,
        CONFIRMED_DISTINCT,
        DISMISSED,
    ]


class OrganizationIdentityAssessment(Base, TimestampMixin):
    """
    Stores deterministic identity coherence evaluation for an organization profile,
    combining statutory registrations, document extractions, embedded PAN verification,
    and cross-document legal name & address alignments.
    """
    __tablename__ = "organization_identity_assessments"
    __table_args__ = (
        Index("ix_org_ident_org_current", "organization_id", "is_current"),
        Index("ix_org_ident_status", "identity_status"),
        Index("ix_org_ident_bid", "bid_id"),
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
    bid_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bids.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Dimensional Match Statuses
    legal_name_status: Mapped[str] = mapped_column(
        String(50),
        default=IdentityMatchStatus.UNKNOWN,
        nullable=False,
    )
    pan_status: Mapped[str] = mapped_column(
        String(50),
        default=IdentityMatchStatus.UNKNOWN,
        nullable=False,
    )
    gst_status: Mapped[str] = mapped_column(
        String(50),
        default=IdentityMatchStatus.UNKNOWN,
        nullable=False,
    )
    cin_status: Mapped[str] = mapped_column(
        String(50),
        default=IdentityMatchStatus.NOT_APPLICABLE,
        nullable=False,
    )
    udyam_status: Mapped[str] = mapped_column(
        String(50),
        default=IdentityMatchStatus.NOT_APPLICABLE,
        nullable=False,
    )
    address_status: Mapped[str] = mapped_column(
        String(50),
        default=IdentityMatchStatus.UNKNOWN,
        nullable=False,
    )
    pan_gst_embedded_status: Mapped[str] = mapped_column(
        String(50),
        default=IdentityMatchStatus.NOT_APPLICABLE,
        nullable=False,
    )

    # Deterministic Composite Metrics
    identity_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    identity_status: Mapped[str] = mapped_column(
        String(50),
        default=OrganizationIdentityStatus.UNKNOWN,
        nullable=False,
    )

    # Explainable Structured Evidence & Signals
    signals_json: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    evidence_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id],
    )
    bid: Mapped[Optional["Bid"]] = relationship(
        "Bid",
        foreign_keys=[bid_id],
    )

    def __repr__(self) -> str:
        return f"<OrganizationIdentityAssessment(id={self.id}, org={self.organization_id}, status='{self.identity_status}', score={self.identity_score})>"


class OrganizationDuplicateMatch(Base, TimestampMixin):
    """
    Represents a detected potential duplicate, shared legal identifier, or similar-name entity match
    between two registered organization profiles.
    """
    __tablename__ = "organization_duplicate_matches"
    __table_args__ = (
        Index("ix_org_dup_pair", "organization_a_id", "organization_b_id", unique=True),
        Index("ix_org_dup_status", "status"),
        Index("ix_org_dup_type", "match_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_a_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_b_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tender_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    match_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    matched_identifiers: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    similarity_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default=OrganizationDuplicateMatchStatus.DETECTED,
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization_a: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_a_id],
    )
    organization_b: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_b_id],
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by],
    )

    def __repr__(self) -> str:
        return f"<OrganizationDuplicateMatch(id={self.id}, org_a={self.organization_a_id}, org_b={self.organization_b_id}, type='{self.match_type}', status='{self.status}')>"
