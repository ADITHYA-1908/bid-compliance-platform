import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BidderOrganizationPublicSummary(BaseModel):
    id: uuid.UUID
    name: str = Field(..., description="Procuring Buyer Organization Name")
    organization_type: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BidderTenderRequirementSummary(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    category: str
    requirement_type: str
    operator: str
    expected_value: Optional[Any] = None
    condition_text: str = Field(..., description="Human-readable condition format for bidders")
    is_mandatory: bool
    display_order: int

    model_config = ConfigDict(from_attributes=True)


class BidderTenderSummary(BaseModel):
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
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BidderTenderDetail(BaseModel):
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
    evaluation_start_date: Optional[datetime] = None
    published_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    organization: BidderOrganizationPublicSummary
    requirements: List[BidderTenderRequirementSummary] = Field(default_factory=list)
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BidderTenderListResponse(BaseModel):
    items: List[BidderTenderSummary]
    page: int
    page_size: int
    total: int
    total_pages: int
