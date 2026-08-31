"""
Scoring Engine Foundation, Category Aggregation & Deterministic Weight Calculation
Pure deterministic scoring functions executing weight resolution, status factor mappings,
normalized rule contributions, category-wise score aggregation, and overall compliance score calculation.
"""

import math
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from app.db.models.compliance_result import ComplianceStatus
from app.services.scoring.scoring_config import ReviewPolicy, ScoringConfig
from app.services.scoring.scoring_models import (
    CategoryScore,
    RuleScoreContribution,
    RuleScoreInput,
    ScoringCalculationResult,
    ScoringReadiness,
    ScoringStatus,
)


def resolve_rule_weight(
    raw_weight: Any,
    default_weight: Decimal = ScoringConfig.DEFAULT_REQUIREMENT_WEIGHT,
) -> Decimal:
    """
    Validates and resolves a requirement weight into a non-negative Decimal.
    Rejects negative weights, NaN, and non-numeric values.
    """
    if raw_weight is None:
        return default_weight

    try:
        if isinstance(raw_weight, float):
            if math.isnan(raw_weight) or math.isinf(raw_weight):
                raise ValueError("Weight cannot be NaN or Infinity")
            weight_dec = Decimal(str(raw_weight))
        elif isinstance(raw_weight, Decimal):
            weight_dec = raw_weight
        elif isinstance(raw_weight, (int, str)):
            weight_dec = Decimal(str(raw_weight).strip())
        else:
            raise ValueError(f"Unsupported weight type: {type(raw_weight)}")
    except (InvalidOperation, TypeError, ValueError) as err:
        raise ValueError(f"Invalid requirement weight '{raw_weight}': {err}")

    if weight_dec < Decimal("0.0"):
        raise ValueError(f"Requirement weight must be non-negative (>= 0), got {weight_dec}")

    return weight_dec.quantize(Decimal("0.0001"), rounding=ScoringConfig.ROUNDING_MODE)


def calculate_rule_contribution(
    rule_input: RuleScoreInput,
    config: Optional[ScoringConfig] = None,
    review_policy: Optional[ReviewPolicy] = None,
) -> RuleScoreContribution:
    """
    Calculates the normalized scoring contribution of a single requirement clause.
    """
    cfg = config or ScoringConfig
    active_policy = review_policy or cfg.REVIEW_POLICY

    # Resolve and validate rule weight
    weight = resolve_rule_weight(rule_input.weight, cfg.DEFAULT_REQUIREMENT_WEIGHT)
    canonical_category = cfg.normalize_category(rule_input.category)
    status = (rule_input.status or ComplianceStatus.PENDING).strip().upper()

    # NOT_APPLICABLE rules are cleanly excluded from the denominator and earned total
    if status == ComplianceStatus.NOT_APPLICABLE:
        return RuleScoreContribution(
            compliance_result_id=str(rule_input.compliance_result_id) if rule_input.compliance_result_id else None,
            requirement_id=str(rule_input.requirement_id),
            requirement_code=rule_input.requirement_code,
            requirement_name=rule_input.requirement_name,
            category=canonical_category,
            status=status,
            weight=weight,
            score_factor=Decimal("0.0000"),
            earned_weight=Decimal("0.0000"),
            eligible_weight=Decimal("0.0000"),
            is_mandatory=rule_input.is_mandatory,
            is_critical=rule_input.is_critical,
            critical_failure=rule_input.critical_failure,
            excluded_from_score=True,
            exclusion_reason="Requirement is NOT_APPLICABLE to this bidder proposal",
        )

    # Scorable requirements
    score_factor = cfg.get_score_factor(status, review_policy=active_policy)
    eligible_weight = weight
    earned_weight = (weight * score_factor).quantize(Decimal("0.0001"), rounding=cfg.ROUNDING_MODE)

    return RuleScoreContribution(
        compliance_result_id=str(rule_input.compliance_result_id) if rule_input.compliance_result_id else None,
        requirement_id=str(rule_input.requirement_id),
        requirement_code=rule_input.requirement_code,
        requirement_name=rule_input.requirement_name,
        category=canonical_category,
        status=status,
        weight=weight,
        score_factor=score_factor,
        earned_weight=earned_weight,
        eligible_weight=eligible_weight,
        is_mandatory=rule_input.is_mandatory,
        is_critical=rule_input.is_critical,
        critical_failure=rule_input.critical_failure,
        excluded_from_score=False,
        exclusion_reason=None,
    )


def aggregate_category_scores(
    rule_contributions: List[RuleScoreContribution],
    config: Optional[ScoringConfig] = None,
) -> Dict[str, CategoryScore]:
    """
    Groups rule-level scoring contributions by domain category and calculates
    deterministic category-wise earned weights, eligible weights, and scores.
    """
    cfg = config or ScoringConfig
    grouped: Dict[str, List[RuleScoreContribution]] = {}

    for contrib in rule_contributions:
        cat = cfg.normalize_category(contrib.category)
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(contrib)

    category_scores: Dict[str, CategoryScore] = {}

    for cat, items in grouped.items():
        total_rules = len(items)
        passed_rules = sum(1 for i in items if i.status == ComplianceStatus.PASS)
        failed_rules = sum(1 for i in items if i.status == ComplianceStatus.FAIL)
        review_rules = sum(1 for i in items if i.status == ComplianceStatus.REVIEW)
        pending_rules = sum(1 for i in items if i.status == ComplianceStatus.PENDING)
        na_rules = sum(1 for i in items if i.status == ComplianceStatus.NOT_APPLICABLE)

        mandatory_fails = sum(1 for i in items if i.is_mandatory and i.status == ComplianceStatus.FAIL)
        critical_fails = sum(1 for i in items if i.critical_failure or (i.is_critical and i.status == ComplianceStatus.FAIL))

        earned_weight = sum((i.earned_weight for i in items), Decimal("0.0000"))
        eligible_weight = sum((i.eligible_weight for i in items if not i.excluded_from_score), Decimal("0.0000"))

        raw_score: Optional[Decimal] = None
        display_score: Optional[Decimal] = None

        if eligible_weight > Decimal("0.0000"):
            score_calc = (earned_weight / eligible_weight) * Decimal("100.0000")
            raw_score = score_calc.quantize(Decimal("0.0001"), rounding=cfg.ROUNDING_MODE)
            display_score = score_calc.quantize(Decimal("0.01"), rounding=cfg.ROUNDING_MODE)

            # Strict bounds safety check
            if not (Decimal("0.0000") <= raw_score <= Decimal("100.0000")):
                raise ValueError(f"Calculated category score {raw_score}% out of valid [0, 100] bounds for category '{cat}'")

        scoring_complete = (pending_rules == 0)
        human_review_required = (review_rules > 0)
        is_provisional = (pending_rules > 0)

        category_scores[cat] = CategoryScore(
            category=cat,
            display_name=cfg.get_category_display_name(cat),
            total_rules=total_rules,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            review_rules=review_rules,
            pending_rules=pending_rules,
            not_applicable_rules=na_rules,
            mandatory_failures=mandatory_fails,
            critical_failures=critical_fails,
            earned_weight=earned_weight.quantize(Decimal("0.0001"), rounding=cfg.ROUNDING_MODE),
            eligible_weight=eligible_weight.quantize(Decimal("0.0001"), rounding=cfg.ROUNDING_MODE),
            raw_score=raw_score,
            display_score=display_score,
            scoring_complete=scoring_complete,
            human_review_required=human_review_required,
            is_provisional=is_provisional,
            rule_contributions=items,
        )

    return category_scores


def evaluate_scoring_foundation(
    bid_id: uuid.UUID,
    tender_id: uuid.UUID,
    rule_inputs: List[RuleScoreInput],
    config: Optional[ScoringConfig] = None,
    review_policy: Optional[ReviewPolicy] = None,
    scoring_version: int = 1,
) -> ScoringCalculationResult:
    """
    Orchestrates foundation scoring calculation across all active tender requirements for a bid.
    Calculates eligible weight, earned weight, readiness, category scores, and overall compliance score.
    """
    cfg = config or ScoringConfig
    active_policy = review_policy or cfg.REVIEW_POLICY

    total_eligible = Decimal("0.0000")
    total_earned = Decimal("0.0000")

    passed_count = 0
    failed_count = 0
    review_count = 0
    pending_count = 0
    na_count = 0
    mandatory_fails = 0
    critical_fails = 0
    human_review_needed = False

    contributions: List[RuleScoreContribution] = []

    for r_in in rule_inputs:
        contrib = calculate_rule_contribution(r_in, config=cfg, review_policy=active_policy)
        contributions.append(contrib)

        status = contrib.status
        if status == ComplianceStatus.PASS:
            passed_count += 1
        elif status == ComplianceStatus.FAIL:
            failed_count += 1
        elif status == ComplianceStatus.REVIEW:
            review_count += 1
        elif status == ComplianceStatus.PENDING:
            pending_count += 1
        elif status == ComplianceStatus.NOT_APPLICABLE:
            na_count += 1

        if contrib.is_mandatory and status == ComplianceStatus.FAIL:
            mandatory_fails += 1
        if contrib.critical_failure or (contrib.is_critical and status == ComplianceStatus.FAIL):
            critical_fails += 1

        if r_in.review_required or status == ComplianceStatus.REVIEW:
            human_review_needed = True

        if not contrib.excluded_from_score:
            total_eligible += contrib.eligible_weight
            total_earned += contrib.earned_weight

    # Determine scoring status & completeness
    total_rules = len(rule_inputs)
    if total_rules == 0 or (total_eligible == Decimal("0.0000") and total_rules == na_count):
        scoring_status = ScoringStatus.NO_SCORABLE_REQUIREMENTS
        scoring_complete = True
    elif pending_count > 0:
        scoring_status = ScoringStatus.INCOMPLETE
        scoring_complete = False
    elif any(c.status == ComplianceStatus.BLOCKED for c in contributions):
        scoring_status = ScoringStatus.BLOCKED
        scoring_complete = False
    else:
        scoring_status = ScoringStatus.READY
        scoring_complete = True

    readiness = ScoringReadiness(
        scoring_ready=True,
        scoring_complete=scoring_complete,
        human_review_required=human_review_needed,
        scoring_status=scoring_status,
        total_rules=total_rules,
        passed_rules=passed_count,
        failed_rules=failed_count,
        review_rules=review_count,
        pending_rules=pending_count,
        not_applicable_rules=na_count,
        mandatory_failures=mandatory_fails,
        critical_failures=critical_fails,
    )

    # Calculate category score breakdown (Part 7B)
    category_scores = aggregate_category_scores(contributions, config=cfg)

    # Calculate overall compliance score (total earned / total eligible)
    overall_score: Optional[Decimal] = None
    if total_eligible > Decimal("0.0000"):
        score_calc = (total_earned / total_eligible) * Decimal("100.0000")
        overall_score = score_calc.quantize(Decimal("0.01"), rounding=cfg.ROUNDING_MODE)

        if not (Decimal("0.00") <= overall_score <= Decimal("100.00")):
            raise ValueError(f"Calculated overall score {overall_score}% out of valid [0, 100] bounds")

    is_provisional = (pending_count > 0)

    calculation_details = {
        "formula_version": cfg.SCORING_FORMULA_VERSION,
        "review_policy": active_policy.value,
        "precision": cfg.INTERNAL_DECIMAL_PRECISION,
        "rounding_mode": "ROUND_HALF_UP",
        "total_rules": total_rules,
        "eligible_weight": str(total_eligible),
        "earned_weight": str(total_earned),
        "overall_score": str(overall_score) if overall_score is not None else None,
        "is_provisional": is_provisional,
        "category_count": len(category_scores),
    }

    return ScoringCalculationResult(
        bid_id=str(bid_id),
        tender_id=str(tender_id),
        scoring_version=scoring_version,
        scoring_formula_version=cfg.SCORING_FORMULA_VERSION,
        readiness=readiness,
        earned_weight=total_earned.quantize(Decimal("0.0001"), rounding=cfg.ROUNDING_MODE),
        eligible_weight=total_eligible.quantize(Decimal("0.0001"), rounding=cfg.ROUNDING_MODE),
        overall_score=overall_score,
        is_provisional=is_provisional,
        category_scores=category_scores,
        rule_contributions=contributions,
        calculation_details=calculation_details,
    )
