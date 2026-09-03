"""
Commercial Evaluation Pydantic Schemas
Defines request and response payloads for commercial bid evaluation,
L1/QCBS scoring, rankings, and explainability cards.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CommercialEvaluationResultItem(BaseModel):
    """Schema for a single bid's commercial evaluation result."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tender_id: uuid.UUID
    bid_id: uuid.UUID
    bid_number: Optional[str] = None
    bidder_name: Optional[str] = None
    evaluation_method: str
    eligibility_status: str
    quoted_amount: Optional[Decimal] = None
    currency: str = "INR"
    technical_score: Optional[float] = None
    financial_score: Optional[float] = None
    final_score: Optional[float] = None
    commercial_rank: Optional[int] = None
    rank_label: str
    is_l1: bool = False
    is_tie: bool = False
    has_critical_blocker: bool = False
    blocker_reason: Optional[str] = None
    explanation: str
    formula_snapshot: Dict[str, Any] = Field(default_factory=dict)
    evaluated_at: datetime
    is_current: bool = True


class TenderCommercialEvaluationResponse(BaseModel):
    """Schema for the full commercial evaluation summary of a tender."""
    model_config = ConfigDict(from_attributes=True)

    tender_id: uuid.UUID
    tender_number: str
    tender_title: str
    evaluation_method: str
    technical_weight: Optional[float] = 70.0
    financial_weight: Optional[float] = 30.0
    custom_weights: Optional[Dict[str, Any]] = None
    total_evaluated_bids: int = 0
    eligible_bids_count: int = 0
    ineligible_bids_count: int = 0
    lowest_compliant_price: Optional[Decimal] = None
    results: List[CommercialEvaluationResultItem] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
