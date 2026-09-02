"""
Document Quality Models for Part 11: Advanced Document Quality Check
Tracks deterministic quality scores, quality levels, blur detection, blank page identification,
skew/rotation, resolution telemetry, corrupted/encrypted flags, and page-level diagnostics.
"""

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.bid_document import BidDocument
    from app.db.models.document_processing import DocumentProcessing


class QualityLevel:
    GOOD = "GOOD"            # 90–100
    ACCEPTABLE = "ACCEPTABLE"  # 70–89
    POOR = "POOR"            # 40–69
    UNUSABLE = "UNUSABLE"    # 0–39

    ALL = [GOOD, ACCEPTABLE, POOR, UNUSABLE]


class DocumentQualityResult(Base, TimestampMixin):
    """
    Centralized Document Quality entity summarizing deterministic image & document
    integrity diagnostics before and during Document AI processing.
    """
    __tablename__ = "document_quality_results"
    __table_args__ = (
        Index("ix_document_quality_doc_id", "document_id"),
        Index("ix_document_quality_level", "quality_level"),
        Index("ix_document_quality_review_req", "review_required"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    processing_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_processing.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Deterministic Quality Metrics
    quality_score: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        nullable=False,
    )
    quality_level: Mapped[str] = mapped_column(
        String(50),
        default=QualityLevel.GOOD,
        nullable=False,
        index=True,
    )

    # Diagnostic Flags
    is_blurry: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    has_blank_pages: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    has_unreadable_pages: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    has_low_resolution_pages: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    has_skewed_pages: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    is_corrupted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    is_password_protected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # OCR Telemetry
    ocr_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    average_ocr_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    min_page_ocr_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    page_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    # Human Review & Explainable Reasons
    review_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    review_reasons: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    bidder_feedback: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    metrics_summary: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    bid_document: Mapped["BidDocument"] = relationship(
        "BidDocument",
        back_populates="quality_result",
    )
    processing: Mapped[Optional["DocumentProcessing"]] = relationship(
        "DocumentProcessing",
        back_populates="quality_result",
    )
    page_qualities: Mapped[List["DocumentPageQuality"]] = relationship(
        "DocumentPageQuality",
        back_populates="quality_result",
        cascade="all, delete-orphan",
        order_by="DocumentPageQuality.page_number.asc()",
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentQualityResult(id={self.id}, doc_id={self.document_id}, "
            f"score={self.quality_score}, level='{self.quality_level}', review={self.review_required})>"
        )


class DocumentPageQuality(Base, TimestampMixin):
    """
    Page-level quality diagnostics for multi-page documents.
    """
    __tablename__ = "document_page_qualities"
    __table_args__ = (
        Index("ix_document_page_quality_doc_page", "document_id", "page_number"),
        Index("ix_document_page_quality_result_id", "quality_result_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    quality_result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_quality_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Image Metrics
    blur_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    dpi: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    resolution: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    ocr_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # Flags
    is_blank: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    is_unreadable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    is_skewed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    skew_angle: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    quality_level: Mapped[str] = mapped_column(
        String(50),
        default=QualityLevel.GOOD,
        nullable=False,
    )
    review_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    issues: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Relationships
    quality_result: Mapped["DocumentQualityResult"] = relationship(
        "DocumentQualityResult",
        back_populates="page_qualities",
    )
    bid_document: Mapped["BidDocument"] = relationship(
        "BidDocument",
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentPageQuality(id={self.id}, page={self.page_number}, "
            f"blur={self.blur_score}, blank={self.is_blank}, level='{self.quality_level}')>"
        )
