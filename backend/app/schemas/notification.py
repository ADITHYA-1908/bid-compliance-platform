"""
Pydantic Schemas for Part 12: Notification Center
"""

from datetime import datetime
import enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.notification import NotificationSeverity, NotificationType


class NotificationCreateRequest(BaseModel):
    recipient_profile_id: uuid.UUID
    organization_id: uuid.UUID
    notification_type: NotificationType
    severity: NotificationSeverity = NotificationSeverity.INFO
    title: str = Field(..., max_length=255)
    message: str
    tender_id: Optional[uuid.UUID] = None
    bid_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    action_url: Optional[str] = None
    dedupe_key: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    id: uuid.UUID
    recipient_profile_id: uuid.UUID
    organization_id: uuid.UUID
    tender_id: Optional[uuid.UUID] = None
    bid_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    notification_type: str
    severity: str
    title: str
    message: str
    is_read: bool
    read_at: Optional[datetime] = None
    action_url: Optional[str] = None
    dedupe_key: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationMarkReadResponse(BaseModel):
    success: bool
    marked_count: int
    unread_count: int
    message: str
