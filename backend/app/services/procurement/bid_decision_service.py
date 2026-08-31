"""
Bid Decision Service for Part 8D: Final Human Decision Workflow
Orchestrates decision readiness verification, strict human-controlled qualification,
immutable decision versioning, evaluation snapshot linkage, and upstream staleness tracking.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.bid import Bid
from app.db.models.bid_decision import (
    BidDecision,
    BidDecisionStatus,
    DisqualificationReasonCategory,
)
from app.db.models.compliance_result import ComplianceResult
from app.db.models.human_review import HumanReviewItem, ReviewSeverity, ReviewStatus
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender import Tender
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.schemas.bid_decision import (
    BidDecisionHistoryItem,
    BidDecisionResponse,
    BidDecisionStatusEnum,
    DecidedByProfileSummary,
    DecisionReadinessResponse,
    DisqualificationReasonCategoryEnum,
    EvaluationSnapshotReference,
)
from app.db.models.audit_event import AuditActorSource, AuditEntityType, AuditEventType
from app.schemas.audit import RecordAuditEventDTO
from app.services.audit.audit_service import AuditService
from app.services.evaluation.bid_evaluation_service import BidEvaluationService

logger = logging.getLogger(__name__)


def _verify_decision_access(
    db: Session,
    user: User,
    tender_id: uuid.UUID,
    bid_id: uuid.UUID,
) -> Tuple[Bid, Tender, Profile, Role]:
    """
    Enforces multi-tenant authorization for bid decision operations.
    Allowed: Authorized Procurement Officers belonging to the tender's organization, and Admins.
    Forbidden: Bidders (HTTP 403) and cross-tenant officers (HTTP 404/403).
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
            detail="Bid decision operations are restricted to authorized Procurement Officers and Admins.",
        )

    stmt = (
        select(Bid)
        .options(
            joinedload(Bid.tender),
            joinedload(Bid.bidder_organization),
        )
        .where(Bid.id == bid_id, Bid.tender_id == tender_id)
    )
    bid = db.execute(stmt).scalar_one_or_none()
    if not bid or not bid.tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid or tender not found or access denied.",
        )

    tender = bid.tender

    if role.name != "ADMIN" and tender.organization_id != profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid or tender not found or access denied.",
        )

    return bid, tender, profile, role


class BidDecisionService:
    """
    Service coordinating Part 8D Final Human Decision Workflow.
    """

    @classmethod
    def get_decision_readiness(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
    ) -> DecisionReadinessResponse:
        """
        Computes deterministic decision readiness and surfaces blocking constraints and advisory warnings.
        """
        bid, tender, profile, role = _verify_decision_access(db, user, tender_id, bid_id)

        # 1. Fetch Unified Evaluation Summary
        eval_summary = BidEvaluationService.get_unified_evaluation(db, user, bid_id)
        comp = eval_summary.compliance
        score = eval_summary.score
        risk = eval_summary.risk
        ai = eval_summary.ai_recommendation

        is_score_stale = "SCORE" in eval_summary.stale_components or (score.is_stale if score else False)
        is_risk_stale = "RISK" in eval_summary.stale_components or (risk.is_stale if risk else False)
        is_ai_stale = "AI" in eval_summary.stale_components or (ai.is_stale if ai else False)

        # 2. Fetch Human Review counts
        review_items = db.scalars(
            select(HumanReviewItem).where(
                HumanReviewItem.bid_id == bid_id,
                HumanReviewItem.is_active == True,  # noqa: E712
            )
        ).all()

        open_statuses = (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.ESCALATED)
        open_reviews = [r for r in review_items if r.status in open_statuses]
        critical_open_reviews = [r for r in open_reviews if r.severity == ReviewSeverity.CRITICAL]

        open_review_count = len(open_reviews)
        critical_open_review_count = len(critical_open_reviews)

        # 3. Check Pending Critical Verifications
        verif_records = db.scalars(
            select(VerificationRecord).where(VerificationRecord.bid_id == bid_id)
        ).all()

        has_pending_critical_verif = any(
            v.verification_status in ("PENDING", "NEEDS_REVIEW", "UNAVAILABLE")
            for v in verif_records
        )

        # 4. Evaluate Qualification Blockers
        can_qualify = True
        blocking_reasons: List[str] = []

        if critical_open_review_count > 0:
            can_qualify = False
            blocking_reasons.append(
                f"{critical_open_review_count} critical human review item(s) remain unresolved in the review queue."
            )

        if not comp.evaluation_complete:
            can_qualify = False
            blocking_reasons.append(
                f"Compliance evaluation is incomplete with {comp.pending_count} pending requirement checks."
            )

        if comp.total_requirements == 0:
            can_qualify = False
            blocking_reasons.append("No tender compliance requirements have been evaluated for this bid.")

        if is_score_stale or is_risk_stale:
            can_qualify = False
            blocking_reasons.append(
                "Deterministic compliance score or risk assessment is stale. Please refresh evaluation before qualification."
            )

        if has_pending_critical_verif and critical_open_review_count == 0:
            # When verification is pending/unavailable, advise deferral
            pass

        # 5. Evaluate Advisory Warnings
        warnings: List[str] = []

        if comp.critical_failures_count > 0:
            warnings.append(
                f"Bid has {comp.critical_failures_count} critical requirement failure(s). Explicit override justification is required."
            )

        if comp.mandatory_failures_count > 0:
            warnings.append(
                f"Bid has {comp.mandatory_failures_count} mandatory requirement failure(s). Review justification is required."
            )

        if open_review_count > 0 and critical_open_review_count == 0:
            warnings.append(
                f"Bid has {open_review_count} non-critical open review item(s) pending attention."
            )

        if risk and risk.adjusted_risk_level in ("HIGH", "CRITICAL"):
            warnings.append(
                f"Adjusted risk level is {risk.adjusted_risk_level} ({risk.adjusted_risk_score:.1f}/100) with active risk floor overrides."
            )

        if ai and ai.recommendation == "DO_NOT_PROCEED_WITHOUT_REVIEW":
            warnings.append(
                "AI Recommendation is DO NOT PROCEED WITHOUT REVIEW (Advisory guidance only)."
            )

        if is_ai_stale:
            warnings.append(
                "AI Recommendation synthesis is stale relative to current compliance data."
            )

        return DecisionReadinessResponse(
            can_qualify=can_qualify,
            can_disqualify=True,
            can_defer=True,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
            evaluation_complete=comp.evaluation_complete,
            evaluation_version=comp.evaluation_version,
            open_review_count=open_review_count,
            critical_open_review_count=critical_open_review_count,
            mandatory_failures_count=comp.mandatory_failures_count,
            critical_failures_count=comp.critical_failures_count,
            has_pending_critical_verifications=has_pending_critical_verif,
            overall_score=score.overall_compliance_score if score else None,
            adjusted_risk_level=risk.adjusted_risk_level if risk else None,
            adjusted_risk_score=risk.adjusted_risk_score if risk else None,
            ai_recommendation=ai.recommendation if ai else None,
            is_score_stale=is_score_stale,
            is_risk_stale=is_risk_stale,
            is_ai_stale=is_ai_stale,
        )

    @classmethod
    def get_current_decision(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
    ) -> BidDecisionResponse:
        """
        Fetches the current authoritative qualification decision for a bid, along with readiness telemetry.
        """
        bid, tender, profile, role = _verify_decision_access(db, user, tender_id, bid_id)
        readiness = cls.get_decision_readiness(db, user, tender_id, bid_id)

        # 1. Fetch current decision
        stmt = (
            select(BidDecision)
            .options(
                joinedload(BidDecision.decided_by_profile).joinedload(Profile.role),
                joinedload(BidDecision.decided_by_profile).joinedload(Profile.organization),
                joinedload(BidDecision.score_snapshot),
                joinedload(BidDecision.risk_snapshot),
                joinedload(BidDecision.ai_recommendation),
            )
            .where(
                BidDecision.bid_id == bid_id,
                BidDecision.is_current == True,  # noqa: E712
            )
        )
        current_dec = db.execute(stmt).unique().scalar_one_or_none()

        # 2. If no decision recorded yet, return default NOT_DECIDED
        if not current_dec:
            # Fetch latest snapshots for reference preview
            score_snap = db.scalars(
                select(BidScoreSnapshot)
                .where(BidScoreSnapshot.bid_id == bid_id, BidScoreSnapshot.is_current == True)  # noqa: E712
                .order_by(BidScoreSnapshot.created_at.desc())
            ).first()
            risk_snap = db.scalars(
                select(BidRiskSnapshot)
                .where(BidRiskSnapshot.bid_id == bid_id, BidRiskSnapshot.is_current == True)  # noqa: E712
                .order_by(BidRiskSnapshot.created_at.desc())
            ).first()
            ai_rec = db.scalars(
                select(AIRecommendationRecord)
                .where(AIRecommendationRecord.bid_id == bid_id)
                .order_by(AIRecommendationRecord.created_at.desc())
            ).first()

            snap_ref = EvaluationSnapshotReference(
                evaluation_version=readiness.evaluation_version,
                score_snapshot_id=score_snap.id if score_snap else None,
                overall_score=float(score_snap.overall_score) if (score_snap and score_snap.overall_score is not None) else None,
                risk_snapshot_id=risk_snap.id if risk_snap else None,
                adjusted_risk_score=float(risk_snap.adjusted_risk_score) if (risk_snap and risk_snap.adjusted_risk_score is not None) else None,
                adjusted_risk_level=risk_snap.adjusted_risk_level if risk_snap else None,
                ai_recommendation_id=ai_rec.id if ai_rec else None,
                ai_recommendation=ai_rec.recommendation if ai_rec else None,
            )

            decided_by_summary = DecidedByProfileSummary(
                profile_id=profile.id,
                full_name=profile.full_name or user.username or "Procurement Officer",
                role_name=role.name,
                organization_name=profile.organization.name if profile.organization else None,
            )

            return BidDecisionResponse(
                id=uuid.uuid4(),  # ephemeral id for not decided
                organization_id=tender.organization_id,
                tender_id=tender.id,
                bid_id=bid.id,
                bid_number=bid.bid_number,
                bidder_name=bid.bidder_organization.name if bid.bidder_organization else None,
                decision=BidDecisionStatusEnum.NOT_DECIDED,
                reason="No formal human evaluation decision has been recorded yet.",
                decision_summary=None,
                category=None,
                decided_at=datetime.now(timezone.utc),
                decision_version=0,
                decided_by=decided_by_summary,
                is_current=True,
                is_stale=False,
                stale_reason=None,
                snapshot_reference=snap_ref,
                readiness=readiness,
            )

        # 3. Check staleness against latest evaluation version
        is_stale = current_dec.is_stale
        stale_reason = current_dec.stale_reason
        if readiness.evaluation_version > current_dec.evaluation_version:
            is_stale = True
            if not stale_reason:
                stale_reason = "Upstream compliance evaluation version advanced after this decision was recorded."

        decided_by_prof = current_dec.decided_by_profile
        decided_by_role_name = decided_by_prof.role.name if (decided_by_prof and decided_by_prof.role) else "PROCUREMENT_OFFICER"
        decided_by_summary = DecidedByProfileSummary(
            profile_id=decided_by_prof.id if decided_by_prof else profile.id,
            full_name=decided_by_prof.full_name if decided_by_prof else "Procurement Officer",
            role_name=decided_by_role_name,
            organization_name=decided_by_prof.organization.name if (decided_by_prof and decided_by_prof.organization) else None,
        )

        score_snap = current_dec.score_snapshot
        risk_snap = current_dec.risk_snapshot
        ai_rec = current_dec.ai_recommendation

        snap_ref = EvaluationSnapshotReference(
            evaluation_version=current_dec.evaluation_version,
            score_snapshot_id=current_dec.score_snapshot_id,
            overall_score=float(score_snap.overall_score) if (score_snap and score_snap.overall_score is not None) else None,
            risk_snapshot_id=current_dec.risk_snapshot_id,
            adjusted_risk_score=float(risk_snap.adjusted_risk_score) if (risk_snap and risk_snap.adjusted_risk_score is not None) else None,
            adjusted_risk_level=risk_snap.adjusted_risk_level if risk_snap else None,
            ai_recommendation_id=current_dec.ai_recommendation_id,
            ai_recommendation=ai_rec.recommendation if ai_rec else None,
        )

        return BidDecisionResponse(
            id=current_dec.id,
            organization_id=current_dec.organization_id,
            tender_id=current_dec.tender_id,
            bid_id=current_dec.bid_id,
            bid_number=bid.bid_number,
            bidder_name=bid.bidder_organization.name if bid.bidder_organization else None,
            decision=BidDecisionStatusEnum(current_dec.decision),
            reason=current_dec.reason,
            decision_summary=current_dec.decision_summary,
            category=current_dec.category,
            decided_at=current_dec.decided_at,
            decision_version=current_dec.decision_version,
            decided_by=decided_by_summary,
            is_current=current_dec.is_current,
            is_stale=is_stale,
            stale_reason=stale_reason,
            snapshot_reference=snap_ref,
            readiness=readiness,
        )

    @classmethod
    def get_decision_history(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
    ) -> List[BidDecisionHistoryItem]:
        """
        Fetches chronological decision versions for full auditability.
        """
        _verify_decision_access(db, user, tender_id, bid_id)

        stmt = (
            select(BidDecision)
            .options(
                joinedload(BidDecision.decided_by_profile).joinedload(Profile.role),
            )
            .where(BidDecision.bid_id == bid_id)
            .order_by(BidDecision.decision_version.desc())
        )
        decisions = db.execute(stmt).unique().scalars().all()

        history: List[BidDecisionHistoryItem] = []
        for d in decisions:
            prof = d.decided_by_profile
            history.append(
                BidDecisionHistoryItem(
                    id=d.id,
                    decision_version=d.decision_version,
                    decision=BidDecisionStatusEnum(d.decision),
                    reason=d.reason,
                    decision_summary=d.decision_summary,
                    category=d.category,
                    decided_at=d.decided_at,
                    decided_by_name=prof.full_name if prof else "Officer",
                    decided_by_role=prof.role.name if (prof and prof.role) else "PROCUREMENT_OFFICER",
                    is_current=d.is_current,
                    is_stale=d.is_stale,
                    stale_reason=d.stale_reason,
                    superseded_at=d.superseded_at,
                )
            )

        return history

    @classmethod
    def record_decision(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
        req: RecordBidDecisionRequest,
    ) -> BidDecisionResponse:
        """
        Authoritatively records a human-controlled bid qualification decision.
        Transactions safely supersede any prior decision and capture exact evaluation snapshot references.
        """
        bid, tender, profile, role = _verify_decision_access(db, user, tender_id, bid_id)

        # 1. Validate reason requirements
        clean_reason = req.reason.strip() if req.reason else ""
        if len(clean_reason) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A factual justification reason of at least 10 characters is required.",
            )

        # 2. Check Decision Readiness & Safeguards
        readiness = cls.get_decision_readiness(db, user, tender_id, bid_id)

        if req.decision == BidDecisionStatusEnum.QUALIFIED and not readiness.can_qualify:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bid qualification blocked by platform safeguards: {'; '.join(readiness.blocking_reasons)}",
            )

        # 3. Fetch latest active evaluation snapshots
        score_snap = db.scalars(
            select(BidScoreSnapshot)
            .where(BidScoreSnapshot.bid_id == bid_id, BidScoreSnapshot.is_current == True)  # noqa: E712
            .order_by(BidScoreSnapshot.created_at.desc())
        ).first()

        risk_snap = db.scalars(
            select(BidRiskSnapshot)
            .where(BidRiskSnapshot.bid_id == bid_id, BidRiskSnapshot.is_current == True)  # noqa: E712
            .order_by(BidRiskSnapshot.created_at.desc())
        ).first()

        ai_rec = db.scalars(
            select(AIRecommendationRecord)
            .where(AIRecommendationRecord.bid_id == bid_id)
            .order_by(AIRecommendationRecord.created_at.desc())
        ).first()

        # 4. Fetch prior active decision to supersede
        prior_decisions = db.scalars(
            select(BidDecision)
            .where(BidDecision.bid_id == bid_id, BidDecision.is_current == True)  # noqa: E712
        ).all()

        max_ver = db.scalar(
            select(func.max(BidDecision.decision_version)).where(BidDecision.bid_id == bid_id)
        ) or 0
        next_version = max_ver + 1

        now_utc = datetime.now(timezone.utc)

        # 5. Create new BidDecision
        new_decision = BidDecision(
            organization_id=tender.organization_id,
            tender_id=tender.id,
            bid_id=bid.id,
            decision=req.decision.value,
            reason=clean_reason,
            decision_summary=req.decision_summary.strip() if req.decision_summary else None,
            category=req.category.value if req.category else None,
            decided_by_profile_id=profile.id,
            decided_at=now_utc,
            decision_version=next_version,
            evaluation_version=readiness.evaluation_version,
            score_snapshot_id=score_snap.id if score_snap else None,
            risk_snapshot_id=risk_snap.id if risk_snap else None,
            ai_recommendation_id=ai_rec.id if ai_rec else None,
            is_current=True,
            is_stale=False,
            stale_reason=None,
        )
        db.add(new_decision)
        db.flush()

        # 6. Supersede prior decisions
        for prior in prior_decisions:
            prior.is_current = False
            prior.superseded_at = now_utc
            prior.superseded_by_decision_id = new_decision.id

        # 7. Record Audit Event
        evt_type = (
            AuditEventType.BID_DECISION_SUPERSEDED
            if prior_decisions
            else AuditEventType.BID_DECISION_CREATED
        )
        AuditService.record_event(
            db,
            RecordAuditEventDTO(
                organization_id=tender.organization_id,
                tender_id=tender.id,
                bid_id=bid.id,
                actor_user_id=user.id,
                actor_profile_id=profile.id,
                actor_name=profile.full_name,
                actor_role=role.name,
                actor_source=AuditActorSource.HUMAN,
                event_type=evt_type,
                entity_type=AuditEntityType.BID_DECISION,
                entity_id=new_decision.id,
                action=req.decision.value,
                summary=f"Procurement Officer recorded final qualification decision '{req.decision.value}' (version {next_version}).",
                metadata={
                    "decision": req.decision.value,
                    "decision_version": next_version,
                    "evaluation_version": readiness.evaluation_version,
                    "category": req.category.value if req.category else None,
                    "reason_excerpt": clean_reason[:200],
                },
            ),
        )

        db.commit()

        logger.info(
            f"[Part 8D Decision Recorded] user_id={user.id} profile_id={profile.id} "
            f"tender_id={tender.id} bid_id={bid.id} decision={req.decision.value} "
            f"version={next_version} timestamp={now_utc.isoformat()}"
        )

        return cls.get_current_decision(db, user, tender_id, bid_id)

    @classmethod
    def check_and_mark_decision_staleness(
        cls,
        db: Session,
        bid_id: uuid.UUID,
        reason: str = "Upstream compliance determination or verification mutated.",
    ) -> int:
        """
        Marks current decision as stale upon upstream evaluation mutations without auto-reversing decision.
        Returns number of decisions marked stale (1 or 0).
        """
        current_dec = db.scalars(
            select(BidDecision).where(BidDecision.bid_id == bid_id, BidDecision.is_current == True)  # noqa: E712
        ).first()
        if current_dec and not current_dec.is_stale:
            current_dec.is_stale = True
            current_dec.stale_reason = reason

            # Record Audit Event
            AuditService.record_event(
                db,
                RecordAuditEventDTO(
                    organization_id=current_dec.organization_id,
                    tender_id=current_dec.tender_id,
                    bid_id=current_dec.bid_id,
                    actor_source=AuditActorSource.SYSTEM,
                    event_type=AuditEventType.BID_DECISION_STALE,
                    entity_type=AuditEntityType.BID_DECISION,
                    entity_id=current_dec.id,
                    action="STALE",
                    summary=f"Decision version {current_dec.decision_version} ({current_dec.decision}) flagged stale: {reason}",
                    metadata={
                        "decision": current_dec.decision,
                        "decision_version": current_dec.decision_version,
                        "stale_reason": reason,
                    },
                ),
            )

            db.commit()
            logger.info(f"[Part 8D Decision Stale] bid_id={bid_id} decision_id={current_dec.id} reason={reason}")
            return 1
        return 0
