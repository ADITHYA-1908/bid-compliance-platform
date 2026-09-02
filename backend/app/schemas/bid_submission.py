"""
Pydantic Schemas for Part 3E: Bid Review & Final Submission Workflow
Defines schemas for submission readiness checks, final submit payload, and submission receipts.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BidSubmissionReadinessChecks(BaseModel):
    """Granular boolean indicators for each mandatory pre-submission criterion."""
    profile_complete: bool
    bid_details_complete: bool
    mandatory_documents_complete: bool
    tender_open: bool
    deadline_valid: bool


class BidSubmissionReadinessResponse(BaseModel):
    """Comprehensive readiness evaluation returned to the bidder review workspace."""
    bid_id: uuid.UUID
    bid_number: str
    ready_to_submit: bool
    checks: BidSubmissionReadinessChecks
    missing_required_fields: List[str] = Field(default_factory=list)
    missing_documents: List[str] = Field(default_factory=list)
    tender_title: str
    tender_number: str
    tender_status: str
    submission_end_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BidSubmitPayload(BaseModel):
    """Payload provided by the bidder upon final submission."""
    declaration_accepted: bool = Field(
        ...,
        description="Must be true to certify bid accuracy, completeness, and submit final proposal.",
    )


class BidSubmitResponse(BaseModel):
    """Tamper-evident submission confirmation and receipt."""
    id: uuid.UUID
    bid_number: str
    submission_reference: str
    status: str
    submitted_at: datetime
    submitted_by_email: str
    submitted_by_name: str
    tender_id: uuid.UUID
    tender_number: str
    tender_title: str
    bidder_organization_name: str
    quoted_amount: Optional[Decimal] = None
    currency: str = "INR"
    message: str = "Bid proposal submitted successfully."

    model_config = ConfigDict(from_attributes=True)
