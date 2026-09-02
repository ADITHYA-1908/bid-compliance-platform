"""
Procurement Analytics & Impact API Router (Part 13)
Provides multi-tenant scoped analytics endpoints for Procurement Officers and Administrators.
"""

from datetime import datetime
import time
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.authorization import require_role
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.analytics import (
    BulkAnalyticsResponse,
    ComplianceAnalyticsResponse,
    DocumentQualityAnalyticsResponse,
    DuplicateAnalyticsResponse,
    HumanReviewAndDecisionResponse,
    OverviewKPIsResponse,
    RiskAnalyticsResponse,
    TenderSpecificAnalyticsResponse,
    TimeSeriesPoint,
    VerificationAnalyticsResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter()


def _get_org_id(current_user: User) -> Optional[uuid.UUID]:
    """
    Returns organization_id for tenant scoping.
    ADMIN users without organization filter can inspect platform-wide.
    """
    user_role = (
        current_user.profile.role.name.upper()
        if current_user.profile and current_user.profile.role
        else None
    )
    if user_role == "ADMIN":
        return None
    return current_user.profile.organization_id if current_user.profile else None


@router.get(
    "/overview",
    response_model=OverviewKPIsResponse,
    summary="Get high-level procurement overview KPIs & impact savings",
)
def get_overview_kpis(
    tender_id: Optional[uuid.UUID] = Query(None, description="Optional tender filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns total tenders, bids, compliance rates, review backlogs, risk summary, and empirical impact savings.
    """
    org_id = _get_org_id(current_user)
    return AnalyticsService.get_overview_kpis(
        db=db,
        org_id=org_id,
        tender_id=tender_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/compliance",
    response_model=ComplianceAnalyticsResponse,
    summary="Get compliance results distribution and common failure reasons",
)
def get_compliance_analytics(
    tender_id: Optional[uuid.UUID] = Query(None, description="Optional tender filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns PASS/FAIL/REVIEW distributions, mandatory failure counts, and root-cause failure breakdown.
    """
    org_id = _get_org_id(current_user)
    return AnalyticsService.get_compliance_analytics(
        db=db,
        org_id=org_id,
        tender_id=tender_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/risk",
    response_model=RiskAnalyticsResponse,
    summary="Get risk level distribution and override signals",
)
def get_risk_analytics(
    tender_id: Optional[uuid.UUID] = Query(None, description="Optional tender filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns LOW/MEDIUM/HIGH/CRITICAL risk counts and applied critical override statistics.
    """
    org_id = _get_org_id(current_user)
    return AnalyticsService.get_risk_analytics(
        db=db,
        org_id=org_id,
        tender_id=tender_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/verification",
    response_model=VerificationAnalyticsResponse,
    summary="Get verification outcome rates and source breakdown",
)
def get_verification_analytics(
    tender_id: Optional[uuid.UUID] = Query(None, description="Optional tender filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns verification outcomes and breakdowns by verification type (GST, PAN, UDYAM, etc.).
    """
    org_id = _get_org_id(current_user)
    return AnalyticsService.get_verification_analytics(
        db=db,
        org_id=org_id,
        tender_id=tender_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/documents",
    response_model=DocumentQualityAnalyticsResponse,
    summary="Get Document Quality tier distribution and image diagnostics (Part 11)",
)
def get_document_quality_analytics(
    tender_id: Optional[uuid.UUID] = Query(None, description="Optional tender filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns document quality tier distributions (GOOD, ACCEPTABLE, POOR, UNUSABLE) and blur/blank diagnostics.
    """
    org_id = _get_org_id(current_user)
    return AnalyticsService.get_document_quality_analytics(
        db=db,
        org_id=org_id,
        tender_id=tender_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/duplicates",
    response_model=DuplicateAnalyticsResponse,
    summary="Get duplicate and cross-bid document reuse telemetry (Part 10)",
)
def get_duplicate_analytics(
    tender_id: Optional[uuid.UUID] = Query(None, description="Optional tender filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns duplicate match type counts and review status progression.
    """
    org_id = _get_org_id(current_user)
    return AnalyticsService.get_duplicate_analytics(
        db=db,
        org_id=org_id,
        tender_id=tender_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/bulk",
    response_model=BulkAnalyticsResponse,
    summary="Get bulk batch verification telemetry (Part 9)",
)
def get_bulk_analytics(
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns bulk job throughput, success rates, and item processing totals.
    """
    org_id = _get_org_id(current_user)
    return AnalyticsService.get_bulk_analytics(
        db=db,
        org_id=org_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/reviews",
    response_model=HumanReviewAndDecisionResponse,
    summary="Get human review queue workload and authoritative qualification decisions (Part 8C & 8D)",
)
def get_human_review_and_decision_analytics(
    tender_id: Optional[uuid.UUID] = Query(None, description="Optional tender filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns review queue status, review reason breakdown, and final human qualification decisions.
    """
    org_id = _get_org_id(current_user)
    return AnalyticsService.get_human_review_and_decision_analytics(
        db=db,
        org_id=org_id,
        tender_id=tender_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/trends",
    response_model=List[TimeSeriesPoint],
    summary="Get daily time-series activity trends",
)
def get_activity_trends(
    tender_id: Optional[uuid.UUID] = Query(None, description="Optional tender filter"),
    days: int = Query(30, ge=7, le=90, description="Number of days lookback"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns daily bid submission and evaluation completion time-series.
    """
    org_id = _get_org_id(current_user)
    return AnalyticsService.get_time_trends(
        db=db,
        org_id=org_id,
        tender_id=tender_id,
        days=days,
    )


@router.get(
    "/tenders/{tender_id}",
    response_model=TenderSpecificAnalyticsResponse,
    summary="Get deep-dive metrics for a specific tender",
)
def get_tender_specific_analytics(
    tender_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns complete multi-dimensional analytics for a specific tender.
    """
    org_id = _get_org_id(current_user)
    try:
        return AnalyticsService.get_tender_specific_analytics(
            db=db,
            tender_id=tender_id,
            org_id=org_id,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get(
    "/export",
    summary="Export comprehensive analytics summary as CSV",
)
def export_analytics_report(
    tender_id: Optional[uuid.UUID] = Query(None, description="Optional tender filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Generates and downloads a CSV summary report of current procurement analytics.
    """
    org_id = _get_org_id(current_user)
    csv_content = AnalyticsService.export_analytics_csv(
        db=db,
        org_id=org_id,
        tender_id=tender_id,
        start_date=start_date,
        end_date=end_date,
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=procurement_analytics_{int(time.time())}.csv"
        },
    )
