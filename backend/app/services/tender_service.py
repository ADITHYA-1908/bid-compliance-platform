"""
Tender Service Layer
Handles business logic, database transactions, organization-scoped querying,
and authorization enforcement for Tender Management.
"""

import math
import uuid
from typing import Optional, Tuple, List
from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, selectinload

from app.db.models.tender import Tender
from app.db.models.user import User
from app.schemas.tender import TenderCreate, TenderUpdate
from app.services.tender_lifecycle_service import (
    get_allowed_transitions,
    transition_tender_status,
)


def create_tender(
    db: Session,
    data: TenderCreate,
    current_user: User,
) -> Tender:
    """
    Creates a new tender in DRAFT status.
    Auto-binds the tender to the authenticated Procurement Officer's organization and profile.
    Prevents duplicate tender numbers with 409 Conflict.
    """
    profile = current_user.profile
    if not profile or not profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user profile is not linked to a valid organization.",
        )

    normalized_num = data.tender_number.strip()

    # Check tender_number uniqueness
    existing = db.scalars(
        select(Tender).where(Tender.tender_number == normalized_num)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tender number '{normalized_num}' already exists.",
        )

    try:
        tender = Tender(
            tender_number=normalized_num,
            title=data.title.strip(),
            description=data.description,
            department=data.department,
            category=data.category,
            procurement_type=data.procurement_type or "GOODS",
            estimated_value=data.estimated_value,
            currency=data.currency or "INR",
            publish_date=data.publish_date,
            submission_start_date=data.submission_start_date,
            submission_end_date=data.submission_end_date,
            evaluation_start_date=data.evaluation_start_date,
            organization_id=profile.organization_id,
            created_by_profile_id=profile.id,
            status="DRAFT",
            is_active=True,
        )
        db.add(tender)
        db.commit()

        # Reload with relationships
        stmt = (
            select(Tender)
            .where(Tender.id == tender.id)
            .options(
                selectinload(Tender.requirements),
                selectinload(Tender.organization),
                selectinload(Tender.created_by),
            )
        )
        t = db.scalars(stmt).first()
        if t:
            t.allowed_transitions = get_allowed_transitions(t.status, t.is_active)
        return t

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tender opportunity.",
        )


def list_tenders(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    include_archived: bool = False,
) -> Tuple[List[Tender], int, int]:
    """
    Returns a paginated list of tenders.
    For PROCUREMENT_OFFICER: strictly scoped to the officer's organization.
    For ADMIN: view across organizations.
    For BIDDER: only published/active non-draft tenders.
    """
    user_role = (
        current_user.profile.role.name.upper()
        if current_user.profile and current_user.profile.role
        else "BIDDER"
    )

    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    query = select(Tender).options(selectinload(Tender.requirements))
    count_query = select(func.count(Tender.id))

    filters = []

    # Active / Archive filter
    if not include_archived:
        filters.append(Tender.is_active == True)  # noqa: E712

    # Organization scoping based on role
    if user_role == "PROCUREMENT_OFFICER":
        if not current_user.profile or not current_user.profile.organization_id:
            return [], 0, 1
        filters.append(Tender.organization_id == current_user.profile.organization_id)
    elif user_role == "BIDDER":
        # Bidders can only view non-draft active tenders
        filters.append(Tender.status != "DRAFT")
    # ADMIN has global visibility

    # Status filter
    if status_filter:
        filters.append(Tender.status == status_filter.strip().upper())

    # Search filter
    if search:
        search_pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Tender.tender_number.ilike(search_pattern),
                Tender.title.ilike(search_pattern),
                Tender.department.ilike(search_pattern),
            )
        )

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = db.scalar(count_query) or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    offset = (page - 1) * page_size
    query = query.order_by(Tender.created_at.desc()).offset(offset).limit(page_size)

    items = db.scalars(query).all()
    for item in items:
        item.allowed_transitions = get_allowed_transitions(item.status, item.is_active)
    return items, total, total_pages


def get_tender_by_id(
    db: Session,
    tender_id: uuid.UUID,
    current_user: User,
) -> Tender:
    """
    Fetches full tender details with requirements.
    Enforces organization isolation for Procurement Officers and draft hiding for Bidders.
    """
    user_role = (
        current_user.profile.role.name.upper()
        if current_user.profile and current_user.profile.role
        else "BIDDER"
    )

    stmt = (
        select(Tender)
        .where(Tender.id == tender_id)
        .options(
            selectinload(Tender.requirements),
            selectinload(Tender.organization),
            selectinload(Tender.created_by),
        )
    )
    tender = db.scalars(stmt).first()

    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found.",
        )

    # Ownership / Visibility check
    if user_role == "PROCUREMENT_OFFICER":
        if (
            not current_user.profile
            or tender.organization_id != current_user.profile.organization_id
        ):
            # Return 404 to avoid leaking existence of other organizations' private tenders
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tender not found.",
            )
    elif user_role == "BIDDER":
        if tender.status == "DRAFT" or not tender.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tender not found.",
            )

    tender.allowed_transitions = get_allowed_transitions(tender.status, tender.is_active)
    return tender


def update_tender(
    db: Session,
    tender_id: uuid.UUID,
    data: TenderUpdate,
    current_user: User,
) -> Tender:
    """
    Updates editable fields of an existing tender.
    Restricted to DRAFT tenders owned by the authenticated Procurement Officer's organization.
    """
    tender = get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

    if tender.status != "DRAFT" or not tender.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only active tenders in DRAFT status can be modified (current status: {tender.status}).",
        )

    update_dict = data.model_dump(exclude_unset=True)

    try:
        for field, value in update_dict.items():
            setattr(tender, field, value)

        db.commit()

        # Reload with relationships
        stmt = (
            select(Tender)
            .where(Tender.id == tender.id)
            .options(
                selectinload(Tender.requirements),
                selectinload(Tender.organization),
                selectinload(Tender.created_by),
            )
        )
        t = db.scalars(stmt).first()
        if t:
            t.allowed_transitions = get_allowed_transitions(t.status, t.is_active)
        return t

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tender details.",
        )


def archive_tender(
    db: Session,
    tender_id: uuid.UUID,
    current_user: User,
) -> Tender:
    """
    Archives a tender via the central lifecycle service.
    """
    return transition_tender_status(
        db=db,
        tender_id=tender_id,
        target_status="ARCHIVED",
        current_user=current_user,
    )
