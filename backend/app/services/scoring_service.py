"""
Scoring Service Layer for Part 7A
Coordinates bid score loading, calculation, RBAC tenant validation, and versioned snapshot persistence.
"""

import logging
import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.db.models.bid import Bid
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.schemas.scoring import (
    BidScoringFoundationResponse,
    CategoryScoreResponse,
    RuleScoreContributionResponse,
    ScoringReadinessResponse,
)
from app.services.scoring.scoring_config import ReviewPolicy, ScoringConfig
from app.services.scoring.scoring_engine import evaluate_scoring_foundation
from app.services.scoring.scoring_models import RuleScoreInput

logger = logging.getLogger(__name__)


from app.db.models.profile import Profile
from app.db.models.role import Role


def validate_bid_access(db: Session, current_user: User, bid_id: uuid.UUID) -> Bid:
    """
    Validates tenant-level access control for a Bid.
    Returns Bid or raises HTTP 404 to prevent enumeration.
    """
    profile = db.scalars(
        select(Profile).where(Profile.id == current_user.profile_id)
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )

    stmt = (
        select(Bid)
        .options(
            joinedload(Bid.tender),
            joinedload(Bid.bidder_organization),
        )
        .where(Bid.id == bid_id)
    )
    bid = db.execute(stmt).scalar_one_or_none()
    if not bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid not found or access denied.",
        )

    # Check RBAC via Profile -> Role
    role = db.scalars(select(Role).where(Role.id == profile.role_id)).first()
    role_name = role.name if role else ""

    if role_name == "ADMIN":
        return bid

    if role_name == "BIDDER":
        if bid.bidder_organization_id != profile.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid not found or access denied.",
            )
        return bid

    if role_name == "PROCUREMENT_OFFICER":
        if not bid.tender or bid.tender.organization_id != profile.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid not found or access denied.",
            )
        return bid

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to access bid score.",
    )



def build_scoring_rule_inputs(db: Session, bid: Bid) -> List[RuleScoreInput]:
    """
    Fetches all active tender requirements and merges them with current compliance results.
    """
    # 1. Fetch active requirements for tender
    req_stmt = (
        select(TenderRequirement)
        .where(TenderRequirement.tender_id == bid.tender_id)
        .order_by(TenderRequirement.display_order.asc(), TenderRequirement.code.asc())
    )
    requirements = db.execute(req_stmt).scalars().all()

    # 2. Fetch current compliance results for this bid
    comp_stmt = (
        select(ComplianceResult)
        .where(
            ComplianceResult.bid_id == bid.id,
            ComplianceResult.is_current == True,  # noqa: E712
        )
    )
    compliance_results = db.execute(comp_stmt).scalars().all()
    comp_map = {cr.tender_requirement_id: cr for cr in compliance_results}

    rule_inputs: List[RuleScoreInput] = []
    for req in requirements:
        cr = comp_map.get(req.id)
        if cr:
            rule_inputs.append(
                RuleScoreInput(
                    compliance_result_id=cr.id,
                    requirement_id=req.id,
                    requirement_code=req.code,
                    requirement_name=req.name,
                    category=req.category,
                    status=cr.compliance_status,
                    weight=cr.weight if cr.weight is not None else req.weight,
                    is_mandatory=cr.is_mandatory,
                    is_critical=getattr(cr, "is_critical", req.is_critical),
                    critical_failure=getattr(cr, "critical_failure", False),
                    review_required=(cr.compliance_status == ComplianceStatus.REVIEW),
                    review_reason=cr.reason if cr.compliance_status == ComplianceStatus.REVIEW else None,
                )
            )
        else:
            # Missing compliance result for active requirement -> treated as PENDING
            rule_inputs.append(
                RuleScoreInput(
                    compliance_result_id=None,
                    requirement_id=req.id,
                    requirement_code=req.code,
                    requirement_name=req.name,
                    category=req.category,
                    status=ComplianceStatus.PENDING,
                    weight=req.weight,
                    is_mandatory=req.is_mandatory,
                    is_critical=req.is_critical,
                    critical_failure=False,
                    review_required=False,
                    review_reason="No compliance determination recorded yet",
                )
            )

    return rule_inputs


def calculate_and_save_bid_score(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    review_policy: Optional[ReviewPolicy] = None,
) -> BidScoringFoundationResponse:
    """
    Executes pure deterministic scoring calculation and persists a new versioned snapshot.
    Marks prior snapshots as is_current = False.
    """
    bid = validate_bid_access(db, current_user, bid_id)
    rule_inputs = build_scoring_rule_inputs(db, bid)

    # Determine next scoring version for this bid
    max_ver_stmt = (
        select(func.max(BidScoreSnapshot.scoring_version))
        .where(BidScoreSnapshot.bid_id == bid.id)
    )
    current_max_ver = db.execute(max_ver_stmt).scalar() or 0
    next_version = current_max_ver + 1

    # Execute scoring calculation engine
    result = evaluate_scoring_foundation(
        bid_id=bid.id,
        tender_id=bid.tender_id,
        rule_inputs=rule_inputs,
        config=ScoringConfig,
        review_policy=review_policy,
        scoring_version=next_version,
    )

    # Mark prior active snapshot(s) as is_current = False
    prior_snapshots_stmt = (
        select(BidScoreSnapshot)
        .where(
            BidScoreSnapshot.bid_id == bid.id,
            BidScoreSnapshot.is_current == True,  # noqa: E712
        )
    )
    prior_snapshots = db.execute(prior_snapshots_stmt).scalars().all()
    for snap in prior_snapshots:
        snap.is_current = False

    # Persist new snapshot
    serialized_contributions = [c.model_dump(mode="json") for c in result.rule_contributions]
    serialized_category_scores = {k: v.model_dump(mode="json") for k, v in result.category_scores.items()}

    new_snapshot = BidScoreSnapshot(
        bid_id=bid.id,
        tender_id=bid.tender_id,
        scoring_version=next_version,
        scoring_formula_version=result.scoring_formula_version,
        scoring_status=result.readiness.scoring_status.value,
        scoring_complete=result.readiness.scoring_complete,
        human_review_required=result.readiness.human_review_required,
        earned_weight=result.earned_weight,
        eligible_weight=result.eligible_weight,
        overall_score=result.overall_score,
        is_provisional=result.is_provisional,
        total_rules_count=result.readiness.total_rules,
        passed_rules_count=result.readiness.passed_rules,
        failed_rules_count=result.readiness.failed_rules,
        review_rules_count=result.readiness.review_rules,
        pending_rules_count=result.readiness.pending_rules,
        not_applicable_count=result.readiness.not_applicable_rules,
        mandatory_failures_count=result.readiness.mandatory_failures,
        critical_failures_count=result.readiness.critical_failures,
        rule_contributions=serialized_contributions,
        category_scores=serialized_category_scores,
        calculation_details=result.calculation_details,
        is_current=True,
    )

    db.add(new_snapshot)
    db.commit()
    db.refresh(new_snapshot)

    logger.info(
        f"Saved score snapshot v{next_version} for bid {bid.id}: "
        f"overall_score={new_snapshot.overall_score}%, "
        f"earned={new_snapshot.earned_weight}/{new_snapshot.eligible_weight}, "
        f"complete={new_snapshot.scoring_complete}"
    )

    return snapshot_to_response(new_snapshot)


def get_bid_score(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> BidScoringFoundationResponse:
    """
    Retrieves current active score snapshot for a bid.
    If no snapshot exists yet, automatically calculates and creates v1.
    """
    bid = validate_bid_access(db, current_user, bid_id)

    snap_stmt = (
        select(BidScoreSnapshot)
        .where(
            BidScoreSnapshot.bid_id == bid.id,
            BidScoreSnapshot.is_current == True,  # noqa: E712
        )
    )
    snapshot = db.execute(snap_stmt).scalar_one_or_none()

    if not snapshot:
        return calculate_and_save_bid_score(db, current_user, bid_id)

    return snapshot_to_response(snapshot)


def snapshot_to_response(snapshot: BidScoreSnapshot) -> BidScoringFoundationResponse:
    """Formats a BidScoreSnapshot ORM model into BidScoringFoundationResponse."""
    contributions = [
        RuleScoreContributionResponse(**c)
        for c in (snapshot.rule_contributions or [])
    ]
    category_scores = {
        k: CategoryScoreResponse(**v)
        for k, v in (snapshot.category_scores or {}).items()
    }

    readiness = ScoringReadinessResponse(
        scoring_ready=True,
        scoring_complete=snapshot.scoring_complete,
        human_review_required=snapshot.human_review_required,
        scoring_status=snapshot.scoring_status,
        total_rules=snapshot.total_rules_count,
        passed_rules=snapshot.passed_rules_count,
        failed_rules=snapshot.failed_rules_count,
        review_rules=snapshot.review_rules_count,
        pending_rules=snapshot.pending_rules_count,
        not_applicable_rules=snapshot.not_applicable_count,
        mandatory_failures=snapshot.mandatory_failures_count,
        critical_failures=snapshot.critical_failures_count,
    )

    return BidScoringFoundationResponse(
        bid_id=str(snapshot.bid_id),
        tender_id=str(snapshot.tender_id),
        scoring_version=snapshot.scoring_version,
        scoring_formula_version=snapshot.scoring_formula_version,
        readiness=readiness,
        earned_weight=snapshot.earned_weight,
        eligible_weight=snapshot.eligible_weight,
        overall_score=snapshot.overall_score,
        is_provisional=snapshot.is_provisional,
        category_scores=category_scores,
        rule_contributions=contributions,
        calculation_details=snapshot.calculation_details or {},
        calculated_at=snapshot.calculated_at,
    )

