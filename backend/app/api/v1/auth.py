from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.core.deps import get_current_user
from app.schemas.auth import (
    SignupRequest,
    BidderSignupRequest,
    ProcurementSignupRequest,
    AdminSignupRequest,
    LoginRequest,
    TokenResponse,
    CurrentUserResponse,
)
from app.services.auth_service import (
    signup_user,
    signup_bidder,
    authenticate_user,
    build_current_user_response,
)

router = APIRouter()


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account (Bidder, Procurement Officer, or Admin)",
)
def signup(
    data: SignupRequest,
    db: Session = Depends(get_db),
):
    """
    Public registration endpoint supporting role specification (BIDDER, PROCUREMENT_OFFICER, ADMIN).
    Creates Organization, Profile, and User inside a single transaction.
    """
    user, token = signup_user(db=db, data=data)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_current_user_response(user),
    )


@router.post(
    "/signup/bidder",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dedicated Bidder / Vendor account registration",
)
def signup_bidder_endpoint(
    data: BidderSignupRequest,
    db: Session = Depends(get_db),
):
    """Creates a vendor entity and registers a user with the BIDDER role."""
    generic_data = SignupRequest(
        full_name=data.full_name,
        email=data.email,
        password=data.password,
        organization_name=data.organization_name,
        organization_type=data.organization_type or "Vendor / Bidder",
        role="BIDDER",
    )
    user, token = signup_user(db=db, data=generic_data, target_role="BIDDER")
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_current_user_response(user),
    )


@router.post(
    "/signup/procurement",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dedicated Procurement Officer / Buyer account registration",
)
def signup_procurement_endpoint(
    data: ProcurementSignupRequest,
    db: Session = Depends(get_db),
):
    """Creates a government department/ministry and registers a PROCUREMENT_OFFICER user."""
    generic_data = SignupRequest(
        full_name=data.full_name,
        email=data.email,
        password=data.password,
        organization_name=data.organization_name,
        organization_type=data.organization_type or "Government Ministry / Public Sector",
        role="PROCUREMENT_OFFICER",
    )
    user, token = signup_user(db=db, data=generic_data, target_role="PROCUREMENT_OFFICER")
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_current_user_response(user),
    )


@router.post(
    "/signup/admin",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dedicated Platform Administrator account registration",
)
def signup_admin_endpoint(
    data: AdminSignupRequest,
    db: Session = Depends(get_db),
):
    """Creates platform oversight entity and registers an ADMIN user."""
    generic_data = SignupRequest(
        full_name=data.full_name,
        email=data.email,
        password=data.password,
        organization_name=data.organization_name,
        organization_type=data.organization_type or "Platform Oversight Authority",
        role="ADMIN",
    )
    user, token = signup_user(db=db, data=generic_data, target_role="ADMIN")
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_current_user_response(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain JWT access token",
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticates a user using email and password.
    Optionally enforces portal role isolation if expected_role is supplied.
    """
    user, token = authenticate_user(db=db, data=data)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_current_user_response(user),
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get currently authenticated user identity",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Protected endpoint that returns the currently logged-in user profile, role, and organization.
    Requires Bearer JWT token in Authorization header.
    """
    return build_current_user_response(current_user)
