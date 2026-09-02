"""
Tender and Tender Requirement Pydantic Schemas
Defines request validation and response serialization schemas for Tender Management
and Dynamic Eligibility / Compliance Requirements.
"""

import math
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TenderRequirementBase(BaseModel):
    """Base schema for dynamic eligibility / compliance requirement."""
    code: str = Field(..., min_length=2, max_length=100, description="Unique requirement code within the tender")
    name: str = Field(..., min_length=2, max_length=255, description="Human-readable requirement title")
    description: Optional[str] = Field(default=None, description="Detailed criteria explanation / instructions")
    category: str = Field(default="STATUTORY", max_length=50, description="STATUTORY, FINANCIAL, TECHNICAL, EXPERIENCE, LOCAL_CONTENT, DOCUMENT, BLACKLISTING, OTHER")
    requirement_type: str = Field(default="BOOLEAN", max_length=50, description="BOOLEAN, NUMBER, TEXT, DATE, DOCUMENT, STATUS")
    operator: str = Field(default="EQUALS", max_length=50, description="EQUALS, NOT_EQUALS, GREATER_THAN, GREATER_THAN_OR_EQUAL, LESS_THAN, LESS_THAN_OR_EQUAL, CONTAINS, EXISTS, NOT_EXISTS")
    expected_value: Optional[Any] = Field(default=None, description="Benchmark value (string, number, boolean, or structured JSON)")
    is_mandatory: bool = Field(default=True, description="Whether this criterion is mandatory for qualification")
    weight: Optional[Decimal] = Field(default=Decimal("10.0"), ge=0, description="Scoring weight points (>= 0)")
    display_order: int = Field(default=0, ge=0, description="Display sorting order index")
    is_active: bool = Field(default=True, description="Active status")


class TenderRequirementCreate(BaseModel):
    """Payload schema for creating a tender requirement."""
    code: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    category: str = Field(default="STATUTORY", max_length=50)
    requirement_type: str = Field(default="BOOLEAN", max_length=50)
    operator: str = Field(default="EQUALS", max_length=50)
    expected_value: Optional[Any] = None
    is_mandatory: bool = True
    weight: Optional[Decimal] = Field(default=Decimal("10.0"), ge=0)
    display_order: int = Field(default=0, ge=0)


class TenderRequirementUpdate(BaseModel):
    """Payload schema for partially updating a tender requirement."""
    code: Optional[str] = Field(default=None, min_length=2, max_length=100)
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=50)
    requirement_type: Optional[str] = Field(default=None, max_length=50)
    operator: Optional[str] = Field(default=None, max_length=50)
    expected_value: Optional[Any] = None
    is_mandatory: Optional[bool] = None
    weight: Optional[Decimal] = Field(default=None, ge=0)
    display_order: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class TenderRequirementResponse(TenderRequirementBase):
    """Response schema for a persisted tender requirement."""
    id: uuid.UUID
    tender_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenderBase(BaseModel):
    """Base schema for tender opportunity."""
    tender_number: str = Field(..., min_length=3, max_length=100)
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    department: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    procurement_type: Optional[str] = Field(default="GOODS", max_length=50)
    estimated_value: Optional[Decimal] = Field(default=None, ge=0)
    currency: str = Field(default="INR", max_length=10)
    publish_date: Optional[datetime] = None
    submission_start_date: Optional[datetime] = None
    submission_end_date: Optional[datetime] = None
    evaluation_start_date: Optional[datetime] = None
    status: str = Field(default="DRAFT", max_length=50)
    is_active: bool = True


class TenderCreate(BaseModel):
    """Payload schema for creating a new tender (Procurement Officer)."""
    tender_number: str = Field(..., min_length=3, max_length=100, description="Unique GeM tender number")
    title: str = Field(..., min_length=3, max_length=255, description="Procurement title")
    description: Optional[str] = Field(default=None, description="Detailed scope of procurement")
    department: Optional[str] = Field(default=None, max_length=255, description="Procuring department / division")
    category: Optional[str] = Field(default=None, max_length=100, description="Product / service category")
    procurement_type: Optional[str] = Field(default="GOODS", max_length=50, description="GOODS, SERVICES, or WORKS")
    estimated_value: Optional[Decimal] = Field(default=None, ge=0, description="Estimated total contract value")
    currency: str = Field(default="INR", max_length=10, description="Currency ISO code")
    publish_date: Optional[datetime] = None
    submission_start_date: Optional[datetime] = None
    submission_end_date: Optional[datetime] = None
    evaluation_start_date: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "TenderCreate":
        if self.submission_start_date and self.submission_end_date:
            if self.submission_end_date < self.submission_start_date:
                raise ValueError("submission_end_date cannot be earlier than submission_start_date.")
        if self.publish_date and self.submission_start_date:
            if self.submission_start_date < self.publish_date:
                raise ValueError("submission_start_date cannot be earlier than publish_date.")
        if self.submission_end_date and self.evaluation_start_date:
            if self.evaluation_start_date < self.submission_end_date:
                raise ValueError("evaluation_start_date cannot be earlier than submission_end_date.")
        return self


class TenderUpdate(BaseModel):
    """Payload schema for updating tender details (Procurement Officer)."""
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = None
    department: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    procurement_type: Optional[str] = Field(default=None, max_length=50)
    estimated_value: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, max_length=10)
    publish_date: Optional[datetime] = None
    submission_start_date: Optional[datetime] = None
    submission_end_date: Optional[datetime] = None
    evaluation_start_date: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "TenderUpdate":
        if self.submission_start_date and self.submission_end_date:
            if self.submission_end_date < self.submission_start_date:
                raise ValueError("submission_end_date cannot be earlier than submission_start_date.")
        return self


class TenderStatusTransition(BaseModel):
    """Payload schema for requesting a lifecycle status transition."""
    target_status: str = Field(
        ...,
        description="Target lifecycle status (e.g. PUBLISHED, OPEN, CLOSED, UNDER_EVALUATION, AWARDED, ARCHIVED)",
    )
    remarks: Optional[str] = Field(default=None, description="Optional officer remarks / rationale for transition")


class TenderResponse(TenderBase):
    """Response schema for a persisted tender including requirements and lifecycle metadata."""
    id: uuid.UUID
    organization_id: uuid.UUID
    created_by_profile_id: uuid.UUID
    published_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    evaluation_started_at: Optional[datetime] = None
    awarded_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    requirements: List[TenderRequirementResponse] = []
    allowed_transitions: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class TenderListResponse(BaseModel):
    """Paginated list response for tenders."""
    items: List[TenderResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
