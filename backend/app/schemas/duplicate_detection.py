"""
Pydantic Schemas for Part 10: Duplicate / Reuse Document Detection
Defines request/response models for duplicate scan jobs, match alerts, side-by-side comparison,
and Procurement Officer review actions.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MatchedFieldDetail(BaseModel):
    field_key: str
    label: str
    value_a: Optional[str] = None
    value_b: Optional[str] = None
    is_exact_match: bool = True
    weight: float = 1.0


class DocumentComparisonMeta(BaseModel):
    document_id: uuid.UUID
    bid_id: uuid.UUID
    bid_number: Optional[str] = None
    bidder_organization_id: uuid.UUID
    bidder_name: str
    document_type: str
    document_name: str
    original_filename: str
    file_size: int
    mime_type: str
    file_hash: Optional[str] = None
    normalized_content_hash: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    text_snippet: Optional[str] = None


class DuplicateMatchListItemResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    tender_id: uuid.UUID
    
    # Document A
    document_a_id: uuid.UUID
    bid_a_id: uuid.UUID
    bid_a_number: Optional[str] = None
    bidder_a_name: str
    document_a_name: str

    # Document B
    document_b_id: uuid.UUID
    bid_b_id: uuid.UUID
    bid_b_number: Optional[str] = None
    bidder_b_name: str
    document_b_name: str

    document_type: str
    match_type: str
    file_hash_match: bool
    content_hash_match: bool
    structured_field_match_score: float
    text_similarity_score: float
    overall_confidence: float

    status: str
    review_required: bool
    matched_fields_summary: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DuplicateMatchDetailResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    tender_id: uuid.UUID
    tender_title: Optional[str] = None
    tender_number: Optional[str] = None

    document_a: DocumentComparisonMeta
    document_b: DocumentComparisonMeta

    match_type: str
    file_hash_match: bool
    content_hash_match: bool
    structured_field_match_score: float
    text_similarity_score: float
    overall_confidence: float

    status: str
    review_required: bool
    matched_fields_details: List[MatchedFieldDetail] = Field(default_factory=list)
    evidence_summary: Dict[str, Any] = Field(default_factory=dict)

    reviewer_notes: Optional[str] = None
    reviewed_by_profile_id: Optional[uuid.UUID] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DuplicateMatchSummaryCounts(BaseModel):
    total: int = 0
    detected: int = 0
    review_required: int = 0
    confirmed_reuse: int = 0
    confirmed_benign: int = 0
    dismissed: int = 0
    exact_file_duplicates: int = 0
    content_duplicates: int = 0
    structured_matches: int = 0
    high_similarity: int = 0


class DuplicateMatchListResponse(BaseModel):
    items: List[DuplicateMatchListItemResponse]
    total: int
    counts: DuplicateMatchSummaryCounts


class DuplicateScanResponse(BaseModel):
    tender_id: uuid.UUID
    tender_number: str
    scanned_documents: int
    scanned_bids: int
    new_matches_found: int
    total_active_matches: int
    duration_ms: float
    summary: str


class DuplicateReviewRequest(BaseModel):
    resolution: str = Field(
        ...,
        description="Review outcome: CONFIRMED_BENIGN, CONFIRMED_REUSE, or DISMISSED",
    )
    reviewer_notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Detailed justification or findings recorded by the Procurement Officer",
    )


class DuplicateReviewResponse(BaseModel):
    match_id: uuid.UUID
    status: str
    resolution: str
    reviewed_by_name: str
    reviewed_at: datetime
    reviewer_notes: Optional[str] = None
    message: str
