from typing import List, Union
from fastapi import Depends, HTTPException, status
from app.core.deps import get_current_user
from app.db.models.user import User


class RoleChecker:
    """
    FastAPI dependency for role-based authorization.
    Verifies that the authenticated user possesses one of the permitted roles.
    Enforces server-side database-backed role validation.
    """

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.upper() for r in allowed_roles]

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_role = (
            current_user.profile.role.name.upper()
            if current_user.profile and current_user.profile.role
            else None
        )

        if not user_role or user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of [{', '.join(self.allowed_roles)}] role permissions.",
            )

        return current_user


def require_role(role: Union[str, List[str]]):
    """Dependency helper to require one or more specific roles."""
    if isinstance(role, list):
        return RoleChecker(role)
    return RoleChecker([role])


def require_any_role(*roles: str):
    """Dependency helper to require any of the specified roles."""
    return RoleChecker(list(roles))
