"""
Bid Document Schemas for Part 3D: Bid Document Upload
"""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


from app.schemas.document_processing import DocumentProcessingResponse


class BidDocumentResponse(BaseModel):
    id: uuid.UUID
    bid_id: uuid.UUID
    tender_requirement_id: Optional[uuid.UUID] = None
    uploaded_by_profile_id: uuid.UUID
    document_type: str
    document_name: str
    original_filename: str
    mime_type: str
    file_size: int
    status: str
    version: int = 1
    notes: Optional[str] = None
    is_active: bool
    uploaded_at: datetime
    updated_at: datetime

    # Contextual metadata
    download_url: Optional[str] = None
    requirement_code: Optional[str] = None
    requirement_name: Optional[str] = None
    is_mandatory: Optional[bool] = None
    processing: Optional[DocumentProcessingResponse] = None

    model_config = ConfigDict(from_attributes=True)


class BidDocumentsSummary(BaseModel):
    total_required: int = 0
    uploaded_required: int = 0
    missing_required: int = 0
    total_uploaded: int = 0
    is_ready_for_submission: bool = False


class BidDocumentListResponse(BaseModel):
    items: List[BidDocumentResponse]
    summary: BidDocumentsSummary


class BidDocumentDownloadResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    mime_type: str
    download_url: Optional[str] = None
    expires_in_seconds: int = 300
