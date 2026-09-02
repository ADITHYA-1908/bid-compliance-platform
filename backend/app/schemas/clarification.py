"""
Pydantic Schemas for Part 16 — Clarification Request Workflow
Defines request payloads, response DTOs, detailed threads, and analytics summaries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class ClarificationResponseCreate(BaseModel):
    response_text: str = Field(..., min_length=5, description="Explanatory response text")
    attached_document_id: Optional[uuid.UUID] = Field(None, description="Optional uploaded supporting/replacement document UUID")
    is_replacement_document: bool = Field(False, description="True if this document replaces a prior rejected/poor document")
    replaced_document_id: Optional[uuid.UUID] = Field(None, description="Prior document UUID being replaced")


class ClarificationResponseDTO(BaseModel):
    id: uuid.UUID
    clarification_request_id: uuid.UUID
    responded_by_profile_id: uuid.UUID
    responded_by_name: Optional[str] = None
    response_text: str
    attached_document_id: Optional[uuid.UUID] = None
    attached_document_name: Optional[str] = None
    is_replacement_document: bool = False
    replaced_document_id: Optional[uuid.UUID] = None
    replaced_document_name: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClarificationRequestCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=255)
    message: str = Field(..., min_length=10, description="Detailed clarification description")
    clarification_type: str = Field(default="OTHER")
    priority: str = Field(default="NORMAL")
    due_date: Optional[datetime] = None
    send_immediately: bool = Field(default=True, description="If True, status is SENT; if False, DRAFT")
    
    # Optional provenance / related context
    related_document_id: Optional[uuid.UUID] = None
    related_requirement_id: Optional[uuid.UUID] = None
    related_rule_version_id: Optional[uuid.UUID] = None
    related_rule_version_number: Optional[int] = None
    related_verification_record_id: Optional[uuid.UUID] = None
    related_compliance_result_id: Optional[uuid.UUID] = None
    related_review_item_id: Optional[uuid.UUID] = None
    related_duplicate_match_id: Optional[uuid.UUID] = None


class ClarificationRequestUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=3, max_length=255)
    message: Optional[str] = Field(None, min_length=10)
    clarification_type: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None


class ClarificationResolveRequest(BaseModel):
    resolution_note: Optional[str] = Field(None, description="Mandatory/Optional resolution explanation")
    trigger_reevaluation: bool = Field(default=False, description="Whether to trigger automated re-evaluation of relevant criteria")


class ClarificationRequestListItemResponse(BaseModel):
    id: uuid.UUID
    tender_id: uuid.UUID
    tender_number: str
    tender_title: str
    bid_id: uuid.UUID
    bid_number: str
    bidder_organization_name: str
    tender_organization_name: str
    created_by_profile_id: uuid.UUID
    created_by_name: str
    subject: str
    clarification_type: str
    priority: str
    status: str
    due_date: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    responses_count: int = 0
    is_overdue: bool = False
    related_requirement_code: Optional[str] = None
    related_document_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClarificationRequestDetailResponse(BaseModel):
    id: uuid.UUID
    tender_id: uuid.UUID
    tender_number: str
    tender_title: str
    bid_id: uuid.UUID
    bid_number: str
    tender_organization_id: uuid.UUID
    tender_organization_name: str
    bidder_organization_id: uuid.UUID
    bidder_organization_name: str
    created_by_profile_id: uuid.UUID
    created_by_name: str
    assigned_bidder_profile_id: Optional[uuid.UUID] = None
    assigned_bidder_name: Optional[str] = None
    subject: str
    message: str
    clarification_type: str
    priority: str
    status: str
    due_date: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    
    # Related Evidence Provenance
    related_document_id: Optional[uuid.UUID] = None
    related_document_name: Optional[str] = None
    related_document_type: Optional[str] = None
    related_requirement_id: Optional[uuid.UUID] = None
    related_requirement_code: Optional[str] = None
    related_requirement_name: Optional[str] = None
    related_rule_version_id: Optional[uuid.UUID] = None
    related_rule_version_number: Optional[int] = None
    related_verification_record_id: Optional[uuid.UUID] = None
    related_compliance_result_id: Optional[uuid.UUID] = None
    related_review_item_id: Optional[uuid.UUID] = None
    related_duplicate_match_id: Optional[uuid.UUID] = None

    # Resolution
    resolved_by_profile_id: Optional[uuid.UUID] = None
    resolved_by_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None

    # Responses timeline
    responses: List[ClarificationResponseDTO] = []
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClarificationRequestListResponse(BaseModel):
    items: List[ClarificationRequestListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ClarificationSummaryResponse(BaseModel):
    total_clarifications: int
    open_clarifications: int
    awaiting_bidder_response: int
    responses_received: int
    under_review: int
    resolved_clarifications: int
    overdue_clarifications: int
    cancelled_clarifications: int


class ClarificationAnalyticsResponse(BaseModel):
    summary: ClarificationSummaryResponse
    avg_response_time_hours: Optional[float] = None
    avg_resolution_time_hours: Optional[float] = None
    by_type: List[Dict[str, Any]] = []
    by_priority: List[Dict[str, Any]] = []
    by_status: List[Dict[str, Any]] = []
