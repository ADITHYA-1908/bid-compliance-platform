"""
Pydantic Schemas for Part 15: Compliance Rule Version History
Defines serialization and validation models for requirement versions,
diff comparisons, rule updates, and re-evaluation requests/responses.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TenderRequirementVersionResponse(BaseModel):
    """Full detail response model for an immutable tender requirement version."""
    id: uuid.UUID
    tender_requirement_id: uuid.UUID
    tender_id: uuid.UUID
    version_number: int
    code: str
    name: str
    description: Optional[str] = None
    category: str
    requirement_type: str
    operator: str
    expected_value: Optional[Any] = None
    unit: Optional[str] = None
    is_mandatory: bool
    is_critical: bool
    weight: Optional[Decimal] = None
    display_order: int
    source_clause: Optional[str] = None
    source_page: Optional[int] = None
    corrigendum_number: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    change_reason: Optional[str] = None
    changed_by_profile_id: Optional[uuid.UUID] = None
    changed_by_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenderRequirementVersionListResponse(BaseModel):
    """List response of all historical versions for a tender requirement."""
    requirement_id: uuid.UUID
    tender_id: uuid.UUID
    code: str
    name: str
    current_version_number: int
    total_versions: int
    versions: List[TenderRequirementVersionResponse]


class TenderRequirementFieldDiff(BaseModel):
    """Field-level difference representation between two versions."""
    field_name: str
    field_label: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    is_different: bool = False
    impact_level: str = "INFO"  # INFO, WARNING, CRITICAL
    impact_summary: str = ""


class TenderRequirementVersionCompareResponse(BaseModel):
    """Comparison diff between two versions of a tender requirement."""
    tender_id: uuid.UUID
    requirement_id: uuid.UUID
    code: str
    name: str
    v1_number: int
    v2_number: int
    v1_id: uuid.UUID
    v2_id: uuid.UUID
    v1_created_at: datetime
    v2_created_at: datetime
    v1_reason: Optional[str] = None
    v2_reason: Optional[str] = None
    v1_author: Optional[str] = None
    v2_author: Optional[str] = None
    has_differences: bool
    differences_count: int
    diffs: List[TenderRequirementFieldDiff]


class TenderRequirementUpdateWithVersionRequest(BaseModel):
    """Payload for updating a tender requirement with explicit versioning tracking."""
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=50)
    requirement_type: Optional[str] = Field(default=None, max_length=50)
    operator: Optional[str] = Field(default=None, max_length=50)
    expected_value: Optional[Any] = None
    unit: Optional[str] = Field(default=None, max_length=50)
    is_mandatory: Optional[bool] = None
    is_critical: Optional[bool] = None
    weight: Optional[Decimal] = Field(default=None, ge=0)
    display_order: Optional[int] = Field(default=None, ge=0)
    source_clause: Optional[str] = Field(default=None, max_length=255)
    source_page: Optional[int] = Field(default=None, ge=1)
    corrigendum_number: Optional[str] = Field(default=None, max_length=100)
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    change_reason: Optional[str] = Field(default=None, description="Mandatory rationale when changing rules in open tenders")
    is_active: Optional[bool] = None


class ReevaluationBidResult(BaseModel):
    """Individual bid re-evaluation outcome."""
    bid_id: uuid.UUID
    bid_number: str
    bidder_name: Optional[str] = None
    previous_compliance_status: Optional[str] = None
    new_compliance_status: str
    status_changed: bool
    is_critical_failure: bool
    score: Optional[Decimal] = None
    risk_level: Optional[str] = None


class ReevaluationResultResponse(BaseModel):
    """Summary response for bulk/single re-evaluation triggered by rule updates."""
    tender_id: uuid.UUID
    tender_number: str
    requirement_id: Optional[uuid.UUID] = None
    rule_code: Optional[str] = None
    new_version_number: Optional[int] = None
    total_bids_reevaluated: int
    status_changes_count: int
    stale_evaluations_cleared: int
    human_decisions_preserved: int
    reevaluated_at: datetime
    bids: List[ReevaluationBidResult]
