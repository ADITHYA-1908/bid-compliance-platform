"""
Risk Override Engine for Part 7D: Critical Overrides & Risk Adjustment Logic
Evaluates deterministic risk adjustments, minimum risk floors, and level escalations
on top of Part 7C mathematical base risk assessments without LLM/AI dependency.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from app.db.models.compliance_result import ComplianceStatus
from app.services.risk.risk_config import RiskConfig, RiskLevel
from app.services.risk.risk_models import (
    RiskAssessment,
    RiskFeatures,
    RiskOverride,
)
from app.services.risk.risk_override_config import (
    OverrideSeverity,
    RiskOverrideConfig,
    RiskOverrideType,
)
from app.services.scoring.scoring_models import RuleScoreInput

logger = logging.getLogger(__name__)


def _get_rule_code(r: Any) -> str:
    """Helper to extract rule/requirement code across RuleScoreInput / dict structures."""
    return getattr(r, "requirement_code", None) or getattr(r, "rule_code", None) or ""


class RiskOverrideEngine:
    """
    Pure deterministic risk adjustment and override evaluation engine.
    Executes auditable business rules to determine if minimum risk floors,
    risk increments, or level escalations must be applied to the base risk.
    """

    @classmethod
    def evaluate_risk_overrides(
        cls,
        base_assessment: RiskAssessment,
        rule_inputs: List[RuleScoreInput],
        config: Optional[RiskOverrideConfig] = None,
    ) -> RiskAssessment:
        """
        Takes a Part 7C base risk assessment and evaluates deterministic overrides
        against current compliance findings. Produces a full RiskAssessment containing
        both base and adjusted risk scores/levels with full override audit trail.
        """
        cfg = config or RiskOverrideConfig

        # If base risk is not scorable / empty rules, return base result untouched
        if base_assessment.base_risk_score is None:
            base_assessment.adjusted_risk_score = None
            base_assessment.adjusted_risk_level = None
            base_assessment.override_applied = False
            base_assessment.override_count = 0
            base_assessment.override_formula_version = cfg.OVERRIDE_FORMULA_VERSION
            base_assessment.applied_overrides = []
            return base_assessment

        base_score = base_assessment.base_risk_score
        base_level = base_assessment.base_risk_level

        # Working variables
        working_score = base_score
        provisional_state = base_assessment.is_provisional
        complete_state = base_assessment.risk_complete
        human_review_state = base_assessment.human_review_required

        applied_overrides: List[RiskOverride] = []
        floors: List[Tuple[Decimal, RiskLevel, RiskOverride]] = []
        increments: List[Tuple[Decimal, RiskOverride]] = []
        highest_min_level: Optional[RiskLevel] = None

        # Filter rule categories
        critical_fails = [
            r for r in rule_inputs
            if r.is_critical and r.status == ComplianceStatus.FAIL and r.critical_failure
        ]
        critical_reviews = [
            r for r in rule_inputs
            if r.is_critical and r.status == ComplianceStatus.REVIEW
        ]
        critical_pendings = [
            r for r in rule_inputs
            if r.is_critical and r.status == ComplianceStatus.PENDING
        ]

        # ---------------------------------------------------------------------
        # Rule 1: Confirmed Active Blacklisting Override
        # ---------------------------------------------------------------------
        blacklisting_rule = next(
            (
                r for r in rule_inputs
                if (_get_rule_code(r) == "NOT_BLACKLISTED" or "BLACKLIST" in _get_rule_code(r).upper())
                and r.status == ComplianceStatus.FAIL
                and r.is_critical
            ),
            None,
        )
        if blacklisting_rule:
            code = _get_rule_code(blacklisting_rule) or "NOT_BLACKLISTED"
            override = RiskOverride(
                rule_code=code,
                override_type=RiskOverrideType.RISK_FLOOR,
                trigger="CONFIRMED_ACTIVE_BLACKLISTING",
                source_requirement_id=str(blacklisting_rule.requirement_id) if blacklisting_rule.requirement_id else None,
                risk_floor=cfg.FLOOR_ACTIVE_BLACKLISTING,
                minimum_level=cfg.LEVEL_ACTIVE_BLACKLISTING,
                reason="Adjusted to CRITICAL because an active blacklisting record was confirmed for a tender requirement marked critical.",
                severity=OverrideSeverity.CRITICAL,
            )
            floors.append((cfg.FLOOR_ACTIVE_BLACKLISTING, cfg.LEVEL_ACTIVE_BLACKLISTING, override))

        # ---------------------------------------------------------------------
        # Rule 2: Confirmed Active Debarment Override
        # ---------------------------------------------------------------------
        debarment_rule = next(
            (
                r for r in rule_inputs
                if "DEBAR" in _get_rule_code(r).upper()
                and r.status == ComplianceStatus.FAIL
                and r.is_critical
            ),
            None,
        )
        if debarment_rule:
            code = _get_rule_code(debarment_rule) or "DEBARMENT_CHECK"
            override = RiskOverride(
                rule_code=code,
                override_type=RiskOverrideType.RISK_FLOOR,
                trigger="CONFIRMED_ACTIVE_DEBARMENT",
                source_requirement_id=str(debarment_rule.requirement_id) if debarment_rule.requirement_id else None,
                risk_floor=cfg.FLOOR_ACTIVE_DEBARMENT,
                minimum_level=cfg.LEVEL_ACTIVE_DEBARMENT,
                reason="Adjusted to CRITICAL because an active debarment record was confirmed at the relevant tender date.",
                severity=OverrideSeverity.CRITICAL,
            )
            floors.append((cfg.FLOOR_ACTIVE_DEBARMENT, cfg.LEVEL_ACTIVE_DEBARMENT, override))

        # ---------------------------------------------------------------------
        # Rule 3: Critical Requirement Failures (Single vs Multiple)
        # Note: Blacklisting/debarment rules are distinct; check remaining critical fails
        # ---------------------------------------------------------------------
        general_critical_fails = [
            r for r in critical_fails
            if r != blacklisting_rule and r != debarment_rule
        ]

        if len(general_critical_fails) >= cfg.MULTIPLE_CRITICAL_THRESHOLD:
            # Multiple Critical Failures (>= 2)
            rule_codes = ", ".join(_get_rule_code(r) or "REQ" for r in general_critical_fails[:3])
            override = RiskOverride(
                rule_code=rule_codes,
                override_type=RiskOverrideType.RISK_FLOOR,
                trigger="MULTIPLE_CRITICAL_REQUIREMENT_FAILURES",
                risk_floor=cfg.FLOOR_MULTIPLE_CRITICAL_FAIL,
                minimum_level=cfg.LEVEL_MULTIPLE_CRITICAL_FAIL,
                reason=f"Risk escalated to CRITICAL because {len(general_critical_fails)} critical tender requirements failed (exceeding multi-failure threshold).",
                severity=OverrideSeverity.CRITICAL,
            )
            floors.append((cfg.FLOOR_MULTIPLE_CRITICAL_FAIL, cfg.LEVEL_MULTIPLE_CRITICAL_FAIL, override))
        elif len(general_critical_fails) == 1:
            # Single Critical Failure (e.g. OEM, BIS, Statutory, Financial, etc.)
            crit_item = general_critical_fails[0]
            code = _get_rule_code(crit_item) or "CRITICAL_REQUIREMENT"
            override = RiskOverride(
                rule_code=code,
                override_type=RiskOverrideType.RISK_FLOOR,
                trigger="SINGLE_CRITICAL_REQUIREMENT_FAILURE",
                source_requirement_id=str(crit_item.requirement_id) if crit_item.requirement_id else None,
                risk_floor=cfg.FLOOR_SINGLE_CRITICAL_FAIL,
                minimum_level=cfg.LEVEL_SINGLE_CRITICAL_FAIL,
                reason=f"Risk increased to at least HIGH because critical requirement '{code}' failed.",
                severity=OverrideSeverity.HIGH,
            )
            floors.append((cfg.FLOOR_SINGLE_CRITICAL_FAIL, cfg.LEVEL_SINGLE_CRITICAL_FAIL, override))

        # ---------------------------------------------------------------------
        # Rule 4: Severe Identifier / Structural Identity Mismatches
        # ---------------------------------------------------------------------
        strong_identity_fail = next(
            (
                r for r in rule_inputs
                if (_get_rule_code(r) == "PAN_GST_CONSISTENCY" or "CIN_MATCH" in _get_rule_code(r).upper() or "UDYAM_MATCH" in _get_rule_code(r).upper())
                and r.status == ComplianceStatus.FAIL
                and (r.is_critical or r.critical_failure)
            ),
            None,
        )
        if strong_identity_fail:
            code = _get_rule_code(strong_identity_fail) or "IDENTITY_CONSISTENCY"
            override = RiskOverride(
                rule_code=code,
                override_type=RiskOverrideType.RISK_FLOOR,
                trigger="SEVERE_IDENTITY_STRUCTURE_MISMATCH",
                source_requirement_id=str(strong_identity_fail.requirement_id) if strong_identity_fail.requirement_id else None,
                risk_floor=cfg.FLOOR_STRONG_IDENTITY_MISMATCH,
                minimum_level=cfg.LEVEL_STRONG_IDENTITY_MISMATCH,
                reason="Risk increased to at least HIGH due to verified structural identifier inconsistency across official registrations.",
                severity=OverrideSeverity.HIGH,
            )
            floors.append((cfg.FLOOR_STRONG_IDENTITY_MISMATCH, cfg.LEVEL_STRONG_IDENTITY_MISMATCH, override))

        # ---------------------------------------------------------------------
        # Rule 5: Critical Review Uncertainty Escalation
        # ---------------------------------------------------------------------
        if len(critical_reviews) > 0:
            provisional_state = True
            human_review_state = True
            first_rev = critical_reviews[0]
            code = _get_rule_code(first_rev) or "CRITICAL_REVIEW"
            override = RiskOverride(
                rule_code=code,
                override_type=RiskOverrideType.REVIEW_ESCALATION,
                trigger="UNRESOLVED_CRITICAL_REVIEW",
                source_requirement_id=str(first_rev.requirement_id) if first_rev.requirement_id else None,
                risk_floor=cfg.FLOOR_CRITICAL_REVIEW,
                minimum_level=cfg.LEVEL_CRITICAL_REVIEW,
                reason=f"Risk remains provisional because {len(critical_reviews)} critical requirement(s) require human review verification.",
                severity=OverrideSeverity.WARNING,
            )
            floors.append((cfg.FLOOR_CRITICAL_REVIEW, cfg.LEVEL_CRITICAL_REVIEW, override))

        # ---------------------------------------------------------------------
        # Rule 6: Critical Pending Uncertainty Escalation
        # ---------------------------------------------------------------------
        if len(critical_pendings) > 0:
            provisional_state = True
            complete_state = False
            first_pend = critical_pendings[0]
            code = _get_rule_code(first_pend) or "CRITICAL_PENDING"
            override = RiskOverride(
                rule_code=code,
                override_type=RiskOverrideType.REVIEW_ESCALATION,
                trigger="UNRESOLVED_CRITICAL_PENDING",
                source_requirement_id=str(first_pend.requirement_id) if first_pend.requirement_id else None,
                reason=f"Risk assessment is provisional because {len(critical_pendings)} critical requirement check(s) remain pending resolution.",
                severity=OverrideSeverity.WARNING,
            )
            applied_overrides.append(override)

        # ---------------------------------------------------------------------
        # Deterministic Score & Level Calculation Order:
        # 1. Start with base risk score
        # 2. Apply increments (if any) and clamp [0..100]
        # 3. Apply highest minimum risk floor: max(score, highest_floor)
        # 4. Clamp to [0..100]
        # 5. Recalculate level using centralized 7C thresholds
        # 6. Apply minimum level floor (never downgrade risk)
        # ---------------------------------------------------------------------
        for inc_val, inc_override in increments:
            working_score += inc_val
            applied_overrides.append(inc_override)

        working_score = RiskConfig.clamp_score(working_score)

        if floors:
            # Find the highest floor
            highest_floor_tuple = max(floors, key=lambda item: item[0])
            highest_floor_val = highest_floor_tuple[0]

            for floor_val, min_level, floor_override in floors:
                applied_overrides.append(floor_override)
                if highest_min_level is None or cfg.compare_risk_levels(min_level, highest_min_level) > 0:
                    highest_min_level = min_level

            # Enforce minimum risk floor (never reduce an already higher risk score)
            working_score = max(working_score, highest_floor_val)

        # Final score clamp
        adjusted_score = RiskConfig.clamp_score(working_score)

        # Threshold Level Recalculation
        recalculated_level = RiskConfig.get_risk_level(adjusted_score)

        # Apply minimum level floor if configured
        if highest_min_level is not None:
            adjusted_level = cfg.max_risk_level(recalculated_level, highest_min_level) or recalculated_level
        else:
            adjusted_level = recalculated_level

        # Populate audit history on applied overrides
        for ovr in applied_overrides:
            ovr.previous_score = base_score
            ovr.new_score = adjusted_score
            ovr.previous_level = base_level.value if base_level else None
            ovr.new_level = adjusted_level.value if adjusted_level else None

        # Build updated summary reasons
        override_reasons = [ovr.reason for ovr in applied_overrides if ovr.reason]
        combined_summary = list(base_assessment.summary_reasons)
        for r in override_reasons:
            if r not in combined_summary:
                combined_summary.append(r)

        # Override Applied Flag
        has_override = (
            len(applied_overrides) > 0
            and (
                adjusted_score != base_score
                or adjusted_level != base_level
                or provisional_state != base_assessment.is_provisional
                or human_review_state != base_assessment.human_review_required
            )
        )

        return RiskAssessment(
            bid_id=base_assessment.bid_id,
            tender_id=base_assessment.tender_id,
            risk_version=base_assessment.risk_version,
            risk_formula_version=base_assessment.risk_formula_version,
            override_formula_version=cfg.OVERRIDE_FORMULA_VERSION,
            base_risk_score=base_assessment.base_risk_score,
            base_risk_level=base_assessment.base_risk_level,
            adjusted_risk_score=adjusted_score,
            adjusted_risk_level=adjusted_level,
            override_applied=has_override,
            override_count=len(applied_overrides),
            applied_overrides=applied_overrides,
            risk_complete=complete_state,
            is_provisional=provisional_state,
            human_review_required=human_review_state,
            features=base_assessment.features,
            contributions=base_assessment.contributions,
            summary_reasons=combined_summary,
            calculation_details={
                **base_assessment.calculation_details,
                "override_model": cfg.MODEL_NAME,
                "override_formula_version": cfg.OVERRIDE_FORMULA_VERSION,
                "execution_order": cfg.EXECUTION_ORDER_DESCRIPTION,
                "floors_evaluated": len(floors),
                "increments_evaluated": len(increments),
            },
            calculated_at=base_assessment.calculated_at,
        )
