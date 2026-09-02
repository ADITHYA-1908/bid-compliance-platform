import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.authorization import require_role
from app.db.session import get_db
from app.db.models.user import User
from app.schemas.compliance import BidComplianceSummaryResponse
from app.schemas.scoring import BidScoringFoundationResponse
from app.schemas.risk import BidRiskAssessmentResponse
from app.schemas.ai import (
    AIQuestionRequest,
    AIQuestionResponse,
    AIRecommendationResponse,
)
from app.schemas.evaluation import BidEvaluationSummaryResponse
from app.schemas.procurement_dashboard import (
    ProcurementDashboardSummaryResponse,
    TenderBidEvaluationsListResponse,
)
from app.schemas.bid_comparison import (
    BidComparisonRequest,
    ShortlistActionRequest,
    ShortlistRecordResponse,
    BidComparisonResponse,
)
from app.schemas.human_review import (
    ReviewQueueResponse,
    ReviewDetailResponse,
    AddReviewNoteRequest,
    ResolveReviewRequest,
)
from app.schemas.bid_decision import (
    BidDecisionResponse,
    BidDecisionHistoryItem,
    RecordBidDecisionRequest,
)
from app.schemas.audit import (
    AuditEventItemResponse,
    AuditListResponse,
)
from app.schemas.procurement_report import (
    BidEvaluationReportResponse,
    TenderReportResponse,
)
from app.schemas.bulk_evaluation import (
    BulkEvaluationJobCreateResponse,
    BulkEvaluationJobStatusResponse,
    BulkEvaluationJobItemResponse,
    BulkEvaluationJobItemsListResponse,
    BulkEvaluationRetryResponse,
    BulkEvaluationCancelResponse,
)
from app.schemas.duplicate_detection import (
    DuplicateScanResponse,
    DuplicateMatchListResponse,
    DuplicateMatchDetailResponse,
    DuplicateReviewRequest,
    DuplicateReviewResponse,
)
from app.schemas.document_quality import DocumentQualityResponse
from app.services.compliance_service import evaluate_bid_compliance, get_bid_compliance
from app.services.scoring_service import calculate_and_save_bid_score, get_bid_score
from app.services.risk_service import calculate_and_save_bid_risk, get_bid_risk
from app.services.ai.ai_recommendation_service import AIRecommendationService
from app.services.evaluation.bid_evaluation_service import BidEvaluationService
from app.services.procurement.procurement_dashboard_service import ProcurementDashboardService
from app.services.procurement.bid_comparison_service import BidComparisonService
from app.services.procurement.human_review_service import HumanReviewService
from app.services.procurement.bid_decision_service import BidDecisionService
from app.services.procurement.bulk_evaluation_service import BulkEvaluationService
from app.services.procurement.duplicate_detection_service import DuplicateDetectionService
from app.services.document_quality_service import DocumentQualityService
from app.services.audit.audit_service import AuditService
from app.services.reports.procurement_report_service import ProcurementReportService
from fastapi.responses import Response

router = APIRouter()


@router.get("/test", summary="Procurement Officer authorization test endpoint")
def procurement_test(
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Role-protected endpoint accessible only to authenticated PROCUREMENT_OFFICER users.
    """
    return {
        "message": "Procurement Officer access granted",
        "role": "PROCUREMENT_OFFICER",
        "user_email": current_user.email,
        "organization": (
            current_user.profile.organization.name
            if current_user.profile and current_user.profile.organization
            else None
        ),
    }


@router.get(
    "/bids/{bid_id}/compliance",
    response_model=BidComplianceSummaryResponse,
    summary="Get compliance results for a tender bid (Procurement Officer)",
)
def get_procurement_bid_compliance(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Allows Procurement Officers to view compliance results for bids on tenders owned by their organization.
    """
    return get_bid_compliance(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.post(
    "/bids/{bid_id}/compliance/evaluate",
    response_model=BidComplianceSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger compliance evaluation for a tender bid (Procurement Officer)",
)
def evaluate_procurement_bid_compliance(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Allows Procurement Officers to trigger compliance evaluation for bids on tenders owned by their organization.
    """
    return evaluate_bid_compliance(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.get(
    "/bids/{bid_id}/score",
    response_model=BidScoringFoundationResponse,
    summary="Get scoring foundation snapshot for a tender bid (Procurement Officer)",
)
def get_procurement_bid_score(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Allows Procurement Officers to view the deterministic scoring foundation snapshot for a bid.
    """
    return get_bid_score(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.post(
    "/bids/{bid_id}/score/calculate",
    response_model=BidScoringFoundationResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger scoring foundation calculation for a tender bid (Procurement Officer)",
)
def calculate_procurement_bid_score(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Allows Procurement Officers to trigger a new scoring calculation version for a bid.
    """
    return calculate_and_save_bid_score(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


# =============================================================================
# Part 7C: Deterministic Risk Assessment Endpoints (Procurement Officer)
# =============================================================================

@router.get(
    "/bids/{bid_id}/risk",
    response_model=BidRiskAssessmentResponse,
    summary="Get base risk assessment snapshot for a tender bid (Procurement Officer)",
)
def get_procurement_bid_risk(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Allows Procurement Officers to view the deterministic base risk assessment snapshot for a bid.
    """
    return get_bid_risk(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.post(
    "/bids/{bid_id}/risk/calculate",
    response_model=BidRiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger base risk calculation for a tender bid (Procurement Officer)",
)
def calculate_procurement_bid_risk(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Allows Procurement Officers to trigger a new base risk calculation version for a bid.
    """
    return calculate_and_save_bid_risk(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


# =============================================================================
# Part 7E: RAG + AI Recommendation & Evidence-Based Explanation Endpoints
# =============================================================================

@router.get(
    "/bids/{bid_id}/ai/recommendation",
    response_model=Optional[AIRecommendationResponse],
    summary="Get current AI evaluation recommendation for a tender bid (Procurement Officer)",
)
def get_procurement_bid_ai_recommendation(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves the current evidence-grounded AI evaluation recommendation for a bid,
    indicating if upstream changes have made the recommendation stale.
    """
    rec, is_stale = AIRecommendationService.get_bid_recommendation(
        db=db,
        user=current_user,
        bid_id=bid_id,
    )
    if not rec:
        return None

    return AIRecommendationResponse(
        id=rec.id,
        bid_id=rec.bid_id,
        score_snapshot_id=rec.score_snapshot_id,
        risk_snapshot_id=rec.risk_snapshot_id,
        recommendation=rec.recommendation,
        recommendation_reason=rec.recommendation_reason,
        summary=rec.summary,
        strengths=rec.strengths or [],
        concerns=rec.concerns or [],
        review_items=rec.review_items or [],
        evidence_refs=rec.evidence_refs or [],
        limitations=rec.limitations or [],
        confidence_label=rec.confidence_label,
        model_provider=rec.model_provider,
        model_name=rec.model_name,
        prompt_version=rec.prompt_version,
        guardrail_applied=rec.guardrail_applied,
        guardrail_reason=rec.guardrail_reason,
        is_stale=is_stale,
        created_at=rec.created_at,
    )


@router.post(
    "/bids/{bid_id}/ai/recommendation",
    response_model=AIRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate or refresh AI evaluation recommendation for a tender bid (Procurement Officer)",
)
def generate_procurement_bid_ai_recommendation(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Triggers RAG indexing, scoped vector retrieval, grounded prompt synthesis,
    and deterministic guardrail validation to generate a non-binding AI evaluation recommendation.
    """
    rec = AIRecommendationService.generate_bid_recommendation(
        db=db,
        user=current_user,
        bid_id=bid_id,
        force_refresh=True,
    )

    return AIRecommendationResponse(
        id=rec.id,
        bid_id=rec.bid_id,
        score_snapshot_id=rec.score_snapshot_id,
        risk_snapshot_id=rec.risk_snapshot_id,
        recommendation=rec.recommendation,
        recommendation_reason=rec.recommendation_reason,
        summary=rec.summary,
        strengths=rec.strengths or [],
        concerns=rec.concerns or [],
        review_items=rec.review_items or [],
        evidence_refs=rec.evidence_refs or [],
        limitations=rec.limitations or [],
        confidence_label=rec.confidence_label,
        model_provider=rec.model_provider,
        model_name=rec.model_name,
        prompt_version=rec.prompt_version,
        guardrail_applied=rec.guardrail_applied,
        guardrail_reason=rec.guardrail_reason,
        is_stale=False,
        created_at=rec.created_at,
    )


@router.post(
    "/bids/{bid_id}/ai/ask",
    response_model=AIQuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask an evidence-grounded question about a bid (Procurement Officer)",
)
def ask_procurement_bid_ai_question(
    bid_id: uuid.UUID,
    request: AIQuestionRequest,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Allows Procurement Officers to ask interactive questions regarding a submitted bid.
    Answers are synthesized strictly from retrieved bid evidence with citation IDs.
    """
    qa_output = AIRecommendationService.ask_bid_question(
        db=db,
        user=current_user,
        bid_id=bid_id,
        question=request.question,
    )

    return AIQuestionResponse(
        question=qa_output.question,
        answer=qa_output.answer,
        evidence_refs=[
            {
                "source_type": ref.source_type,
                "source_id": ref.source_id,
                "title": ref.title,
                "page": ref.page,
                "rule_code": ref.rule_code,
                "summary": ref.summary,
            }
            for ref in qa_output.evidence_refs
        ],
        limitations=qa_output.limitations,
    )


# =============================================================================
# Part 7F: Unified Bid Evaluation Endpoints (Procurement Officer)
# =============================================================================

@router.get(
    "/bids/{bid_id}/evaluation",
    response_model=BidEvaluationSummaryResponse,
    summary="Get unified Part 7 bid evaluation summary (Procurement Officer)",
)
def get_procurement_bid_unified_evaluation(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Returns the comprehensive, unified Part 7 evaluation summary for a bid combining
    deterministic Compliance findings, Category & Overall Scoring, Base & Adjusted Risk,
    Critical Overrides, Review summaries, and Grounded AI Recommendations.
    """
    return BidEvaluationService.get_unified_evaluation(
        db=db,
        user=current_user,
        bid_id=bid_id,
    )


@router.post(
    "/bids/{bid_id}/evaluation/refresh",
    response_model=BidEvaluationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh deterministic score and risk evaluations for a bid (Procurement Officer)",
)
def refresh_procurement_bid_evaluation(
    bid_id: uuid.UUID,
    refresh_ai: bool = False,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Deterministically recalculates the bid's scoring and risk assessments.
    If refresh_ai is True, explicitly re-indexes RAG knowledge and regenerates the AI recommendation.
    """
    return BidEvaluationService.refresh_bid_evaluation(
        db=db,
        user=current_user,
        bid_id=bid_id,
        refresh_ai=refresh_ai,
    )


@router.post(
    "/bids/{bid_id}/evaluation/ai/regenerate",
    response_model=BidEvaluationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Explicitly regenerate AI evaluation recommendation for a bid (Procurement Officer)",
)
def regenerate_procurement_bid_ai_evaluation(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Explicitly forces a fresh RAG knowledge indexing and AI recommendation synthesis for the bid.
    """
    return BidEvaluationService.refresh_bid_evaluation(
        db=db,
        user=current_user,
        bid_id=bid_id,
        refresh_ai=True,
    )


# =============================================================================
# Part 8A: Procurement Evaluation Dashboard Foundation Endpoints
# =============================================================================

@router.get(
    "/dashboard",
    response_model=ProcurementDashboardSummaryResponse,
    summary="Get procurement officer dashboard overview and metrics (Procurement Officer)",
)
def get_procurement_dashboard(
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Returns aggregated metrics and active tender evaluation statuses for the authenticated
    Procurement Officer's procuring entity.
    """
    return ProcurementDashboardService.get_dashboard_summary(
        db=db,
        user=current_user,
    )


@router.get(
    "/tenders/{tender_id}/evaluations",
    response_model=TenderBidEvaluationsListResponse,
    summary="Get paginated submitted bids evaluation matrix for a tender (Procurement Officer)",
)
def get_tender_bid_evaluations_list(
    tender_id: uuid.UUID,
    search: Optional[str] = None,
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    review_required: Optional[bool] = None,
    critical_only: Optional[bool] = None,
    recommendation: Optional[str] = None,
    shortlisted_only: Optional[bool] = None,
    sort_by: str = "submitted_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Returns the paginated, filtered, and sorted evaluation matrix for all submitted bids
    of a specific tender owned by the officer's organization.
    """
    return ProcurementDashboardService.get_tender_bid_evaluations(
        db=db,
        user=current_user,
        tender_id=tender_id,
        search=search,
        status_filter=status,
        risk_level=risk_level,
        review_required=review_required,
        critical_only=critical_only,
        recommendation=recommendation,
        shortlisted_only=shortlisted_only,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Part 8B: Bid Comparison & Shortlisting View Endpoints
# =============================================================================

@router.post(
    "/tenders/{tender_id}/compare-bids",
    response_model=BidComparisonResponse,
    summary="Compare 2 to 5 submitted bids side-by-side (Procurement Officer)",
)
def compare_tender_bids(
    tender_id: uuid.UUID,
    request: BidComparisonRequest,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Executes a side-by-side comparative analysis of 2 to 5 submitted bids belonging
    strictly to the specified tender. Returns overall compliance scores, category matrices,
    risk assessments, defects, review items, and requirement-by-requirement determinations.
    """
    return BidComparisonService.compare_tender_bids(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_ids=request.bid_ids,
    )


@router.post(
    "/tenders/{tender_id}/bids/{bid_id}/shortlist",
    response_model=ShortlistRecordResponse,
    summary="Add submitted bid to shortlist for further review (Procurement Officer)",
)
def add_bid_to_shortlist(
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
    request: ShortlistActionRequest = ShortlistActionRequest(),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Marks a submitted bid as SHORTLISTED for further detailed review by the Procurement Officer.
    This is a human-controlled decision support action and does NOT constitute qualification or award.
    """
    return BidComparisonService.add_to_shortlist(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
        reason=request.reason,
    )


@router.delete(
    "/tenders/{tender_id}/bids/{bid_id}/shortlist",
    response_model=ShortlistRecordResponse,
    summary="Remove submitted bid from shortlist (Procurement Officer)",
)
def remove_bid_from_shortlist(
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
    reason: Optional[str] = None,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Removes a submitted bid from the shortlist.
    """
    return BidComparisonService.remove_from_shortlist(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
        reason=reason,
    )


@router.get(
    "/tenders/{tender_id}/shortlists",
    response_model=List[ShortlistRecordResponse],
    summary="Get all shortlisted bids for a tender (Procurement Officer)",
)
def get_tender_shortlists(
    tender_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves all currently shortlisted bids and their rationale for the specified tender.
    """
    return BidComparisonService.get_tender_shortlists(
        db=db,
        user=current_user,
        tender_id=tender_id,
    )


# =========================================================================
# Part 8C: Human Review & Evidence Inspection Endpoints
# =========================================================================

@router.get(
    "/reviews",
    response_model=ReviewQueueResponse,
    summary="Get human review queue with filters, search, and KPIs (Procurement Officer)",
)
def get_human_review_queue(
    tender_id: Optional[uuid.UUID] = None,
    bid_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    review_type: Optional[str] = None,
    category: Optional[str] = None,
    critical_only: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves the paginated human review queue for the Procurement Officer's organization,
    with real-time KPI counts, search across vendors/clauses/IDs, and multi-dimensional filters.
    """
    return HumanReviewService.get_review_queue(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
        status_filter=status,
        severity=severity,
        review_type=review_type,
        category=category,
        critical_only=critical_only,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewDetailResponse,
    summary="Get complete evidence inspection workspace package for a review item (Procurement Officer)",
)
def get_human_review_detail(
    review_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Loads the full evidence package for a HumanReviewItem: requirement clause, actual vs expected,
    source document provenance & snippet, verification & sandbox transparency, cross-document comparison,
    advisory AI explanation, and notes history.
    """
    return HumanReviewService.get_review_detail(
        db=db,
        user=current_user,
        review_id=review_id,
    )


@router.post(
    "/reviews/{review_id}/start",
    response_model=ReviewDetailResponse,
    summary="Start reviewing / claim a review item (Procurement Officer)",
)
def start_human_review(
    review_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Claims a review item and transitions its status from OPEN to IN_REVIEW.
    """
    return HumanReviewService.start_review(
        db=db,
        user=current_user,
        review_id=review_id,
    )


@router.post(
    "/reviews/{review_id}/notes",
    response_model=ReviewDetailResponse,
    summary="Add an auditable remark or note to a review item (Procurement Officer)",
)
def add_human_review_note(
    review_id: uuid.UUID,
    request: AddReviewNoteRequest,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Appends an immutable, auditable remark to the review item's activity history.
    """
    return HumanReviewService.add_review_note(
        db=db,
        user=current_user,
        review_id=review_id,
        req=request,
    )


@router.post(
    "/reviews/{review_id}/resolve",
    response_model=ReviewDetailResponse,
    summary="Resolve or escalate a human review item with mandatory rationale (Procurement Officer)",
)
def resolve_human_review(
    review_id: uuid.UUID,
    request: ResolveReviewRequest,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Resolves a HumanReviewItem (CONFIRMED, REJECTED, NEEDS_MORE_EVIDENCE, ESCALATED, NOT_APPLICABLE).
    Atomically updates effective requirement compliance, recalculates deterministic Score/Risk,
    and invalidates downstream AI recommendations.
    """
    return HumanReviewService.resolve_review(
        db=db,
        user=current_user,
        review_id=review_id,
        req=request,
    )


@router.post(
    "/tenders/{tender_id}/bids/{bid_id}/sync-reviews",
    response_model=List[ReviewDetailResponse],
    summary="Sync review items for a submitted bid (Procurement Officer)",
)
def sync_bid_reviews(
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Idempotently synchronizes HumanReviewItems from current compliance, verification, and document extractions.
    """
    items = HumanReviewService.sync_review_items_for_bid(db=db, bid_id=bid_id)
    return [HumanReviewService.get_review_detail(db=db, user=current_user, review_id=i.id) for i in items]


# =============================================================================
# Part 8D: Final Human Decision Workflow Endpoints
# =============================================================================

@router.get(
    "/tenders/{tender_id}/bids/{bid_id}/decision",
    response_model=BidDecisionResponse,
    summary="Get current authoritative human decision and readiness for a bid (Procurement Officer)",
)
def get_bid_decision(
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves the current authoritative human-controlled qualification decision (QUALIFIED, DISQUALIFIED, UNDER_REVIEW, NOT_DECIDED)
    along with comprehensive decision readiness telemetry and evaluation snapshot provenance.
    """
    return BidDecisionService.get_current_decision(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
    )


@router.post(
    "/tenders/{tender_id}/bids/{bid_id}/decision",
    response_model=BidDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Record or update a human-controlled bid qualification decision (Procurement Officer)",
)
def record_bid_decision(
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
    request: RecordBidDecisionRequest,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Authoritatively records a human-controlled bid qualification decision with required rationale.
    Enforces qualification readiness safeguards, transactions safely supersede prior decisions,
    captures snapshot references, and preserves submission lifecycle and tender status.
    """
    return BidDecisionService.record_decision(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
        req=request,
    )


@router.get(
    "/tenders/{tender_id}/bids/{bid_id}/decisions",
    response_model=List[BidDecisionHistoryItem],
    summary="Get chronological decision history for a bid (Procurement Officer)",
)
def get_bid_decision_history(
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Fetches full chronological decision version history for auditability and compliance inspection.
    """
    return BidDecisionService.get_decision_history(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
    )


# =============================================================================
# Part 8E: Audit Trail & Decision History Endpoints
# =============================================================================

@router.get(
    "/audit",
    response_model=AuditListResponse,
    summary="Query multi-dimensional procurement audit trail (Procurement Officer)",
)
def get_procurement_audit_events(
    tender_id: Optional[uuid.UUID] = None,
    bid_id: Optional[uuid.UUID] = None,
    actor_user_id: Optional[uuid.UUID] = None,
    event_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Queries and filters immutable audit events with strict multi-tenant scoping, full-text search,
    real-time KPI calculation, and server-side pagination.
    """
    return AuditService.get_audit_events(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        entity_type=entity_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/tenders/{tender_id}/audit",
    response_model=AuditListResponse,
    summary="Get audit trail for a specific tender (Procurement Officer)",
)
def get_tender_audit_events(
    tender_id: uuid.UUID,
    event_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves the tenant-scoped audit event log for a specific procurement tender.
    """
    return AuditService.get_audit_events(
        db=db,
        user=current_user,
        tender_id=tender_id,
        event_type=event_type,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/tenders/{tender_id}/bids/{bid_id}/audit",
    response_model=AuditListResponse,
    summary="Get audit trail for a specific proposal (Procurement Officer)",
)
def get_bid_audit_events(
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves the tenant-scoped audit event log for a specific proposal.
    """
    return AuditService.get_audit_events(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/tenders/{tender_id}/bids/{bid_id}/timeline",
    response_model=List[AuditEventItemResponse],
    summary="Get chronological lifecycle timeline for a proposal (Procurement Officer)",
)
def get_bid_timeline(
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves the complete chronological lifecycle event sequence for a proposal.
    """
    return AuditService.get_bid_timeline(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
    )


# =============================================================================
# Part 8E: Procurement Evaluation Reports & PDF Exports
# =============================================================================

@router.get(
    "/tenders/{tender_id}/report",
    response_model=TenderReportResponse,
    summary="Get structured Tender Evaluation Summary report (Procurement Officer)",
)
def get_tender_evaluation_report(
    tender_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Builds a comprehensive Tender Evaluation Summary Report DTO from stored evaluation facts.
    """
    return ProcurementReportService.get_tender_summary_report(
        db=db,
        user=current_user,
        tender_id=tender_id,
    )


@router.get(
    "/tenders/{tender_id}/report/pdf",
    summary="Download Tender Evaluation Summary PDF report (Procurement Officer)",
)
def download_tender_evaluation_pdf(
    tender_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Generates and downloads a publication-grade vector PDF report for the Tender Evaluation Summary.
    """
    pdf_bytes = ProcurementReportService.generate_tender_summary_pdf(
        db=db,
        user=current_user,
        tender_id=tender_id,
    )
    filename = f"tender_evaluation_summary_{tender_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/tenders/{tender_id}/bids/{bid_id}/report",
    response_model=BidEvaluationReportResponse,
    summary="Get structured Bid Compliance & Decision Dossier (Procurement Officer)",
)
def get_bid_evaluation_report(
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Builds a comprehensive Bid Evaluation Dossier without mutating evaluations or running LLMs.
    """
    return ProcurementReportService.get_bid_evaluation_report(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
    )


@router.get(
    "/tenders/{tender_id}/bids/{bid_id}/report/pdf",
    summary="Download Bid Evaluation Dossier PDF report (Procurement Officer)",
)
def download_bid_evaluation_pdf(
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Generates and downloads a publication-grade vector PDF report for the Bid Evaluation Dossier.
    """
    pdf_bytes = ProcurementReportService.generate_bid_evaluation_pdf(
        db=db,
        user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
    )
    filename = f"bid_evaluation_dossier_{bid_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# =========================================================================
# Part 9: Bulk Verification & Batch Processing Endpoints
# =========================================================================

@router.post(
    "/tenders/{tender_id}/bulk-evaluation",
    response_model=BulkEvaluationJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Tender-Level Bulk Bid Verification & Evaluation Batch",
)
def trigger_bulk_evaluation(
    tender_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Creates and queues a bulk evaluation job for all eligible submitted bids on a tender.
    Dispatches asynchronous background execution across document extraction, claims verification,
    compliance evaluation, scoring, risk calculation, and human review synchronization.
    """
    job = BulkEvaluationService.create_bulk_evaluation_job(
        db=db,
        user=current_user,
        tender_id=tender_id,
    )

    # Queue background execution
    background_tasks.add_task(
        BulkEvaluationService.run_bulk_evaluation_pipeline,
        job_id=job.id,
        user_id=current_user.id,
    )

    return BulkEvaluationJobCreateResponse(
        job_id=job.id,
        tender_id=job.tender_id,
        status=job.status,
        total_bids=job.total_bids,
        message=f"Bulk evaluation job created and queued for {job.total_bids} submitted bids.",
        created_at=job.created_at,
    )


@router.get(
    "/tenders/{tender_id}/bulk-evaluation/active",
    response_model=Optional[BulkEvaluationJobStatusResponse],
    summary="Get active or latest bulk evaluation job for a tender",
)
def get_active_tender_bulk_evaluation(
    tender_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves the active (or latest) bulk evaluation job status and telemetry for a specific tender.
    """
    return BulkEvaluationService.get_active_job_for_tender(
        db=db,
        user=current_user,
        tender_id=tender_id,
    )


@router.get(
    "/bulk-evaluations/{job_id}",
    response_model=BulkEvaluationJobStatusResponse,
    summary="Get bulk evaluation job status and progress summary",
)
def get_bulk_evaluation_status(
    job_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves real-time execution status, percentage completion, and diagnostic counts for a job.
    """
    return BulkEvaluationService.get_job_status(
        db=db,
        user=current_user,
        job_id=job_id,
    )


@router.get(
    "/bulk-evaluations/{job_id}/items",
    response_model=BulkEvaluationJobItemsListResponse,
    summary="Get paginated list of per-bid items in a bulk evaluation job",
)
def get_bulk_evaluation_items(
    job_id: uuid.UUID,
    item_status: Optional[str] = Query(None, alias="status", description="Filter by item status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated per-bid item diagnostics, stage progressions, and error details.
    """
    return BulkEvaluationService.get_job_items(
        db=db,
        user=current_user,
        job_id=job_id,
        status_filter=item_status,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/bulk-evaluations/{job_id}/retry-failed",
    response_model=BulkEvaluationRetryResponse,
    summary="Retry all failed items in a bulk evaluation job",
)
def retry_failed_bulk_items(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Re-queues all items in the batch that experienced technical processing failures and restarts background execution.
    """
    retried_count = BulkEvaluationService.retry_failed_job_items(
        db=db,
        user=current_user,
        job_id=job_id,
    )

    if retried_count > 0:
        background_tasks.add_task(
            BulkEvaluationService.run_bulk_evaluation_pipeline,
            job_id=job_id,
            user_id=current_user.id,
        )

    return BulkEvaluationRetryResponse(
        job_id=job_id,
        retried_count=retried_count,
        status="QUEUED" if retried_count > 0 else "NO_FAILED_ITEMS",
        message=f"Re-queued {retried_count} failed items for processing." if retried_count > 0 else "No failed items to retry.",
    )


@router.post(
    "/bulk-evaluations/{job_id}/items/{item_id}/retry",
    response_model=BulkEvaluationJobItemResponse,
    summary="Retry an individual failed item in a bulk evaluation job",
)
def retry_single_bulk_item(
    job_id: uuid.UUID,
    item_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Re-queues a single failed item and triggers background processing.
    """
    item = BulkEvaluationService.retry_single_job_item(
        db=db,
        user=current_user,
        job_id=job_id,
        item_id=item_id,
    )

    background_tasks.add_task(
        BulkEvaluationService.run_bulk_evaluation_pipeline,
        job_id=job_id,
        user_id=current_user.id,
    )

    return BulkEvaluationJobItemResponse(
        id=item.id,
        job_id=item.job_id,
        bid_id=item.bid_id,
        bid_number=item.bid.bid_number if item.bid else None,
        bidder_name=item.bid.bidder_organization.name if item.bid and item.bid.bidder_organization else None,
        status=item.status,
        current_stage=item.current_stage,
        document_processing_status=item.document_processing_status,
        verification_status=item.verification_status,
        compliance_status=item.compliance_status,
        score_status=item.score_status,
        risk_status=item.risk_status,
        final_score=item.final_score,
        risk_level=item.risk_level,
        review_required=item.review_required,
        critical_findings_count=item.critical_findings_count,
        error_code=item.error_code,
        error_message=item.error_message,
        is_retryable=item.is_retryable,
        started_at=item.started_at,
        completed_at=item.completed_at,
        created_at=item.created_at,
    )


@router.post(
    "/bulk-evaluations/{job_id}/cancel",
    response_model=BulkEvaluationCancelResponse,
    summary="Cancel an active or queued bulk evaluation job",
)
def cancel_bulk_evaluation(
    job_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Cancels a running or queued bulk evaluation job, safely halting processing of remaining items.
    """
    job = BulkEvaluationService.cancel_bulk_evaluation_job(
        db=db,
        user=current_user,
        job_id=job_id,
    )
    return BulkEvaluationCancelResponse(
        job_id=job.id,
        status=job.status,
        message=f"Bulk evaluation job '{job.id}' has been cancelled.",
    )


# ==============================================================================
# Part 10: Duplicate / Reuse Document Detection Endpoints
# ==============================================================================


@router.post(
    "/tenders/{tender_id}/duplicate-scan",
    response_model=DuplicateScanResponse,
    summary="Execute duplicate and document reuse scan across submitted bids",
)
def scan_tender_duplicates(
    tender_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Scans all active submitted bids for a tender using multi-signal analysis (file hashes,
    normalized text hashes, structured extracted fields, and semantic similarity) to detect
    cross-bidder document reuse anomalies. Legitimate same-bidder version replacements are excluded.
    """
    return DuplicateDetectionService.scan_tender_for_duplicates(
        db=db,
        user=current_user,
        tender_id=tender_id,
    )


@router.get(
    "/tenders/{tender_id}/duplicate-matches",
    response_model=DuplicateMatchListResponse,
    summary="List duplicate/reuse match alerts for a tender",
)
def list_tender_duplicate_matches(
    tender_id: uuid.UUID,
    status: Optional[str] = Query(None, description="Filter by status (DETECTED, REVIEW_REQUIRED, CONFIRMED_BENIGN, CONFIRMED_REUSE, DISMISSED)"),
    match_type: Optional[str] = Query(None, description="Filter by match type (EXACT_FILE_DUPLICATE, CONTENT_DUPLICATE, STRUCTURED_DATA_MATCH, HIGH_SIMILARITY, POSSIBLE_REUSE)"),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves list of detected duplicate document matches for a tender with breakdown summary counts.
    """
    return DuplicateDetectionService.get_tender_duplicate_matches(
        db=db,
        user=current_user,
        tender_id=tender_id,
        status_filter=status,
        match_type_filter=match_type,
    )


@router.get(
    "/duplicate-matches/{match_id}",
    response_model=DuplicateMatchDetailResponse,
    summary="Get side-by-side duplicate match comparison details",
)
def get_duplicate_match_details(
    match_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves full side-by-side inspection details for a duplicate match including document metadata,
    matching structured fields, text snippets, and reviewer notes.
    """
    return DuplicateDetectionService.get_duplicate_match_detail(
        db=db,
        user=current_user,
        match_id=match_id,
    )


@router.post(
    "/duplicate-matches/{match_id}/review",
    response_model=DuplicateReviewResponse,
    summary="Submit Procurement Officer review decision on a duplicate document alert",
)
def review_duplicate_match_endpoint(
    match_id: uuid.UUID,
    payload: DuplicateReviewRequest,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Records human Procurement Officer evaluation on a duplicate document alert:
    - CONFIRMED_BENIGN: Legitimate co-submission, authorized multi-dealer certificate, or common public template.
    - CONFIRMED_REUSE: Confirmed unauthorized cross-bidder document reuse.
    - DISMISSED: Coincidence / false alarm.
    """
    return DuplicateDetectionService.review_duplicate_match(
        db=db,
        user=current_user,
        match_id=match_id,
        review_dto=payload,
    )


# =============================================================================
# Part 11: Document Quality Diagnostics Inspection Endpoint
# =============================================================================

@router.get(
    "/tenders/{tender_id}/bids/{bid_id}/documents/{document_id}/quality",
    response_model=DocumentQualityResponse,
    summary="Get detailed document quality diagnostics & page breakdown for Procurement Officer",
)
def read_procurement_document_quality(
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for Procurement Officers to inspect complete document quality diagnostics:
    deterministic quality score (0-100), quality level (GOOD/ACCEPTABLE/POOR/UNUSABLE),
    blur sharpness, blank page markers, OCR confidence, skew metrics, and page issues.
    Strict multi-tenant organization boundary enforced.
    """
    return DocumentQualityService.get_document_quality_for_procurement(
        db=db,
        current_user=current_user,
        tender_id=tender_id,
        bid_id=bid_id,
        document_id=document_id,
    )







