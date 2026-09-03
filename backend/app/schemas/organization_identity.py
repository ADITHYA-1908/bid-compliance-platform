"""
Pydantic Schemas for Organization Identity Verification & Duplicate Entity Detection
BidVerify AI — Integrated Bid Compliance Verification Platform for GeM Procurement
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OrganizationIdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    bid_id: Optional[uuid.UUID] = None

    legal_name_status: str
    pan_status: str
    gst_status: str
    cin_status: str
    udyam_status: str
    address_status: str
    pan_gst_embedded_status: str

    identity_score: float
    identity_status: str

    signals_json: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_json: Dict[str, Any] = Field(default_factory=dict)

    is_current: bool = True
    evaluated_at: datetime


class OrganizationDuplicateMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_a_id: uuid.UUID
    organization_b_id: uuid.UUID
    organization_a_name: Optional[str] = None
    organization_b_name: Optional[str] = None
    tender_id: Optional[uuid.UUID] = None

    match_type: str
    matched_identifiers: Dict[str, Any] = Field(default_factory=dict)
    similarity_score: float
    status: str
    notes: Optional[str] = None

    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class OrganizationDuplicateResolvePayload(BaseModel):
    status: str = Field(..., description="CONFIRMED_SAME_ENTITY, CONFIRMED_DISTINCT, DISMISSED, REVIEW_REQUIRED")
    notes: Optional[str] = None


class OrganizationIdentityOverviewResponse(BaseModel):
    assessment: OrganizationIdentityResponse
    duplicate_matches: List[OrganizationDuplicateMatchResponse] = Field(default_factory=list)
