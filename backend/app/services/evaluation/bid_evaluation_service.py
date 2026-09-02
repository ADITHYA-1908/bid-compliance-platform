"""
Bid Evaluation Service for Part 7F: Final Score, Risk, AI Recommendation Integration
Coordinates the unified, auditable bid evaluation output combining Compliance (Part 6),
Scoring (Part 7A/7B), Risk (Part 7C/7D), and AI Recommendation (Part 7E).
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.bid import Bid
from app.db.models.compliance_result import ComplianceResult
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.schemas.evaluation import (
    BidEvaluationSummaryResponse,
    CriticalFindingItem,
    EvaluationAISection,
    EvaluationComplianceSection,
    EvaluationCriticalSummary,
    EvaluationReviewSummary,
    EvaluationRiskSection,
    EvaluationScoreSection,
)
from app.services.ai.ai_recommendation_service import AIRecommendationService
from app.services.risk_service import calculate_and_save_bid_risk
from app.services.scoring_service import calculate_and_save_bid_score

logger = logging.getLogger(__name__)


def _verify_evaluation_access(db: Session, user: User, bid_id: uuid.UUID) -> Tuple[Bid, Profile]:
    """
    Validates user authorization for unified bid evaluation.
    Allowed: Procurement Officers of the tender organization and Admins.
    Forbidden: Bidders and cross-tenant users.
    """
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

    profile = db.scalars(select(Profile).where(Profile.id == user.profile_id)).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile not found.",
        )

    role = db.scalars(select(Role).where(Role.id == profile.role_id)).first()
    role_name = role.name if role else ""

    if role_name == "ADMIN":
        return bid, profile

    if role_name == "PROCUREMENT_OFFICER":
        if not bid.tender or bid.tender.organization_id != profile.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid not found or access denied.",
            )
        return bid, profile

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Bid evaluation summary is restricted to authorized Procurement Officers.",
    )


class BidEvaluationService:
    """
    Unified evaluation coordinator for Part 7.
    """

    @classmethod
    def get_unified_evaluation(
        cls,
        db: Session,
        user: User,
        bid_id: uuid.UUID,
    ) -> BidEvaluationSummaryResponse:
        """
        Builds the unified bid evaluation summary combining Compliance, Scoring,
        Risk, Overrides, and Grounded AI Recommendations.
        """
        bid, profile = _verify_evaluation_access(db, user, bid_id)

        # 1. Load active compliance results
        compliance_results = db.scalars(
            select(ComplianceResult)
            .where(
                ComplianceResult.bid_id == bid_id,
                ComplianceResult.is_current == True,  # noqa: E712
            )
        ).all()

        # Load requirements map
        req_ids = [cr.tender_requirement_id for cr in compliance_results if cr.tender_requirement_id]
        reqs_map: Dict[uuid.UUID, TenderRequirement] = {}
        if req_ids:
            reqs = db.scalars(select(TenderRequirement).where(TenderRequirement.id.in_(req_ids))).all()
            reqs_map = {r.id: r for r in reqs}

        # 2. Load active Score Snapshot
        score_snap = db.scalars(
            select(BidScoreSnapshot)
            .where(
                BidScoreSnapshot.bid_id == bid_id,
                BidScoreSnapshot.is_current == True,  # noqa: E712
            )
            .order_by(BidScoreSnapshot.created_at.desc())
        ).first()

        # 3. Load active Risk Snapshot
        risk_snap = db.scalars(
            select(BidRiskSnapshot)
            .where(
                BidRiskSnapshot.bid_id == bid_id,
                BidRiskSnapshot.is_current == True,  # noqa: E712
            )
            .order_by(BidRiskSnapshot.created_at.desc())
        ).first()

        # 4. Load latest AI Recommendation Record
        ai_rec = db.scalars(
            select(AIRecommendationRecord)
            .where(AIRecommendationRecord.bid_id == bid_id)
            .order_by(AIRecommendationRecord.created_at.desc())
        ).first()

        # 5. Determine version consistency and component staleness
        latest_comp_ver = max([cr.evaluation_version or 1 for cr in compliance_results], default=1)
        stale_components: List[str] = []

        # Score Staleness
        is_score_stale = False
        if not score_snap or score_snap.is_current is False:
            is_score_stale = True
            stale_components.append("SCORE")
        elif getattr(score_snap, "scoring_version", getattr(score_snap, "score_version", 1)) < latest_comp_ver:
            is_score_stale = True
            stale_components.append("SCORE")

        # Risk Staleness
        is_risk_stale = False
        if not risk_snap or risk_snap.is_current is False or is_score_stale:
            is_risk_stale = True
            stale_components.append("RISK")
        elif score_snap and risk_snap.created_at and score_snap.created_at and risk_snap.created_at < score_snap.created_at:
            is_risk_stale = True
            stale_components.append("RISK")

        # AI Recommendation Staleness
        is_ai_stale = False
        ai_status = "NOT_GENERATED"
        if ai_rec:
            if ai_rec.is_stale or is_score_stale or is_risk_stale:
                is_ai_stale = True
                ai_status = "STALE"
                stale_components.append("AI")
            elif score_snap and ai_rec.score_snapshot_id and ai_rec.score_snapshot_id != score_snap.id:
                is_ai_stale = True
                ai_status = "STALE"
                stale_components.append("AI")
            elif risk_snap and ai_rec.risk_snapshot_id and ai_rec.risk_snapshot_id != risk_snap.id:
                is_ai_stale = True
                ai_status = "STALE"
                stale_components.append("AI")
            else:
                ai_status = "CURRENT"

        # 6. Build Compliance Section
        pass_count = sum(1 for cr in compliance_results if cr.compliance_status == "PASS")
        fail_count = sum(1 for cr in compliance_results if cr.compliance_status == "FAIL")
        review_count = sum(1 for cr in compliance_results if cr.compliance_status == "REVIEW")
        pending_count = sum(1 for cr in compliance_results if cr.compliance_status == "PENDING")
        na_count = sum(1 for cr in compliance_results if cr.compliance_status == "NOT_APPLICABLE")
        mand_fail_count = sum(1 for cr in compliance_results if cr.compliance_status == "FAIL" and cr.is_mandatory)
        crit_fail_count = sum(1 for cr in compliance_results if cr.compliance_status == "FAIL" and getattr(cr, "is_critical", False))

        comp_section = EvaluationComplianceSection(
            total_requirements=len(compliance_results),
            pass_count=pass_count,
            fail_count=fail_count,
            review_count=review_count,
            pending_count=pending_count,
            not_applicable_count=na_count,
            mandatory_failures_count=mand_fail_count,
            critical_failures_count=crit_fail_count,
            evaluation_complete=(pending_count == 0 and len(compliance_results) > 0),
            evaluation_version=latest_comp_ver,
        )

        # 7. Build Score Section
        if score_snap:
            earned_w = float(score_snap.earned_weight) if score_snap.earned_weight is not None else 0.0
            elig_w = float(score_snap.eligible_weight) if score_snap.eligible_weight is not None else 0.0
            overall_s = float(score_snap.overall_score) if score_snap.overall_score is not None else None
            score_type = "FINAL" if score_snap.scoring_complete else "PROVISIONAL"
            score_ver = getattr(score_snap, "scoring_version", getattr(score_snap, "score_version", 1))

            score_section = EvaluationScoreSection(
                overall_compliance_score=overall_s,
                score_type=score_type,
                scoring_complete=score_snap.scoring_complete,
                earned_weight=earned_w,
                eligible_weight=elig_w,
                category_scores=score_snap.category_scores or {},
                formula_version=score_snap.scoring_formula_version or "v1.0",
                is_stale=is_score_stale,
                snapshot_id=score_snap.id,
                scoring_version=score_ver,
            )
        else:
            score_section = EvaluationScoreSection(
                is_stale=True,
                score_type="PROVISIONAL",
                scoring_complete=False,
            )

        # 8. Build Risk Section
        if risk_snap:
            b_score = float(risk_snap.base_risk_score) if risk_snap.base_risk_score is not None else None
            a_score = float(risk_snap.adjusted_risk_score) if risk_snap.adjusted_risk_score is not None else b_score
            a_level = risk_snap.adjusted_risk_level or risk_snap.base_risk_level
            reasons = list(risk_snap.summary_reasons or [])

            risk_section = EvaluationRiskSection(
                base_risk_score=b_score,
                base_risk_level=risk_snap.base_risk_level,
                adjusted_risk_score=a_score,
                adjusted_risk_level=a_level,
                override_applied=risk_snap.override_applied or False,
                applied_overrides=risk_snap.applied_overrides or [],
                risk_complete=risk_snap.risk_complete,
                is_provisional=risk_snap.is_provisional or not risk_snap.risk_complete,
                risk_formula_version=risk_snap.risk_formula_version or "v1.0",
                override_formula_version=risk_snap.override_formula_version or "v1.0",
                is_stale=is_risk_stale,
                snapshot_id=risk_snap.id,
                risk_version=risk_snap.risk_version or 1,
                summary_reasons=reasons,
            )
        else:
            risk_section = EvaluationRiskSection(
                is_stale=True,
                risk_complete=False,
                is_provisional=True,
            )

        # 9. Build AI Section
        if ai_rec:
            ai_section = EvaluationAISection(
                status=ai_status,
                recommendation=ai_rec.recommendation,
                recommendation_reason=ai_rec.recommendation_reason,
                summary=ai_rec.summary,
                strengths=ai_rec.strengths or [],
                concerns=ai_rec.concerns or [],
                review_items=ai_rec.review_items or [],
                evidence_refs=ai_rec.evidence_refs or [],
                limitations=ai_rec.limitations or [],
                confidence_label=ai_rec.confidence_label,
                model_provider=ai_rec.model_provider,
                model_name=ai_rec.model_name,
                prompt_version=ai_rec.prompt_version,
                guardrail_applied=ai_rec.guardrail_applied or False,
                guardrail_reason=ai_rec.guardrail_reason,
                recommendation_id=ai_rec.id,
                is_stale=is_ai_stale,
            )
        else:
            ai_section = EvaluationAISection(
                status="NOT_GENERATED",
                is_stale=False,
            )

        # 10. Build Critical Findings Summary
        critical_findings: List[CriticalFindingItem] = []
        for cr in compliance_results:
            req = reqs_map.get(cr.tender_requirement_id) if cr.tender_requirement_id else None
            is_crit = getattr(cr, "is_critical", False) or (req.is_critical if req else False)
            if is_crit and cr.compliance_status == "FAIL":
                override_match = None
                if risk_snap and risk_snap.applied_overrides:
                    for ov in risk_snap.applied_overrides:
                        if req and ov.get("rule_code") == req.code:
                            override_match = f"{ov.get('override_type')} (Floor: {ov.get('risk_floor')})"
                            break

                critical_findings.append(
                    CriticalFindingItem(
                        requirement_code=req.code if req else "CRIT-REQ",
                        requirement_name=req.name if req else "Critical Requirement",
                        category=req.category if req else "GENERAL",
                        compliance_status=cr.compliance_status,
                        is_mandatory=cr.is_mandatory,
                        is_critical=True,
                        risk_override=override_match,
                        finding_reason=cr.reason or "Critical requirement verification failed.",
                    )
                )

        crit_summary = EvaluationCriticalSummary(
            critical_failure_present=(len(critical_findings) > 0),
            critical_failure_count=crit_fail_count,
            critical_review_count=sum(1 for cr in compliance_results if cr.compliance_status == "REVIEW" and getattr(cr, "is_critical", False)),
            critical_override_applied=risk_section.override_applied,
            critical_findings=critical_findings,
        )

        # 11. Build Review Summary
        review_reasons: List[str] = []
        for cr in compliance_results:
            if cr.compliance_status == "REVIEW":
                req = reqs_map.get(cr.tender_requirement_id)
                code_str = f"[{req.code}] " if req else ""
                review_reasons.append(f"{code_str}{cr.reason or 'Requires officer review'}")
            elif cr.compliance_status == "PENDING":
                req = reqs_map.get(cr.tender_requirement_id)
                code_str = f"[{req.code}] " if req else ""
                review_reasons.append(f"{code_str}Verification check pending completion")

        review_summary = EvaluationReviewSummary(
            human_review_required=bool(
                review_count > 0
                or pending_count > 0
                or crit_fail_count > 0
                or risk_section.override_applied
                or (ai_rec is not None and ai_rec.recommendation in ["REVIEW_REQUIRED", "DO_NOT_PROCEED_WITHOUT_REVIEW"])
            ),
            total_review_items=review_count + pending_count,
            review_reasons=review_reasons,
            is_provisional=bool(pending_count > 0 or risk_section.is_provisional),
        )

        # 12. Determine Evaluation Completeness (Deterministic: Compliance + Score + Risk)
        eval_complete = (
            comp_section.evaluation_complete
            and score_section.scoring_complete
            and risk_section.risk_complete
            and not is_score_stale
            and not is_risk_stale
        )

        return BidEvaluationSummaryResponse(
            bid_id=bid.id,
            tender_id=bid.tender_id,
            bid_number=bid.bid_number,
            tender_number=bid.tender.tender_number if bid.tender else "N/A",
            tender_title=bid.tender.title if bid.tender else "N/A",
            bidder_name=bid.bidder_organization.name if bid.bidder_organization else "N/A",
            bid_status=bid.status,
            compliance=comp_section,
            score=score_section,
            risk=risk_section,
            ai_recommendation=ai_section,
            critical_summary=crit_summary,
            review_summary=review_summary,
            evaluation_complete=eval_complete,
            human_review_required=review_summary.human_review_required,
            stale_components=stale_components,
            final_decision_status="NOT_MADE",
            generated_at=datetime.utcnow(),
        )

    @classmethod
    def refresh_bid_evaluation(
        cls,
        db: Session,
        user: User,
        bid_id: uuid.UUID,
        refresh_ai: bool = False,
    ) -> BidEvaluationSummaryResponse:
        """
        Refreshes deterministic Score and Risk evaluations.
        If refresh_ai is True, also re-indexes knowledge and regenerates AI recommendation.
        """
        bid, profile = _verify_evaluation_access(db, user, bid_id)

        # 1. Deterministic Recalculations (cheap & authoritative)
        calculate_and_save_bid_score(db, user, bid_id)
        calculate_and_save_bid_risk(db, user, bid_id)

        # 2. Optional AI Regeneration (only when explicitly requested)
        if refresh_ai:
            try:
                AIRecommendationService.generate_bid_recommendation(
                    db=db,
                    user=user,
                    bid_id=bid_id,
                    force_refresh=True,
                )
            except Exception as e:
                logger.error(f"AI recommendation refresh failed during unified refresh: {e}", exc_info=True)
                # Failure of LLM does not prevent deterministic evaluation refresh

        return cls.get_unified_evaluation(db, user, bid_id)
