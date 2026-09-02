"""
Compliance Engine Pydantic Schemas for Part 6A
Defines serialization models for compliance evaluation requests, rule results, and bid-level summaries.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ComplianceReviewItemResponse(BaseModel):
    """Schema representing an item requiring human review."""
    model_config = ConfigDict(from_attributes=True)

    requirement_id: uuid.UUID
    requirement_code: str
    requirement_name: str
    category: str
    compliance_status: str
    review_type: Optional[str] = None
    reason: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    source_name: Optional[str] = None
    is_mandatory: bool = True
    is_critical: bool = False


class ComplianceResultItemResponse(BaseModel):
    """Schema representing an individual evaluated TenderRequirement result."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bid_id: uuid.UUID
    tender_id: uuid.UUID
    tender_requirement_id: uuid.UUID
    requirement_code: str
    requirement_name: str
    category: str
    requirement_type: str
    compliance_status: str
    actual_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    operator: Optional[str] = None
    reason: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    source_verification_ids: Optional[List[str]] = None
    is_mandatory: bool = True
    is_critical: bool = False
    critical_failure: bool = False
    weight: Optional[Decimal] = None
    rule_version_id: Optional[uuid.UUID] = None
    rule_version_number: Optional[int] = 1
    evaluation_version: int = 1
    is_current: bool = True
    evaluated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ComplianceSummaryCounts(BaseModel):
    """Aggregate counts for rule compliance states."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    review: int = 0
    pending: int = 0
    not_applicable: int = 0
    blocked: int = 0
    mandatory_failures: int = 0
    critical_failures: int = 0


class BidComplianceSummaryResponse(BaseModel):
    """Complete bid compliance evaluation summary response."""
    model_config = ConfigDict(from_attributes=True)

    bid_id: uuid.UUID
    tender_id: uuid.UUID
    tender_number: Optional[str] = None
    bidder_name: Optional[str] = None
    compliance_evaluation_complete: bool = False
    counts: ComplianceSummaryCounts
    results: List[ComplianceResultItemResponse] = Field(default_factory=list)
    review_items: List[ComplianceReviewItemResponse] = Field(default_factory=list)
    evaluated_at: Optional[datetime] = None
