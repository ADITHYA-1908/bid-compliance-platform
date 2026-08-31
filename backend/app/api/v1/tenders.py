"""
Tender Management API Router
Provides endpoints for Procurement Officers to create, list, view, update,
and archive tender opportunities, as well as configure dynamic eligibility
and compliance requirements.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.core.deps import get_current_user
from app.core.authorization import require_role
from app.schemas.tender import (
    TenderCreate,
    TenderUpdate,
    TenderResponse,
    TenderListResponse,
    TenderStatusTransition,
    TenderRequirementCreate,
    TenderRequirementUpdate,
    TenderRequirementResponse,
)
from app.services import tender_service, tender_requirement_service, tender_lifecycle_service

router = APIRouter()


# ==========================================
# Tender Opportunity Endpoints
# ==========================================

@router.post(
    "",
    response_model=TenderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tender opportunity",
)
def create_tender(
    data: TenderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Creates a new procurement tender in DRAFT status.
    Auto-binds tender to the authenticated Procurement Officer's organization and profile.
    Only users with 'PROCUREMENT_OFFICER' role are authorized.
    """
    tender = tender_service.create_tender(db=db, data=data, current_user=current_user)
    return tender


@router.get(
    "",
    response_model=TenderListResponse,
    summary="List tenders with filtering and pagination",
)
def list_tenders(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by tender status (e.g. DRAFT, PUBLISHED)"),
    search: Optional[str] = Query(default=None, description="Search across tender number, title, and department"),
    include_archived: bool = Query(default=False, description="Include soft-deleted / archived tenders"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a paginated list of tenders.
    - Procurement Officers: strictly scoped to their owning organization.
    - Admins: global visibility across all organizations.
    - Bidders: view active public / published opportunities.
    """
    items, total, total_pages = tender_service.list_tenders(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        status_filter=status,
        search=search,
        include_archived=include_archived,
    )
    return TenderListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get(
    "/{tender_id}",
    response_model=TenderResponse,
    summary="Get full tender details",
)
def get_tender(
    tender_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches full tender details including configured requirements and owning organization.
    Enforces cross-organization access isolation.
    """
    tender = tender_service.get_tender_by_id(
        db=db,
        tender_id=tender_id,
        current_user=current_user,
    )
    return tender


@router.patch(
    "/{tender_id}",
    response_model=TenderResponse,
    summary="Update tender details",
)
def update_tender(
    tender_id: uuid.UUID,
    data: TenderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Updates editable fields of a tender.
    Only DRAFT tenders owned by the authenticated Procurement Officer's organization can be modified.
    """
    tender = tender_service.update_tender(
        db=db,
        tender_id=tender_id,
        data=data,
        current_user=current_user,
    )
    return tender


@router.post(
    "/{tender_id}/transition",
    response_model=TenderResponse,
    summary="Transition tender lifecycle status",
)
def transition_tender_status(
    tender_id: uuid.UUID,
    data: TenderStatusTransition,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Transitions the lifecycle state of a tender (e.g. DRAFT -> PUBLISHED -> OPEN -> CLOSED -> UNDER_EVALUATION -> AWARDED -> ARCHIVED).
    Enforces state machine rules, pre-publish validation, and organization ownership.
    """
    tender = tender_lifecycle_service.transition_tender_status(
        db=db,
        tender_id=tender_id,
        target_status=data.target_status,
        current_user=current_user,
        remarks=data.remarks,
    )
    return tender


@router.delete(
    "/{tender_id}",
    response_model=TenderResponse,
    summary="Archive / soft-delete a tender",
)
def archive_tender(
    tender_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Soft-deletes / archives a tender by setting is_active=false and status='ARCHIVED'.
    Preserves audit history and prevents accidental data loss.
    """
    tender = tender_service.archive_tender(
        db=db,
        tender_id=tender_id,
        current_user=current_user,
    )
    return tender


# ==========================================
# Dynamic Requirements & Rules Endpoints (Part 2D)
# ==========================================

@router.get(
    "/{tender_id}/requirements",
    response_model=List[TenderRequirementResponse],
    summary="List all eligibility requirements for a tender",
)
def list_requirements(
    tender_id: uuid.UUID,
    include_inactive: bool = Query(default=False, description="Include deactivated requirements"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves all eligibility and compliance requirements configured for the given tender.
    Ordered by display order ascending.
    """
    return tender_requirement_service.list_requirements(
        db=db,
        tender_id=tender_id,
        current_user=current_user,
        include_inactive=include_inactive,
    )


@router.post(
    "/{tender_id}/requirements",
    response_model=TenderRequirementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an eligibility/compliance requirement to a tender",
)
def create_requirement(
    tender_id: uuid.UUID,
    data: TenderRequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Attaches a dynamic compliance condition/criteria rule to an active DRAFT tender.
    Only authorized Procurement Officers belonging to the owning organization can configure requirements.
    """
    return tender_requirement_service.create_requirement(
        db=db,
        tender_id=tender_id,
        data=data,
        current_user=current_user,
    )


@router.get(
    "/{tender_id}/requirements/{requirement_id}",
    response_model=TenderRequirementResponse,
    summary="Get details of a specific tender requirement",
)
def get_requirement(
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches a specific eligibility requirement by ID.
    """
    return tender_requirement_service.get_requirement(
        db=db,
        tender_id=tender_id,
        requirement_id=requirement_id,
        current_user=current_user,
    )


@router.patch(
    "/{tender_id}/requirements/{requirement_id}",
    response_model=TenderRequirementResponse,
    summary="Update an existing tender requirement",
)
def update_requirement(
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    data: TenderRequirementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Updates criteria, expected value, weight, or ordering of a tender requirement.
    Restricted to active DRAFT tenders.
    """
    return tender_requirement_service.update_requirement(
        db=db,
        tender_id=tender_id,
        requirement_id=requirement_id,
        data=data,
        current_user=current_user,
    )


@router.delete(
    "/{tender_id}/requirements/{requirement_id}",
    response_model=TenderRequirementResponse,
    summary="Deactivate / soft-delete a tender requirement",
)
def deactivate_requirement(
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Soft-deletes a requirement by setting is_active=false, preserving audit history.
    Restricted to active DRAFT tenders.
    """
    return tender_requirement_service.deactivate_requirement(
        db=db,
        tender_id=tender_id,
        requirement_id=requirement_id,
        current_user=current_user,
    )
