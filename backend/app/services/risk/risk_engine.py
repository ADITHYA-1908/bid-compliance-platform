"""
Deterministic Base Risk Assessment Engine for Part 7C
Pure mathematical functions executing risk feature extraction, indicator weight contributions,
normalized composite risk scoring, threshold level assignment, and explainable reason generation.

Strict Part 7C Architectural Boundaries:
- Pure deterministic calculation without LLMs or probabilistic ML models.
- No critical hard overrides or blacklisting auto-critical logic (reserved for Part 7D).
- No automated qualification or disqualification decisions.
- No human procurement officer final decision workflows.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from app.db.models.compliance_result import ComplianceStatus
from app.services.risk.risk_config import RiskConfig, RiskIndicator, RiskLevel
from app.services.risk.risk_models import (
    RiskAssessment,
    RiskContribution,
    RiskFeatures,
)
from app.services.scoring.scoring_models import RuleScoreContribution, ScoringCalculationResult


def extract_risk_features(
    score_result: ScoringCalculationResult,
    cross_document_mismatch_count: int = 0,
    low_confidence_count: int = 0,
) -> RiskFeatures:
    """
    Extracts normalized risk features from Part 7B scoring results and rule contributions.
    """
    contributions = score_result.rule_contributions or []
    readiness = score_result.readiness

    total_rules = readiness.total_rules
    na_count = readiness.not_applicable_rules
    applicable_rules = max(0, total_rules - na_count)

    passed_count = readiness.passed_rules
    fail_count = readiness.failed_rules
    review_count = readiness.review_rules
    pending_count = readiness.pending_rules

    mandatory_rules_count = sum(1 for c in contributions if c.is_mandatory and not c.excluded_from_score)
    mandatory_failure_count = readiness.mandatory_failures
    critical_failure_count = readiness.critical_failures

    # Count integrity category findings
    integrity_contribs = [c for c in contributions if c.category == "INTEGRITY" and not c.excluded_from_score]
    integrity_rules_count = len(integrity_contribs)
    integrity_fail_count = sum(1 for c in integrity_contribs if c.status == ComplianceStatus.FAIL)
    integrity_review_count = sum(1 for c in integrity_contribs if c.status == ComplianceStatus.REVIEW)

    # Detect cross-document / identity mismatches from rule contributions if not explicitly passed
    detected_mismatches = cross_document_mismatch_count
    for c in contributions:
        code_upper = (c.requirement_code or "").upper()
        name_upper = (c.requirement_name or "").upper()
        if "CONSISTENCY" in code_upper or "MISMATCH" in code_upper or "CONSISTENCY" in name_upper or "MISMATCH" in name_upper:
            if c.status in [ComplianceStatus.FAIL, ComplianceStatus.REVIEW]:
                detected_mismatches += 1

    return RiskFeatures(
        overall_compliance_score=score_result.overall_score,
        total_rules=total_rules,
        applicable_rules=applicable_rules,
        passed_count=passed_count,
        fail_count=fail_count,
        review_count=review_count,
        pending_count=pending_count,
        not_applicable_count=na_count,
        mandatory_rules_count=mandatory_rules_count,
        mandatory_failure_count=mandatory_failure_count,
        critical_failure_count=critical_failure_count,
        integrity_rules_count=integrity_rules_count,
        integrity_fail_count=integrity_fail_count,
        integrity_review_count=integrity_review_count,
        cross_document_mismatch_count=detected_mismatches,
        low_confidence_count=low_confidence_count,
        scoring_complete=readiness.scoring_complete,
        human_review_required=readiness.human_review_required,
    )


def calculate_risk_contributions(
    features: RiskFeatures,
    config: Optional[RiskConfig] = None,
) -> List[RiskContribution]:
    """
    Computes individual weighted risk contributions for each deterministic risk indicator.
    """
    cfg = config or RiskConfig
    contributions: List[RiskContribution] = []

    # 1. Compliance Deficit Contribution (Max Weight: 40.0)
    meta_deficit = cfg.get_indicator_metadata(RiskIndicator.COMPLIANCE_DEFICIT)
    if features.overall_compliance_score is not None:
        raw_deficit = max(Decimal("0.0000"), Decimal("100.0000") - Decimal(str(features.overall_compliance_score)))
        norm_deficit = (raw_deficit / Decimal("100.0000")).quantize(cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE)
        w_deficit = (norm_deficit * cfg.WEIGHT_COMPLIANCE_DEFICIT).quantize(cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE)
        reason_deficit = f"Overall compliance deficit of {raw_deficit:.2f}% contributed {w_deficit:.2f} risk points."
        raw_val_deficit = f"{raw_deficit:.2f}%"
    else:
        norm_deficit = Decimal("0.0000")
        w_deficit = Decimal("0.0000")
        raw_val_deficit = "N/A"
        reason_deficit = "Overall compliance score is unavailable."

    contributions.append(
        RiskContribution(
            indicator=RiskIndicator.COMPLIANCE_DEFICIT,
            name=meta_deficit["name"],
            raw_value=raw_val_deficit,
            normalized_value=norm_deficit,
            weight=cfg.WEIGHT_COMPLIANCE_DEFICIT,
            weighted_contribution=w_deficit,
            reason=reason_deficit,
        )
    )

    # 2. Rule Failures Contribution (Max Weight: 20.0)
    meta_fail = cfg.get_indicator_metadata(RiskIndicator.RULE_FAILURES)
    if features.applicable_rules > 0:
        fail_rate = (Decimal(str(features.fail_count)) / Decimal(str(features.applicable_rules))).quantize(
            cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE
        )
        w_fail = (fail_rate * cfg.WEIGHT_RULE_FAILURES).quantize(cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE)
        reason_fail = (
            f"{features.fail_count} failed requirement(s) out of {features.applicable_rules} "
            f"applicable ({fail_rate * 100:.1f}% failure rate) contributed {w_fail:.2f} risk points."
        )
        raw_val_fail = f"{features.fail_count}/{features.applicable_rules} ({fail_rate * 100:.1f}%)"
    else:
        fail_rate = Decimal("0.0000")
        w_fail = Decimal("0.0000")
        raw_val_fail = "0/0"
        reason_fail = "No applicable requirements to evaluate failure rate."

    contributions.append(
        RiskContribution(
            indicator=RiskIndicator.RULE_FAILURES,
            name=meta_fail["name"],
            raw_value=raw_val_fail,
            normalized_value=fail_rate,
            weight=cfg.WEIGHT_RULE_FAILURES,
            weighted_contribution=w_fail,
            reason=reason_fail,
        )
    )

    # 3. Review Uncertainty Contribution (Max Weight: 15.0)
    meta_review = cfg.get_indicator_metadata(RiskIndicator.REVIEW_UNCERTAINTY)
    if features.applicable_rules > 0:
        review_rate = (Decimal(str(features.review_count)) / Decimal(str(features.applicable_rules))).quantize(
            cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE
        )
        w_review = (review_rate * cfg.WEIGHT_REVIEW_UNCERTAINTY).quantize(cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE)
        reason_review = (
            f"{features.review_count} requirement(s) requiring human review "
            f"({review_rate * 100:.1f}% review rate) added {w_review:.2f} uncertainty risk points."
        )
        raw_val_review = f"{features.review_count}/{features.applicable_rules} ({review_rate * 100:.1f}%)"
    else:
        review_rate = Decimal("0.0000")
        w_review = Decimal("0.0000")
        raw_val_review = "0/0"
        reason_review = "Zero human review items detected."

    contributions.append(
        RiskContribution(
            indicator=RiskIndicator.REVIEW_UNCERTAINTY,
            name=meta_review["name"],
            raw_value=raw_val_review,
            normalized_value=review_rate,
            weight=cfg.WEIGHT_REVIEW_UNCERTAINTY,
            weighted_contribution=w_review,
            reason=reason_review,
        )
    )

    # 4. Pending Uncertainty Contribution (Max Weight: 10.0)
    meta_pending = cfg.get_indicator_metadata(RiskIndicator.PENDING_UNCERTAINTY)
    if features.applicable_rules > 0:
        pending_rate = (Decimal(str(features.pending_count)) / Decimal(str(features.applicable_rules))).quantize(
            cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE
        )
        w_pending = (pending_rate * cfg.WEIGHT_PENDING_UNCERTAINTY).quantize(cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE)
        reason_pending = (
            f"{features.pending_count} pending verification check(s) "
            f"({pending_rate * 100:.1f}% pending rate) added {w_pending:.2f} provisional risk points."
        )
        raw_val_pending = f"{features.pending_count}/{features.applicable_rules} ({pending_rate * 100:.1f}%)"
    else:
        pending_rate = Decimal("0.0000")
        w_pending = Decimal("0.0000")
        raw_val_pending = "0/0"
        reason_pending = "Zero pending verification checks."

    contributions.append(
        RiskContribution(
            indicator=RiskIndicator.PENDING_UNCERTAINTY,
            name=meta_pending["name"],
            raw_value=raw_val_pending,
            normalized_value=pending_rate,
            weight=cfg.WEIGHT_PENDING_UNCERTAINTY,
            weighted_contribution=w_pending,
            reason=reason_pending,
        )
    )

    # 5. Mandatory Failures Contribution (Max Weight: 10.0)
    meta_mandatory = cfg.get_indicator_metadata(RiskIndicator.MANDATORY_FAILURES)
    if features.mandatory_rules_count > 0:
        mand_rate = min(
            Decimal("1.0000"),
            (Decimal(str(features.mandatory_failure_count)) / Decimal(str(features.mandatory_rules_count))).quantize(
                cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE
            ),
        )
        w_mandatory = (mand_rate * cfg.WEIGHT_MANDATORY_FAILURES).quantize(cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE)
        reason_mandatory = (
            f"{features.mandatory_failure_count} mandatory requirement failure(s) out of {features.mandatory_rules_count} "
            f"mandatory clauses added {w_mandatory:.2f} risk points."
        )
        raw_val_mand = f"{features.mandatory_failure_count}/{features.mandatory_rules_count}"
    elif features.mandatory_failure_count > 0:
        mand_rate = Decimal("1.0000")
        w_mandatory = cfg.WEIGHT_MANDATORY_FAILURES
        reason_mandatory = f"{features.mandatory_failure_count} mandatory failure(s) recorded (+{w_mandatory:.2f} risk points)."
        raw_val_mand = f"{features.mandatory_failure_count}"
    else:
        mand_rate = Decimal("0.0000")
        w_mandatory = Decimal("0.0000")
        raw_val_mand = "0/0"
        reason_mandatory = "Zero mandatory requirement failures detected."

    contributions.append(
        RiskContribution(
            indicator=RiskIndicator.MANDATORY_FAILURES,
            name=meta_mandatory["name"],
            raw_value=raw_val_mand,
            normalized_value=mand_rate,
            weight=cfg.WEIGHT_MANDATORY_FAILURES,
            weighted_contribution=w_mandatory,
            reason=reason_mandatory,
        )
    )

    # 6. Integrity Concerns Contribution (Max Weight: 5.0)
    meta_integ = cfg.get_indicator_metadata(RiskIndicator.INTEGRITY_CONCERNS)
    denom_integ = max(1, features.integrity_rules_count)
    points_integ = (
        Decimal(str(features.integrity_fail_count))
        + (Decimal("0.5000") * Decimal(str(features.integrity_review_count)))
        + (Decimal("0.5000") * Decimal(str(features.cross_document_mismatch_count)))
    )
    norm_integ = min(
        Decimal("1.0000"),
        (points_integ / Decimal(str(denom_integ))).quantize(cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE),
    )
    w_integ = (norm_integ * cfg.WEIGHT_INTEGRITY_CONCERNS).quantize(cfg.INTERNAL_PRECISION, rounding=cfg.ROUNDING_MODE)

    if (
        features.integrity_fail_count > 0
        or features.integrity_review_count > 0
        or features.cross_document_mismatch_count > 0
    ):
        reason_integ = (
            f"Integrity & identity signals (fails={features.integrity_fail_count}, "
            f"reviews={features.integrity_review_count}, mismatches={features.cross_document_mismatch_count}) "
            f"contributed {w_integ:.2f} risk points."
        )
        raw_val_integ = (
            f"fails={features.integrity_fail_count}, rev={features.integrity_review_count}, "
            f"mismatches={features.cross_document_mismatch_count}"
        )
    else:
        reason_integ = "No debarment, blacklisting, or cross-document identity integrity issues detected."
        raw_val_integ = "None"

    contributions.append(
        RiskContribution(
            indicator=RiskIndicator.INTEGRITY_CONCERNS,
            name=meta_integ["name"],
            raw_value=raw_val_integ,
            normalized_value=norm_integ,
            weight=cfg.WEIGHT_INTEGRITY_CONCERNS,
            weighted_contribution=w_integ,
            reason=reason_integ,
        )
    )

    return contributions


def generate_summary_reasons(
    features: RiskFeatures,
    base_risk_score: Optional[Decimal],
    base_risk_level: Optional[RiskLevel],
    is_provisional: bool,
) -> List[str]:
    """
    Generates deterministic, human-readable summary explanations for the risk assessment.
    """
    reasons: List[str] = []

    if base_risk_score is None or base_risk_level is None:
        reasons.append("No scorable requirements found to compute base risk assessment.")
        return reasons

    reasons.append(f"Base risk evaluated as {base_risk_level.value} with a score of {base_risk_score:.2f}/100.")

    if is_provisional or features.pending_count > 0:
        reasons.append(f"Risk assessment remains provisional because {features.pending_count} check(s) are pending.")

    if features.fail_count > 0:
        reasons.append(f"Risk elevated due to {features.fail_count} failed requirement(s).")

    if features.mandatory_failure_count > 0:
        reasons.append(f"{features.mandatory_failure_count} mandatory requirement(s) failed.")

    if features.critical_failure_count > 0:
        reasons.append(
            f"{features.critical_failure_count} critical failure signal(s) recorded in audit telemetry "
            f"(overrides evaluated separately in Part 7D)."
        )

    if features.review_count > 0:
        reasons.append(f"{features.review_count} requirement(s) require human review.")

    if features.integrity_fail_count > 0 or features.cross_document_mismatch_count > 0:
        reasons.append("Cross-document consistency or statutory integrity findings require officer inspection.")

    if not reasons or len(reasons) == 1:
        if base_risk_level == RiskLevel.LOW:
            reasons.append("All applicable requirements satisfied with zero mandatory or integrity concerns.")

    return reasons


def evaluate_base_risk(
    features: RiskFeatures,
    bid_id: uuid.UUID,
    tender_id: uuid.UUID,
    config: Optional[RiskConfig] = None,
    risk_version: int = 1,
) -> RiskAssessment:
    """
    Pure deterministic orchestration of base risk calculation for a bid proposal.
    Calculates indicator contributions, sums bounded base risk score, assigns risk level,
    and formats complete explainable audit payload.
    """
    cfg = config or RiskConfig

    # Safe handling of empty/unscorable bids
    if features.total_rules == 0 or (features.applicable_rules == 0 and features.not_applicable_count == features.total_rules):
        contributions = calculate_risk_contributions(features, config=cfg)
        summary_reasons = ["No scorable requirements found for this tender to compute risk."]
        calculation_details = {
            "formula_version": cfg.RISK_FORMULA_VERSION,
            "model_name": cfg.MODEL_NAME,
            "applicable_rules": 0,
            "total_rules": features.total_rules,
            "raw_sum": "0.0000",
            "clamped_score": None,
        }

        return RiskAssessment(
            bid_id=str(bid_id),
            tender_id=str(tender_id),
            risk_version=risk_version,
            risk_formula_version=cfg.RISK_FORMULA_VERSION,
            base_risk_score=None,
            base_risk_level=None,
            risk_complete=False,
            is_provisional=False,
            human_review_required=features.human_review_required,
            features=features,
            contributions=contributions,
            summary_reasons=summary_reasons,
            calculation_details=calculation_details,
        )

    # Calculate deterministic contributions
    contributions = calculate_risk_contributions(features, config=cfg)

    # Sum contributions
    raw_sum = sum((c.weighted_contribution for c in contributions), Decimal("0.0000"))
    base_risk_score = cfg.clamp_score(raw_sum)
    base_risk_level = cfg.get_risk_level(base_risk_score)

    is_provisional = (features.pending_count > 0 or not features.scoring_complete)
    risk_complete = (features.scoring_complete and features.pending_count == 0)

    summary_reasons = generate_summary_reasons(
        features=features,
        base_risk_score=base_risk_score,
        base_risk_level=base_risk_level,
        is_provisional=is_provisional,
    )

    calculation_details = {
        "formula_version": cfg.RISK_FORMULA_VERSION,
        "model_name": cfg.MODEL_NAME,
        "precision": str(cfg.INTERNAL_PRECISION),
        "rounding_mode": cfg.ROUNDING_MODE,
        "weights": {
            "compliance_deficit": str(cfg.WEIGHT_COMPLIANCE_DEFICIT),
            "rule_failures": str(cfg.WEIGHT_RULE_FAILURES),
            "review_uncertainty": str(cfg.WEIGHT_REVIEW_UNCERTAINTY),
            "pending_uncertainty": str(cfg.WEIGHT_PENDING_UNCERTAINTY),
            "mandatory_failures": str(cfg.WEIGHT_MANDATORY_FAILURES),
            "integrity_concerns": str(cfg.WEIGHT_INTEGRITY_CONCERNS),
        },
        "thresholds": {
            "low_max": str(cfg.THRESHOLD_LOW_MAX),
            "medium_max": str(cfg.THRESHOLD_MEDIUM_MAX),
            "high_max": str(cfg.THRESHOLD_HIGH_MAX),
            "critical_max": str(cfg.THRESHOLD_CRITICAL_MAX),
        },
        "raw_sum": str(raw_sum),
        "base_risk_score": str(base_risk_score),
        "base_risk_level": base_risk_level.value,
        "is_provisional": is_provisional,
        "risk_complete": risk_complete,
    }

    return RiskAssessment(
        bid_id=str(bid_id),
        tender_id=str(tender_id),
        risk_version=risk_version,
        risk_formula_version=cfg.RISK_FORMULA_VERSION,
        base_risk_score=base_risk_score,
        base_risk_level=base_risk_level,
        risk_complete=risk_complete,
        is_provisional=is_provisional,
        human_review_required=features.human_review_required,
        features=features,
        contributions=contributions,
        summary_reasons=summary_reasons,
        calculation_details=calculation_details,
    )
