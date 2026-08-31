from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.role import Role
from app.schemas.role import RoleResponse

router = APIRouter()


@router.get("", response_model=List[RoleResponse], summary="List all system roles")
def get_roles(db: Session = Depends(get_db)):
    """
    Retrieve all registered system roles from the database.
    Confirms FastAPI -> SQLAlchemy -> PostgreSQL connection pipeline.
    """
    try:
        stmt = select(Role).order_by(Role.name)
        roles = db.scalars(stmt).all()
        return roles
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch roles from the database.",
        )
