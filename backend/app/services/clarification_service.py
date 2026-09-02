"""
Clarification Request & Response Service for Part 16
Orchestrates auditable communication, evidence clarification, replacement document
linkage, deduplicated deadline notifications, and safe compliance re-evaluations.
"""

from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, case, desc, func, or_, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models.audit_event import (
    AuditEvent,
    AuditEventType,
    AuditEntityType,
    AuditActorSource,
)
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.clarification import (
    ClarificationPriority,
    ClarificationRequest,
    ClarificationResponse,
    ClarificationStatus,
    ClarificationType,
)
from app.db.models.compliance_result import ComplianceResult
from app.db.models.document_duplicate_match import DocumentDuplicateMatch
from app.db.models.human_review import (
    HumanReviewItem,
    HumanReviewNote,
    ReviewResolution,
    ReviewStatus,
)
from app.db.models.notification import (
    Notification,
    NotificationSeverity,
    NotificationType,
)
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.tender_requirement_version import TenderRequirementVersion
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.schemas.audit import RecordAuditEventDTO
from app.schemas.clarification import (
    ClarificationAnalyticsResponse,
    ClarificationRequestCreate,
    ClarificationRequestDetailResponse,
    ClarificationRequestListItemResponse,
    ClarificationRequestListResponse,
    ClarificationRequestUpdate,
    ClarificationResolveRequest,
    ClarificationResponseCreate,
    ClarificationResponseDTO,
    ClarificationSummaryResponse,
)
from app.services.audit.audit_service import AuditService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ClarificationService:
    """
    Central orchestration service for BidVerify AI clarification workflows.
    """

    @classmethod
    def create_clarification_request(
        cls,
        db: Session,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
        current_profile: Profile,
        payload: ClarificationRequestCreate,
    ) -> ClarificationRequest:
        """
        Procurement Officer creates a new Clarification Request for a Bid.
        Can be saved as DRAFT or sent immediately (SENT).
        """
        # 1. Fetch and validate Tender and Bid
        tender = db.scalars(select(Tender).where(Tender.id == tender_id)).first()
        if not tender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tender not found.",
            )

        bid = db.scalars(select(Bid).where(Bid.id == bid_id)).first()
        if not bid or bid.tender_id != tender_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bid does not exist or does not belong to the specified tender.",
            )

        # Multi-tenant check: current profile must belong to the tender's organization
        if current_profile.organization_id != tender.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to create clarification requests for this tender.",
            )

        # 2. Rule version provenance auto-lookup if requirement provided
        rule_version_id = payload.related_rule_version_id
        rule_version_number = payload.related_rule_version_number

        if payload.related_requirement_id and (not rule_version_id or not rule_version_number):
            req = db.scalars(
                select(TenderRequirement).where(
                    and_(
                        TenderRequirement.id == payload.related_requirement_id,
                        TenderRequirement.tender_id == tender_id,
                    )
                )
            ).first()
            if req:
                rule_version_number = req.current_version_number or 1
                # Find active version row if exists
                active_ver = db.scalars(
                    select(TenderRequirementVersion).where(
                        and_(
                            TenderRequirementVersion.tender_requirement_id == req.id,
                            TenderRequirementVersion.is_active == True,
                        )
                    )
                ).first()
                if active_ver:
                    rule_version_id = active_ver.id

        # 3. Determine initial status and timestamps
        now = datetime.now(timezone.utc)
        initial_status = ClarificationStatus.SENT if payload.send_immediately else ClarificationStatus.DRAFT
        sent_at = now if payload.send_immediately else None

        clarification_id = uuid.uuid4()
        req_record = ClarificationRequest(
            id=clarification_id,
            tender_id=tender_id,
            bid_id=bid_id,
            tender_organization_id=tender.organization_id,
            bidder_organization_id=bid.bidder_organization_id,
            created_by_profile_id=current_profile.id,
            assigned_bidder_profile_id=bid.created_by_profile_id,
            subject=payload.subject.strip(),
            message=payload.message.strip(),
            clarification_type=payload.clarification_type,
            priority=payload.priority,
            status=initial_status,
            due_date=payload.due_date,
            sent_at=sent_at,
            related_document_id=payload.related_document_id,
            related_requirement_id=payload.related_requirement_id,
            related_rule_version_id=rule_version_id,
            related_rule_version_number=rule_version_number,
            related_verification_record_id=payload.related_verification_record_id,
            related_compliance_result_id=payload.related_compliance_result_id,
            related_review_item_id=payload.related_review_item_id,
            related_duplicate_match_id=payload.related_duplicate_match_id,
            is_active=True,
        )

        db.add(req_record)
        db.flush()

        # 4. Audit Log
        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=tender.organization_id,
                    tender_id=tender_id,
                    bid_id=bid_id,
                    event_type=AuditEventType.CLARIFICATION_CREATED,
                    entity_type=AuditEntityType.CLARIFICATION_REQUEST,
                    entity_id=clarification_id,
                    actor_profile_id=current_profile.id,
                    actor_source=AuditActorSource.HUMAN,
                    action="CREATE_CLARIFICATION",
                    summary=f"Created clarification request for '{payload.subject}'",
                    metadata={
                        "subject": payload.subject,
                        "clarification_type": payload.clarification_type,
                        "priority": payload.priority,
                        "status": initial_status,
                        "due_date": payload.due_date.isoformat() if payload.due_date else None,
                        "related_requirement_id": str(payload.related_requirement_id) if payload.related_requirement_id else None,
                        "related_rule_version_number": rule_version_number,
                    },
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to record audit event for clarification creation: {e}")

        # 5. If sent immediately, dispatch notification to bidder & emit sent audit
        if payload.send_immediately:
            try:
                AuditService.record_event(
                    db=db,
                    event_dto=RecordAuditEventDTO(
                        organization_id=tender.organization_id,
                        tender_id=tender_id,
                        bid_id=bid_id,
                        event_type=AuditEventType.CLARIFICATION_SENT,
                        entity_type=AuditEntityType.CLARIFICATION_REQUEST,
                        entity_id=clarification_id,
                        actor_profile_id=current_profile.id,
                        actor_source=AuditActorSource.HUMAN,
                        action="SEND_CLARIFICATION",
                        summary=f"Sent clarification request for '{payload.subject}'",
                        metadata={"subject": payload.subject},
                    ),
                )
            except Exception as e:
                logger.warning(f"Failed to record audit event for clarification sent: {e}")

            cls._dispatch_clarification_requested_notification(
                db=db,
                clarification=req_record,
                tender=tender,
                bid=bid,
            )

        db.commit()
        db.refresh(req_record)
        return req_record

    @classmethod
    def send_clarification_request(
        cls,
        db: Session,
        clarification_id: uuid.UUID,
        current_profile: Profile,
    ) -> ClarificationRequest:
        """
        Transitions a DRAFT clarification to SENT and notifies the Bidder.
        """
        req = db.scalars(
            select(ClarificationRequest).where(ClarificationRequest.id == clarification_id)
        ).first()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clarification request not found.",
            )

        if current_profile.organization_id != req.tender_organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to send this clarification.",
            )

        if req.status != ClarificationStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot send clarification with status '{req.status}'. Only DRAFT requests can be sent.",
            )

        now = datetime.now(timezone.utc)
        req.status = ClarificationStatus.SENT
        req.sent_at = now
        db.flush()

        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=req.tender_organization_id,
                    tender_id=req.tender_id,
                    bid_id=req.bid_id,
                    event_type=AuditEventType.CLARIFICATION_SENT,
                    entity_type=AuditEntityType.CLARIFICATION_REQUEST,
                    entity_id=req.id,
                    actor_profile_id=current_profile.id,
                    actor_source=AuditActorSource.HUMAN,
                    action="SEND_CLARIFICATION",
                    summary=f"Sent clarification request for '{req.subject}'",
                    metadata={"subject": req.subject},
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to record audit event for clarification sent: {e}")

        tender = req.tender or db.scalars(select(Tender).where(Tender.id == req.tender_id)).first()
        bid = req.bid or db.scalars(select(Bid).where(Bid.id == req.bid_id)).first()
        cls._dispatch_clarification_requested_notification(db=db, clarification=req, tender=tender, bid=bid)

        db.commit()
        db.refresh(req)
        return req

    @classmethod
    def mark_clarification_viewed(
        cls,
        db: Session,
        clarification_id: uuid.UUID,
        current_profile: Profile,
    ) -> ClarificationRequest:
        """
        Transitions status from SENT to VIEWED when the Bidder opens the clarification.
        """
        req = db.scalars(
            select(ClarificationRequest).where(ClarificationRequest.id == clarification_id)
        ).first()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clarification request not found.",
            )

        # Ensure viewer is from bidder organization
        if current_profile.organization_id != req.bidder_organization_id:
            return req

        if req.status == ClarificationStatus.SENT:
            now = datetime.now(timezone.utc)
            req.status = ClarificationStatus.VIEWED
            req.viewed_at = now
            db.flush()

            try:
                AuditService.record_event(
                    db=db,
                    event_dto=RecordAuditEventDTO(
                        organization_id=req.tender_organization_id,
                        tender_id=req.tender_id,
                        bid_id=req.bid_id,
                        event_type=AuditEventType.CLARIFICATION_VIEWED,
                        entity_type=AuditEntityType.CLARIFICATION_REQUEST,
                        entity_id=req.id,
                        actor_profile_id=current_profile.id,
                        actor_source=AuditActorSource.HUMAN,
                        action="VIEW_CLARIFICATION",
                        summary=f"Bidder viewed clarification request '{req.subject}'",
                        metadata={"viewed_at": now.isoformat()},
                    ),
                )
            except Exception as e:
                logger.warning(f"Failed to record audit event for clarification viewed: {e}")

            db.commit()
            db.refresh(req)

        return req

    @classmethod
    def respond_to_clarification(
        cls,
        db: Session,
        clarification_id: uuid.UUID,
        current_profile: Profile,
        payload: ClarificationResponseCreate,
    ) -> ClarificationResponse:
        """
        Bidder submits response text and optional supporting or replacement document.
        Transitions clarification to RESPONDED and notifies Procurement Officer.
        """
        req = db.scalars(
            select(ClarificationRequest).where(ClarificationRequest.id == clarification_id)
        ).first()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clarification request not found.",
            )

        # Multi-tenant security check: must belong to bidder organization
        if current_profile.organization_id != req.bidder_organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to respond to this clarification.",
            )

        # Locked state check
        if req.status in (
            ClarificationStatus.RESOLVED,
            ClarificationStatus.CLOSED,
            ClarificationStatus.CANCELLED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot respond to a clarification with status '{req.status}'. This thread is closed.",
            )

        # 1. Handle replacement document logic if specified
        replaced_doc_id = payload.replaced_document_id or req.related_document_id
        if payload.is_replacement_document and payload.attached_document_id and replaced_doc_id:
            # Check replaced document
            old_doc = db.scalars(
                select(BidDocument).where(BidDocument.id == replaced_doc_id)
            ).first()
            if old_doc and old_doc.bid_id == req.bid_id:
                old_doc.is_active = False
                old_doc.status = "REPLACED"

            # Check new document
            new_doc = db.scalars(
                select(BidDocument).where(BidDocument.id == payload.attached_document_id)
            ).first()
            if new_doc and new_doc.bid_id == req.bid_id:
                new_doc.is_active = True
                new_doc.status = "UPLOADED"
                if old_doc:
                    new_doc.version = old_doc.version + 1
                    if not new_doc.tender_requirement_id and old_doc.tender_requirement_id:
                        new_doc.tender_requirement_id = old_doc.tender_requirement_id

        # 2. Create ClarificationResponse record
        now = datetime.now(timezone.utc)
        resp_id = uuid.uuid4()
        response_record = ClarificationResponse(
            id=resp_id,
            clarification_request_id=req.id,
            responded_by_profile_id=current_profile.id,
            response_text=payload.response_text.strip(),
            attached_document_id=payload.attached_document_id,
            is_replacement_document=payload.is_replacement_document,
            replaced_document_id=replaced_doc_id if payload.is_replacement_document else None,
            metadata_json={
                "submitted_at": now.isoformat(),
                "has_attachment": bool(payload.attached_document_id),
                "is_replacement": payload.is_replacement_document,
            },
        )
        db.add(response_record)

        # 3. Update ClarificationRequest state
        req.status = ClarificationStatus.RESPONDED
        req.responded_at = now
        db.flush()

        # 4. Audit Log
        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=req.tender_organization_id,
                    tender_id=req.tender_id,
                    bid_id=req.bid_id,
                    event_type=AuditEventType.CLARIFICATION_RESPONDED,
                    entity_type=AuditEntityType.CLARIFICATION_RESPONSE,
                    entity_id=resp_id,
                    actor_profile_id=current_profile.id,
                    actor_source=AuditActorSource.HUMAN,
                    action="RESPOND_CLARIFICATION",
                    summary=f"Bidder responded to clarification request '{req.subject}'",
                    metadata={
                        "clarification_id": str(req.id),
                        "has_attachment": bool(payload.attached_document_id),
                        "is_replacement_document": payload.is_replacement_document,
                        "attached_document_id": str(payload.attached_document_id) if payload.attached_document_id else None,
                    },
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to record audit event for clarification responded: {e}")

        # 5. Notify Procurement Officer
        tender = req.tender or db.scalars(select(Tender).where(Tender.id == req.tender_id)).first()
        bid = req.bid or db.scalars(select(Bid).where(Bid.id == req.bid_id)).first()
        bid_num = bid.bid_number if bid else "Unknown"
        tender_title = tender.title if tender else "Tender"

        NotificationService.create_notification(
            db=db,
            recipient_profile_id=req.created_by_profile_id,
            organization_id=req.tender_organization_id,
            notification_type=NotificationType.CLARIFICATION_RESPONDED,
            severity=NotificationSeverity.INFO,
            title="Clarification Response Received",
            message=f"Bidder responded to clarification '{req.subject}' on Bid {bid_num} for tender '{tender_title}'.",
            tender_id=req.tender_id,
            bid_id=req.bid_id,
            document_id=payload.attached_document_id,
            action_url=f"/procurement/clarifications?id={req.id}",
            dedupe_key=f"clarification_resp_{req.id}_{resp_id}",
            metadata_json={"clarification_id": str(req.id), "response_id": str(resp_id)},
        )

        # 6. If linked to a HumanReviewItem, add an informative note
        if req.related_review_item_id:
            review_item = db.scalars(
                select(HumanReviewItem).where(HumanReviewItem.id == req.related_review_item_id)
            ).first()
            if review_item:
                note = HumanReviewNote(
                    id=uuid.uuid4(),
                    review_item_id=review_item.id,
                    author_profile_id=current_profile.id,
                    note_text=f"[Clarification Response] Bidder provided explanation for '{req.subject}': {payload.response_text[:200]}...",
                )
                db.add(note)

        db.commit()
        db.refresh(response_record)
        return response_record

    @classmethod
    def mark_under_review(
        cls,
        db: Session,
        clarification_id: uuid.UUID,
        current_profile: Profile,
    ) -> ClarificationRequest:
        """
        Procurement Officer marks a responded clarification as UNDER_REVIEW while analyzing evidence.
        """
        req = db.scalars(
            select(ClarificationRequest).where(ClarificationRequest.id == clarification_id)
        ).first()
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clarification not found.")

        if current_profile.organization_id != req.tender_organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

        req.status = ClarificationStatus.UNDER_REVIEW
        db.flush()

        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=req.tender_organization_id,
                    tender_id=req.tender_id,
                    bid_id=req.bid_id,
                    event_type=AuditEventType.CLARIFICATION_UNDER_REVIEW,
                    entity_type=AuditEntityType.CLARIFICATION_REQUEST,
                    entity_id=req.id,
                    actor_profile_id=current_profile.id,
                    actor_source=AuditActorSource.HUMAN,
                    action="REVIEW_CLARIFICATION",
                    summary=f"Procurement officer marked clarification '{req.subject}' as UNDER_REVIEW",
                    metadata={"status": ClarificationStatus.UNDER_REVIEW},
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to record audit event for clarification review: {e}")

        db.commit()
        db.refresh(req)
        return req

    @classmethod
    def resolve_clarification(
        cls,
        db: Session,
        clarification_id: uuid.UUID,
        current_profile: Profile,
        payload: ClarificationResolveRequest,
    ) -> ClarificationRequest:
        """
        Procurement Officer resolves the clarification with an auditable resolution note.
        Optionally triggers deterministic re-evaluation of relevant criteria.
        """
        req = db.scalars(
            select(ClarificationRequest).where(ClarificationRequest.id == clarification_id)
        ).first()
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clarification not found.")

        if current_profile.organization_id != req.tender_organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

        now = datetime.now(timezone.utc)
        req.status = ClarificationStatus.RESOLVED
        req.resolved_by_profile_id = current_profile.id
        req.resolved_at = now
        req.resolution_note = payload.resolution_note.strip() if payload.resolution_note else None
        db.flush()

        # Audit event
        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=req.tender_organization_id,
                    tender_id=req.tender_id,
                    bid_id=req.bid_id,
                    event_type=AuditEventType.CLARIFICATION_RESOLVED,
                    entity_type=AuditEntityType.CLARIFICATION_REQUEST,
                    entity_id=req.id,
                    actor_profile_id=current_profile.id,
                    actor_source=AuditActorSource.HUMAN,
                    action="RESOLVE_CLARIFICATION",
                    summary=f"Procurement officer resolved clarification '{req.subject}'",
                    metadata={
                        "resolution_note": req.resolution_note,
                        "trigger_reevaluation": payload.trigger_reevaluation,
                    },
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to record audit event for clarification resolve: {e}")

        # Notify Bidder
        tender = req.tender or db.scalars(select(Tender).where(Tender.id == req.tender_id)).first()
        bid = req.bid or db.scalars(select(Bid).where(Bid.id == req.bid_id)).first()
        tender_title = tender.title if tender else "Tender"

        NotificationService.create_notification(
            db=db,
            recipient_profile_id=req.assigned_bidder_profile_id or bid.created_by_profile_id,
            organization_id=req.bidder_organization_id,
            notification_type=NotificationType.CLARIFICATION_RESOLVED,
            severity=NotificationSeverity.SUCCESS,
            title="Clarification Resolved",
            message=f"Clarification '{req.subject}' on tender '{tender_title}' has been marked as RESOLVED by the Procurement Officer.",
            tender_id=req.tender_id,
            bid_id=req.bid_id,
            action_url=f"/bidder/clarifications?id={req.id}",
            dedupe_key=f"clarification_resolved_{req.id}",
            metadata_json={"clarification_id": str(req.id), "resolution_note": req.resolution_note},
        )

        # Optional re-evaluation trigger
        if payload.trigger_reevaluation:
            cls.reevaluate_clarification_evidence(db=db, clarification=req, current_profile=current_profile)

        db.commit()
        db.refresh(req)
        return req

    @classmethod
    def cancel_clarification(
        cls,
        db: Session,
        clarification_id: uuid.UUID,
        current_profile: Profile,
        reason: Optional[str] = None,
    ) -> ClarificationRequest:
        """
        Procurement Officer cancels an open clarification request.
        """
        req = db.scalars(
            select(ClarificationRequest).where(ClarificationRequest.id == clarification_id)
        ).first()
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clarification not found.")

        if current_profile.organization_id != req.tender_organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

        req.status = ClarificationStatus.CANCELLED
        req.resolution_note = reason.strip() if reason else "Clarification request cancelled by Procurement Officer."
        db.flush()

        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=req.tender_organization_id,
                    tender_id=req.tender_id,
                    bid_id=req.bid_id,
                    event_type=AuditEventType.CLARIFICATION_CANCELLED,
                    entity_type=AuditEntityType.CLARIFICATION_REQUEST,
                    entity_id=req.id,
                    actor_profile_id=current_profile.id,
                    actor_source=AuditActorSource.HUMAN,
                    action="CANCEL_CLARIFICATION",
                    summary=f"Procurement officer cancelled clarification '{req.subject}'",
                    metadata={"reason": req.resolution_note},
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to record audit event for clarification cancelled: {e}")

        db.commit()
        db.refresh(req)
        return req

    @classmethod
    def reevaluate_clarification_evidence(
        cls,
        db: Session,
        clarification: ClarificationRequest,
        current_profile: Profile,
    ) -> Dict[str, Any]:
        """
        Safely re-evaluates compliance, scoring, and risk for the bid using newly submitted evidence.
        Strict non-self-approval principle: Existing human decisions (QUALIFIED / DISQUALIFIED / UNDER_REVIEW)
        are NEVER automatically modified.
        """
        from app.services.compliance_service import ComplianceService
        from app.services.scoring_service import ScoringService
        from app.services.risk_service import RiskService

        # 1. Trigger compliance evaluation
        compliance_summary = ComplianceService.evaluate_bid_compliance(
            db=db,
            bid_id=clarification.bid_id,
            reevaluate=True,
        )

        # 2. Trigger scoring calculation
        score_snapshot = ScoringService.compute_bid_score(
            db=db,
            bid_id=clarification.bid_id,
        )

        # 3. Trigger risk assessment
        risk_snapshot = RiskService.assess_bid_risk(
            db=db,
            bid_id=clarification.bid_id,
        )

        # Record audit event
        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=clarification.tender_organization_id,
                    tender_id=clarification.tender_id,
                    bid_id=clarification.bid_id,
                    event_type=AuditEventType.COMPLIANCE_RULE_REEVALUATION_REQUESTED,
                    entity_type=AuditEntityType.CLARIFICATION_REQUEST,
                    entity_id=clarification.id,
                    actor_profile_id=current_profile.id,
                    actor_source=AuditActorSource.HUMAN,
                    action="REEVALUATE_CLARIFICATION_CRITERIA",
                    summary=f"Re-evaluated criteria following clarification '{clarification.subject}'",
                    metadata={
                        "clarification_id": str(clarification.id),
                        "overall_compliance": compliance_summary.overall_status.value if hasattr(compliance_summary.overall_status, "value") else str(compliance_summary.overall_status),
                        "total_score": float(score_snapshot.total_score) if score_snapshot and score_snapshot.total_score is not None else None,
                        "risk_level": risk_snapshot.risk_level if risk_snapshot else None,
                    },
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to record audit event for clarification re-evaluation: {e}")

        return {
            "bid_id": str(clarification.bid_id),
            "compliance_status": compliance_summary.overall_status.value if hasattr(compliance_summary.overall_status, "value") else str(compliance_summary.overall_status),
            "total_score": float(score_snapshot.total_score) if score_snapshot and score_snapshot.total_score is not None else None,
            "risk_level": risk_snapshot.risk_level if risk_snapshot else None,
        }

    @classmethod
    def check_and_notify_due_dates(cls, db: Session) -> Dict[str, int]:
        """
        Scans active clarification requests and sends deduplicated countdown notifications:
        - 3 days remaining
        - 1 day remaining
        - Overdue alerts
        """
        now = datetime.now(timezone.utc)
        open_statuses = [
            ClarificationStatus.SENT,
            ClarificationStatus.VIEWED,
            ClarificationStatus.RESPONDED,
            ClarificationStatus.UNDER_REVIEW,
        ]

        active_requests = db.scalars(
            select(ClarificationRequest)
            .where(
                and_(
                    ClarificationRequest.is_active == True,
                    ClarificationRequest.due_date.is_not(None),
                    ClarificationRequest.status.in_(open_statuses),
                )
            )
            .options(
                joinedload(ClarificationRequest.tender),
                joinedload(ClarificationRequest.bid),
            )
        ).all()

        due_soon_3d_count = 0
        due_soon_1d_count = 0
        overdue_count = 0

        for req in active_requests:
            if not req.due_date:
                continue

            due_date = req.due_date if req.due_date.tzinfo else req.due_date.replace(tzinfo=timezone.utc)
            delta = due_date - now

            tender_title = req.tender.title if req.tender else "Tender"
            bid_num = req.bid.bid_number if req.bid else "Bid"
            recipient_id = req.assigned_bidder_profile_id or (req.bid.created_by_profile_id if req.bid else None)

            # 1. Overdue
            if delta.total_seconds() < 0:
                overdue_count += 1
                if recipient_id:
                    NotificationService.create_notification(
                        db=db,
                        recipient_profile_id=recipient_id,
                        organization_id=req.bidder_organization_id,
                        notification_type=NotificationType.CLARIFICATION_OVERDUE,
                        severity=NotificationSeverity.CRITICAL,
                        title="Clarification Request Overdue",
                        message=f"Clarification '{req.subject}' on Bid {bid_num} ({tender_title}) was due on {due_date.strftime('%d %b %Y')}.",
                        tender_id=req.tender_id,
                        bid_id=req.bid_id,
                        action_url=f"/bidder/clarifications?id={req.id}",
                        dedupe_key=f"clarification_overdue_{req.id}",
                        cooldown_hours=72,
                    )
            # 2. Due in <= 1 day
            elif delta <= timedelta(days=1):
                due_soon_1d_count += 1
                if recipient_id:
                    NotificationService.create_notification(
                        db=db,
                        recipient_profile_id=recipient_id,
                        organization_id=req.bidder_organization_id,
                        notification_type=NotificationType.CLARIFICATION_DUE_SOON,
                        severity=NotificationSeverity.WARNING,
                        title="Clarification Due in Less Than 24 Hours",
                        message=f"Urgent: Clarification '{req.subject}' for {tender_title} is due in less than 24 hours.",
                        tender_id=req.tender_id,
                        bid_id=req.bid_id,
                        action_url=f"/bidder/clarifications?id={req.id}",
                        dedupe_key=f"clarification_due_1d_{req.id}",
                        cooldown_hours=48,
                    )
            # 3. Due in <= 3 days
            elif delta <= timedelta(days=3):
                due_soon_3d_count += 1
                if recipient_id:
                    NotificationService.create_notification(
                        db=db,
                        recipient_profile_id=recipient_id,
                        organization_id=req.bidder_organization_id,
                        notification_type=NotificationType.CLARIFICATION_DUE_SOON,
                        severity=NotificationSeverity.INFO,
                        title="Clarification Response Due Soon",
                        message=f"Reminder: Clarification '{req.subject}' for {tender_title} is due on {due_date.strftime('%d %b %Y')}.",
                        tender_id=req.tender_id,
                        bid_id=req.bid_id,
                        action_url=f"/bidder/clarifications?id={req.id}",
                        dedupe_key=f"clarification_due_3d_{req.id}",
                        cooldown_hours=72,
                    )

        db.commit()
        return {
            "due_soon_3d": due_soon_3d_count,
            "due_soon_1d": due_soon_1d_count,
            "overdue": overdue_count,
        }

    @classmethod
    def list_procurement_clarifications(
        cls,
        db: Session,
        organization_id: uuid.UUID,
        tender_id: Optional[uuid.UUID] = None,
        bid_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ClarificationRequestListResponse:
        """
        Lists clarification requests scoped to the Procurement Officer's organization.
        """
        stmt = (
            select(ClarificationRequest)
            .where(
                and_(
                    ClarificationRequest.tender_organization_id == organization_id,
                    ClarificationRequest.is_active == True,
                )
            )
            .options(
                joinedload(ClarificationRequest.tender),
                joinedload(ClarificationRequest.bid).joinedload(Bid.bidder_organization),
                joinedload(ClarificationRequest.tender_organization),
                joinedload(ClarificationRequest.created_by),
                joinedload(ClarificationRequest.related_requirement),
                joinedload(ClarificationRequest.related_document),
                selectinload(ClarificationRequest.responses),
            )
        )

        if tender_id:
            stmt = stmt.where(ClarificationRequest.tender_id == tender_id)
        if bid_id:
            stmt = stmt.where(ClarificationRequest.bid_id == bid_id)
        if status_filter:
            stmt = stmt.where(ClarificationRequest.status == status_filter.upper())
        if priority_filter:
            stmt = stmt.where(ClarificationRequest.priority == priority_filter.upper())
        if type_filter:
            stmt = stmt.where(ClarificationRequest.clarification_type == type_filter.upper())
        if search:
            search_pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    ClarificationRequest.subject.ilike(search_pattern),
                    ClarificationRequest.message.ilike(search_pattern),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Pagination and ordering
        stmt = stmt.order_by(desc(ClarificationRequest.created_at))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        records = db.scalars(stmt).unique().all()
        now = datetime.now(timezone.utc)

        items: List[ClarificationRequestListItemResponse] = []
        for r in records:
            is_overdue = bool(
                r.due_date
                and r.status not in (ClarificationStatus.RESOLVED, ClarificationStatus.CLOSED, ClarificationStatus.CANCELLED)
                and (r.due_date if r.due_date.tzinfo else r.due_date.replace(tzinfo=timezone.utc)) < now
            )
            tender_num = r.tender.tender_number if r.tender else "Unknown"
            tender_title = r.tender.title if r.tender else "Unknown"
            bid_num = r.bid.bid_number if r.bid else "Unknown"
            bidder_name = r.bid.bidder_organization.name if (r.bid and r.bid.bidder_organization) else "Unknown"
            tender_org_name = r.tender_organization.name if r.tender_organization else "Procurement Dept"
            creator_name = r.created_by.full_name if r.created_by else "Procurement Officer"

            items.append(
                ClarificationRequestListItemResponse(
                    id=r.id,
                    tender_id=r.tender_id,
                    tender_number=tender_num,
                    tender_title=tender_title,
                    bid_id=r.bid_id,
                    bid_number=bid_num,
                    bidder_organization_name=bidder_name,
                    tender_organization_name=tender_org_name,
                    created_by_profile_id=r.created_by_profile_id,
                    created_by_name=creator_name,
                    subject=r.subject,
                    clarification_type=r.clarification_type,
                    priority=r.priority,
                    status=r.status,
                    due_date=r.due_date,
                    sent_at=r.sent_at,
                    viewed_at=r.viewed_at,
                    responded_at=r.responded_at,
                    resolved_at=r.resolved_at,
                    responses_count=len(r.responses or []),
                    is_overdue=is_overdue,
                    related_requirement_code=r.related_requirement.code if r.related_requirement else None,
                    related_document_name=r.related_document.original_filename if r.related_document else None,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return ClarificationRequestListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    def list_bidder_clarifications(
        cls,
        db: Session,
        organization_id: uuid.UUID,
        tender_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ClarificationRequestListResponse:
        """
        Lists clarification requests scoped to the Bidder's organization.
        Excludes DRAFT requests created by officers that haven't been sent.
        """
        stmt = (
            select(ClarificationRequest)
            .where(
                and_(
                    ClarificationRequest.bidder_organization_id == organization_id,
                    ClarificationRequest.status != ClarificationStatus.DRAFT,
                    ClarificationRequest.is_active == True,
                )
            )
            .options(
                joinedload(ClarificationRequest.tender),
                joinedload(ClarificationRequest.bid).joinedload(Bid.bidder_organization),
                joinedload(ClarificationRequest.tender_organization),
                joinedload(ClarificationRequest.created_by),
                joinedload(ClarificationRequest.related_requirement),
                joinedload(ClarificationRequest.related_document),
                selectinload(ClarificationRequest.responses),
            )
        )

        if tender_id:
            stmt = stmt.where(ClarificationRequest.tender_id == tender_id)
        if status_filter:
            stmt = stmt.where(ClarificationRequest.status == status_filter.upper())
        if priority_filter:
            stmt = stmt.where(ClarificationRequest.priority == priority_filter.upper())
        if type_filter:
            stmt = stmt.where(ClarificationRequest.clarification_type == type_filter.upper())
        if search:
            search_pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    ClarificationRequest.subject.ilike(search_pattern),
                    ClarificationRequest.message.ilike(search_pattern),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Pagination and ordering
        stmt = stmt.order_by(desc(ClarificationRequest.created_at))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        records = db.scalars(stmt).unique().all()
        now = datetime.now(timezone.utc)

        items: List[ClarificationRequestListItemResponse] = []
        for r in records:
            is_overdue = bool(
                r.due_date
                and r.status not in (ClarificationStatus.RESOLVED, ClarificationStatus.CLOSED, ClarificationStatus.CANCELLED)
                and (r.due_date if r.due_date.tzinfo else r.due_date.replace(tzinfo=timezone.utc)) < now
            )
            tender_num = r.tender.tender_number if r.tender else "Unknown"
            tender_title = r.tender.title if r.tender else "Unknown"
            bid_num = r.bid.bid_number if r.bid else "Unknown"
            bidder_name = r.bid.bidder_organization.name if (r.bid and r.bid.bidder_organization) else "Unknown"
            tender_org_name = r.tender_organization.name if r.tender_organization else "Procurement Dept"
            creator_name = r.created_by.full_name if r.created_by else "Procurement Officer"

            items.append(
                ClarificationRequestListItemResponse(
                    id=r.id,
                    tender_id=r.tender_id,
                    tender_number=tender_num,
                    tender_title=tender_title,
                    bid_id=r.bid_id,
                    bid_number=bid_num,
                    bidder_organization_name=bidder_name,
                    tender_organization_name=tender_org_name,
                    created_by_profile_id=r.created_by_profile_id,
                    created_by_name=creator_name,
                    subject=r.subject,
                    clarification_type=r.clarification_type,
                    priority=r.priority,
                    status=r.status,
                    due_date=r.due_date,
                    sent_at=r.sent_at,
                    viewed_at=r.viewed_at,
                    responded_at=r.responded_at,
                    resolved_at=r.resolved_at,
                    responses_count=len(r.responses or []),
                    is_overdue=is_overdue,
                    related_requirement_code=r.related_requirement.code if r.related_requirement else None,
                    related_document_name=r.related_document.original_filename if r.related_document else None,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return ClarificationRequestListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    def get_clarification_detail(
        cls,
        db: Session,
        clarification_id: uuid.UUID,
        current_profile: Profile,
    ) -> ClarificationRequestDetailResponse:
        """
        Retrieves the complete thread and context for a Clarification Request.
        """
        req = db.scalars(
            select(ClarificationRequest)
            .where(ClarificationRequest.id == clarification_id)
            .options(
                joinedload(ClarificationRequest.tender),
                joinedload(ClarificationRequest.bid).joinedload(Bid.bidder_organization),
                joinedload(ClarificationRequest.tender_organization),
                joinedload(ClarificationRequest.created_by),
                joinedload(ClarificationRequest.assigned_bidder),
                joinedload(ClarificationRequest.resolved_by),
                joinedload(ClarificationRequest.related_document),
                joinedload(ClarificationRequest.related_requirement),
                selectinload(ClarificationRequest.responses).joinedload(ClarificationResponse.responded_by),
                selectinload(ClarificationRequest.responses).joinedload(ClarificationResponse.attached_document),
                selectinload(ClarificationRequest.responses).joinedload(ClarificationResponse.replaced_document),
            )
        ).first()

        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clarification request not found.")

        # Security check: profile must belong to tender org OR bidder org
        if (
            current_profile.organization_id != req.tender_organization_id
            and current_profile.organization_id != req.bidder_organization_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this clarification request.",
            )

        # If viewed by bidder and currently SENT, mark VIEWED
        if current_profile.organization_id == req.bidder_organization_id and req.status == ClarificationStatus.SENT:
            cls.mark_clarification_viewed(db=db, clarification_id=req.id, current_profile=current_profile)

        now = datetime.now(timezone.utc)
        is_overdue = bool(
            req.due_date
            and req.status not in (ClarificationStatus.RESOLVED, ClarificationStatus.CLOSED, ClarificationStatus.CANCELLED)
            and (req.due_date if req.due_date.tzinfo else req.due_date.replace(tzinfo=timezone.utc)) < now
        )

        response_dtos: List[ClarificationResponseDTO] = []
        for r in req.responses or []:
            resp_name = r.responded_by.full_name if r.responded_by else "Bidder Representative"
            doc_name = r.attached_document.original_filename if r.attached_document else None
            rep_name = r.replaced_document.original_filename if r.replaced_document else None

            response_dtos.append(
                ClarificationResponseDTO(
                    id=r.id,
                    clarification_request_id=r.clarification_request_id,
                    responded_by_profile_id=r.responded_by_profile_id,
                    responded_by_name=resp_name,
                    response_text=r.response_text,
                    attached_document_id=r.attached_document_id,
                    attached_document_name=doc_name,
                    is_replacement_document=r.is_replacement_document,
                    replaced_document_id=r.replaced_document_id,
                    replaced_document_name=rep_name,
                    metadata_json=r.metadata_json,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )

        creator_name = req.created_by.full_name if req.created_by else "Procurement Officer"
        assigned_name = req.assigned_bidder.full_name if req.assigned_bidder else None
        resolver_name = req.resolved_by.full_name if req.resolved_by else None

        return ClarificationRequestDetailResponse(
            id=req.id,
            tender_id=req.tender_id,
            tender_number=req.tender.tender_number if req.tender else "Unknown",
            tender_title=req.tender.title if req.tender else "Unknown",
            bid_id=req.bid_id,
            bid_number=req.bid.bid_number if req.bid else "Unknown",
            tender_organization_id=req.tender_organization_id,
            tender_organization_name=req.tender_organization.name if req.tender_organization else "Procurement Dept",
            bidder_organization_id=req.bidder_organization_id,
            bidder_organization_name=req.bid.bidder_organization.name if (req.bid and req.bid.bidder_organization) else "Unknown",
            created_by_profile_id=req.created_by_profile_id,
            created_by_name=creator_name,
            assigned_bidder_profile_id=req.assigned_bidder_profile_id,
            assigned_bidder_name=assigned_name,
            subject=req.subject,
            message=req.message,
            clarification_type=req.clarification_type,
            priority=req.priority,
            status=req.status,
            due_date=req.due_date,
            sent_at=req.sent_at,
            viewed_at=req.viewed_at,
            responded_at=req.responded_at,
            related_document_id=req.related_document_id,
            related_document_name=req.related_document.original_filename if req.related_document else None,
            related_document_type=req.related_document.document_type if req.related_document else None,
            related_requirement_id=req.related_requirement_id,
            related_requirement_code=req.related_requirement.code if req.related_requirement else None,
            related_requirement_name=req.related_requirement.name if req.related_requirement else None,
            related_rule_version_id=req.related_rule_version_id,
            related_rule_version_number=req.related_rule_version_number,
            related_verification_record_id=req.related_verification_record_id,
            related_compliance_result_id=req.related_compliance_result_id,
            related_review_item_id=req.related_review_item_id,
            related_duplicate_match_id=req.related_duplicate_match_id,
            resolved_by_profile_id=req.resolved_by_profile_id,
            resolved_by_name=resolver_name,
            resolved_at=req.resolved_at,
            resolution_note=req.resolution_note,
            responses=response_dtos,
            is_overdue=is_overdue,
            created_at=req.created_at,
            updated_at=req.updated_at,
        )

    @classmethod
    def get_clarification_summary(
        cls,
        db: Session,
        organization_id: uuid.UUID,
        tender_id: Optional[uuid.UUID] = None,
        is_bidder: bool = False,
    ) -> ClarificationSummaryResponse:
        """
        Computes summary counters for clarification requests.
        """
        base_filter = [ClarificationRequest.is_active == True]
        if is_bidder:
            base_filter.append(ClarificationRequest.bidder_organization_id == organization_id)
            base_filter.append(ClarificationRequest.status != ClarificationStatus.DRAFT)
        else:
            base_filter.append(ClarificationRequest.tender_organization_id == organization_id)

        if tender_id:
            base_filter.append(ClarificationRequest.tender_id == tender_id)

        now = datetime.now(timezone.utc)

        total = db.scalar(
            select(func.count(ClarificationRequest.id)).where(and_(*base_filter))
        ) or 0

        open_count = db.scalar(
            select(func.count(ClarificationRequest.id)).where(
                and_(
                    *base_filter,
                    ClarificationRequest.status.in_([
                        ClarificationStatus.SENT,
                        ClarificationStatus.VIEWED,
                        ClarificationStatus.RESPONDED,
                        ClarificationStatus.UNDER_REVIEW,
                    ]),
                )
            )
        ) or 0

        awaiting_count = db.scalar(
            select(func.count(ClarificationRequest.id)).where(
                and_(
                    *base_filter,
                    ClarificationRequest.status.in_([
                        ClarificationStatus.SENT,
                        ClarificationStatus.VIEWED,
                    ]),
                )
            )
        ) or 0

        responded_count = db.scalar(
            select(func.count(ClarificationRequest.id)).where(
                and_(
                    *base_filter,
                    ClarificationRequest.status == ClarificationStatus.RESPONDED,
                )
            )
        ) or 0

        under_review_count = db.scalar(
            select(func.count(ClarificationRequest.id)).where(
                and_(
                    *base_filter,
                    ClarificationRequest.status == ClarificationStatus.UNDER_REVIEW,
                )
            )
        ) or 0

        resolved_count = db.scalar(
            select(func.count(ClarificationRequest.id)).where(
                and_(
                    *base_filter,
                    ClarificationRequest.status == ClarificationStatus.RESOLVED,
                )
            )
        ) or 0

        cancelled_count = db.scalar(
            select(func.count(ClarificationRequest.id)).where(
                and_(
                    *base_filter,
                    ClarificationRequest.status == ClarificationStatus.CANCELLED,
                )
            )
        ) or 0

        overdue_count = db.scalar(
            select(func.count(ClarificationRequest.id)).where(
                and_(
                    *base_filter,
                    ClarificationRequest.due_date.is_not(None),
                    ClarificationRequest.due_date < now,
                    ClarificationRequest.status.in_([
                        ClarificationStatus.SENT,
                        ClarificationStatus.VIEWED,
                        ClarificationStatus.RESPONDED,
                        ClarificationStatus.UNDER_REVIEW,
                    ]),
                )
            )
        ) or 0

        return ClarificationSummaryResponse(
            total_clarifications=total,
            open_clarifications=open_count,
            awaiting_bidder_response=awaiting_count,
            responses_received=responded_count,
            under_review=under_review_count,
            resolved_clarifications=resolved_count,
            overdue_clarifications=overdue_count,
            cancelled_clarifications=cancelled_count,
        )

    @classmethod
    def get_clarification_analytics(
        cls,
        db: Session,
        organization_id: uuid.UUID,
        tender_id: Optional[uuid.UUID] = None,
        is_bidder: bool = False,
    ) -> ClarificationAnalyticsResponse:
        """
        Computes analytics metrics and distributions for clarification workflows.
        """
        summary = cls.get_clarification_summary(
            db=db,
            organization_id=organization_id,
            tender_id=tender_id,
            is_bidder=is_bidder,
        )

        base_filter = [ClarificationRequest.is_active == True]
        if is_bidder:
            base_filter.append(ClarificationRequest.bidder_organization_id == organization_id)
            base_filter.append(ClarificationRequest.status != ClarificationStatus.DRAFT)
        else:
            base_filter.append(ClarificationRequest.tender_organization_id == organization_id)

        if tender_id:
            base_filter.append(ClarificationRequest.tender_id == tender_id)

        # Average response time (hours from sent_at to responded_at)
        responded_items = db.scalars(
            select(ClarificationRequest).where(
                and_(
                    *base_filter,
                    ClarificationRequest.sent_at.is_not(None),
                    ClarificationRequest.responded_at.is_not(None),
                )
            )
        ).all()

        avg_resp_hours: Optional[float] = None
        if responded_items:
            total_resp_seconds = sum(
                (item.responded_at - item.sent_at).total_seconds()
                for item in responded_items
                if item.responded_at and item.sent_at and item.responded_at >= item.sent_at
            )
            avg_resp_hours = round(total_resp_seconds / (len(responded_items) * 3600), 1)

        # Average resolution time (hours from created_at/sent_at to resolved_at)
        resolved_items = db.scalars(
            select(ClarificationRequest).where(
                and_(
                    *base_filter,
                    ClarificationRequest.resolved_at.is_not(None),
                )
            )
        ).all()

        avg_res_hours: Optional[float] = None
        if resolved_items:
            total_res_seconds = sum(
                (item.resolved_at - (item.sent_at or item.created_at)).total_seconds()
                for item in resolved_items
                if item.resolved_at and item.resolved_at >= (item.sent_at or item.created_at)
            )
            avg_res_hours = round(total_res_seconds / (len(resolved_items) * 3600), 1)

        # Group by Type
        type_rows = db.execute(
            select(
                ClarificationRequest.clarification_type,
                func.count(ClarificationRequest.id).label("count"),
            )
            .where(and_(*base_filter))
            .group_by(ClarificationRequest.clarification_type)
        ).all()
        by_type = [{"type": row[0], "count": row[1]} for row in type_rows]

        # Group by Priority
        priority_rows = db.execute(
            select(
                ClarificationRequest.priority,
                func.count(ClarificationRequest.id).label("count"),
            )
            .where(and_(*base_filter))
            .group_by(ClarificationRequest.priority)
        ).all()
        by_priority = [{"priority": row[0], "count": row[1]} for row in priority_rows]

        # Group by Status
        status_rows = db.execute(
            select(
                ClarificationRequest.status,
                func.count(ClarificationRequest.id).label("count"),
            )
            .where(and_(*base_filter))
            .group_by(ClarificationRequest.status)
        ).all()
        by_status = [{"status": row[0], "count": row[1]} for row in status_rows]

        return ClarificationAnalyticsResponse(
            summary=summary,
            avg_response_time_hours=avg_resp_hours,
            avg_resolution_time_hours=avg_res_hours,
            by_type=by_type,
            by_priority=by_priority,
            by_status=by_status,
        )

    # -------------------------------------------------------------------------
    # Internal Notification Helper
    # -------------------------------------------------------------------------
    @classmethod
    def _dispatch_clarification_requested_notification(
        cls,
        db: Session,
        clarification: ClarificationRequest,
        tender: Optional[Tender],
        bid: Optional[Bid],
    ) -> Optional[Notification]:
        recipient_id = clarification.assigned_bidder_profile_id or (bid.created_by_profile_id if bid else None)
        if not recipient_id:
            # Fallback to any bidder profile in the organization
            profile = db.scalars(
                select(Profile).where(Profile.organization_id == clarification.bidder_organization_id)
            ).first()
            recipient_id = profile.id if profile else None

        if not recipient_id:
            return None

        tender_title = tender.title if tender else "Tender"
        severity = NotificationSeverity.CRITICAL if clarification.priority == ClarificationPriority.URGENT else NotificationSeverity.WARNING

        due_text = f" Due by {clarification.due_date.strftime('%d %b %Y')}." if clarification.due_date else ""

        return NotificationService.create_notification(
            db=db,
            recipient_profile_id=recipient_id,
            organization_id=clarification.bidder_organization_id,
            notification_type=NotificationType.CLARIFICATION_REQUESTED,
            severity=severity,
            title="Clarification Request Received",
            message=f"Procurement Officer requested clarification for '{clarification.subject}' on tender '{tender_title}'.{due_text}",
            tender_id=clarification.tender_id,
            bid_id=clarification.bid_id,
            document_id=clarification.related_document_id,
            action_url=f"/bidder/clarifications?id={clarification.id}",
            dedupe_key=f"clarification_req_{clarification.id}",
            metadata_json={"clarification_id": str(clarification.id), "priority": clarification.priority},
        )
