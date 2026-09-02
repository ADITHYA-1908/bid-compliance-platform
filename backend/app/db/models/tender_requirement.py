"""
Tender Requirement Model
Represents configurable eligibility, technical, statutory, and compliance conditions
attached to a specific Tender. Stored dynamically as data rather than hard-coded logic.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any, List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
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
    from app.db.models.bid_document import BidDocument



class TenderRequirement(Base, TimestampMixin):
    """
    Configurable eligibility / compliance criteria for a tender.
    Supports dynamic operators (EQUALS, GREATER_THAN_OR_EQUAL, EXISTS, etc.)
    and structured expected values (JSON) for future rule evaluation.
    """
    __tablename__ = "tender_requirements"
    __table_args__ = (
        CheckConstraint("weight >= 0", name="ck_tender_requirements_weight_positive"),
        CheckConstraint("display_order >= 0", name="ck_tender_requirements_display_order_positive"),
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
        index=True,
    )
    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
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
        default="STATUTORY",
        server_default="STATUTORY",
        nullable=False,
    )
    requirement_type: Mapped[str] = mapped_column(
        String(50),
        default="BOOLEAN",
        server_default="BOOLEAN",
        nullable=False,
    )
    operator: Mapped[str] = mapped_column(
        String(50),
        default="EQUALS",
        server_default="EQUALS",
        nullable=False,
    )
    expected_value: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    is_critical: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    weight: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=5, scale=2),
        default=10.0,
        server_default="10.0",
        nullable=True,
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # Relationships
    tender: Mapped["Tender"] = relationship(
        "Tender",
        back_populates="requirements",
    )
    bid_documents: Mapped[List["BidDocument"]] = relationship(
        "BidDocument",
        back_populates="tender_requirement",
    )

    def __repr__(self) -> str:

        return f"<TenderRequirement(id={self.id}, code='{self.code}', name='{self.name}', mandatory={self.is_mandatory})>"
