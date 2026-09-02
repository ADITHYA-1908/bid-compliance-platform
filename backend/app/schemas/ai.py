"""
AI Pydantic Schemas for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceRefResponse(BaseModel):
    source_type: str
    source_id: str
    title: str
    page: Optional[int] = None
    rule_code: Optional[str] = None
    summary: str


class AIRecommendationResponse(BaseModel):
    id: Optional[uuid.UUID] = None
    bid_id: uuid.UUID
    score_snapshot_id: Optional[uuid.UUID] = None
    risk_snapshot_id: Optional[uuid.UUID] = None
    recommendation: str
    recommendation_reason: str
    summary: str
    strengths: List[str]
    concerns: List[str]
    review_items: List[str]
    evidence_refs: List[EvidenceRefResponse]
    limitations: List[str]
    confidence_label: str
    model_provider: str
    model_name: str
    prompt_version: str
    guardrail_applied: bool
    guardrail_reason: Optional[str] = None
    is_stale: bool = False
    disclaimer: str = Field(
        default="This AI-assisted recommendation is grounded in deterministic verification, compliance, and risk evidence. Final qualification and award decisions remain with the authorized Procurement Officer."
    )
    created_at: Optional[datetime] = None


class AIQuestionRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500, description="Procurement Officer inquiry regarding the bid")


class AIQuestionResponse(BaseModel):
    question: str
    answer: str
    evidence_refs: List[EvidenceRefResponse]
    limitations: List[str]
    disclaimer: str = Field(
        default="AI answers are grounded in retrieved bid evidence and official compliance records."
    )
