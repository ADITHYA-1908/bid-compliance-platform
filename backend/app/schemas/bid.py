"""
Bid Schemas for Part 3C: Bid Creation & Tender Participation
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BidTenderSummary(BaseModel):
    id: uuid.UUID
    tender_number: str
    title: str
    description: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    procurement_type: Optional[str] = None
    estimated_value: Optional[Decimal] = None
    currency: str = "INR"
    status: str
    publish_date: Optional[datetime] = None
    submission_start_date: Optional[datetime] = None
    submission_end_date: Optional[datetime] = None
    organization_name: Optional[str] = None
    organization_city: Optional[str] = None
    organization_state: Optional[str] = None
    active_requirements_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BidderOrgSummary(BaseModel):
    id: uuid.UUID
    name: str
    trade_name: Optional[str] = None
    pan_number: Optional[str] = None
    gstin: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BidCreate(BaseModel):
    quoted_amount: Optional[Decimal] = Field(None, description="Proposed total commercial quote", ge=0)
    currency: Optional[str] = Field("INR", max_length=10)
    technical_summary: Optional[str] = Field(None, max_length=10000)
    commercial_notes: Optional[str] = Field(None, max_length=10000)
    remarks: Optional[str] = Field(None, max_length=5000)


class BidUpdate(BaseModel):
    quoted_amount: Optional[Decimal] = Field(None, description="Proposed total commercial quote", ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    technical_summary: Optional[str] = Field(None, max_length=10000)
    commercial_notes: Optional[str] = Field(None, max_length=10000)
    remarks: Optional[str] = Field(None, max_length=5000)


class BidListItem(BaseModel):
    id: uuid.UUID
    bid_number: str
    status: str
    quoted_amount: Optional[Decimal] = None
    currency: str = "INR"
    tender_id: uuid.UUID
    tender_number: str
    tender_title: str
    tender_status: str
    department: Optional[str] = None
    category: Optional[str] = None
    procurement_type: Optional[str] = None
    submission_end_date: Optional[datetime] = None
    procuring_organization_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BidListResponse(BaseModel):
    items: List[BidListItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class BidResponse(BaseModel):
    id: uuid.UUID
    tender_id: uuid.UUID
    bidder_organization_id: uuid.UUID
    created_by_profile_id: uuid.UUID
    bid_number: str
    status: str
    quoted_amount: Optional[Decimal] = None
    currency: str = "INR"
    technical_summary: Optional[str] = None
    commercial_notes: Optional[str] = None
    remarks: Optional[str] = None
    submitted_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Associated summaries
    tender: BidTenderSummary
    bidder_organization: Optional[BidderOrgSummary] = None

    model_config = ConfigDict(from_attributes=True)
