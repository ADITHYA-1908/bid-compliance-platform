"""
Validation and Benchmarking Models for Empirical Performance Evaluation
Stores validation runs, aggregated benchmark metrics, and per-case granular evaluation results.
"""

from datetime import datetime, timezone
import enum
from typing import Any, Dict, List, Optional
import uuid
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


class ValidationStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ValidationErrorType(str, enum.Enum):
    NONE = "NONE"
    OCR_ERROR = "OCR_ERROR"
    CLASSIFICATION_ERROR = "CLASSIFICATION_ERROR"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    COMPLIANCE_MISMATCH = "COMPLIANCE_MISMATCH"
    RAG_MISMATCH = "RAG_MISMATCH"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    FALSE_NEGATIVE = "FALSE_NEGATIVE"
    PROCESSING_EXCEPTION = "PROCESSING_EXCEPTION"


class ValidationRun(Base):
    """
    Stores an empirical benchmarking execution run with aggregate accuracy,
    confusion matrix counts, precision/recall/F1, false positive/negative rates,
    RAG retrieval scores, and processing timing comparisons.
    """
    __tablename__ = "validation_runs"
    __table_args__ = (
        Index("ix_validation_runs_status_created", "status", "created_at"),
        Index("ix_validation_runs_org_created", "organization_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0")
    engine_versions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=ValidationStatus.PENDING.value)

    # Dataset counts
    total_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Core Accuracy Metrics (0.0 to 100.0)
    ocr_accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    classification_accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    field_extraction_accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    compliance_accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Confusion Matrix Counts
    true_positives: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    true_negatives: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    false_positives: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    false_negatives: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Derived Statistical Metrics (0.0 to 1.0 or 0.0 to 100.0)
    precision: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    recall: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    f1_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    false_positive_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    false_negative_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # RAG Retrieval Metrics
    rag_retrieval_accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rag_citation_accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Timing & Manual Comparison
    average_processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_manual_time_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_reduction_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Extended Breakdown Telemetry
    summary_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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
    case_results: Mapped[List["ValidationCaseResult"]] = relationship(
        "ValidationCaseResult",
        back_populates="validation_run",
        cascade="all, delete-orphan",
        order_by="ValidationCaseResult.test_case_id.asc()",
    )


class ValidationCaseResult(Base):
    """
    Granular evaluation result for an individual ground truth test case within a validation run.
    """
    __tablename__ = "validation_case_results"
    __table_args__ = (
        Index("ix_case_results_run_correct", "validation_run_id", "is_correct"),
        Index("ix_case_results_category", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("validation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_level: Mapped[str] = mapped_column(String(50), nullable=False, default="GOOD")

    # Ground Truth vs Actual Results
    expected_result_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    actual_result_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Verification Outcomes
    is_correct: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_type: Mapped[str] = mapped_column(String(50), default=ValidationErrorType.NONE.value, nullable=False)
    error_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Component-Specific Flags & Accuracies
    ocr_correct: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ocr_accuracy: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    classification_correct: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    extraction_correct: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    compliance_correct: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rag_correct: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timing
    processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    manual_baseline_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    details_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    validation_run: Mapped["ValidationRun"] = relationship(
        "ValidationRun",
        back_populates="case_results",
    )
