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
            is_mandatory=data.is_mandatory,
            weight=data.weight,
            display_order=data.display_order,
            is_active=True,
        )
        db.add(requirement)
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
            detail="Failed to create tender requirement rule.",
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
    data: TenderRequirementUpdate,
    current_user: User,
) -> TenderRequirement:
    """
    Partially updates an existing tender requirement.
    Restricted to active DRAFT tenders.
    """
    tender = tender_service.get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

    if tender.status != "DRAFT" or not tender.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requirements can only be modified for active tenders in DRAFT status (current status: {tender.status}).",
        )

    req = get_requirement(db=db, tender_id=tender_id, requirement_id=requirement_id, current_user=current_user)

    update_dict = data.model_dump(exclude_unset=True)

    if "code" in update_dict and update_dict["code"]:
        normalized_code = update_dict["code"].strip().upper()
        if normalized_code != req.code:
            existing = db.scalars(
                select(TenderRequirement).where(
                    TenderRequirement.tender_id == tender_id,
                    TenderRequirement.code == normalized_code,
                    TenderRequirement.id != requirement_id,
                    TenderRequirement.is_active == True,  # noqa: E712
                )
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Requirement with code '{normalized_code}' already exists for this tender.",
                )
            update_dict["code"] = normalized_code

    if "category" in update_dict and update_dict["category"]:
        update_dict["category"] = update_dict["category"].strip().upper()

    if "requirement_type" in update_dict and update_dict["requirement_type"]:
        update_dict["requirement_type"] = update_dict["requirement_type"].strip().upper()

    if "operator" in update_dict and update_dict["operator"]:
        update_dict["operator"] = update_dict["operator"].strip().upper()

    try:
        for field, value in update_dict.items():
            setattr(req, field, value)

        db.commit()
        db.refresh(req)
        return req

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tender requirement.",
        )


def deactivate_requirement(
    db: Session,
    tender_id: uuid.UUID,
    requirement_id: uuid.UUID,
    current_user: User,
) -> TenderRequirement:
    """
    Soft-deletes / deactivates a tender requirement (sets is_active=False).
    Preserves historical criteria records for auditability.
    """
    tender = tender_service.get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

    if tender.status != "DRAFT" or not tender.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requirements can only be deactivated for active tenders in DRAFT status (current status: {tender.status}).",
        )

    req = get_requirement(db=db, tender_id=tender_id, requirement_id=requirement_id, current_user=current_user)

    try:
        req.is_active = False
        db.commit()
        db.refresh(req)
        return req

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate tender requirement.",
        )
