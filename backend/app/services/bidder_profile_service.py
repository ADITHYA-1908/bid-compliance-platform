import uuid
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.orm import Session, selectinload

from app.db.models.user import User
from app.db.models.profile import Profile
from app.db.models.organization import Organization
from app.schemas.bidder_profile import (
    ProfileCompletionInfo,
    BidderOrganizationSummary,
    BidderOrganizationDetails,
    BidderProfileDetails,
    BidderProfileResponse,
    BidderOrganizationResponse,
    BidderProfileUpdate,
    BidderOrganizationUpdate,
)


def calculate_profile_completion(
    profile: Profile,
    organization: Optional[Organization]
) -> ProfileCompletionInfo:
    """
    Computes statutory and identity completeness of a Bidder Profile.
    Evaluates 9 essential compliance fields required for GeM procurement eligibility.
    """
    required_checks = [
        ("Legal Business Name", bool(organization and organization.name and organization.name.strip())),
        ("Organization Type", bool(organization and organization.organization_type and organization.organization_type.strip())),
        ("Registered Address", bool(organization and organization.registered_address and organization.registered_address.strip())),
        ("City", bool(organization and organization.city and organization.city.strip())),
        ("State", bool(organization and organization.state and organization.state.strip())),
        ("PIN Code", bool(organization and organization.pincode and organization.pincode.strip())),
        ("Contact Person Name", bool(profile and profile.full_name and profile.full_name.strip())),
        ("Contact Phone", bool(profile and profile.phone and profile.phone.strip())),
        ("PAN Number", bool(organization and organization.pan_number and organization.pan_number.strip())),
    ]

    total_required = len(required_checks)
    completed_count = sum(1 for _, is_valid in required_checks if is_valid)
    missing_fields = [field_name for field_name, is_valid in required_checks if not is_valid]
    
    percentage = int(round((completed_count / total_required) * 100)) if total_required > 0 else 0
    is_complete = completed_count == total_required

    return ProfileCompletionInfo(
        completion_percentage=percentage,
        is_complete=is_complete,
        missing_required_fields=missing_fields,
        completed_fields_count=completed_count,
        total_required_fields=total_required,
    )


def _get_or_create_user_organization(db: Session, current_user: User) -> Tuple[Profile, Organization]:
    """Ensures the authenticated user has a Profile and an Organization."""
    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile record not found for the authenticated user.",
        )

    profile = current_user.profile
    org = profile.organization

    if not org:
        # If no organization exists yet, create an initial one
        org = Organization(
            name=f"{profile.full_name}'s Enterprise",
            organization_type="PROPRIETORSHIP",
            is_active=True,
        )
        db.add(org)
        db.flush()
        profile.organization_id = org.id
        db.commit()
        db.refresh(profile)
        db.refresh(org)

    return profile, org


def get_bidder_profile(db: Session, current_user: User) -> BidderProfileResponse:
    """Retrieves current bidder's personal profile along with organization summary and completion status."""
    profile, org = _get_or_create_user_organization(db, current_user)
    completion = calculate_profile_completion(profile, org)

    role_name = profile.role.name if profile.role else "BIDDER"

    org_summary = (
        BidderOrganizationSummary(
            id=org.id,
            name=org.name,
            trade_name=org.trade_name,
            organization_type=org.organization_type,
            business_category=org.business_category,
            city=org.city,
            state=org.state,
            pan_number=org.pan_number,
            gstin=org.gstin,
            udyam_number=org.udyam_number,
        )
        if org
        else None
    )

    profile_details = BidderProfileDetails(
        id=profile.id,
        email=profile.email,
        full_name=profile.full_name,
        phone=profile.phone,
        designation=profile.designation,
        role=role_name,
        is_active=profile.is_active,
        organization=org_summary,
    )

    return BidderProfileResponse(
        profile=profile_details,
        completion=completion,
    )


def update_bidder_profile(
    db: Session,
    current_user: User,
    data: BidderProfileUpdate,
) -> BidderProfileResponse:
    """Updates current bidder's personal and signatory contact information."""
    profile, org = _get_or_create_user_organization(db, current_user)

    if data.full_name is not None:
        profile.full_name = data.full_name
    if data.phone is not None:
        profile.phone = data.phone
    if data.designation is not None:
        profile.designation = data.designation

    db.commit()
    db.refresh(profile)

    return get_bidder_profile(db, current_user)


def get_bidder_organization(db: Session, current_user: User) -> BidderOrganizationResponse:
    """Retrieves current bidder's full organization details and statutory registration status."""
    profile, org = _get_or_create_user_organization(db, current_user)
    completion = calculate_profile_completion(profile, org)

    org_details = BidderOrganizationDetails.model_validate(org)

    return BidderOrganizationResponse(
        organization=org_details,
        completion=completion,
    )


def update_bidder_organization(
    db: Session,
    current_user: User,
    data: BidderOrganizationUpdate,
) -> BidderOrganizationResponse:
    """
    Updates bidder organization fields with uniqueness verification for PAN and GSTIN.
    Prevents cross-tenant collision and returns clean 409 Conflict if duplicate detected.
    """
    profile, org = _get_or_create_user_organization(db, current_user)

    # 1. Uniqueness check for PAN
    if data.pan_number:
        clean_pan = data.pan_number.strip().upper()
        existing_pan = db.scalars(
            select(Organization.id).where(
                and_(
                    Organization.pan_number == clean_pan,
                    Organization.id != org.id,
                    Organization.is_active == True,
                )
            )
        ).first()
        if existing_pan:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"The PAN '{clean_pan}' is already registered to another organization.",
            )

    # 2. Uniqueness check for GSTIN
    if data.gstin:
        clean_gstin = data.gstin.strip().upper()
        existing_gstin = db.scalars(
            select(Organization.id).where(
                and_(
                    Organization.gstin == clean_gstin,
                    Organization.id != org.id,
                    Organization.is_active == True,
                )
            )
        ).first()
        if existing_gstin:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"The GSTIN '{clean_gstin}' is already registered to another organization.",
            )

    # 3. Apply updates
    update_data = data.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        if hasattr(org, field_name):
            setattr(org, field_name, value)

    db.commit()
    db.refresh(org)

    completion = calculate_profile_completion(profile, org)
    org_details = BidderOrganizationDetails.model_validate(org)

    return BidderOrganizationResponse(
        organization=org_details,
        completion=completion,
    )
