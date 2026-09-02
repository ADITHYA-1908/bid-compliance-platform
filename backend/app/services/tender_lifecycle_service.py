"""
Tender Lifecycle & Status Management Service (Part 2E)
Provides centralized state machine transitions, readiness validations,
and lifecycle audit timestamp tracking for procurement tenders.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User


# Explicit State Machine Graph
ALLOWED_TRANSITIONS: Dict[str, List[str]] = {
    "DRAFT": ["PUBLISHED", "ARCHIVED"],
    "PUBLISHED": ["OPEN", "ARCHIVED"],
    "OPEN": ["CLOSED"],
    "CLOSED": ["UNDER_EVALUATION"],
    "UNDER_EVALUATION": ["AWARDED", "ARCHIVED"],
    "AWARDED": ["ARCHIVED"],
    "ARCHIVED": [],
}


def get_allowed_transitions(current_status: str, is_active: bool = True) -> List[str]:
    """
    Returns the list of valid next status targets from the current lifecycle state.
    """
    if not is_active or current_status.upper() == "ARCHIVED":
        return []
    return ALLOWED_TRANSITIONS.get(current_status.upper(), [])


def validate_publish_readiness(tender: Tender, db: Session) -> None:
    """
    Ensures a DRAFT tender meets all structural and compliance prerequisites before publication:
    1. Core metadata fields are populated.
    2. Submission timeline dates are valid and in the future.
    3. At least one active TenderRequirement is configured.
    """
    errors: List[str] = []

    # 1. Required metadata checks
    if not tender.tender_number or not tender.tender_number.strip():
        errors.append("Tender number is required.")
    if not tender.title or not tender.title.strip():
        errors.append("Tender title is required.")
    if not tender.department or not tender.department.strip():
        errors.append("Procuring department is required.")
    if not tender.category or not tender.category.strip():
        errors.append("Procurement category is required.")
    if not tender.procurement_type or not tender.procurement_type.strip():
        errors.append("Procurement type is required.")

    # 2. Timeline validation
    now_utc = datetime.now(timezone.utc)
    if not tender.submission_start_date:
        errors.append("Bid submission start date is required.")
    if not tender.submission_end_date:
        errors.append("Bid submission deadline (end date) is required.")

    if tender.submission_start_date and tender.submission_end_date:
        if tender.submission_end_date <= tender.submission_start_date:
            errors.append("Submission end date must be after submission start date.")
        # Ensure submission end date has not already passed
        if tender.submission_end_date <= now_utc:
            errors.append("Submission deadline cannot be in the past.")

    # 3. Requirement rule check (must have at least one active requirement)
    active_req_count = db.scalar(
        select(TenderRequirement)
        .where(
            TenderRequirement.tender_id == tender.id,
            TenderRequirement.is_active == True,  # noqa: E712
        )
    )
    if not active_req_count:
        errors.append("Tender must have at least one active eligibility/compliance requirement configured before publishing.")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tender cannot be published due to validation errors: {'; '.join(errors)}",
        )


def validate_transition(
    tender: Tender,
    target_status: str,
    db: Session,
) -> None:
    """
    Validates state machine rules for moving from tender.status to target_status.
    Raises 409 Conflict if transition is not permitted or fails readiness checks.
    """
    current = tender.status.upper()
    target = target_status.strip().upper()

    if not tender.is_active and current != "ARCHIVED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inactive tenders cannot undergo status transitions.",
        )

    allowed = get_allowed_transitions(current, tender.is_active)
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tender cannot transition from {current} to {target}. Allowed transitions: {', '.join(allowed) if allowed else 'None (Terminal state)'}.",
        )

    # Specific state validations
    if target == "PUBLISHED":
        validate_publish_readiness(tender=tender, db=db)


def transition_tender_status(
    db: Session,
    tender_id: uuid.UUID,
    target_status: str,
    current_user: User,
    remarks: str = None,
) -> Tender:
    """
    Executes a lifecycle status transition on a Tender with full authorization,
    readiness validation, timestamp recording, and transaction safety.
    """
    from app.services import tender_service

    # Retrieve tender and enforce organization authorization
    tender = tender_service.get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

    target = target_status.strip().upper()

    # Validate transition against state machine
    validate_transition(tender=tender, target_status=target, db=db)

    now_utc = datetime.now(timezone.utc)

    try:
        tender.status = target

        # Set transition timestamps according to target
        if target == "PUBLISHED":
            if not tender.published_at:
                tender.published_at = now_utc
            if not tender.publish_date:
                tender.publish_date = now_utc
        elif target == "OPEN":
            if not tender.opened_at:
                tender.opened_at = now_utc
        elif target == "CLOSED":
            if not tender.closed_at:
                tender.closed_at = now_utc
        elif target == "UNDER_EVALUATION":
            if not tender.evaluation_started_at:
                tender.evaluation_started_at = now_utc
        elif target == "AWARDED":
            if not tender.awarded_at:
                tender.awarded_at = now_utc
        elif target == "ARCHIVED":
            if not tender.archived_at:
                tender.archived_at = now_utc
            tender.is_active = False

        db.commit()

        # Reload tender with relationships
        stmt = (
            select(Tender)
            .where(Tender.id == tender.id)
            .options(
                selectinload(Tender.requirements),
                selectinload(Tender.organization),
                selectinload(Tender.created_by),
            )
        )
        updated_tender = db.scalars(stmt).first()
        # Attach allowed_transitions dynamically
        updated_tender.allowed_transitions = get_allowed_transitions(updated_tender.status, updated_tender.is_active)
        return updated_tender

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete lifecycle status transition to {target}: {str(e)}",
        )
