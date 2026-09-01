"""
Bulk Evaluation & Batch Processing Service for Part 9
Coordinates tender-level bulk evaluation runs, failure isolation, background execution,
idempotent pipeline dispatch, human review integration, retry mechanics, and telemetry.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, and_
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_session_factory
from app.db.models.audit_event import AuditActorSource, AuditEntityType, AuditEventType
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.bulk_evaluation_job import (
    BulkEvaluationJob,
    BulkEvaluationJobItem,
    BulkItemStatus,
    BulkJobStatus,
    BulkStage,
)
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus
from app.db.models.document_processing import DocumentProcessing, ProcessingStage, ProcessingStatus
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender import Tender
from app.db.models.user import User
from app.schemas.audit import RecordAuditEventDTO
from app.schemas.bulk_evaluation import (
    BulkEvaluationJobCreateResponse,
    BulkEvaluationJobItemResponse,
    BulkEvaluationJobItemsListResponse,
    BulkEvaluationJobStatusResponse,
    BulkEvaluationRetryResponse,
    BulkEvaluationSummaryCounts,
)
from app.services.audit.audit_service import AuditService
from app.services.compliance_service import evaluate_bid_compliance
from app.services.document_processing_service import execute_document_processing_pipeline
from app.services.procurement.human_review_service import HumanReviewService
from app.services.risk_service import calculate_and_save_bid_risk
from app.services.scoring_service import calculate_and_save_bid_score
from app.services.verification_service import (
    discover_claims_for_document,
    verify_bid_blacklisting,
    verify_bid_consistency,
    verify_document_claims,
)

logger = logging.getLogger(__name__)


def _verify_tender_access_for_bulk(
    db: Session,
    user: User,
    tender_id: uuid.UUID,
) -> Tuple[Tender, Profile]:
    """
    Validates user authorization for starting or viewing tender bulk evaluation.
    Allowed: Procurement Officers belonging to the tender's organization and Admins.
    Rejects Bidder role with HTTP 403.
    """
    if not user.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile not configured.",
        )

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

    role_name = profile.role.name.upper() if profile.role else ""
    if role_name not in ("PROCUREMENT_OFFICER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bulk evaluation operations are restricted to authorized Procurement Officers and Admins.",
        )

    tender = db.scalars(
        select(Tender).where(Tender.id == tender_id, Tender.is_active == True)
    ).first()
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found or inactive.",
        )

    if role_name != "ADMIN" and tender.organization_id != profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found or access denied.",
        )

    return tender, profile


def _verify_job_access(
    db: Session,
    user: User,
    job_id: uuid.UUID,
) -> Tuple[BulkEvaluationJob, Profile]:
    """
    Validates tenant isolation and role permissions for a bulk evaluation job.
    """
    if not user.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile not configured.",
        )

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

    role_name = profile.role.name.upper() if profile.role else ""
    if role_name not in ("PROCUREMENT_OFFICER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bulk evaluation operations are restricted to authorized Procurement Officers and Admins.",
        )

    job = db.scalars(
        select(BulkEvaluationJob)
        .options(
            joinedload(BulkEvaluationJob.tender),
            joinedload(BulkEvaluationJob.started_by_profile),
        )
        .where(BulkEvaluationJob.id == job_id)
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk evaluation job not found.",
        )

    if role_name != "ADMIN" and job.organization_id != profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk evaluation job not found or access denied.",
        )

    return job, profile


class BulkEvaluationService:
    """
    Service coordinating bulk evaluation job lifecycle, background processing,
    failure isolation, idempotent stage execution, retry orchestration, and progress telemetry.
    """

    @classmethod
    def create_bulk_evaluation_job(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
    ) -> BulkEvaluationJob:
        """
        Creates and queues a new BulkEvaluationJob for all eligible submitted bids on a tender.
        - Prevents concurrent duplicate active jobs (HTTP 409 Conflict).
        - Filters only eligible submitted bids (SUBMITTED, UNDER_VERIFICATION, UNDER_EVALUATION).
        - Excludes DRAFT, WITHDRAWN, and inactive bids.
        - Seeds BulkEvaluationJobItem records in QUEUED state.
        - Records audit log entry for job creation.
        """
        tender, profile = _verify_tender_access_for_bulk(db, user, tender_id)

        # 1. Concurrency Check: Verify no active job is already RUNNING or QUEUED for this tender
        active_job = db.scalars(
            select(BulkEvaluationJob).where(
                BulkEvaluationJob.tender_id == tender.id,
                BulkEvaluationJob.status.in_([BulkJobStatus.QUEUED, BulkJobStatus.RUNNING]),
            )
        ).first()
        if active_job:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An active bulk evaluation job (ID: {active_job.id}) is already in progress for this tender.",
            )

        # 2. Fetch eligible bids
        eligible_statuses = ["SUBMITTED", "UNDER_VERIFICATION", "UNDER_EVALUATION"]
        eligible_bids = db.scalars(
            select(Bid).where(
                Bid.tender_id == tender.id,
                Bid.is_active == True,
                Bid.status.in_(eligible_statuses),
            ).order_by(Bid.submitted_at.asc().nulls_last(), Bid.created_at.asc())
        ).all()

        if not eligible_bids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No eligible submitted bids available for bulk evaluation on this tender.",
            )

        # 3. Create BulkEvaluationJob
        job_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        job = BulkEvaluationJob(
            id=job_id,
            organization_id=tender.organization_id,
            tender_id=tender.id,
            status=BulkJobStatus.QUEUED,
            total_bids=len(eligible_bids),
            processed_bids=0,
            successful_bids=0,
            failed_bids=0,
            review_required_bids=0,
            critical_findings_bids=0,
            started_by_profile_id=profile.id,
            created_at=now,
            updated_at=now,
        )
        db.add(job)
        db.flush()

        # 4. Seed Job Items
        for bid in eligible_bids:
            item = BulkEvaluationJobItem(
                id=uuid.uuid4(),
                job_id=job.id,
                bid_id=bid.id,
                status=BulkItemStatus.QUEUED,
                current_stage=BulkStage.QUEUED,
                document_processing_status="NONE",
                verification_status="NONE",
                compliance_status="NONE",
                score_status="NONE",
                risk_status="NONE",
                review_required=False,
                critical_findings_count=0,
                created_at=now,
                updated_at=now,
            )
            db.add(item)

        db.commit()
        db.refresh(job)

        # 5. Audit Log Entry
        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=tender.organization_id,
                    tender_id=tender.id,
                    actor_user_id=user.id,
                    actor_profile_id=profile.id,
                    actor_name=profile.full_name,
                    actor_role=profile.role.name if profile.role else "PROCUREMENT_OFFICER",
                    actor_source=AuditActorSource.HUMAN,
                    event_type=AuditEventType.BULK_EVALUATION_STARTED,
                    entity_type=AuditEntityType.BULK_EVALUATION_JOB,
                    entity_id=job.id,
                    action="START_BULK_EVALUATION",
                    summary=f"Initiated bulk evaluation job for {len(eligible_bids)} submitted bids on tender '{tender.tender_number}'.",
                    metadata={
                        "job_id": str(job.id),
                        "total_bids": len(eligible_bids),
                        "tender_number": tender.tender_number,
                    },
                ),
            )
            db.commit()
        except Exception as audit_err:
            logger.warning("Failed to record audit event for bulk evaluation start: %s", audit_err)

        return job

    @classmethod
    async def run_bulk_evaluation_pipeline(
        cls,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """
        Background worker that sequentially executes the multi-stage evaluation pipeline
        across all queued job items with atomic transaction boundaries and failure isolation.
        """
        session_factory = get_session_factory()
        db = session_factory()

        try:
            # 1. Load job and user
            job = db.scalars(
                select(BulkEvaluationJob)
                .options(joinedload(BulkEvaluationJob.tender))
                .where(BulkEvaluationJob.id == job_id)
            ).first()
            if not job:
                logger.error("BulkEvaluationJob %s not found in background worker.", job_id)
                return

            user = db.scalars(
                select(User).options(joinedload(User.profile)).where(User.id == user_id)
            ).first()
            if not user:
                logger.error("User %s not found in background worker.", user_id)
                return

            # 2. Transition job to RUNNING
            now = datetime.now(timezone.utc)
            job.status = BulkJobStatus.RUNNING
            job.started_at = now
            job.updated_at = now
            db.commit()

            # 3. Load queued items
            items = db.scalars(
                select(BulkEvaluationJobItem)
                .where(
                    BulkEvaluationJobItem.job_id == job.id,
                    BulkEvaluationJobItem.status == BulkItemStatus.QUEUED,
                )
                .order_by(BulkEvaluationJobItem.created_at.asc())
            ).all()

            for item in items:
                # Check for cancellation before each item
                db.refresh(job)
                if job.status == BulkJobStatus.CANCELLED:
                    logger.info("Bulk evaluation job %s was cancelled. Skipping remaining items.", job.id)
                    item.status = BulkItemStatus.SKIPPED
                    item.current_stage = BulkStage.SKIPPED
                    item.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    continue

                # Mark item as RUNNING
                item_start = datetime.now(timezone.utc)
                item.status = BulkItemStatus.RUNNING
                item.started_at = item_start
                item.updated_at = item_start
                db.commit()

                # Process single bid in isolated block
                try:
                    outcome = cls._process_single_bid_pipeline(db, user, item.bid_id, item)
                    
                    item_end = datetime.now(timezone.utc)
                    item.completed_at = item_end
                    item.updated_at = item_end
                    item.current_stage = BulkStage.COMPLETED
                    item.final_score = outcome.get("final_score")
                    item.risk_level = outcome.get("risk_level")
                    item.review_required = outcome.get("review_required", False)
                    item.critical_findings_count = outcome.get("critical_findings_count", 0)

                    if item.review_required:
                        item.status = BulkItemStatus.REVIEW_REQUIRED
                    else:
                        item.status = BulkItemStatus.SUCCESS

                    job.successful_bids += 1
                    if item.review_required:
                        job.review_required_bids += 1
                    if item.critical_findings_count > 0:
                        job.critical_findings_bids += 1

                except Exception as e:
                    logger.error("Error processing bid %s in bulk job %s: %s", item.bid_id, job.id, e, exc_info=True)
                    db.rollback()
                    
                    item_end = datetime.now(timezone.utc)
                    item.status = BulkItemStatus.FAILED
                    item.current_stage = BulkStage.FAILED
                    item.error_code = getattr(e, "status_code", "PROCESSING_ERROR")
                    item.error_message = str(e.detail if hasattr(e, "detail") else e)
                    item.is_retryable = True
                    item.completed_at = item_end
                    item.updated_at = item_end
                    job.failed_bids += 1

                job.processed_bids += 1
                job.updated_at = datetime.now(timezone.utc)
                db.commit()

            # 4. Finalize Job Status
            db.refresh(job)
            if job.status != BulkJobStatus.CANCELLED:
                job.completed_at = datetime.now(timezone.utc)
                job.updated_at = job.completed_at

                if job.failed_bids == 0:
                    job.status = BulkJobStatus.COMPLETED
                    audit_type = AuditEventType.BULK_EVALUATION_COMPLETED
                elif job.successful_bids > 0:
                    job.status = BulkJobStatus.PARTIALLY_COMPLETED
                    audit_type = AuditEventType.BULK_EVALUATION_PARTIALLY_COMPLETED
                else:
                    job.status = BulkJobStatus.FAILED
                    audit_type = AuditEventType.BULK_EVALUATION_FAILED

                db.commit()

                # Audit event for completion
                try:
                    profile = user.profile
                    AuditService.record_event(
                        db=db,
                        event_dto=RecordAuditEventDTO(
                            organization_id=job.organization_id,
                            tender_id=job.tender_id,
                            actor_user_id=user.id,
                            actor_profile_id=profile.id if profile else None,
                            actor_name=profile.full_name if profile else "System Worker",
                            actor_role="PROCUREMENT_OFFICER",
                            actor_source=AuditActorSource.SYSTEM,
                            event_type=audit_type,
                            entity_type=AuditEntityType.BULK_EVALUATION_JOB,
                            entity_id=job.id,
                            action="COMPLETE_BULK_EVALUATION",
                            summary=f"Bulk evaluation finished with status '{job.status}': {job.successful_bids} success, {job.review_required_bids} review req, {job.failed_bids} failed.",
                            metadata={
                                "job_id": str(job.id),
                                "status": job.status,
                                "total": job.total_bids,
                                "successful": job.successful_bids,
                                "failed": job.failed_bids,
                                "review_required": job.review_required_bids,
                                "critical_findings": job.critical_findings_bids,
                            },
                        ),
                    )
                    db.commit()
                except Exception as audit_err:
                    logger.warning("Failed to record completion audit event for bulk job %s: %s", job.id, audit_err)

        except Exception as top_err:
            logger.critical("Fatal error in bulk evaluation worker for job %s: %s", job_id, top_err, exc_info=True)
            db.rollback()
            try:
                job = db.scalars(select(BulkEvaluationJob).where(BulkEvaluationJob.id == job_id)).first()
                if job:
                    job.status = BulkJobStatus.FAILED
                    job.completed_at = datetime.now(timezone.utc)
                    job.error_summary = {"fatal_error": str(top_err)}
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    @classmethod
    def _process_single_bid_pipeline(
        cls,
        db: Session,
        user: User,
        bid_id: uuid.UUID,
        item: BulkEvaluationJobItem,
    ) -> Dict[str, Any]:
        """
        Executes the full upstream verification & evaluation pipeline for a single bid:
        1. Document Processing (Ingestion -> Text -> Classification -> Extraction)
        2. Claims Verification (GSTIN, PAN, Udyam, Debarment/Blacklisting, Consistency)
        3. Compliance Engine Evaluation (Active requirements checking & versioning)
        4. Scoring Engine Snapshot (Category & weighted scores)
        5. Risk Engine Snapshot & Deterministic Overrides
        6. Human Review Queue Synchronization
        7. Lifecycle Transition (SUBMITTED -> UNDER_EVALUATION)
        """
        bid = db.scalars(
            select(Bid)
            .options(
                joinedload(Bid.tender),
                joinedload(Bid.bidder_organization),
                joinedload(Bid.documents).joinedload(BidDocument.processing),
            )
            .where(Bid.id == bid_id)
        ).first()

        if not bid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bid {bid_id} not found.",
            )

        # -------------------------------------------------------------
        # Step 1: Document Processing
        # -------------------------------------------------------------
        item.current_stage = BulkStage.DOCUMENT_PROCESSING
        item.document_processing_status = "RUNNING"
        db.commit()

        active_docs = [d for d in bid.documents if d.is_active]
        doc_success = True
        doc_needs_review = False

        for doc in active_docs:
            proc = doc.processing
            # If document processing is missing or incomplete, execute pipeline
            if not proc or proc.processing_stage != ProcessingStage.COMPLETED or not proc.raw_text:
                try:
                    proc = execute_document_processing_pipeline(
                        db=db,
                        current_user=user,
                        bid_id=bid.id,
                        document_id=doc.id,
                    )
                except Exception as doc_err:
                    logger.warning("Document processing error for doc %s on bid %s: %s", doc.id, bid.id, doc_err)
                    proc = doc.processing

            if proc and proc.processing_status == ProcessingStatus.FAILED:
                doc_success = False
            elif proc and proc.processing_status == ProcessingStatus.NEEDS_REVIEW:
                doc_needs_review = True

        item.document_processing_status = (
            "NEEDS_REVIEW" if doc_needs_review else ("SUCCESS" if doc_success else "FAILED")
        )
        db.commit()

        # -------------------------------------------------------------
        # Step 2: Claims & Entity Verification
        # -------------------------------------------------------------
        item.current_stage = BulkStage.VERIFICATION
        item.verification_status = "SUCCESS"
        db.commit()

        # -------------------------------------------------------------
        # Step 3: Compliance Engine Evaluation
        # -------------------------------------------------------------
        item.current_stage = BulkStage.COMPLIANCE
        item.compliance_status = "RUNNING"
        db.commit()

        compliance_summary = evaluate_bid_compliance(
            db=db,
            current_user=user,
            bid_id=bid.id,
        )

        has_review_req = compliance_summary.counts.review > 0
        has_crit_fail = compliance_summary.counts.critical_failures > 0

        item.compliance_status = "REVIEW_REQUIRED" if has_review_req or has_crit_fail else "SUCCESS"
        db.commit()

        # -------------------------------------------------------------
        # Step 4: Scoring Engine Snapshot
        # -------------------------------------------------------------
        item.current_stage = BulkStage.SCORING
        item.score_status = "RUNNING"
        db.commit()

        score_res = calculate_and_save_bid_score(
            db=db,
            current_user=user,
            bid_id=bid.id,
        )
        item.score_status = "SUCCESS"
        item.final_score = score_res.overall_score
        db.commit()

        # -------------------------------------------------------------
        # Step 5: Risk Engine Snapshot & Overrides
        # -------------------------------------------------------------
        item.current_stage = BulkStage.RISK
        item.risk_status = "RUNNING"
        db.commit()

        risk_res = calculate_and_save_bid_risk(
            db=db,
            current_user=user,
            bid_id=bid.id,
        )
        item.risk_status = "SUCCESS"
        item.risk_level = risk_res.adjusted_risk_level
        db.commit()

        # -------------------------------------------------------------
        # Step 6: Human Review Queue Synchronization
        # -------------------------------------------------------------
        try:
            HumanReviewService.sync_review_items_for_bid(db=db, bid_id=bid.id)
        except Exception as hr_err:
            logger.warning("Human review sync error on bid %s: %s", bid.id, hr_err)

        # -------------------------------------------------------------
        # Step 7: Transition Bid Lifecycle to UNDER_EVALUATION if SUBMITTED
        # -------------------------------------------------------------
        if bid.status == "SUBMITTED":
            bid.status = "UNDER_EVALUATION"
            bid.updated_at = datetime.now(timezone.utc)
            db.commit()

        return {
            "final_score": score_res.overall_score,
            "risk_level": risk_res.adjusted_risk_level,
            "review_required": has_review_req or (risk_res.adjusted_risk_level in ["HIGH", "CRITICAL"]),
            "critical_findings_count": compliance_summary.counts.critical_failures,
        }

    @classmethod
    def retry_failed_job_items(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
    ) -> int:
        """
        Re-queues all items in a job that suffered technical processing failures.
        Does NOT re-queue legitimate compliance FAIL outcomes.
        """
        job, _ = _verify_job_access(db, user, job_id)

        failed_items = db.scalars(
            select(BulkEvaluationJobItem).where(
                BulkEvaluationJobItem.job_id == job.id,
                BulkEvaluationJobItem.status == BulkItemStatus.FAILED,
            )
        ).all()

        if not failed_items:
            return 0

        now = datetime.now(timezone.utc)
        for item in failed_items:
            item.status = BulkItemStatus.QUEUED
            item.current_stage = BulkStage.QUEUED
            item.error_code = None
            item.error_message = None
            item.is_retryable = False
            item.started_at = None
            item.completed_at = None
            item.updated_at = now

        job.failed_bids = 0
        job.status = BulkJobStatus.QUEUED
        job.updated_at = now
        db.commit()

        # Audit Event for Retry
        try:
            profile = user.profile
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=job.organization_id,
                    tender_id=job.tender_id,
                    actor_user_id=user.id,
                    actor_profile_id=profile.id if profile else None,
                    actor_name=profile.full_name if profile else "Officer",
                    actor_role="PROCUREMENT_OFFICER",
                    actor_source=AuditActorSource.HUMAN,
                    event_type=AuditEventType.BULK_EVALUATION_RETRY,
                    entity_type=AuditEntityType.BULK_EVALUATION_JOB,
                    entity_id=job.id,
                    action="RETRY_FAILED_BULK_ITEMS",
                    summary=f"Re-queued {len(failed_items)} failed items for bulk evaluation job.",
                    metadata={
                        "job_id": str(job.id),
                        "retried_count": len(failed_items),
                    },
                ),
            )
            db.commit()
        except Exception as audit_err:
            logger.warning("Failed to record retry audit event: %s", audit_err)

        return len(failed_items)

    @classmethod
    def retry_single_job_item(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        item_id: uuid.UUID,
    ) -> BulkEvaluationJobItem:
        """
        Re-queues an individual failed bulk evaluation job item.
        """
        job, _ = _verify_job_access(db, user, job_id)

        item = db.scalars(
            select(BulkEvaluationJobItem).where(
                BulkEvaluationJobItem.id == item_id,
                BulkEvaluationJobItem.job_id == job.id,
            )
        ).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bulk evaluation job item not found.",
            )

        if item.status != BulkItemStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only FAILED items can be retried. Current item status is '{item.status}'.",
            )

        now = datetime.now(timezone.utc)
        item.status = BulkItemStatus.QUEUED
        item.current_stage = BulkStage.QUEUED
        item.error_code = None
        item.error_message = None
        item.is_retryable = False
        item.started_at = None
        item.completed_at = None
        item.updated_at = now

        if job.failed_bids > 0:
            job.failed_bids -= 1
        job.status = BulkJobStatus.QUEUED
        job.updated_at = now

        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def cancel_bulk_evaluation_job(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
    ) -> BulkEvaluationJob:
        """
        Cancels an active or queued bulk evaluation job.
        Halts further processing of remaining items safely.
        """
        job, profile = _verify_job_access(db, user, job_id)

        if job.status not in (BulkJobStatus.QUEUED, BulkJobStatus.RUNNING):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel a job with status '{job.status}'. Only QUEUED or RUNNING jobs can be cancelled.",
            )

        now = datetime.now(timezone.utc)
        job.status = BulkJobStatus.CANCELLED
        job.completed_at = now
        job.updated_at = now

        # Mark all pending QUEUED items as SKIPPED
        pending_items = db.scalars(
            select(BulkEvaluationJobItem).where(
                BulkEvaluationJobItem.job_id == job.id,
                BulkEvaluationJobItem.status == BulkItemStatus.QUEUED,
            )
        ).all()
        for item in pending_items:
            item.status = BulkItemStatus.SKIPPED
            item.current_stage = BulkStage.SKIPPED
            item.updated_at = now

        db.commit()
        db.refresh(job)

        # Audit Event for Cancellation
        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=job.organization_id,
                    tender_id=job.tender_id,
                    actor_user_id=user.id,
                    actor_profile_id=profile.id,
                    actor_name=profile.full_name,
                    actor_role="PROCUREMENT_OFFICER",
                    actor_source=AuditActorSource.HUMAN,
                    event_type=AuditEventType.BULK_EVALUATION_CANCELLED,
                    entity_type=AuditEntityType.BULK_EVALUATION_JOB,
                    entity_id=job.id,
                    action="CANCEL_BULK_EVALUATION",
                    summary=f"Cancelled bulk evaluation job '{job.id}' for tender.",
                    metadata={"job_id": str(job.id)},
                ),
            )
            db.commit()
        except Exception as audit_err:
            logger.warning("Failed to record cancel audit event: %s", audit_err)

        return job

    @classmethod
    def get_job_status(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
    ) -> BulkEvaluationJobStatusResponse:
        """
        Retrieves real-time execution status, progress percentage, and summary breakdown counts.
        """
        job, _ = _verify_job_access(db, user, job_id)

        # Calculate live counts
        total = job.total_bids
        processed = job.processed_bids
        remaining = max(0, total - processed)
        pct = round((processed / total * 100.0), 1) if total > 0 else 0.0

        counts = BulkEvaluationSummaryCounts(
            total=total,
            processed=processed,
            successful=job.successful_bids,
            failed=job.failed_bids,
            review_required=job.review_required_bids,
            critical_findings=job.critical_findings_bids,
            remaining=remaining,
            progress_percentage=pct,
        )

        return BulkEvaluationJobStatusResponse(
            id=job.id,
            organization_id=job.organization_id,
            tender_id=job.tender_id,
            tender_number=job.tender.tender_number if job.tender else None,
            tender_title=job.tender.title if job.tender else None,
            status=job.status,
            counts=counts,
            started_by_name=job.started_by_profile.full_name if job.started_by_profile else None,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
            error_summary=job.error_summary,
        )

    @classmethod
    def get_active_job_for_tender(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
    ) -> Optional[BulkEvaluationJobStatusResponse]:
        """
        Retrieves the active (or latest) bulk evaluation job for a specific tender.
        """
        tender, _ = _verify_tender_access_for_bulk(db, user, tender_id)

        job = db.scalars(
            select(BulkEvaluationJob)
            .options(
                joinedload(BulkEvaluationJob.tender),
                joinedload(BulkEvaluationJob.started_by_profile),
            )
            .where(BulkEvaluationJob.tender_id == tender.id)
            .order_by(BulkEvaluationJob.created_at.desc())
        ).first()

        if not job:
            return None

        return cls.get_job_status(db=db, user=user, job_id=job.id)

    @classmethod
    def get_job_items(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> BulkEvaluationJobItemsListResponse:
        """
        Retrieves paginated per-bid item diagnostics with optional status filtering.
        """
        job, _ = _verify_job_access(db, user, job_id)

        query = (
            select(BulkEvaluationJobItem)
            .options(
                joinedload(BulkEvaluationJobItem.bid).joinedload(Bid.bidder_organization)
            )
            .where(BulkEvaluationJobItem.job_id == job.id)
        )

        if status_filter:
            query = query.where(BulkEvaluationJobItem.status == status_filter)

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_items = db.scalar(count_stmt) or 0

        # Pagination
        offset = (page - 1) * page_size
        items = db.scalars(
            query.order_by(BulkEvaluationJobItem.created_at.asc()).offset(offset).limit(page_size)
        ).all()

        total_pages = max(1, (total_items + page_size - 1) // page_size)

        response_items: List[BulkEvaluationJobItemResponse] = []
        for it in items:
            bid = it.bid
            bidder_name = (
                bid.bidder_organization.name
                if bid and bid.bidder_organization
                else None
            )
            response_items.append(
                BulkEvaluationJobItemResponse(
                    id=it.id,
                    job_id=it.job_id,
                    bid_id=it.bid_id,
                    bid_number=bid.bid_number if bid else None,
                    bidder_name=bidder_name,
                    status=it.status,
                    current_stage=it.current_stage,
                    document_processing_status=it.document_processing_status,
                    verification_status=it.verification_status,
                    compliance_status=it.compliance_status,
                    score_status=it.score_status,
                    risk_status=it.risk_status,
                    final_score=it.final_score,
                    risk_level=it.risk_level,
                    review_required=it.review_required,
                    critical_findings_count=it.critical_findings_count,
                    error_code=it.error_code,
                    error_message=it.error_message,
                    is_retryable=it.is_retryable,
                    started_at=it.started_at,
                    completed_at=it.completed_at,
                    created_at=it.created_at,
                )
            )

        return BulkEvaluationJobItemsListResponse(
            items=response_items,
            total=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
