"""
Notification Service
Part 12 — Notification Center for BidVerify AI
Multi-tenant, role-aware, event-driven in-app notifications with deduplication.
"""

from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select, update, or_, and_
from sqlalchemy.orm import Session, joinedload

from app.db.models.audit_event import (
    AuditEventType,
    AuditEntityType,
    AuditActorSource,
)
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.bulk_evaluation_job import BulkEvaluationJob, BulkJobStatus
from app.db.models.document_duplicate_match import DocumentDuplicateMatch
from app.db.models.document_quality import DocumentQualityResult, QualityLevel
from app.db.models.human_review import HumanReviewItem, ReviewSeverity
from app.db.models.notification import (
    Notification,
    NotificationSeverity,
    NotificationType,
)
from app.db.models.profile import Profile
from app.db.models.tender import Tender
from app.db.models.user import User
from app.schemas.audit import RecordAuditEventDTO
from app.services.audit.audit_service import AuditService

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Centralized Notification Service for creating, querying, and managing
    in-app notifications for Bidders, Procurement Officers, and Administrators.
    """

    @classmethod
    def create_notification(
        cls,
        db: Session,
        recipient_profile_id: uuid.UUID,
        organization_id: uuid.UUID,
        notification_type: Union[NotificationType, str],
        severity: Union[NotificationSeverity, str],
        title: str,
        message: str,
        tender_id: Optional[uuid.UUID] = None,
        bid_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        action_url: Optional[str] = None,
        dedupe_key: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        cooldown_hours: Optional[int] = 24,
    ) -> Notification:
        """
        Creates a new notification for a specific recipient profile.
        If dedupe_key is provided and a notification with the same dedupe_key exists
        within the cooldown window, returns the existing record to prevent spamming.
        """
        type_str = notification_type.value if isinstance(notification_type, NotificationType) else str(notification_type)
        sev_str = severity.value if isinstance(severity, NotificationSeverity) else str(severity)

        # Deduplication check
        if dedupe_key:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=cooldown_hours or 24)
            existing = db.scalars(
                select(Notification).where(
                    Notification.recipient_profile_id == recipient_profile_id,
                    Notification.dedupe_key == dedupe_key,
                    Notification.created_at >= cutoff,
                )
            ).first()

            if existing:
                logger.debug(
                    "Notification skipped due to dedupe_key '%s' within %dh cooldown.",
                    dedupe_key,
                    cooldown_hours or 24,
                )
                return existing

        notification = Notification(
            id=uuid.uuid4(),
            recipient_profile_id=recipient_profile_id,
            organization_id=organization_id,
            tender_id=tender_id,
            bid_id=bid_id,
            document_id=document_id,
            notification_type=type_str,
            severity=sev_str,
            title=title.strip()[:255],
            message=message.strip(),
            is_read=False,
            read_at=None,
            action_url=action_url,
            dedupe_key=dedupe_key,
            metadata_json=metadata_json or {},
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        # Audit logging (graceful)
        cls._record_notification_audit(
            db=db,
            notification=notification,
            event_type=AuditEventType.NOTIFICATION_CREATED,
            action="NOTIFICATION_CREATED",
            summary=f"Notification '{notification.title}' sent to profile {recipient_profile_id}.",
        )

        return notification

    # -------------------------------------------------------------------------
    # Workflow Event Handlers
    # -------------------------------------------------------------------------

    @classmethod
    def notify_bid_submitted(cls, db: Session, bid: Bid) -> List[Notification]:
        """
        Emits notifications when a bid is submitted:
        1. Confirmation to the Bidder creator (SUCCESS).
        2. Alert to the Tender creator / Procurement Officer (INFO).
        """
        notifications: List[Notification] = []
        tender = bid.tender or db.scalars(select(Tender).where(Tender.id == bid.tender_id)).first()
        tender_title = tender.title if tender else "Tender"
        tender_org_id = tender.organization_id if tender else bid.bidder_organization_id

        # 1. Bidder confirmation
        if bid.created_by_profile_id:
            n1 = cls.create_notification(
                db=db,
                recipient_profile_id=bid.created_by_profile_id,
                organization_id=bid.bidder_organization_id,
                notification_type=NotificationType.BID_SUBMITTED,
                severity=NotificationSeverity.SUCCESS,
                title=f"Bid Submitted: {bid.bid_number}",
                message=f"Your bid for tender '{tender_title}' has been successfully submitted and queued for automated compliance verification.",
                tender_id=bid.tender_id,
                bid_id=bid.id,
                action_url=f"/bidder/bids/{bid.id}",
                dedupe_key=f"bid_sub_bidder_{bid.id}",
                metadata_json={"bid_number": bid.bid_number, "tender_title": tender_title},
            )
            notifications.append(n1)

        # 2. Procurement Officer alert
        if tender and tender.created_by_profile_id:
            n2 = cls.create_notification(
                db=db,
                recipient_profile_id=tender.created_by_profile_id,
                organization_id=tender_org_id,
                notification_type=NotificationType.BID_SUBMITTED,
                severity=NotificationSeverity.INFO,
                title=f"New Bid Received: {bid.bid_number}",
                message=f"A new bid package has been submitted for tender '{tender_title}'.",
                tender_id=bid.tender_id,
                bid_id=bid.id,
                action_url=f"/procurement/tenders/{tender.id}/bids/{bid.id}",
                dedupe_key=f"bid_sub_officer_{bid.id}",
                metadata_json={"bid_number": bid.bid_number, "tender_title": tender_title},
            )
            notifications.append(n2)

        return notifications

    @classmethod
    def notify_document_quality_review(
        cls,
        db: Session,
        doc: BidDocument,
        qr: DocumentQualityResult,
    ) -> List[Notification]:
        """
        Emits notifications when an uploaded document has poor or unusable quality.
        - Bidder receives plain-English, non-technical alert.
        - Procurement Officer receives technical quality review alert.
        """
        notifications: List[Notification] = []
        if qr.quality_level not in (QualityLevel.POOR, QualityLevel.UNUSABLE) and not qr.review_required:
            return notifications

        bid = doc.bid or db.scalars(select(Bid).where(Bid.id == doc.bid_id)).first()
        if not bid:
            return notifications

        tender = bid.tender or db.scalars(select(Tender).where(Tender.id == bid.tender_id)).first()

        # Extract string value of quality level safely
        ql_val = qr.quality_level.value if hasattr(qr.quality_level, "value") else str(qr.quality_level)
        is_unusable = ql_val.upper() == "UNUSABLE"

        # 1. Bidder alert (plain-English feedback)
        if doc.uploaded_by_profile_id or bid.created_by_profile_id:
            recipient_id = doc.uploaded_by_profile_id or bid.created_by_profile_id
            first_feedback = qr.bidder_feedback[0] if qr.bidder_feedback else "Please verify and upload a clearer copy."
            n_bidder = cls.create_notification(
                db=db,
                recipient_profile_id=recipient_id,
                organization_id=bid.bidder_organization_id,
                notification_type=NotificationType.DOCUMENT_QUALITY_REVIEW_REQUIRED,
                severity=NotificationSeverity.CRITICAL if is_unusable else NotificationSeverity.WARNING,
                title=f"Document Quality Alert: {doc.original_filename}",
                message=f"Your uploaded document '{doc.document_name}' has quality issues ({ql_val}). {first_feedback}",
                tender_id=bid.tender_id,
                bid_id=bid.id,
                document_id=doc.id,
                action_url=f"/bidder/bids/{bid.id}",
                dedupe_key=f"quality_bidder_{doc.id}_{ql_val}",
                metadata_json={
                    "quality_level": ql_val,
                    "quality_score": qr.quality_score,
                    "document_name": doc.document_name,
                },
            )
            notifications.append(n_bidder)

        # 2. Procurement Officer alert
        if tender and tender.created_by_profile_id:
            n_po = cls.create_notification(
                db=db,
                recipient_profile_id=tender.created_by_profile_id,
                organization_id=tender.organization_id,
                notification_type=NotificationType.DOCUMENT_QUALITY_REVIEW_REQUIRED,
                severity=NotificationSeverity.WARNING,
                title=f"Low Quality Document in Bid {bid.bid_number}",
                message=f"Document '{doc.original_filename}' scored {qr.quality_score}/100 ({ql_val}). Manual review may be required.",
                tender_id=bid.tender_id,
                bid_id=bid.id,
                document_id=doc.id,
                action_url=f"/procurement/tenders/{tender.id}/bids/{bid.id}",
                dedupe_key=f"quality_po_{doc.id}_{ql_val}",
                metadata_json={
                    "quality_level": ql_val,
                    "quality_score": qr.quality_score,
                    "bid_number": bid.bid_number,
                },
            )
            notifications.append(n_po)

        return notifications

    @classmethod
    def notify_duplicate_document_alert(
        cls,
        db: Session,
        match: DocumentDuplicateMatch,
        doc_a: BidDocument,
        doc_b: BidDocument,
        tender_id: uuid.UUID,
    ) -> Optional[Notification]:
        """
        Emits high-priority alert to Procurement Officer when a high-risk duplicate or
        reused document across different bidder organizations is detected.
        """
        tender = db.scalars(select(Tender).where(Tender.id == tender_id)).first()
        if not tender or not tender.created_by_profile_id:
            return None

        bid_b = doc_b.bid or db.scalars(select(Bid).where(Bid.id == doc_b.bid_id)).first()
        bid_b_num = bid_b.bid_number if bid_b else "Unknown"

        sim_pct = round((match.overall_similarity_score or 0.0) * 100, 1)
        severity = NotificationSeverity.CRITICAL if sim_pct >= 85.0 else NotificationSeverity.WARNING

        return cls.create_notification(
            db=db,
            recipient_profile_id=tender.created_by_profile_id,
            organization_id=tender.organization_id,
            notification_type=NotificationType.DUPLICATE_DOCUMENT_ALERT,
            severity=severity,
            title="Duplicate / Reuse Document Alert",
            message=f"Document '{doc_b.original_filename}' in bid '{bid_b_num}' exhibits {sim_pct}% match with '{doc_a.original_filename}'. Potential collusion or certificate reuse.",
            tender_id=tender_id,
            bid_id=doc_b.bid_id,
            document_id=doc_b.id,
            action_url=f"/procurement/tenders/{tender_id}/duplicates",
            dedupe_key=f"dup_alert_{match.id}",
            metadata_json={
                "match_id": str(match.id),
                "similarity_score": match.overall_similarity_score,
                "match_type": match.match_type.value if hasattr(match.match_type, "value") else str(match.match_type),
            },
        )

    @classmethod
    def notify_bulk_evaluation_completed(
        cls,
        db: Session,
        job: BulkEvaluationJob,
    ) -> Optional[Notification]:
        """
        Emits completion summary notification to the Procurement Officer who launched a bulk job.
        """
        recipient_id = getattr(job, "started_by_profile_id", None) or getattr(job, "created_by_profile_id", None)
        if not recipient_id:
            # Fallback to tender creator
            tender = job.tender or db.scalars(select(Tender).where(Tender.id == job.tender_id)).first()
            recipient_id = tender.created_by_profile_id if tender else None

        if not recipient_id:
            return None

        status_val = job.status.value if hasattr(job.status, "value") else str(job.status)
        is_partial = status_val in ("PARTIALLY_COMPLETED", "FAILED") or (job.failed_bids > 0)
        n_type = NotificationType.BULK_EVALUATION_PARTIAL if is_partial else NotificationType.BULK_EVALUATION_COMPLETED
        severity = NotificationSeverity.WARNING if is_partial else NotificationSeverity.SUCCESS

        job_ident = getattr(job, "job_number", None) or f"JOB-{str(job.id)[:8].upper()}"
        title = f"Bulk Verification {status_val}: {job_ident}"
        success_cnt = getattr(job, "successful_bids", 0)
        message = (
            f"Processed {job.total_bids} bids: {success_cnt} successful, "
            f"{job.failed_bids} failed, {job.review_required_bids} flagged for review."
        )

        return cls.create_notification(
            db=db,
            recipient_profile_id=recipient_id,
            organization_id=job.organization_id,
            notification_type=n_type,
            severity=severity,
            title=title,
            message=message,
            tender_id=job.tender_id,
            action_url=f"/procurement/tenders/{job.tender_id}/bulk",
            dedupe_key=f"bulk_job_done_{job.id}",
            metadata_json={
                "job_id": str(job.id),
                "job_ident": job_ident,
                "total_bids": job.total_bids,
                "successful_bids": success_cnt,
                "failed_bids": job.failed_bids,
                "review_required_bids": job.review_required_bids,
            },
        )

    @classmethod
    def notify_human_review_required(
        cls,
        db: Session,
        review_item: HumanReviewItem,
    ) -> Optional[Notification]:
        """
        Emits notification to assigned Procurement Officer when a human review item is created.
        """
        tender = db.scalars(select(Tender).where(Tender.id == review_item.tender_id)).first()
        if not tender:
            return None

        recipient_id = review_item.assigned_to_profile_id or tender.created_by_profile_id
        if not recipient_id:
            return None

        sev_map = {
            ReviewSeverity.CRITICAL: NotificationSeverity.CRITICAL,
            ReviewSeverity.HIGH: NotificationSeverity.WARNING,
            ReviewSeverity.MEDIUM: NotificationSeverity.INFO,
            ReviewSeverity.LOW: NotificationSeverity.INFO,
        }
        severity = sev_map.get(review_item.severity, NotificationSeverity.WARNING)

        return cls.create_notification(
            db=db,
            recipient_profile_id=recipient_id,
            organization_id=tender.organization_id,
            notification_type=NotificationType.VERIFICATION_REVIEW_REQUIRED,
            severity=severity,
            title=f"Human Review Required: {review_item.title}",
            message=review_item.description or f"A pending review item requires manual decision in bid {review_item.bid_id}.",
            tender_id=review_item.tender_id,
            bid_id=review_item.bid_id,
            document_id=review_item.document_id,
            action_url=f"/procurement/tenders/{review_item.tender_id}/bids/{review_item.bid_id}",
            dedupe_key=f"review_item_alert_{review_item.id}",
            metadata_json={
                "review_item_id": str(review_item.id),
                "review_type": review_item.review_type.value if hasattr(review_item.review_type, "value") else str(review_item.review_type),
                "severity": review_item.severity.value if hasattr(review_item.severity, "value") else str(review_item.severity),
            },
        )

    @classmethod
    def notify_tender_deadline_approaching(
        cls,
        db: Session,
        tender_id: uuid.UUID,
        days_remaining: int,
        bidder_profile_ids: List[uuid.UUID],
    ) -> List[Notification]:
        """
        Sends tender deadline reminders to active bidders (e.g. 7, 3, 1 day remaining).
        """
        notifications: List[Notification] = []
        tender = db.scalars(select(Tender).where(Tender.id == tender_id)).first()
        if not tender:
            return notifications

        severity = NotificationSeverity.CRITICAL if days_remaining <= 1 else (
            NotificationSeverity.WARNING if days_remaining <= 3 else NotificationSeverity.INFO
        )

        for prof_id in bidder_profile_ids:
            prof = db.scalars(select(Profile).where(Profile.id == prof_id)).first()
            if not prof:
                continue

            n = cls.create_notification(
                db=db,
                recipient_profile_id=prof_id,
                organization_id=prof.organization_id,
                notification_type=NotificationType.TENDER_DEADLINE_APPROACHING,
                severity=severity,
                title=f"Tender Deadline: {days_remaining} Day(s) Left",
                message=f"The submission window for tender '{tender.title}' closes in {days_remaining} day(s). Ensure all required documents are uploaded.",
                tender_id=tender.id,
                action_url=f"/bidder/tenders/{tender.id}",
                dedupe_key=f"deadline_{tender.id}_{days_remaining}d_{prof_id}",
                metadata_json={"days_remaining": days_remaining, "tender_number": tender.tender_number},
            )
            notifications.append(n)

        return notifications

    @classmethod
    def notify_certificate_expiring(
        cls,
        db: Session,
        doc: BidDocument,
        days_remaining: int,
    ) -> Optional[Notification]:
        """
        Emits certificate expiration alerts (e.g. 30, 7 days before or expired).
        """
        bid = doc.bid or db.scalars(select(Bid).where(Bid.id == doc.bid_id)).first()
        if not bid:
            return None

        recipient_id = doc.uploaded_by_profile_id or bid.created_by_profile_id
        if not recipient_id:
            return None

        if days_remaining <= 0:
            sev = NotificationSeverity.CRITICAL
            title = f"Certificate Expired: {doc.original_filename}"
            msg = f"Uploaded certificate '{doc.document_name}' has expired. Please upload a renewed certificate."
        elif days_remaining <= 7:
            sev = NotificationSeverity.CRITICAL
            title = f"Certificate Expiring Soon: {doc.original_filename}"
            msg = f"Uploaded certificate '{doc.document_name}' will expire in {days_remaining} days."
        else:
            sev = NotificationSeverity.WARNING
            title = f"Certificate Expiry Reminder: {doc.original_filename}"
            msg = f"Uploaded certificate '{doc.document_name}' will expire in {days_remaining} days."

        return cls.create_notification(
            db=db,
            recipient_profile_id=recipient_id,
            organization_id=bid.bidder_organization_id,
            notification_type=NotificationType.CERTIFICATE_EXPIRING,
            severity=sev,
            title=title,
            message=msg,
            tender_id=bid.tender_id,
            bid_id=bid.id,
            document_id=doc.id,
            action_url=f"/bidder/documents",
            dedupe_key=f"cert_exp_{doc.id}_{days_remaining}d",
            metadata_json={"days_remaining": days_remaining, "document_name": doc.document_name},
        )

    # -------------------------------------------------------------------------
    # Retrieval & Read/Unread State Management
    # -------------------------------------------------------------------------

    @classmethod
    def get_notifications_for_user(
        cls,
        db: Session,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        is_read: Optional[bool] = None,
        severity: Optional[str] = None,
        notification_type: Optional[str] = None,
        tender_id: Optional[uuid.UUID] = None,
        bid_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Notification], int, int]:
        """
        Retrieves paginated notifications for the authenticated user's profile
        with strict multi-tenant and profile boundary checks.
        Returns: (items, total_count, unread_count)
        """
        if not current_user.profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile not configured.",
            )

        page = max(1, page)
        page_size = max(1, min(100, page_size))

        # Base filter strictly scoped to current user profile
        conditions = [Notification.recipient_profile_id == current_user.profile_id]

        if is_read is not None:
            conditions.append(Notification.is_read == is_read)
        if severity:
            conditions.append(Notification.severity == severity.upper())
        if notification_type:
            conditions.append(Notification.notification_type == notification_type.upper())
        if tender_id:
            conditions.append(Notification.tender_id == tender_id)
        if bid_id:
            conditions.append(Notification.bid_id == bid_id)
        if search and search.strip():
            kw = f"%{search.strip()}%"
            conditions.append(or_(Notification.title.ilike(kw), Notification.message.ilike(kw)))

        # Total matching records
        total_count = db.scalar(
            select(func.count(Notification.id)).where(and_(*conditions))
        ) or 0

        # Unread count for current user
        unread_count = db.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_profile_id == current_user.profile_id,
                Notification.is_read == False,
            )
        ) or 0

        # Paginated items
        items = db.scalars(
            select(Notification)
            .where(and_(*conditions))
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return list(items), total_count, unread_count

    @classmethod
    def get_unread_count_for_user(cls, db: Session, current_user: User) -> int:
        """
        Fast unread notification count query for navbar badge polling.
        """
        if not current_user.profile_id:
            return 0

        count = db.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_profile_id == current_user.profile_id,
                Notification.is_read == False,
            )
        )
        return count or 0

    @classmethod
    def mark_as_read(
        cls,
        db: Session,
        current_user: User,
        notification_id: uuid.UUID,
    ) -> Notification:
        """
        Marks a specific notification as read. Enforces strict profile ownership.
        """
        if not current_user.profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile not configured.",
            )

        notification = db.scalars(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.recipient_profile_id == current_user.profile_id,
            )
        ).first()

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or access denied.",
            )

        if not notification.is_read:
            notification.mark_read()
            db.commit()
            db.refresh(notification)

            cls._record_notification_audit(
                db=db,
                notification=notification,
                event_type=AuditEventType.NOTIFICATION_READ,
                action="NOTIFICATION_READ",
                summary=f"Notification '{notification.title}' marked as read.",
                user=current_user,
            )

        return notification

    @classmethod
    def mark_as_unread(
        cls,
        db: Session,
        current_user: User,
        notification_id: uuid.UUID,
    ) -> Notification:
        """
        Marks a specific notification as unread. Enforces strict profile ownership.
        """
        if not current_user.profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile not configured.",
            )

        notification = db.scalars(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.recipient_profile_id == current_user.profile_id,
            )
        ).first()

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or access denied.",
            )

        if notification.is_read:
            notification.mark_unread()
            db.commit()
            db.refresh(notification)

        return notification

    @classmethod
    def mark_all_as_read(cls, db: Session, current_user: User) -> int:
        """
        Marks all unread notifications for the current authenticated profile as read.
        Returns the number of notifications marked.
        """
        if not current_user.profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile not configured.",
            )

        now_utc = datetime.now(timezone.utc)
        result = db.execute(
            update(Notification)
            .where(
                Notification.recipient_profile_id == current_user.profile_id,
                Notification.is_read == False,
            )
            .values(is_read=True, read_at=now_utc)
        )
        marked_count = result.rowcount
        db.commit()

        if marked_count > 0:
            cls._record_bulk_read_audit(db=db, user=current_user, marked_count=marked_count)

        return marked_count

    # -------------------------------------------------------------------------
    # Audit Logging Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _record_notification_audit(
        cls,
        db: Session,
        notification: Notification,
        event_type: str,
        action: str,
        summary: str,
        user: Optional[User] = None,
    ) -> None:
        """Gracefully records audit trail events for notification actions."""
        try:
            actor_user_id = user.id if user else None
            actor_profile_id = user.profile_id if user and user.profile_id else None
            actor_name = user.profile.full_name if (user and user.profile) else "Notification Service"
            actor_role = user.profile.role.name if (user and user.profile and user.profile.role) else "SYSTEM"

            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=notification.organization_id,
                    tender_id=notification.tender_id,
                    bid_id=notification.bid_id,
                    actor_user_id=actor_user_id,
                    actor_profile_id=actor_profile_id,
                    actor_name=actor_name,
                    actor_role=actor_role,
                    actor_source=AuditActorSource.HUMAN if user else AuditActorSource.SYSTEM,
                    event_type=event_type,
                    entity_type=AuditEntityType.NOTIFICATION,
                    entity_id=notification.id,
                    action=action,
                    summary=summary,
                    metadata={
                        "notification_type": notification.notification_type,
                        "severity": notification.severity,
                        "recipient_profile_id": str(notification.recipient_profile_id),
                    },
                ),
            )
            db.commit()
        except Exception as audit_err:
            logger.warning("Failed to record notification audit event: %s", audit_err)

    @classmethod
    def _record_bulk_read_audit(cls, db: Session, user: User, marked_count: int) -> None:
        """Gracefully records bulk mark-all-read audit summary."""
        try:
            profile = user.profile or db.scalars(select(Profile).where(Profile.id == user.profile_id)).first()
            org_id = profile.organization_id if profile else None
            if not org_id:
                return

            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=org_id,
                    actor_user_id=user.id,
                    actor_profile_id=user.profile_id,
                    actor_name=profile.full_name if profile else user.email,
                    actor_role=profile.role.name if (profile and profile.role) else "USER",
                    actor_source=AuditActorSource.HUMAN,
                    event_type=AuditEventType.NOTIFICATIONS_ALL_READ,
                    entity_type=AuditEntityType.NOTIFICATION,
                    entity_id=user.profile_id,
                    action="NOTIFICATIONS_ALL_READ",
                    summary=f"User marked {marked_count} notifications as read.",
                    metadata={"marked_count": marked_count},
                ),
            )
            db.commit()
        except Exception as audit_err:
            logger.warning("Failed to record bulk read audit: %s", audit_err)
