from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.core.deps import get_current_user
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    CurrentUserResponse,
)
from app.services.auth_service import (
    signup_bidder,
    authenticate_user,
    build_current_user_response,
)

router = APIRouter()


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new Bidder user account",
)
def signup(
    data: SignupRequest,
    db: Session = Depends(get_db),
):
    """
    Public registration endpoint.
    Creates Organization, Profile, and User with default 'BIDDER' role.
    Issues a JWT access token upon successful registration.
    """
    user, token = signup_bidder(db=db, data=data)
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
    Returns signed JWT access token and user metadata.
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
