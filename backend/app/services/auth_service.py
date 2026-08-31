from typing import Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password, verify_password, create_access_token
from app.db.models.user import User
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.organization import Organization
from app.schemas.auth import SignupRequest, LoginRequest, CurrentUserResponse


def build_current_user_response(user: User) -> CurrentUserResponse:
    """Helper to convert User model into safe CurrentUserResponse schema."""
    role_name = user.profile.role.name if user.profile and user.profile.role else "BIDDER"
    org_name = (
        user.profile.organization.name
        if user.profile and user.profile.organization
        else None
    )
    full_name = user.profile.full_name if user.profile else "User"

    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=full_name,
        role=role_name,
        organization=org_name,
        is_active=user.is_active,
    )


def signup_bidder(db: Session, data: SignupRequest) -> Tuple[User, str]:
    """
    Registers a new public Bidder user.
    Enforces security rule: public registrations always receive the BIDDER role.
    Creates Organization, Profile, and User inside a single atomic transaction.
    """
    normalized_email = data.email.strip().lower()

    # 1. Check for existing account
    existing_user = db.scalars(
        select(User).where(User.email == normalized_email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    existing_profile = db.scalars(
        select(Profile).where(Profile.email == normalized_email)
    ).first()
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A profile with this email address already exists.",
        )

    # 2. Lookup standard BIDDER role
    bidder_role = db.scalars(
        select(Role).where(Role.name == "BIDDER")
    ).first()
    if not bidder_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System role 'BIDDER' is not configured in database.",
        )

    try:
        # 3. Create Organization
        organization = Organization(
            name=data.organization_name.strip(),
            organization_type=data.organization_type or "Vendor / Bidder",
            is_active=True,
        )
        db.add(organization)
        db.flush()

        # 4. Create Profile
        profile = Profile(
            full_name=data.full_name.strip(),
            email=normalized_email,
            role_id=bidder_role.id,
            organization_id=organization.id,
            is_active=True,
        )
        db.add(profile)
        db.flush()

        # 5. Create User with hashed password
        password_hashed = hash_password(data.password)
        user = User(
            email=normalized_email,
            password_hash=password_hashed,
            profile_id=profile.id,
            is_active=True,
        )
        db.add(user)
        db.commit()

        # Reload with relationships
        stmt = (
            select(User)
            .where(User.id == user.id)
            .options(
                selectinload(User.profile).selectinload(Profile.role),
                selectinload(User.profile).selectinload(Profile.organization),
            )
        )
        reloaded_user = db.scalars(stmt).first()
        token = create_access_token(subject=str(user.id), email=user.email)
        return reloaded_user, token

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user account.",
        )


def authenticate_user(db: Session, data: LoginRequest) -> Tuple[User, str]:
    """
    Authenticates a user via email and password.
    Returns the User model and a signed JWT access token.
    Uses generic error message to prevent account enumeration.
    """
    normalized_email = data.email.strip().lower()

    stmt = (
        select(User)
        .where(User.email == normalized_email)
        .options(
            selectinload(User.profile).selectinload(Profile.role),
            selectinload(User.profile).selectinload(Profile.organization),
        )
    )
    user = db.scalars(stmt).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact support.",
        )

    token = create_access_token(subject=str(user.id), email=user.email)
    return user, token
