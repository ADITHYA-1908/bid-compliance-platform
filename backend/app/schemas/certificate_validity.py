"""
Certificate Validity Schemas
Part 14 — Certificate Validity Monitoring for BidVerify AI
Pydantic response and request models for certificate monitoring.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DocumentValidityDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    bid_id: Optional[uuid.UUID] = None
    organization_id: uuid.UUID
    document_name: Optional[str] = None
    document_type: str
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    validity_status: str
    days_until_expiry: Optional[int] = None
    date_source: str
    source_page: Optional[int] = None
    source_text: Optional[str] = None
    confidence: float
    is_current: bool
    submission_validity_status: Optional[str] = None
    last_checked_at: datetime
    next_check_at: Optional[datetime] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CertificateValidityStatsDTO(BaseModel):
    total_monitored: int = 0
    valid_count: int = 0
    expiring_soon_count: int = 0
    expired_count: int = 0
    no_expiry_count: int = 0
    review_required_count: int = 0
    unknown_count: int = 0


class BidderCertificateListResponse(BaseModel):
    items: List[DocumentValidityDTO]
    total: int
    page: int
    page_size: int
    total_pages: int
    stats: CertificateValidityStatsDTO


class ProcurementCertificateListResponse(BaseModel):
    items: List[DocumentValidityDTO]
    total: int
    page: int
    page_size: int
    total_pages: int


class CertificateValidityRecheckResponse(BaseModel):
    record: DocumentValidityDTO
    message: str


class PeriodicValidityCheckResponse(BaseModel):
    total_checked: int
    status_transitions: int
    status_breakdown: Dict[str, int]
    reference_date: str
