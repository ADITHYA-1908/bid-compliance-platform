"""
Notifications API Endpoints
Part 12 — Notification Center for BidVerify AI
Multi-tenant, role-aware in-app notification management.
"""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.notification import (
    NotificationListResponse,
    NotificationMarkReadResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_read: Optional[bool] = Query(None, description="Filter by read/unread state"),
    severity: Optional[str] = Query(None, description="Filter by severity (INFO, SUCCESS, WARNING, CRITICAL)"),
    notification_type: Optional[str] = Query(None, description="Filter by notification category type"),
    tender_id: Optional[uuid.UUID] = Query(None, description="Filter by related tender ID"),
    bid_id: Optional[uuid.UUID] = Query(None, description="Filter by related bid ID"),
    search: Optional[str] = Query(None, description="Search keyword in title and message"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated notifications for the authenticated user with strict profile/tenant isolation.
    """
    items, total, unread_count = NotificationService.get_notifications_for_user(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        is_read=is_read,
        severity=severity,
        notification_type=notification_type,
        tender_id=tender_id,
        bid_id=bid_id,
        search=search,
    )

    total_pages = max(1, (total + page_size - 1) // page_size)

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fast query returning unread notification count for header navbar badge polling.
    """
    count = NotificationService.get_unread_count_for_user(db=db, current_user=current_user)
    return UnreadCountResponse(unread_count=count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marks a single notification as read.
    """
    notification = NotificationService.mark_as_read(
        db=db,
        current_user=current_user,
        notification_id=notification_id,
    )
    return NotificationResponse.model_validate(notification)


@router.post("/{notification_id}/unread", response_model=NotificationResponse)
def mark_notification_unread(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marks a single notification as unread.
    """
    notification = NotificationService.mark_as_unread(
        db=db,
        current_user=current_user,
        notification_id=notification_id,
    )
    return NotificationResponse.model_validate(notification)


@router.post("/mark-all-read", response_model=NotificationMarkReadResponse)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marks all unread notifications for the authenticated user as read in bulk.
    """
    marked_count = NotificationService.mark_all_as_read(
        db=db,
        current_user=current_user,
    )
    remaining_unread = NotificationService.get_unread_count_for_user(db=db, current_user=current_user)

    return NotificationMarkReadResponse(
        success=True,
        marked_count=marked_count,
        unread_count=remaining_unread,
        message=f"Marked {marked_count} notification(s) as read.",
    )
