"""
Risk Service Layer for Part 7C & Part 7D: Deterministic Risk & Overrides Engine
Coordinates bid risk calculation, score snapshot loading, deterministic override evaluation,
RBAC tenant validation, and versioned risk snapshot persistence.
"""

import logging
import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.db.models.bid import Bid
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.user import User
from app.schemas.risk import (
    BidRiskAssessmentResponse,
    RiskContributionResponse,
    RiskFeaturesResponse,
    RiskOverrideResponse,
)
from app.services.risk.risk_config import RiskConfig
from app.services.risk.risk_engine import (
    evaluate_base_risk,
    extract_risk_features,
)
from app.services.risk.risk_models import RiskAssessment, RiskFeatures
from app.services.risk.risk_override_config import RiskOverrideConfig
from app.services.risk.risk_override_engine import RiskOverrideEngine
from app.services.scoring.scoring_config import ScoringConfig
from app.services.scoring.scoring_engine import evaluate_scoring_foundation
from app.services.scoring_service import (
    build_scoring_rule_inputs,
    validate_bid_access,
)

logger = logging.getLogger(__name__)


def calculate_and_save_bid_risk(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    config: Optional[RiskConfig] = None,
    override_config: Optional[RiskOverrideConfig] = None,
) -> BidRiskAssessmentResponse:
    """
    Executes Part 7C deterministic base risk calculation followed by Part 7D
    critical overrides and risk adjustments. Persists a new versioned snapshot
    and marks prior risk snapshots as is_current = False.
    """
    cfg = config or RiskConfig
    ovr_cfg = override_config or RiskOverrideConfig
    bid = validate_bid_access(db, current_user, bid_id)

    # 1. Fetch current scoring foundation evaluation for this bid
    rule_inputs = build_scoring_rule_inputs(db, bid)
    score_result = evaluate_scoring_foundation(
        bid_id=bid.id,
        tender_id=bid.tender_id,
        rule_inputs=rule_inputs,
        config=ScoringConfig,
    )

    # 2. Extract normalized risk features from score result
    features = extract_risk_features(score_result=score_result)

    # 3. Determine next risk version for this bid
    max_ver_stmt = (
        select(func.max(BidRiskSnapshot.risk_version))
        .where(BidRiskSnapshot.bid_id == bid.id)
    )
    current_max_ver = db.execute(max_ver_stmt).scalar() or 0
    next_version = current_max_ver + 1

    # 4. Evaluate Part 7C deterministic base risk
    base_assessment = evaluate_base_risk(
        features=features,
        bid_id=bid.id,
        tender_id=bid.tender_id,
        config=cfg,
        risk_version=next_version,
    )

    # 5. Evaluate Part 7D deterministic risk overrides & floors
    final_assessment = RiskOverrideEngine.evaluate_risk_overrides(
        base_assessment=base_assessment,
        rule_inputs=rule_inputs,
        config=ovr_cfg,
    )

    # 6. Mark prior active risk snapshot(s) as is_current = False
    prior_snapshots_stmt = (
        select(BidRiskSnapshot)
        .where(
            BidRiskSnapshot.bid_id == bid.id,
            BidRiskSnapshot.is_current == True,  # noqa: E712
        )
    )
    prior_snapshots = db.execute(prior_snapshots_stmt).scalars().all()
    for snap in prior_snapshots:
        snap.is_current = False

    # 7. Persist new risk snapshot with both base and adjusted metrics
    serialized_features = final_assessment.features.model_dump(mode="json")
    serialized_contributions = [c.model_dump(mode="json") for c in final_assessment.contributions]
    serialized_overrides = [o.model_dump(mode="json") for o in final_assessment.applied_overrides]

    new_snapshot = BidRiskSnapshot(
        bid_id=bid.id,
        tender_id=bid.tender_id,
        risk_version=next_version,
        risk_formula_version=final_assessment.risk_formula_version,
        override_formula_version=final_assessment.override_formula_version,
        base_risk_score=final_assessment.base_risk_score,
        base_risk_level=final_assessment.base_risk_level.value if final_assessment.base_risk_level else None,
        adjusted_risk_score=final_assessment.adjusted_risk_score,
        adjusted_risk_level=final_assessment.adjusted_risk_level.value if final_assessment.adjusted_risk_level else None,
        override_applied=final_assessment.override_applied,
        override_count=final_assessment.override_count,
        applied_overrides=serialized_overrides,
        risk_complete=final_assessment.risk_complete,
        is_provisional=final_assessment.is_provisional,
        human_review_required=final_assessment.human_review_required,
        feature_snapshot=serialized_features,
        contribution_details=serialized_contributions,
        summary_reasons=final_assessment.summary_reasons,
        calculation_details=final_assessment.calculation_details,
        is_current=True,
    )

    db.add(new_snapshot)
    db.commit()
    db.refresh(new_snapshot)

    logger.info(
        f"Saved risk snapshot v{next_version} for bid {bid.id}: "
        f"base_score={new_snapshot.base_risk_score}, "
        f"adjusted_score={new_snapshot.adjusted_risk_score}, "
        f"adjusted_level='{new_snapshot.adjusted_risk_level}', "
        f"overrides={new_snapshot.override_count}, "
        f"provisional={new_snapshot.is_provisional}"
    )

    return risk_snapshot_to_response(new_snapshot)


def get_bid_risk(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> BidRiskAssessmentResponse:
    """
    Retrieves current active risk snapshot for a bid.
    If no risk snapshot exists yet, automatically calculates and creates v1.
    """
    bid = validate_bid_access(db, current_user, bid_id)

    snap_stmt = (
        select(BidRiskSnapshot)
        .where(
            BidRiskSnapshot.bid_id == bid.id,
            BidRiskSnapshot.is_current == True,  # noqa: E712
        )
    )
    snapshot = db.execute(snap_stmt).scalar_one_or_none()

    if not snapshot:
        return calculate_and_save_bid_risk(db, current_user, bid_id)

    return risk_snapshot_to_response(snapshot)


def risk_snapshot_to_response(snapshot: BidRiskSnapshot) -> BidRiskAssessmentResponse:
    """Formats a BidRiskSnapshot ORM model into BidRiskAssessmentResponse."""
    feat_data = snapshot.feature_snapshot or {}
    features = RiskFeaturesResponse(**feat_data)

    contributions = [
        RiskContributionResponse(**c)
        for c in (snapshot.contribution_details or [])
    ]

    applied_overrides = [
        RiskOverrideResponse(**o)
        for o in (snapshot.applied_overrides or [])
    ]

    return BidRiskAssessmentResponse(
        id=str(snapshot.id),
        bid_id=str(snapshot.bid_id),
        tender_id=str(snapshot.tender_id),
        risk_version=snapshot.risk_version,
        risk_formula_version=snapshot.risk_formula_version,
        override_formula_version=snapshot.override_formula_version or "v1",
        base_risk_score=snapshot.base_risk_score,
        base_risk_level=snapshot.base_risk_level,
        adjusted_risk_score=snapshot.adjusted_risk_score,
        adjusted_risk_level=snapshot.adjusted_risk_level,
        override_applied=snapshot.override_applied,
        override_count=snapshot.override_count,
        applied_overrides=applied_overrides,
        risk_complete=snapshot.risk_complete,
        is_provisional=snapshot.is_provisional,
        human_review_required=snapshot.human_review_required,
        features=features,
        contributions=contributions,
        summary_reasons=snapshot.summary_reasons or [],
        calculation_details=snapshot.calculation_details or {},
        calculated_at=snapshot.calculated_at,
    )
