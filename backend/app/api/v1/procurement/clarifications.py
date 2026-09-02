"""
Procurement Clarification API Router
Part 16 — Clarification Request Workflow for BidVerify AI
Provides authenticated endpoints for Procurement Officers and Admins
to create, manage, inspect, review, re-evaluate, and resolve clarification requests.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import require_role
from app.db.models.bid import Bid
from app.db.models.tender import Tender
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.clarification import (
    ClarificationAnalyticsResponse,
    ClarificationRequestCreate,
    ClarificationRequestDetailResponse,
    ClarificationRequestListResponse,
    ClarificationResolveRequest,
    ClarificationSummaryResponse,
)
from app.services.clarification_service import ClarificationService

router = APIRouter()


@router.post(
    "/bids/{bid_id}",
    response_model=ClarificationRequestDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create clarification request for a bid",
)
def create_bid_clarification(
    bid_id: uuid.UUID,
    payload: ClarificationRequestCreate,
    tender_id: Optional[uuid.UUID] = Query(None, description="Optional tender ID confirmation"),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Creates a new Clarification Request targeted at the bidder for a specific bid.
    Can be sent immediately (SENT) or saved as a DRAFT.
    """
    bid = db.scalars(select(Bid).where(Bid.id == bid_id)).first()
    if not bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid not found.",
        )

    t_id = tender_id or bid.tender_id
    req = ClarificationService.create_clarification_request(
        db=db,
        tender_id=t_id,
        bid_id=bid_id,
        current_profile=current_user.profile,
        payload=payload,
    )
    return ClarificationService.get_clarification_detail(
        db=db,
        clarification_id=req.id,
        current_profile=current_user.profile,
    )


@router.get(
    "",
    response_model=ClarificationRequestListResponse,
    summary="List procurement clarification requests",
)
def list_procurement_clarifications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    tender_id: Optional[uuid.UUID] = Query(None, description="Filter by tender ID"),
    bid_id: Optional[uuid.UUID] = Query(None, description="Filter by bid ID"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, SENT, VIEWED, RESPONDED, UNDER_REVIEW, RESOLVED, CLOSED, EXPIRED, CANCELLED)"),
    priority: Optional[str] = Query(None, description="Filter by priority (LOW, NORMAL, HIGH, URGENT)"),
    type: Optional[str] = Query(None, description="Filter by clarification type"),
    search: Optional[str] = Query(None, description="Search keyword in subject or message"),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Lists paginated clarification requests scoped to the Procurement Officer's organization.
    """
    org_id = current_user.profile.organization_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have an associated organization.",
        )

    return ClarificationService.list_procurement_clarifications(
        db=db,
        organization_id=org_id,
        tender_id=tender_id,
        bid_id=bid_id,
        status_filter=status,
        priority_filter=priority,
        type_filter=type,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/summary",
    response_model=ClarificationSummaryResponse,
    summary="Get procurement clarification summary counters",
)
def get_procurement_clarification_summary(
    tender_id: Optional[uuid.UUID] = Query(None, description="Filter by tender ID"),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Returns summary counters of open, awaiting, responded, and resolved clarifications.
    """
    org_id = current_user.profile.organization_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have an associated organization.",
        )

    return ClarificationService.get_clarification_summary(
        db=db,
        organization_id=org_id,
        tender_id=tender_id,
        is_bidder=False,
    )


@router.get(
    "/analytics",
    response_model=ClarificationAnalyticsResponse,
    summary="Get procurement clarification analytics",
)
def get_procurement_clarification_analytics(
    tender_id: Optional[uuid.UUID] = Query(None, description="Filter by tender ID"),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Returns detailed analytics metrics and distributions for clarifications.
    """
    org_id = current_user.profile.organization_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have an associated organization.",
        )

    return ClarificationService.get_clarification_analytics(
        db=db,
        organization_id=org_id,
        tender_id=tender_id,
        is_bidder=False,
    )


@router.get(
    "/{id}",
    response_model=ClarificationRequestDetailResponse,
    summary="Get clarification request detail & timeline thread",
)
def get_procurement_clarification_detail(
    id: uuid.UUID,
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Retrieves full request detail, related evidence context, and chronological responses.
    """
    return ClarificationService.get_clarification_detail(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
    )


@router.post(
    "/{id}/send",
    response_model=ClarificationRequestDetailResponse,
    summary="Send a draft clarification request",
)
def send_procurement_clarification(
    id: uuid.UUID,
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Transitions a DRAFT clarification to SENT and notifies the Bidder.
    """
    ClarificationService.send_clarification_request(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
    )
    return ClarificationService.get_clarification_detail(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
    )


@router.post(
    "/{id}/review",
    response_model=ClarificationRequestDetailResponse,
    summary="Mark clarification as under review",
)
def review_procurement_clarification(
    id: uuid.UUID,
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Transitions a responded clarification to UNDER_REVIEW.
    """
    ClarificationService.mark_under_review(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
    )
    return ClarificationService.get_clarification_detail(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
    )


@router.post(
    "/{id}/resolve",
    response_model=ClarificationRequestDetailResponse,
    summary="Resolve clarification request",
)
def resolve_procurement_clarification(
    id: uuid.UUID,
    payload: ClarificationResolveRequest,
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Resolves the clarification with an audit note and optional automated re-evaluation.
    """
    ClarificationService.resolve_clarification(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
        payload=payload,
    )
    return ClarificationService.get_clarification_detail(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
    )


@router.post(
    "/{id}/cancel",
    response_model=ClarificationRequestDetailResponse,
    summary="Cancel clarification request",
)
def cancel_procurement_clarification(
    id: uuid.UUID,
    reason: Optional[str] = Query(None, description="Reason for cancellation"),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Cancels an open clarification request.
    """
    ClarificationService.cancel_clarification(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
        reason=reason,
    )
    return ClarificationService.get_clarification_detail(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
    )


@router.post(
    "/{id}/reevaluate",
    response_model=Dict[str, Any],
    summary="Re-evaluate relevant criteria for clarification bid",
)
def reevaluate_clarification_evidence(
    id: uuid.UUID,
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Explicit action to safely re-run compliance, scoring, and risk evaluation on the bid.
    """
    req = ClarificationService.get_clarification_detail(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
    )
    # Fetch ORM
    req_orm = db.scalars(select(ClarificationRequest).where(ClarificationRequest.id == id)).first()
    if not req_orm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clarification not found.")

    return ClarificationService.reevaluate_clarification_evidence(
        db=db,
        clarification=req_orm,
        current_profile=current_user.profile,
    )
