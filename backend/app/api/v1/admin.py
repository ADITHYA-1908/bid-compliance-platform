from fastapi import APIRouter, Depends
from app.core.authorization import require_role
from app.db.models.user import User

router = APIRouter()


@router.get("/test", summary="Admin authorization test endpoint")
def admin_test(
    current_user: User = Depends(require_role("ADMIN")),
):
    """
    Role-protected endpoint accessible only to authenticated ADMIN users.
    """
    return {
        "message": "Admin access granted",
        "role": "ADMIN",
        "user_email": current_user.email,
        "organization": (
            current_user.profile.organization.name
            if current_user.profile and current_user.profile.organization
            else None
        ),
    }
