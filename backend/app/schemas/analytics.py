"""
Pydantic DTO Schemas for Procurement Analytics & Impact Dashboard (Part 13)
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProcurementImpactResponse(BaseModel):
    measured_time_reduction_percentage: float
    avg_automated_time_ms: float
    avg_manual_baseline_sec: float
    total_validation_cases: int
    dataset_version: str


class OverviewKPIsResponse(BaseModel):
    total_tenders: int
    active_tenders: int
    total_bids: int
    submitted_bids: int
    evaluated_bids: int
    compliance_rate_percentage: Optional[float] = None
    open_reviews_count: int
    high_critical_risk_bids: int
    average_risk_score: Optional[float] = None
    poor_quality_documents_count: int
    average_quality_score: Optional[float] = None
    duplicate_alerts_count: int
    expired_certificates_count: int = 0
    expiring_soon_certificates_count: int = 0
    procurement_impact: Optional[ProcurementImpactResponse] = None


class FailedRequirementSummary(BaseModel):
    requirement_code: str
    title: str
    category: str
    fail_count: int


class CommonFailureReason(BaseModel):
    reason: str
    count: int


class ComplianceAnalyticsResponse(BaseModel):
    distribution: Dict[str, int]
    total_evaluations: int
    overall_compliance_rate: Optional[float] = None
    mandatory_failures_count: int
    top_failed_requirements: List[FailedRequirementSummary]
    common_failure_reasons: List[CommonFailureReason]


class RiskAnalyticsResponse(BaseModel):
    distribution: Dict[str, int]
    total_risk_evaluated_bids: int
    average_risk_score: Optional[float] = None
    overrides_applied_count: int


class VerificationSourceBreakdown(BaseModel):
    verification_type: str
    total: int
    verified: int
    failed: int
    review_required: int
    success_rate: float


class VerificationAnalyticsResponse(BaseModel):
    status_distribution: Dict[str, int]
    total_verifications: int
    source_breakdown: List[VerificationSourceBreakdown]


class QualityDiagnostics(BaseModel):
    blurry_documents: int
    blank_page_documents: int
    low_resolution_documents: int


class DocumentQualityAnalyticsResponse(BaseModel):
    distribution: Dict[str, int]
    total_documents_analyzed: int
    average_quality_score: Optional[float] = None
    diagnostics: QualityDiagnostics


class DuplicateAnalyticsResponse(BaseModel):
    total_duplicate_alerts: int
    match_type_distribution: Dict[str, int]
    status_distribution: Dict[str, int]


class BulkAnalyticsResponse(BaseModel):
    total_jobs: int
    status_distribution: Dict[str, int]
    total_bids_processed: int
    job_success_rate: Optional[float] = None


class ReviewTypeSummary(BaseModel):
    review_type: str
    count: int


class DisqualificationCategorySummary(BaseModel):
    category: str
    count: int


class HumanReviewAndDecisionResponse(BaseModel):
    total_reviews: int
    review_status_distribution: Dict[str, int]
    review_types_breakdown: List[ReviewTypeSummary]
    total_human_decisions: int
    decision_status_distribution: Dict[str, int]
    disqualification_categories: List[DisqualificationCategorySummary]


class TimeSeriesPoint(BaseModel):
    date: str
    submitted_bids: int
    evaluated_bids: int


class TenderSpecificAnalyticsResponse(BaseModel):
    tender_id: uuid.UUID
    tender_number: str
    title: str
    status: str
    estimated_amount: Optional[float] = None
    overview_kpis: OverviewKPIsResponse
    compliance_analytics: ComplianceAnalyticsResponse
    risk_analytics: RiskAnalyticsResponse
    verification_analytics: VerificationAnalyticsResponse
    human_reviews_and_decisions: HumanReviewAndDecisionResponse
