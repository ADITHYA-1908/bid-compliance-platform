"""
Pydantic DTO Schemas for Empirical Validation and Benchmarking
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ValidationRunCreateRequest(BaseModel):
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    max_cases: Optional[int] = None
    notes: Optional[str] = None


class ValidationCaseResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    validation_run_id: uuid.UUID
    test_case_id: str
    title: str
    category: str
    document_type: str
    quality_level: str
    expected_result_json: Dict[str, Any]
    actual_result_json: Dict[str, Any]
    is_correct: bool
    error_type: str
    error_reason: Optional[str] = None
    ocr_correct: bool
    ocr_accuracy: float
    classification_correct: bool
    extraction_correct: bool
    compliance_correct: bool
    rag_correct: bool
    processing_time_ms: float
    manual_baseline_sec: float
    details_json: Optional[Dict[str, Any]] = None
    created_at: datetime


class ValidationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    name: str
    dataset_version: str
    engine_versions: Optional[Dict[str, Any]] = None
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    ocr_accuracy: float
    classification_accuracy: float
    field_extraction_accuracy: float
    compliance_accuracy: float
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    false_negative_rate: float
    rag_retrieval_accuracy: float
    rag_citation_accuracy: float
    average_processing_time_ms: float
    average_manual_time_sec: float
    time_reduction_percentage: float
    summary_json: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ValidationRunListResponse(BaseModel):
    items: List[ValidationRunResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ValidationCaseListResponse(BaseModel):
    items: List[ValidationCaseResultResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ValidationDatasetCaseResponse(BaseModel):
    id: str
    title: str
    category: str
    document_type: str
    quality_level: str
    expected_doc_type: str
    expected_compliance_status: str
    manual_baseline_sec: float


class ValidationPPTSummaryResponse(BaseModel):
    slide_title: str
    dataset_overview: Dict[str, Any]
    performance_metrics: Dict[str, str]
    speed_and_efficiency_gains: Dict[str, str]
    key_takeaways: List[str]
    observed_limitations: List[str]
