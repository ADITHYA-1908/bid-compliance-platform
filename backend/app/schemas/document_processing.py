"""
Pydantic Schemas for Part 4A, 4B, 4C, 4D & 4E
Provides type-safe serialization for document processing lifecycle, stages, OCR methods,
deterministic classification results, structured entity extraction, confidence metrics,
and execution telemetry.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExtractedFieldItem(BaseModel):
    value: Any = Field(..., description="Normalized field value (string, number, boolean, or dict)")
    confidence: float = Field(..., description="Field-level extraction confidence score (0.0 to 1.0)")
    evidence: str = Field(..., description="Concise text snippet or matched evidence")
    page: int = Field(default=1, description="1-indexed document page number provenance")
    is_conflict: bool = Field(default=False, description="Whether multiple conflicting values were identified")
    conflict_values: List[Any] = Field(default_factory=list, description="Alternative values detected in the document")


class DocumentExtractedDataResponse(BaseModel):
    document_id: uuid.UUID
    bid_id: uuid.UUID
    document_type: str
    fields: Dict[str, ExtractedFieldItem] = Field(default_factory=dict)
    extraction_confidence: float
    confidence_level: str  # HIGH, MEDIUM, LOW
    extraction_method: str = "RULE_BASED"
    requires_review: bool = False
    review_reasons: List[str] = Field(default_factory=list)


class DocumentProcessingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bid_document_id: uuid.UUID
    processing_status: str = Field(..., description="QUEUED, PROCESSING, COMPLETED, FAILED, NEEDS_REVIEW")
    processing_stage: str = Field(..., description="INGESTION, TEXT_EXTRACTION, OCR, CLASSIFICATION, STRUCTURED_EXTRACTION, COMPLETED")
    extraction_method: str = Field(default="NONE", description="NONE, DIGITAL_PDF, OCR, HYBRID")
    raw_text: Optional[str] = None
    normalized_text: Optional[str] = None
    page_count: Optional[int] = None

    # Part 4D: Classification Fields
    detected_document_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification_confidence_level: Optional[str] = None
    classification_method: Optional[str] = None
    classification_reason: Optional[str] = None
    classification_requires_review: bool = False

    # Part 4E: Structured Extraction Fields
    extracted_data: Optional[Dict[str, Any]] = None
    extraction_confidence: Optional[float] = None
    extraction_requires_review: bool = False
    structured_extraction_method: Optional[str] = None

    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentProcessTriggerResponse(BaseModel):
    message: str
    processing: DocumentProcessingResponse


class DocumentExtractedTextResponse(BaseModel):
    document_id: uuid.UUID
    bid_id: uuid.UUID
    processing_status: str
    processing_stage: str
    extraction_method: str
    page_count: Optional[int] = None
    character_count: Optional[int] = None
    raw_text: Optional[str] = None
    normalized_text: Optional[str] = None
    is_ocr_required: bool = False
    quality_label: Optional[str] = None

    # Classification summary
    detected_document_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification_confidence_level: Optional[str] = None
    classification_reason: Optional[str] = None
    classification_requires_review: bool = False

    # Structured Extraction summary (Part 4E)
    extracted_data: Optional[Dict[str, Any]] = None
    extraction_confidence: Optional[float] = None
    extraction_requires_review: bool = False


class DocumentClassificationResponse(BaseModel):
    document_id: uuid.UUID
    bid_id: uuid.UUID
    processing_status: str
    processing_stage: str
    detected_document_type: str
    expected_document_type: Optional[str] = None
    classification_confidence: float
    confidence_level: str  # HIGH, MEDIUM, LOW
    classification_method: str
    classification_reason: str
    classification_requires_review: bool
