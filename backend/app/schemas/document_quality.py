"""
Pydantic Schemas for Part 11: Advanced Document Quality Check
Defines serialization models for document quality assessments, page-level diagnostics,
bidder-facing feedback, and procurement audit evidence.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentPageQualityResponse(BaseModel):
    id: uuid.UUID
    quality_result_id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    blur_score: float
    width: Optional[int] = None
    height: Optional[int] = None
    dpi: Optional[int] = None
    resolution: Optional[str] = None
    ocr_confidence: Optional[float] = None
    is_blank: bool
    is_unreadable: bool
    is_skewed: bool
    skew_angle: Optional[float] = None
    quality_level: str
    review_reason: Optional[str] = None
    issues: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentQualityResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    processing_id: Optional[uuid.UUID] = None
    quality_score: float
    quality_level: str
    is_blurry: bool
    has_blank_pages: bool
    has_unreadable_pages: bool
    has_low_resolution_pages: bool
    has_skewed_pages: bool
    is_corrupted: bool
    is_password_protected: bool
    ocr_confidence: Optional[float] = None
    average_ocr_confidence: Optional[float] = None
    min_page_ocr_confidence: Optional[float] = None
    page_count: int
    review_required: bool
    review_reasons: List[str] = Field(default_factory=list)
    bidder_feedback: List[str] = Field(default_factory=list)
    metrics_summary: Dict[str, Any] = Field(default_factory=dict)
    page_qualities: List[DocumentPageQualityResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QualityCheckTriggerResponse(BaseModel):
    document_id: uuid.UUID
    quality_score: float
    quality_level: str
    review_required: bool
    message: str
    bidder_feedback: List[str] = Field(default_factory=list)
    created_at: datetime
