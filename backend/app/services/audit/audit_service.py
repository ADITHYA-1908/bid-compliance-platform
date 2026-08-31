"""
Audit Service
Coordinates append-only event recording, multi-dimensional search, timeline generation,
and KPI metrics calculation for Part 8E Audit Trail & Decision History.
"""

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import cast, func, or_, select, String
from sqlalchemy.orm import Session, joinedload

from app.db.models.audit_event import AuditActorSource, AuditEntityType, AuditEventType, AuditEvent
from app.db.models.bid import Bid
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.user import User
from app.schemas.audit import (
    AuditEventActorSummary,
    AuditEventItemResponse,
    AuditKPIsResponse,
    AuditListResponse,
    RecordAuditEventDTO,
)

logger = logging.getLogger(__name__)

# Maximum metadata size to prevent bloat (16 KB)
MAX_METADATA_SIZE_BYTES = 16 * 1024

# Human-friendly labels for UI rendering
EVENT_LABEL_MAP: Dict[str, str] = {
    AuditEventType.TENDER_CREATED: "Tender Created",
    AuditEventType.TENDER_UPDATED: "Tender Details Updated",
    AuditEventType.TENDER_PUBLISHED: "Tender Published",
    AuditEventType.TENDER_STATUS_CHANGED: "Tender Status Changed",
    AuditEventType.BID_CREATED: "Bid Draft Created",
    AuditEventType.BID_DOCUMENT_UPLOADED: "Bid Document Uploaded",
    AuditEventType.BID_DOCUMENT_REPLACED: "Bid Document Replaced",
    AuditEventType.BID_SUBMITTED: "Bid Formal Submission",
    AuditEventType.DOCUMENT_PROCESSING_COMPLETED: "Document OCR Processing Completed",
    AuditEventType.DOCUMENT_CLASSIFIED: "Document Classified",
    AuditEventType.DOCUMENT_EXTRACTION_COMPLETED: "Document Entities Extracted",
    AuditEventType.VERIFICATION_STARTED: "External Verification Initiated",
    AuditEventType.VERIFICATION_COMPLETED: "External Verification Completed",
    AuditEventType.VERIFICATION_UNAVAILABLE: "External Verification Unavailable",
    AuditEventType.VERIFICATION_RETRIED: "External Verification Retried",
    AuditEventType.COMPLIANCE_EVALUATED: "Compliance Rules Evaluated",
    AuditEventType.COMPLIANCE_RE_EVALUATED: "Compliance Rules Re-evaluated",
    AuditEventType.SCORE_CALCULATED: "Compliance Score Calculated",
    AuditEventType.SCORE_RECALCULATED: "Compliance Score Recalculated",
    AuditEventType.RISK_CALCULATED: "Deterministic Risk Calculated",
    AuditEventType.RISK_OVERRIDE_APPLIED: "Critical Risk Floor Override Applied",
    AuditEventType.AI_RECOMMENDATION_GENERATED: "AI Recommendation Generated",
    AuditEventType.AI_RECOMMENDATION_REGENERATED: "AI Recommendation Regenerated",
    AuditEventType.AI_RECOMMENDATION_STALE: "AI Recommendation Flagged Stale",
    AuditEventType.HUMAN_REVIEW_STARTED: "Human Review Started",
    AuditEventType.HUMAN_REVIEW_NOTE_ADDED: "Reviewer Note Appended",
    AuditEventType.HUMAN_REVIEW_RESOLVED: "Human Review Resolved",
    AuditEventType.HUMAN_REVIEW_ESCALATED: "Human Review Escalated",
    AuditEventType.BID_SHORTLISTED: "Bid Added to Shortlist",
    AuditEventType.BID_REMOVED_FROM_SHORTLIST: "Bid Removed from Shortlist",
    AuditEventType.BID_DECISION_CREATED: "Final Human Decision Recorded",
    AuditEventType.BID_DECISION_SUPERSEDED: "Decision Superseded by New Version",
    AuditEventType.BID_DECISION_RECONFIRMED: "Decision Reconfirmed by Officer",
    AuditEventType.BID_DECISION_STALE: "Decision Flagged Stale on Upstream Mutation",
}


def _verify_audit_access(db: Session, user: User) -> Tuple[Profile, Role]:
    """
    Enforces multi-tenant authorization for procurement audit trail operations.
    Allowed: PROCUREMENT_OFFICER (tenant-scoped) and ADMIN (full scope).
    Forbidden: BIDDER (HTTP 403).
    """
    profile = db.scalars(
        select(Profile)
        .options(joinedload(Profile.role), joinedload(Profile.organization))
        .where(Profile.id == user.profile_id)
    ).first()
    if not profile or not profile.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile or role not found.",
        )

    role = profile.role
    if role.name not in ("PROCUREMENT_OFFICER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Procurement audit trail and reports are restricted to authorized Procurement Officers and Admins.",
        )

    return profile, role


def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strips any sensitive credentials and enforces payload size bounds.
    """
    if not metadata:
        return {}

    sanitized = {}
    sensitive_keys = {
        "password", "password_hash", "token", "access_token", "secret",
        "jwt", "api_key", "authorization", "raw_ocr_text", "binary_content"
    }

    for k, v in metadata.items():
        if k.lower() in sensitive_keys:
            continue
        # Convert non-serializable objects (UUIDs, Decimals, Datetimes)
        if isinstance(v, uuid.UUID):
            sanitized[k] = str(v)
        elif isinstance(v, datetime):
            sanitized[k] = v.isoformat()
        else:
            sanitized[k] = v

    # Check serialized size
    try:
        serialized = json.dumps(sanitized)
        if len(serialized.encode("utf-8")) > MAX_METADATA_SIZE_BYTES:
            sanitized = {
                "truncated": True,
                "summary": "Metadata truncated due to size limit (>16KB)",
                "item_keys": list(metadata.keys())[:20],
            }
    except Exception:
        sanitized = {"error": "Metadata serialization failed"}

    return sanitized


class AuditService:
    """
    Central service managing append-only event logging, queries, and timelines.
    """

    @classmethod
    def record_event(
        cls,
        db: Session,
        event_dto: RecordAuditEventDTO,
    ) -> AuditEvent:
        """
        Appends an immutable AuditEvent to the database within the caller's transaction.
        """
        clean_meta = _sanitize_metadata(event_dto.metadata)

        audit_event = AuditEvent(
            organization_id=event_dto.organization_id,
            tender_id=event_dto.tender_id,
            bid_id=event_dto.bid_id,
            actor_user_id=event_dto.actor_user_id,
            actor_profile_id=event_dto.actor_profile_id,
            actor_name=event_dto.actor_name,
            actor_role=event_dto.actor_role,
            actor_source=event_dto.actor_source,
            event_type=event_dto.event_type,
            entity_type=event_dto.entity_type,
            entity_id=event_dto.entity_id,
            action=event_dto.action,
            summary=event_dto.summary,
            metadata_json=clean_meta,
            ip_address=event_dto.ip_address,
            user_agent=event_dto.user_agent,
            created_at=datetime.now(timezone.utc),
        )

        db.add(audit_event)
        # Flush to generate ID within active transaction
        db.flush()

        logger.info(
            f"[AuditEvent] org={event_dto.organization_id} type={event_dto.event_type} "
            f"actor={event_dto.actor_name or event_dto.actor_source} entity={event_dto.entity_type}:{event_dto.entity_id}"
        )

        return audit_event

    @classmethod
    def record_tender_event(
        cls,
        db: Session,
        organization_id: uuid.UUID,
        tender_id: uuid.UUID,
        event_type: str,
        action: str,
        summary: str,
        metadata: Optional[Dict[str, Any]] = None,
        user: Optional[User] = None,
    ) -> AuditEvent:
        """Convenience helper for Tender events."""
        actor_name = None
        actor_role = None
        actor_user_id = None
        actor_profile_id = None
        actor_source = AuditActorSource.SYSTEM

        if user:
            actor_user_id = user.id
            actor_profile_id = user.profile_id
            actor_source = AuditActorSource.HUMAN
            if user.profile:
                actor_name = user.profile.full_name
                if user.profile.role:
                    actor_role = user.profile.role.name

        dto = RecordAuditEventDTO(
            organization_id=organization_id,
            tender_id=tender_id,
            bid_id=None,
            actor_user_id=actor_user_id,
            actor_profile_id=actor_profile_id,
            actor_name=actor_name,
            actor_role=actor_role,
            actor_source=actor_source,
            event_type=event_type,
            entity_type=AuditEntityType.TENDER,
            entity_id=tender_id,
            action=action,
            summary=summary,
            metadata=metadata or {},
        )
        return cls.record_event(db, dto)

    @classmethod
    def record_bid_event(
        cls,
        db: Session,
        organization_id: uuid.UUID,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
        event_type: str,
        action: str,
        summary: str,
        metadata: Optional[Dict[str, Any]] = None,
        user: Optional[User] = None,
        actor_source: str = AuditActorSource.HUMAN,
    ) -> AuditEvent:
        """Convenience helper for Bid events."""
        actor_name = None
        actor_role = None
        actor_user_id = None
        actor_profile_id = None

        if user:
            actor_user_id = user.id
            actor_profile_id = user.profile_id
            if user.profile:
                actor_name = user.profile.full_name
                if user.profile.role:
                    actor_role = user.profile.role.name

        dto = RecordAuditEventDTO(
            organization_id=organization_id,
            tender_id=tender_id,
            bid_id=bid_id,
            actor_user_id=actor_user_id,
            actor_profile_id=actor_profile_id,
            actor_name=actor_name,
            actor_role=actor_role,
            actor_source=actor_source,
            event_type=event_type,
            entity_type=AuditEntityType.BID,
            entity_id=bid_id,
            action=action,
            summary=summary,
            metadata=metadata or {},
        )
        return cls.record_event(db, dto)

    @classmethod
    def get_audit_events(
        cls,
        db: Session,
        user: User,
        tender_id: Optional[uuid.UUID] = None,
        bid_id: Optional[uuid.UUID] = None,
        actor_user_id: Optional[uuid.UUID] = None,
        event_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AuditListResponse:
        """
        Queries and filters audit events with strict multi-tenant isolation, search, and pagination.
        """
        profile, role = _verify_audit_access(db, user)

        # 1. Base Query with joined entity relations for display
        stmt = (
            select(AuditEvent)
            .options(
                joinedload(AuditEvent.tender),
                joinedload(AuditEvent.bid).joinedload(Bid.bidder_organization),
                joinedload(AuditEvent.actor_profile).joinedload(Profile.role),
            )
        )

        # 2. Multi-Tenant Scope Filter
        if role.name != "ADMIN":
            stmt = stmt.where(AuditEvent.organization_id == profile.organization_id)

        # 3. Optional Filters
        if tender_id:
            stmt = stmt.where(AuditEvent.tender_id == tender_id)
        if bid_id:
            stmt = stmt.where(AuditEvent.bid_id == bid_id)
        if actor_user_id:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if entity_type:
            stmt = stmt.where(AuditEvent.entity_type == entity_type)
        if date_from:
            stmt = stmt.where(AuditEvent.created_at >= date_from)
        if date_to:
            stmt = stmt.where(AuditEvent.created_at <= date_to)

        # 4. Search Filter
        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.outerjoin(Tender, AuditEvent.tender_id == Tender.id).outerjoin(
                Bid, AuditEvent.bid_id == Bid.id
            ).where(
                or_(
                    AuditEvent.summary.ilike(term),
                    AuditEvent.action.ilike(term),
                    AuditEvent.actor_name.ilike(term),
                    AuditEvent.event_type.ilike(term),
                    Tender.tender_number.ilike(term),
                    Tender.title.ilike(term),
                    Bid.bid_number.ilike(term),
                    cast(AuditEvent.metadata_json, String).ilike(term),
                )
            )

        # 5. Count Total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # 6. Pagination & Ordering (Newest First)
        offset = (page - 1) * page_size
        stmt = stmt.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).offset(offset).limit(page_size)
        raw_events = db.execute(stmt).unique().scalars().all()

        # 7. Compute Real-time KPIs within user's scope
        now_utc = datetime.now(timezone.utc)
        start_of_today = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)

        kpi_scope_filter = [AuditEvent.organization_id == profile.organization_id] if role.name != "ADMIN" else []
        if tender_id:
            kpi_scope_filter.append(AuditEvent.tender_id == tender_id)

        all_scope_events = db.scalars(
            select(AuditEvent).where(*kpi_scope_filter)
        ).all()

        kpis = AuditKPIsResponse(
            total_events=len(all_scope_events),
            events_today=sum(1 for e in all_scope_events if e.created_at >= start_of_today),
            decisions_recorded=sum(1 for e in all_scope_events if "DECISION" in e.event_type),
            reviews_resolved=sum(1 for e in all_scope_events if e.event_type == AuditEventType.HUMAN_REVIEW_RESOLVED),
            ai_events=sum(1 for e in all_scope_events if e.actor_source == AuditActorSource.AI_SERVICE or "AI_" in e.event_type),
            system_events=sum(1 for e in all_scope_events if e.actor_source == AuditActorSource.SYSTEM),
        )

        # 8. Build DTO Response
        items: List[AuditEventItemResponse] = []
        for e in raw_events:
            actor_name = e.actor_name
            actor_role = e.actor_role
            if e.actor_profile:
                actor_name = actor_name or e.actor_profile.full_name
                if e.actor_profile.role:
                    actor_role = actor_role or e.actor_profile.role.name

            tender_num = e.tender.tender_number if e.tender else None
            bid_num = e.bid.bid_number if e.bid else None
            bidder_n = (
                e.bid.bidder_organization.name
                if e.bid and e.bid.bidder_organization
                else None
            )

            items.append(
                AuditEventItemResponse(
                    id=e.id,
                    organization_id=e.organization_id,
                    tender_id=e.tender_id,
                    bid_id=e.bid_id,
                    tender_number=tender_num,
                    bid_number=bid_num,
                    bidder_name=bidder_n,
                    actor=AuditEventActorSummary(
                        user_id=e.actor_user_id,
                        profile_id=e.actor_profile_id,
                        name=actor_name,
                        role=actor_role,
                        source=e.actor_source,
                    ),
                    event_type=e.event_type,
                    event_label=EVENT_LABEL_MAP.get(e.event_type, e.event_type.replace("_", " ").title()),
                    entity_type=e.entity_type,
                    entity_id=e.entity_id,
                    action=e.action,
                    summary=e.summary,
                    metadata=e.metadata_json or {},
                    ip_address=e.ip_address,
                    created_at=e.created_at,
                )
            )

        total_pages = max(1, (total + page_size - 1) // page_size)

        return AuditListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            kpis=kpis,
        )

    @classmethod
    def get_bid_timeline(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
    ) -> List[AuditEventItemResponse]:
        """
        Retrieves the complete chronological lifecycle event sequence for a proposal.
        """
        res = cls.get_audit_events(
            db=db,
            user=user,
            tender_id=tender_id,
            bid_id=bid_id,
            page=1,
            page_size=1000,
        )
        # Order chronological (oldest to newest for timeline presentation)
        return sorted(res.items, key=lambda x: x.created_at)
