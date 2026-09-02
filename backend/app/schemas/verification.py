"""
Pydantic Schemas for Verification Engine (Part 5A)
Standardizes API request/response payloads for claim verifications, telemetry,
evidence inspection, and retry workflows.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class VerificationEvidenceItem(BaseModel):
    field: Optional[str] = None
    claimed_value: Optional[Any] = None
    source: Optional[str] = None
    matched: Optional[bool] = None
    details: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class VerificationRecordResponse(BaseModel):
    id: uuid.UUID
    bid_id: uuid.UUID
    bid_document_id: Optional[uuid.UUID] = None
    document_processing_id: Optional[uuid.UUID] = None
    verification_type: str
    verification_status: str
    source_name: str
    source_type: str
    claim_source: str
    claimed_value: str
    verified_value: Optional[str] = None
    match_status: str
    confidence: float
    evidence: Optional[Dict[str, Any]] = None
    request_payload: Optional[Dict[str, Any]] = None
    response_payload: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    attempt_number: int = 1
    trigger_source: str
    verification_started_at: Optional[datetime] = None
    verification_completed_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerificationSummaryItem(BaseModel):
    id: uuid.UUID
    verification_type: str
    verification_status: str
    source_name: str
    source_type: str
    claimed_value: str
    verified_value: Optional[str] = None
    match_status: str
    confidence: float
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    attempt_number: int = 1
    is_retryable: bool = False
    evidence: Optional[Dict[str, Any]] = None
    request_payload: Optional[Dict[str, Any]] = None
    response_payload: Optional[Dict[str, Any]] = None
    verification_completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentVerificationListResponse(BaseModel):
    bid_id: uuid.UUID
    bid_document_id: uuid.UUID
    document_name: str
    detected_document_type: Optional[str] = None
    total_verifications: int
    verifications: List[VerificationSummaryItem]


class BidVerificationListResponse(BaseModel):
    bid_id: uuid.UUID
    bid_number: str
    total_verifications: int
    verified_count: int
    not_verified_count: int
    needs_review_count: int
    unavailable_count: int
    failed_count: int
    pending_count: int
    verification_ready_for_compliance: bool = False
    verifications: List[VerificationSummaryItem]


class VerificationTriggerResponse(BaseModel):
    message: str
    bid_id: uuid.UUID
    bid_document_id: Optional[uuid.UUID] = None
    created_count: int
    results: List[VerificationSummaryItem]


class VerificationRetryPayload(BaseModel):
    notes: Optional[str] = None


class VerificationRetryResponse(BaseModel):
    message: str
    verification: VerificationRecordResponse
