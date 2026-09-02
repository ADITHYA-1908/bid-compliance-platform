"""
Evaluation Schemas for Part 7F: Final Score, Risk, AI Recommendation Integration
Defines unified bid-level evaluation summary schemas combining Compliance (Part 6),
Scoring (Part 7A/7B), Risk (Part 7C/7D), and AI Recommendation (Part 7E).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EvaluationComplianceSection(BaseModel):
    """Summarizes Part 6 deterministic compliance findings."""
    model_config = ConfigDict(from_attributes=True)

    total_requirements: int = Field(default=0, description="Total active requirements evaluated")
    pass_count: int = Field(default=0, description="Number of passed rules")
    fail_count: int = Field(default=0, description="Number of failed rules")
    review_count: int = Field(default=0, description="Number of rules flagged for human review")
    pending_count: int = Field(default=0, description="Number of pending/unresolved rules")
    not_applicable_count: int = Field(default=0, description="Number of not applicable rules")
    mandatory_failures_count: int = Field(default=0, description="Number of failed mandatory rules")
    critical_failures_count: int = Field(default=0, description="Number of failed critical rules")
    evaluation_complete: bool = Field(default=False, description="True if no checks remain pending")
    evaluation_version: int = Field(default=1, description="Latest compliance evaluation version")


class EvaluationScoreSection(BaseModel):
    """Summarizes Part 7A/7B deterministic scoring results."""
    model_config = ConfigDict(from_attributes=True)

    overall_compliance_score: Optional[float] = Field(default=None, description="0-100 overall compliance score")
    score_type: str = Field(default="FINAL", description="FINAL or PROVISIONAL")
    scoring_complete: bool = Field(default=False, description="True if all rules evaluated without pending")
    earned_weight: float = Field(default=0.0, description="Total earned weight")
    eligible_weight: float = Field(default=0.0, description="Total eligible weight")
    category_scores: Dict[str, Any] = Field(default_factory=dict, description="Itemized scores by category")
    formula_version: str = Field(default="v1.0", description="Scoring formula version")
    is_stale: bool = Field(default=False, description="True if upstream compliance has changed")
    snapshot_id: Optional[uuid.UUID] = Field(default=None, description="Score snapshot ID")
    scoring_version: int = Field(default=1, description="Score snapshot version")


class EvaluationRiskSection(BaseModel):
    """Summarizes Part 7C/7D deterministic risk assessments and applied critical overrides."""
    model_config = ConfigDict(from_attributes=True)

    base_risk_score: Optional[float] = Field(default=None, description="0-100 base mathematical risk score")
    base_risk_level: Optional[str] = Field(default=None, description="LOW, MEDIUM, HIGH, CRITICAL")
    adjusted_risk_score: Optional[float] = Field(default=None, description="Risk score after critical override floors")
    adjusted_risk_level: Optional[str] = Field(default=None, description="Risk level after critical overrides")
    override_applied: bool = Field(default=False, description="True if one or more critical override floors applied")
    applied_overrides: List[Dict[str, Any]] = Field(default_factory=list, description="Itemized list of applied overrides")
    risk_complete: bool = Field(default=False, description="True if risk calculation is complete")
    is_provisional: bool = Field(default=False, description="True if pending checks or reviews make risk provisional")
    risk_formula_version: str = Field(default="v1.0", description="Base risk formula version")
    override_formula_version: str = Field(default="v1.0", description="Override formula version")
    is_stale: bool = Field(default=False, description="True if upstream score or compliance has changed")
    snapshot_id: Optional[uuid.UUID] = Field(default=None, description="Risk snapshot ID")
    risk_version: int = Field(default=1, description="Risk snapshot version")
    summary_reasons: List[str] = Field(default_factory=list, description="Explainable deterministic risk reasons")


class EvaluationAISection(BaseModel):
    """Summarizes Part 7E grounded AI evaluation recommendations and citations."""
    model_config = ConfigDict(from_attributes=True)

    status: str = Field(default="CURRENT", description="CURRENT, STALE, UNAVAILABLE, or NOT_GENERATED")
    recommendation: Optional[str] = Field(default=None, description="PROCEED, REVIEW_REQUIRED, DO_NOT_PROCEED_WITHOUT_REVIEW, etc.")
    recommendation_reason: Optional[str] = Field(default=None, description="Direct factual justification")
    summary: Optional[str] = Field(default=None, description="Executive summary")
    strengths: List[str] = Field(default_factory=list, description="Itemized key strengths grounded in evidence")
    concerns: List[str] = Field(default_factory=list, description="Itemized concerns grounded in evidence")
    review_items: List[str] = Field(default_factory=list, description="Items requiring officer review")
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list, description="Grounded citations from vector retrieval")
    limitations: List[str] = Field(default_factory=list, description="Advisory data limitations")
    confidence_label: Optional[str] = Field(default=None, description="HIGH, MEDIUM, or LOW")
    model_provider: Optional[str] = Field(default=None, description="LLM provider name")
    model_name: Optional[str] = Field(default=None, description="LLM model name")
    prompt_version: Optional[str] = Field(default=None, description="Prompt version used")
    guardrail_applied: bool = Field(default=False, description="True if recommendation guardrail downgraded output")
    guardrail_reason: Optional[str] = Field(default=None, description="Reason for guardrail adjustment")
    recommendation_id: Optional[uuid.UUID] = Field(default=None, description="AI recommendation record ID")
    is_stale: bool = Field(default=False, description="True if upstream score, risk, or compliance changed")


class CriticalFindingItem(BaseModel):
    """Itemized critical failure or high-risk finding."""
    requirement_code: str
    requirement_name: str
    category: str
    compliance_status: str
    is_mandatory: bool
    is_critical: bool
    risk_override: Optional[str] = None
    finding_reason: str
    evidence_ref: Optional[str] = None


class EvaluationCriticalSummary(BaseModel):
    """High-visibility summary of critical defects, failures, and overrides."""
    critical_failure_present: bool = Field(default=False)
    critical_failure_count: int = Field(default=0)
    critical_review_count: int = Field(default=0)
    critical_override_applied: bool = Field(default=False)
    critical_findings: List[CriticalFindingItem] = Field(default_factory=list)


class EvaluationReviewSummary(BaseModel):
    """Summary of items requiring human procurement officer inspection."""
    human_review_required: bool = Field(default=False)
    total_review_items: int = Field(default=0)
    review_reasons: List[str] = Field(default_factory=list)
    is_provisional: bool = Field(default=False)


class BidEvaluationSummaryResponse(BaseModel):
    """
    Unified Part 7 Bid Evaluation Summary response combining Compliance, Scoring,
    Risk, Critical Overrides, and AI Recommendation.
    """
    model_config = ConfigDict(from_attributes=True)

    bid_id: uuid.UUID
    tender_id: uuid.UUID
    bid_number: str
    tender_number: str
    tender_title: str
    bidder_name: str
    bid_status: str

    compliance: EvaluationComplianceSection
    score: EvaluationScoreSection
    risk: EvaluationRiskSection
    ai_recommendation: EvaluationAISection

    critical_summary: EvaluationCriticalSummary
    review_summary: EvaluationReviewSummary

    evaluation_complete: bool = Field(
        default=False,
        description="True if deterministic compliance, scoring, and risk are complete (independent of AI status)"
    )
    human_review_required: bool = Field(
        default=False,
        description="True if deterministic compliance reviews, critical reviews, or risk overrides require inspection"
    )
    stale_components: List[str] = Field(
        default_factory=list,
        description="List of stale components (e.g. ['SCORE', 'RISK', 'AI'])"
    )
    final_decision_status: str = Field(
        default="NOT_MADE",
        description="Final procurement decision status (reserved for Part 8; always NOT_MADE in Part 7)"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)
