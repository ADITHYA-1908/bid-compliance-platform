"""
Organization Identity Verification & Duplicate Entity Detection API Endpoints
BidVerify AI — Integrated Bid Compliance Verification Platform for GeM Procurement
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import require_role
from app.db.models.bid import Bid
from app.db.models.organization import Organization
from app.db.models.organization_identity import (
    OrganizationDuplicateMatch,
    OrganizationIdentityAssessment,
)
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.organization_identity import (
    OrganizationDuplicateMatchResponse,
    OrganizationDuplicateResolvePayload,
    OrganizationIdentityOverviewResponse,
    OrganizationIdentityResponse,
)
from app.services.organization_identity_service import organization_identity_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Bidder Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/bidder/organization/identity",
    response_model=OrganizationIdentityOverviewResponse,
    summary="Get Bidder's Organization Identity Assessment",
)
def get_bidder_organization_identity(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["BIDDER"])),
):
    """
    Returns the active identity coherence assessment and detected duplicate signals for the logged-in bidder.
    """
    if not current_user.profile or not current_user.profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization profile.",
        )

    org_id = current_user.profile.organization_id

    # Retrieve or generate assessment
    assessment = (
        db.query(OrganizationIdentityAssessment)
        .filter(
            OrganizationIdentityAssessment.organization_id == org_id,
            OrganizationIdentityAssessment.is_current == True,
        )
        .first()
    )

    if not assessment:
        assessment = organization_identity_service.evaluate_organization_identity(
            db=db,
            organization_id=org_id,
            actor_id=current_user.id,
            actor_name=current_user.full_name or current_user.email,
        )

    # Detect duplicate entity signals
    dup_matches = organization_identity_service.detect_organization_duplicates(
        db=db,
        organization_id=org_id,
    )

    # Format duplicate match responses
    match_responses = []
    for m in dup_matches:
        org_a = db.query(Organization).filter(Organization.id == m.organization_a_id).first()
        org_b = db.query(Organization).filter(Organization.id == m.organization_b_id).first()
        match_responses.append(
            OrganizationDuplicateMatchResponse(
                id=m.id,
                organization_a_id=m.organization_a_id,
                organization_b_id=m.organization_b_id,
                organization_a_name=org_a.name if org_a else None,
                organization_b_name=org_b.name if org_b else None,
                tender_id=m.tender_id,
                match_type=m.match_type,
                matched_identifiers=m.matched_identifiers or {},
                similarity_score=m.similarity_score,
                status=m.status,
                notes=m.notes,
                reviewed_by=m.reviewed_by,
                reviewed_at=m.reviewed_at,
                created_at=m.created_at,
            )
        )

    return OrganizationIdentityOverviewResponse(
        assessment=assessment,
        duplicate_matches=match_responses,
    )


@router.post(
    "/bidder/organization/identity/evaluate",
    response_model=OrganizationIdentityOverviewResponse,
    summary="Trigger Re-evaluation of Bidder Organization Identity",
)
def evaluate_bidder_organization_identity(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["BIDDER"])),
):
    """
    Triggers re-evaluation of statutory coherence and cross-checks duplicate entities for the bidder's organization.
    """
    if not current_user.profile or not current_user.profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization profile.",
        )

    org_id = current_user.profile.organization_id
    assessment = organization_identity_service.evaluate_organization_identity(
        db=db,
        organization_id=org_id,
        actor_id=current_user.id,
        actor_name=current_user.full_name or current_user.email,
    )

    dup_matches = organization_identity_service.detect_organization_duplicates(
        db=db,
        organization_id=org_id,
    )

    match_responses = []
    for m in dup_matches:
        org_a = db.query(Organization).filter(Organization.id == m.organization_a_id).first()
        org_b = db.query(Organization).filter(Organization.id == m.organization_b_id).first()
        match_responses.append(
            OrganizationDuplicateMatchResponse(
                id=m.id,
                organization_a_id=m.organization_a_id,
                organization_b_id=m.organization_b_id,
                organization_a_name=org_a.name if org_a else None,
                organization_b_name=org_b.name if org_b else None,
                tender_id=m.tender_id,
                match_type=m.match_type,
                matched_identifiers=m.matched_identifiers or {},
                similarity_score=m.similarity_score,
                status=m.status,
                notes=m.notes,
                reviewed_by=m.reviewed_by,
                reviewed_at=m.reviewed_at,
                created_at=m.created_at,
            )
        )

    return OrganizationIdentityOverviewResponse(
        assessment=assessment,
        duplicate_matches=match_responses,
    )


# ---------------------------------------------------------------------------
# Procurement Officer & Admin Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/procurement/organizations/{org_id}/identity",
    response_model=OrganizationIdentityOverviewResponse,
    summary="Procurement Officer / Admin Identity Inspection",
)
def get_organization_identity_procurement(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns full legal identity breakdown, confidence score, and duplicate matches for an organization.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {org_id} not found.",
        )

    assessment = (
        db.query(OrganizationIdentityAssessment)
        .filter(
            OrganizationIdentityAssessment.organization_id == org_id,
            OrganizationIdentityAssessment.is_current == True,
        )
        .first()
    )

    if not assessment:
        assessment = organization_identity_service.evaluate_organization_identity(
            db=db,
            organization_id=org_id,
            actor_id=current_user.id,
            actor_name=current_user.full_name or current_user.email,
        )

    dup_matches = organization_identity_service.detect_organization_duplicates(
        db=db,
        organization_id=org_id,
    )

    match_responses = []
    for m in dup_matches:
        org_a = db.query(Organization).filter(Organization.id == m.organization_a_id).first()
        org_b = db.query(Organization).filter(Organization.id == m.organization_b_id).first()
        match_responses.append(
            OrganizationDuplicateMatchResponse(
                id=m.id,
                organization_a_id=m.organization_a_id,
                organization_b_id=m.organization_b_id,
                organization_a_name=org_a.name if org_a else None,
                organization_b_name=org_b.name if org_b else None,
                tender_id=m.tender_id,
                match_type=m.match_type,
                matched_identifiers=m.matched_identifiers or {},
                similarity_score=m.similarity_score,
                status=m.status,
                notes=m.notes,
                reviewed_by=m.reviewed_by,
                reviewed_at=m.reviewed_at,
                created_at=m.created_at,
            )
        )

    return OrganizationIdentityOverviewResponse(
        assessment=assessment,
        duplicate_matches=match_responses,
    )


@router.post(
    "/procurement/organizations/duplicates/{match_id}/resolve",
    response_model=OrganizationDuplicateMatchResponse,
    summary="Resolve Organization Duplicate Entity Match",
)
def resolve_organization_duplicate_match(
    match_id: uuid.UUID,
    payload: OrganizationDuplicateResolvePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Records an official officer determination on a duplicate entity match (CONFIRMED_SAME_ENTITY, CONFIRMED_DISTINCT, DISMISSED).
    """
    try:
        resolved = organization_identity_service.resolve_duplicate_match(
            db=db,
            match_id=match_id,
            user_id=current_user.id,
            new_status=payload.status,
            notes=payload.notes,
        )

        org_a = db.query(Organization).filter(Organization.id == resolved.organization_a_id).first()
        org_b = db.query(Organization).filter(Organization.id == resolved.organization_b_id).first()

        return OrganizationDuplicateMatchResponse(
            id=resolved.id,
            organization_a_id=resolved.organization_a_id,
            organization_b_id=resolved.organization_b_id,
            organization_a_name=org_a.name if org_a else None,
            organization_b_name=org_b.name if org_b else None,
            tender_id=resolved.tender_id,
            match_type=resolved.match_type,
            matched_identifiers=resolved.matched_identifiers or {},
            similarity_score=resolved.similarity_score,
            status=resolved.status,
            notes=resolved.notes,
            reviewed_by=resolved.reviewed_by,
            reviewed_at=resolved.reviewed_at,
            created_at=resolved.created_at,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )


@router.get(
    "/procurement/bids/{bid_id}/identity-assessment",
    response_model=OrganizationIdentityOverviewResponse,
    summary="Get Organization Identity Assessment for a Bid",
)
def get_bid_organization_identity(
    bid_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
):
    """
    Returns the organization identity assessment associated with a specific submitted bid.
    """
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bid {bid_id} not found.",
        )

    org_id = bid.bidder_organization_id
    assessment = (
        db.query(OrganizationIdentityAssessment)
        .filter(
            OrganizationIdentityAssessment.organization_id == org_id,
            OrganizationIdentityAssessment.is_current == True,
        )
        .first()
    )

    if not assessment:
        assessment = organization_identity_service.evaluate_organization_identity(
            db=db,
            organization_id=org_id,
            bid_id=bid_id,
            actor_id=current_user.id,
            actor_name=current_user.full_name or current_user.email,
        )

    dup_matches = organization_identity_service.detect_organization_duplicates(
        db=db,
        organization_id=org_id,
        tender_id=bid.tender_id,
    )

    match_responses = []
    for m in dup_matches:
        org_a = db.query(Organization).filter(Organization.id == m.organization_a_id).first()
        org_b = db.query(Organization).filter(Organization.id == m.organization_b_id).first()
        match_responses.append(
            OrganizationDuplicateMatchResponse(
                id=m.id,
                organization_a_id=m.organization_a_id,
                organization_b_id=m.organization_b_id,
                organization_a_name=org_a.name if org_a else None,
                organization_b_name=org_b.name if org_b else None,
                tender_id=m.tender_id,
                match_type=m.match_type,
                matched_identifiers=m.matched_identifiers or {},
                similarity_score=m.similarity_score,
                status=m.status,
                notes=m.notes,
                reviewed_by=m.reviewed_by,
                reviewed_at=m.reviewed_at,
                created_at=m.created_at,
            )
        )

    return OrganizationIdentityOverviewResponse(
        assessment=assessment,
        duplicate_matches=match_responses,
    )
