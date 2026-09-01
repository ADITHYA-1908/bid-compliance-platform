"""
Document Processing Model for Part 4A, 4B, 4C & 4D
Tracks extraction pipeline state, stages, OCR methods, deterministic classification,
and execution telemetry for BidDocuments.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
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
    from app.db.models.verification_record import VerificationRecord


class ProcessingStatus:
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"

    ALL = [QUEUED, PROCESSING, COMPLETED, FAILED, NEEDS_REVIEW]


class ProcessingStage:
    INGESTION = "INGESTION"
    TEXT_EXTRACTION = "TEXT_EXTRACTION"
    OCR = "OCR"
    CLASSIFICATION = "CLASSIFICATION"
    STRUCTURED_EXTRACTION = "STRUCTURED_EXTRACTION"
    COMPLETED = "COMPLETED"

    ALL = [
        INGESTION,
        TEXT_EXTRACTION,
        OCR,
        CLASSIFICATION,
        STRUCTURED_EXTRACTION,
        COMPLETED,
    ]


class ExtractionMethod:
    NONE = "NONE"
    DIGITAL_PDF = "DIGITAL_PDF"
    OCR = "OCR"
    HYBRID = "HYBRID"

    ALL = [NONE, DIGITAL_PDF, OCR, HYBRID]


class DocumentClass:
    GST_CERTIFICATE = "GST_CERTIFICATE"
    PAN = "PAN"
    UDYAM_CERTIFICATE = "UDYAM_CERTIFICATE"
    OEM_AUTHORIZATION = "OEM_AUTHORIZATION"
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    TURNOVER_CERTIFICATE = "TURNOVER_CERTIFICATE"
    EXPERIENCE_CERTIFICATE = "EXPERIENCE_CERTIFICATE"
    LOCAL_CONTENT_DECLARATION = "LOCAL_CONTENT_DECLARATION"
    BLACKLIST_DECLARATION = "BLACKLIST_DECLARATION"
    TECHNICAL_DOCUMENT = "TECHNICAL_DOCUMENT"
    COMMERCIAL_DOCUMENT = "COMMERCIAL_DOCUMENT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"

    ALL = [
        GST_CERTIFICATE,
        PAN,
        UDYAM_CERTIFICATE,
        OEM_AUTHORIZATION,
        FINANCIAL_STATEMENT,
        TURNOVER_CERTIFICATE,
        EXPERIENCE_CERTIFICATE,
        LOCAL_CONTENT_DECLARATION,
        BLACKLIST_DECLARATION,
        TECHNICAL_DOCUMENT,
        COMMERCIAL_DOCUMENT,
        OTHER,
        UNKNOWN,
    ]


class ClassificationConfidenceLevel:
    HIGH = "HIGH"        # >= 0.80
    MEDIUM = "MEDIUM"    # 0.55 - 0.79
    LOW = "LOW"          # < 0.55


class DocumentProcessing(Base, TimestampMixin):
    """
    DocumentProcessing entity representing the lifecycle state, stage, extracted text,
    classification outcomes, structured entity extraction, and execution telemetry
    of an individual BidDocument version.
    """
    __tablename__ = "document_processing"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bid_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    processing_status: Mapped[str] = mapped_column(
        String(50),
        default=ProcessingStatus.QUEUED,
        server_default=ProcessingStatus.QUEUED,
        nullable=False,
        index=True,
    )
    processing_stage: Mapped[str] = mapped_column(
        String(50),
        default=ProcessingStage.INGESTION,
        server_default=ProcessingStage.INGESTION,
        nullable=False,
        index=True,
    )
    extraction_method: Mapped[str] = mapped_column(
        String(50),
        default=ExtractionMethod.NONE,
        server_default=ExtractionMethod.NONE,
        nullable=False,
    )

    raw_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    normalized_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    normalized_content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    page_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Part 4D: Document Classification Fields
    detected_document_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    classification_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    classification_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    classification_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    classification_requires_review: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # Part 4E: Structured Entity Extraction Fields
    extracted_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    extraction_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    extraction_requires_review: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    structured_extraction_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    processing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    bid_document: Mapped["BidDocument"] = relationship(
        "BidDocument",
        back_populates="processing",
    )
    verifications: Mapped[List["VerificationRecord"]] = relationship(
        "VerificationRecord",
        back_populates="document_processing",
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentProcessing(id={self.id}, doc_id={self.bid_document_id}, "
            f"status='{self.processing_status}', stage='{self.processing_stage}', "
            f"detected_type='{self.detected_document_type}', conf={self.classification_confidence})>"
        )
