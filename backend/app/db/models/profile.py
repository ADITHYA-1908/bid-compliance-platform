import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.organization import Organization
    from app.db.models.role import Role
    from app.db.models.user import User
    from app.db.models.tender import Tender
    from app.db.models.bid import Bid
    from app.db.models.bid_document import BidDocument



class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    designation: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    role: Mapped[Optional["Role"]] = relationship(
        "Role",
        back_populates="profiles",
    )
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization",
        back_populates="profiles",
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="profile",
        uselist=False,
    )
    created_tenders: Mapped[List["Tender"]] = relationship(
        "Tender",
        back_populates="created_by",
    )
    created_bids: Mapped[List["Bid"]] = relationship(
        "Bid",
        foreign_keys="[Bid.created_by_profile_id]",
        back_populates="created_by_profile",
    )
    submitted_bids: Mapped[List["Bid"]] = relationship(
        "Bid",
        foreign_keys="[Bid.submitted_by_profile_id]",
        back_populates="submitted_by_profile",
    )
    uploaded_documents: Mapped[List["BidDocument"]] = relationship(
        "BidDocument",
        back_populates="uploaded_by_profile",
    )


    def __repr__(self) -> str:

        return f"<Profile(id={self.id}, email='{self.email}', full_name='{self.full_name}')>"
