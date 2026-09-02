"""
Pydantic Schemas for Part 9: Bulk Verification & Batch Processing
Provides structured request payloads, response models, progress telemetry,
and paginated item listings for tender-level batch evaluation runs.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BulkEvaluationSummaryCounts(BaseModel):
    total: int = Field(0, description="Total eligible submitted bids in batch")
    processed: int = Field(0, description="Number of bids processed so far")
    successful: int = Field(0, description="Number of bids processed with full success")
    failed: int = Field(0, description="Number of bids with technical processing errors")
    review_required: int = Field(0, description="Number of bids requiring human review")
    critical_findings: int = Field(0, description="Number of bids with critical non-compliance")
    remaining: int = Field(0, description="Number of bids awaiting processing")
    progress_percentage: float = Field(0.0, description="Completion percentage (0.0 - 100.0)")


class BulkEvaluationJobCreateResponse(BaseModel):
    job_id: uuid.UUID
    tender_id: uuid.UUID
    status: str
    total_bids: int
    message: str
    created_at: datetime


class BulkEvaluationJobStatusResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    tender_id: uuid.UUID
    tender_number: Optional[str] = None
    tender_title: Optional[str] = None
    status: str
    counts: BulkEvaluationSummaryCounts
    started_by_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    error_summary: Optional[Dict[str, Any]] = None


class BulkEvaluationJobItemResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    bid_id: uuid.UUID
    bid_number: Optional[str] = None
    bidder_name: Optional[str] = None
    status: str
    current_stage: str
    document_processing_status: str
    verification_status: str
    compliance_status: str
    score_status: str
    risk_status: str
    final_score: Optional[float] = None
    risk_level: Optional[str] = None
    review_required: bool = False
    critical_findings_count: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    is_retryable: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class BulkEvaluationJobItemsListResponse(BaseModel):
    items: List[BulkEvaluationJobItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BulkEvaluationRetryResponse(BaseModel):
    job_id: uuid.UUID
    retried_count: int
    status: str
    message: str


class BulkEvaluationCancelResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    message: str
