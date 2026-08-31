import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.profile import Profile
    from app.db.models.tender import Tender
    from app.db.models.bid import Bid


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Legal Business Name
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    # Trade / Display Name
    trade_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    # Organization Type (e.g. PROPRIETORSHIP, PARTNERSHIP, LLP, PRIVATE_LIMITED, etc.)
    organization_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    # Business Category (e.g. Micro, Small, Medium, Large, OEM, Trader, Service Provider)
    business_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    # Year Established
    year_established: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    # Legacy registration number field preserved
    registration_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    # Registered Address
    registered_address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    pincode: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        default="India",
        nullable=True,
    )
    # Official Contact Information
    official_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    official_phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    website: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    # Statutory Registrations / Identifiers
    pan_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )
    gstin: Mapped[Optional[str]] = mapped_column(
        String(25),
        nullable=True,
        index=True,
    )
    udyam_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    cin_llpin: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    startup_india_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    nsic_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    epfo_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    esic_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    profiles: Mapped[List["Profile"]] = relationship(
        "Profile",
        back_populates="organization",
    )
    tenders: Mapped[List["Tender"]] = relationship(
        "Tender",
        back_populates="organization",
    )
    bids: Mapped[List["Bid"]] = relationship(
        "Bid",
        back_populates="bidder_organization",
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}')>"

