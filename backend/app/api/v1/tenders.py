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
from app.schemas.rule_version import (
    TenderRequirementVersionResponse,
    TenderRequirementVersionListResponse,
    TenderRequirementVersionCompareResponse,
    TenderRequirementUpdateWithVersionRequest,
    ReevaluationResultResponse,
)
from app.services import tender_service, tender_requirement_service, tender_lifecycle_service
from app.services.rule_version_service import RuleVersionService

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


@router.put(
    "/{tender_id}/requirements/{requirement_id}",
    response_model=TenderRequirementResponse,
    summary="Update a tender requirement with explicit version tracking",
)
def update_requirement_with_version(
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    data: TenderRequirementUpdateWithVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Updates requirement criteria and creates a new immutable version record.
    Requires change_reason for published tenders or when bids already exist.
    """
    return tender_requirement_service.update_requirement(
        db=db,
        tender_id=tender_id,
        requirement_id=requirement_id,
        data=data,
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
    data: TenderRequirementUpdateWithVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Updates criteria, expected value, weight, or ordering of a tender requirement.
    Creates a new immutable version if criteria changed.
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
    """
    return tender_requirement_service.deactivate_requirement(
        db=db,
        tender_id=tender_id,
        requirement_id=requirement_id,
        current_user=current_user,
    )


# ==========================================
# Compliance Rule Version History Endpoints (Part 15)
# ==========================================

@router.get(
    "/{tender_id}/requirements/{requirement_id}/versions",
    response_model=TenderRequirementVersionListResponse,
    summary="List historical versions of a tender requirement",
)
def list_requirement_versions(
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves complete chronological version history for a tender requirement,
    including version numbers, author provenance, change reasons, and criteria diffs.
    """
    return RuleVersionService.list_requirement_versions(
        db=db,
        tender_id=tender_id,
        requirement_id=requirement_id,
        current_user=current_user,
    )


@router.get(
    "/{tender_id}/requirements/{requirement_id}/versions/compare",
    response_model=TenderRequirementVersionCompareResponse,
    summary="Compare two historical versions of a requirement",
)
def compare_requirement_versions(
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    v1: int = Query(..., ge=1, description="Base version number"),
    v2: int = Query(..., ge=1, description="Target version number to compare against"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Performs field-by-field diff comparison between two requirement versions.
    """
    return RuleVersionService.compare_versions(
        db=db,
        tender_id=tender_id,
        requirement_id=requirement_id,
        v1_num=v1,
        v2_num=v2,
        current_user=current_user,
    )


@router.get(
    "/{tender_id}/requirements/{requirement_id}/versions/{version_identifier}",
    response_model=TenderRequirementVersionResponse,
    summary="Get details of a specific requirement version",
)
def get_requirement_version(
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    version_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a single historical version snapshot by version number or UUID.
    """
    parsed_ident: Union[uuid.UUID, int]
    try:
        parsed_ident = uuid.UUID(version_identifier)
    except ValueError:
        try:
            parsed_ident = int(version_identifier)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Version identifier must be a valid UUID or integer version number.",
            )

    return RuleVersionService.get_requirement_version(
        db=db,
        tender_id=tender_id,
        requirement_id=requirement_id,
        version_identifier=parsed_ident,
        current_user=current_user,
    )


@router.post(
    "/{tender_id}/requirements/{requirement_id}/reevaluate",
    response_model=ReevaluationResultResponse,
    summary="Re-evaluate all tender bids against latest rule version",
)
def reevaluate_requirement_bids(
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Explicitly re-runs compliance, scoring, and risk evaluations for all bids
    of the tender against the updated rule version, while preserving human decisions.
    """
    return RuleVersionService.reevaluate_tender_bids(
        db=db,
        tender_id=tender_id,
        requirement_id=requirement_id,
        current_user=current_user,
    )


@router.post(
    "/{tender_id}/reevaluate-all-rules",
    response_model=ReevaluationResultResponse,
    summary="Re-evaluate all bids against all current tender rules",
)
def reevaluate_all_tender_rules(
    tender_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PROCUREMENT_OFFICER")),
):
    """
    Explicitly re-runs compliance, scoring, and risk evaluations for all tender bids
    across all active tender requirements.
    """
    return RuleVersionService.reevaluate_tender_bids(
        db=db,
        tender_id=tender_id,
        requirement_id=None,
        current_user=current_user,
    )
