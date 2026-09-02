"""
Tender Requirement Service Layer
Handles business logic, criteria validation, dynamic condition storage,
and organization-scoped authorization for Tender Eligibility & Compliance Rules.
"""

import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.schemas.tender import (
    TenderRequirementCreate,
    TenderRequirementUpdate,
)
from app.services import tender_service


def list_requirements(
    db: Session,
    tender_id: uuid.UUID,
    current_user: User,
    include_inactive: bool = False,
) -> List[TenderRequirement]:
    """
    Returns all eligibility and compliance requirements configured for a tender.
    Ordered by display_order ascending, then creation timestamp.
    """
    # Enforces role and organization isolation
    tender_service.get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

    stmt = select(TenderRequirement).where(TenderRequirement.tender_id == tender_id)

    if not include_inactive:
        stmt = stmt.where(TenderRequirement.is_active == True)  # noqa: E712

    stmt = stmt.order_by(
        TenderRequirement.display_order.asc(),
        TenderRequirement.created_at.asc(),
    )
    return db.scalars(stmt).all()


def create_requirement(
    db: Session,
    tender_id: uuid.UUID,
    data: TenderRequirementCreate,
    current_user: User,
) -> TenderRequirement:
    """
    Attaches a new dynamic eligibility/compliance requirement to a tender.
    Restricted to Procurement Officers modifying active DRAFT tenders in their organization.
    Prevents duplicate active codes within the same tender.
    """
    tender = tender_service.get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

    if tender.status != "DRAFT" or not tender.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requirements can only be configured for active tenders in DRAFT status (current status: {tender.status}).",
        )

    normalized_code = data.code.strip().upper()

    # Check duplicate code within the same tender
    existing = db.scalars(
        select(TenderRequirement).where(
            TenderRequirement.tender_id == tender_id,
            TenderRequirement.code == normalized_code,
            TenderRequirement.is_active == True,  # noqa: E712
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Requirement with code '{normalized_code}' already exists for this tender.",
        )

    try:
        requirement = TenderRequirement(
            tender_id=tender_id,
            code=normalized_code,
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            category=data.category.strip().upper(),
            requirement_type=data.requirement_type.strip().upper(),
            operator=data.operator.strip().upper(),
            expected_value=data.expected_value,
            unit=getattr(data, "unit", None),
            is_mandatory=data.is_mandatory,
            weight=data.weight,
            display_order=data.display_order,
            source_clause=getattr(data, "source_clause", None),
            source_page=getattr(data, "source_page", None),
            corrigendum_number=getattr(data, "corrigendum_number", None),
            is_active=True,
            current_version_number=1,
            last_changed_by_profile_id=current_user.profile_id if current_user else None,
        )
        db.add(requirement)
        db.flush()

        # Seed initial Version 1 snapshot for complete provenance
        from app.services.rule_version_service import RuleVersionService
        RuleVersionService.create_initial_version(
            db=db,
            requirement=requirement,
            current_user=current_user,
            change_reason="Initial baseline requirement version",
        )

        db.commit()
        db.refresh(requirement)
        return requirement

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tender requirement rule: {e}",
        )


def get_requirement(
    db: Session,
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    current_user: User,
) -> TenderRequirement:
    """
    Fetches a specific requirement, verifying tender access.
    """
    tender_service.get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

    stmt = select(TenderRequirement).where(
        TenderRequirement.id == requirement_id,
        TenderRequirement.tender_id == tender_id,
    )
    req = db.scalars(stmt).first()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender requirement not found.",
        )

    return req


def update_requirement(
    db: Session,
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    data: Union[TenderRequirementUpdate, Any],
    current_user: User,
) -> TenderRequirement:
    """
    Updates an existing tender requirement with full immutable versioning.
    Tracks changed fields, calculates next version number, and preserves audit trail.
    """
    from app.services.rule_version_service import RuleVersionService
    from app.schemas.rule_version import TenderRequirementUpdateWithVersionRequest

    if isinstance(data, dict):
        version_payload = TenderRequirementUpdateWithVersionRequest(**data)
    elif isinstance(data, TenderRequirementUpdateWithVersionRequest):
        version_payload = data
    else:
        version_payload = TenderRequirementUpdateWithVersionRequest(**data.model_dump(exclude_unset=True))

    req, _, _ = RuleVersionService.update_requirement_with_version(
        db=db,
        tender_id=tender_id,
        requirement_id=requirement_id,
        data=version_payload,
        current_user=current_user,
    )
    return req


def deactivate_requirement(
    db: Session,
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    current_user: User,
) -> TenderRequirement:
    """
    Soft-deletes / deactivates a tender requirement (sets is_active=False).
    Creates an immutable version snapshot recording the deactivation event.
    """
    from app.services.rule_version_service import RuleVersionService
    from app.schemas.rule_version import TenderRequirementUpdateWithVersionRequest

    payload = TenderRequirementUpdateWithVersionRequest(
        is_active=False,
        change_reason="Requirement deactivated/archived",
    )
    req, _, _ = RuleVersionService.update_requirement_with_version(
        db=db,
        tender_id=tender_id,
        requirement_id=requirement_id,
        data=payload,
        current_user=current_user,
    )
    return req
