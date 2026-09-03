from typing import Optional, Tuple
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


def signup_user(
    db: Session,
    data: SignupRequest,
    target_role: str | None = None,
) -> Tuple[User, str]:
    """
    Registers a new user with the specified or requested platform role:
    - BIDDER
    - PROCUREMENT_OFFICER
    - ADMIN
    Creates Organization, Profile, and User inside a single atomic transaction.
    """
    normalized_email = data.email.strip().lower()
    selected_role = (target_role or data.role or "BIDDER").strip().upper()
    if selected_role in ["PROCUREMENT", "OFFICER"]:
        selected_role = "PROCUREMENT_OFFICER"

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

    # 2. Lookup role from database
    role_obj = db.scalars(
        select(Role).where(Role.name == selected_role)
    ).first()
    if not role_obj:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System role '{selected_role}' is not configured in database.",
        )

    # Determine default organization type based on role
    default_org_type = "Vendor / Bidder"
    if selected_role == "PROCUREMENT_OFFICER":
        default_org_type = "Government Ministry / Public Sector"
    elif selected_role == "ADMIN":
        default_org_type = "Platform Oversight Authority"

    org_type = data.organization_type or default_org_type

    try:
        # 3. Create Organization
        organization = Organization(
            name=data.organization_name.strip(),
            organization_type=org_type,
            is_active=True,
        )
        db.add(organization)
        db.flush()

        # 4. Create Profile
        profile = Profile(
            full_name=data.full_name.strip(),
            email=normalized_email,
            role_id=role_obj.id,
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
            detail=f"Failed to register user account: {str(e)}",
        )


def signup_bidder(db: Session, data: SignupRequest) -> Tuple[User, str]:
    """Backward compatibility alias for public Bidder registration."""
    return signup_user(db=db, data=data, target_role="BIDDER")


def authenticate_user(db: Session, data: LoginRequest) -> Tuple[User, str]:
    """
    Authenticates a user via email and password.
    Optionally enforces expected role for isolated portal access.
    Returns the User model and a signed JWT access token.
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

    # Optional expected_role check for portal isolation
    if data.expected_role:
        user_role = user.profile.role.name if user.profile and user.profile.role else None
        if user_role != data.expected_role:
            readable_role = user_role.replace("_", " ").title() if user_role else "Unknown"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This account is registered with role '{readable_role}'. Please use the {readable_role} Portal to sign in.",
            )

    token = create_access_token(subject=str(user.id), email=user.email)
    return user, token
