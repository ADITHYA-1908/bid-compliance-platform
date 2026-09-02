"""
Bid Comparison Service for Part 8B: Bid Comparison & Shortlisting View
Provides high-performance, single-query batch aggregation for side-by-side bid comparisons,
category performance matrices, requirement determination breakdowns, difference detection,
and human-controlled shortlisting workflows.
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.bid import Bid
from app.db.models.bid_shortlist import BidShortlist
from app.db.models.bid_decision import BidDecision
from app.db.models.compliance_result import ComplianceResult
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User

from app.schemas.bid_comparison import (
    BidComparisonItem,
    BidComparisonResponse,
    CategoryComparisonRow,
    CategoryScoreComparisonValue,
    ComparisonHighlights,
    CriticalFindingComparisonItem,
    RequirementBidResultItem,
    RequirementComparisonRow,
    ShortlistRecordResponse,
)
from app.db.models.audit_event import AuditActorSource, AuditEntityType, AuditEventType
from app.schemas.audit import RecordAuditEventDTO
from app.services.audit.audit_service import AuditService

logger = logging.getLogger(__name__)

# Standard Category Order for display
CATEGORY_ORDER = [
    "STATUTORY",
    "FINANCIAL",
    "EXPERIENCE",
    "TECHNICAL",
    "OEM",
    "LOCAL_CONTENT",
    "BIS",
    "DOCUMENTS",
    "INTEGRITY",
    "OTHER",
]

CATEGORY_DISPLAY_NAMES: Dict[str, str] = {
    "STATUTORY": "Statutory & Legal Credentials",
    "FINANCIAL": "Financial Capacity & Turnover",
    "EXPERIENCE": "Past Experience & Work Orders",
    "TECHNICAL": "Technical & Quality Specifications",
    "OEM": "OEM Authorization & Manufacturer Certifications",
    "LOCAL_CONTENT": "Make in India (MII) & Local Content",
    "BIS": "BIS / Industry Standard Certifications",
    "DOCUMENTS": "Mandatory Submission Documents",
    "INTEGRITY": "Integrity, Debarment & Vigilance",
    "OTHER": "General Requirements",
}


class BidComparisonService:
    """Service orchestrating multi-bid comparisons and shortlist management for a tender."""

    @staticmethod
    def _verify_procurement_access(db: Session, user: User, tender_id: uuid.UUID) -> Tuple[Tender, Profile]:
        """
        Validates user authorization for the target Tender.
        Allowed: Procurement Officers of the tender's organization and Admins.
        Forbidden: Bidders and cross-tenant officers.
        """
        stmt = (
            select(Tender)
            .options(joinedload(Tender.organization))
            .where(
                Tender.id == tender_id,
                Tender.is_active == True,
            )
        )
        tender = db.execute(stmt).scalar_one_or_none()
        if not tender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tender not found or access denied.",
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
            return tender, profile

        if role_name == "PROCUREMENT_OFFICER":
            if tender.organization_id != profile.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tender not found or access denied.",
                )
            return tender, profile

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Procurement Officer or Admin role required.",
        )

    @classmethod
    def compare_tender_bids(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        bid_ids: List[uuid.UUID],
    ) -> BidComparisonResponse:
        """
        Executes a high-efficiency comparative evaluation across 2 to 5 submitted bids
        belonging strictly to the same tender.
        """
        tender, profile = cls._verify_procurement_access(db, user, tender_id)

        # 1. Validate Selection Bounds
        if not bid_ids or len(bid_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 bids must be selected for comparison.",
            )

        # Deduplicate while preserving order
        dedup_bid_ids: List[uuid.UUID] = []
        for b_id in bid_ids:
            if b_id not in dedup_bid_ids:
                dedup_bid_ids.append(b_id)

        if len(dedup_bid_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 distinct bids must be selected for comparison.",
            )

        if len(dedup_bid_ids) > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A maximum of 5 bids can be compared simultaneously.",
            )

        # 2. Batch-Fetch Target Bids with Tenant & Scoping Validation
        stmt_bids = (
            select(Bid)
            .options(joinedload(Bid.bidder_organization))
            .where(
                Bid.id.in_(dedup_bid_ids),
                Bid.is_active == True,
            )
        )
        bids = db.execute(stmt_bids).scalars().all()
        bids_map = {b.id: b for b in bids}

        # Check all requested bids exist
        for b_id in dedup_bid_ids:
            if b_id not in bids_map:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Bid '{b_id}' not found or inactive.",
                )

        # Enforce Same-Tender Scoping Constraint (Reject mixed-tender requests)
        for b in bids:
            if b.tender_id != tender_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bid '{b.bid_number}' does not belong to tender '{tender.tender_number}'. All compared bids must belong to the same tender.",
                )
            if b.status != "SUBMITTED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bid '{b.bid_number}' has status '{b.status}'. Only submitted bids can be compared.",
                )

        # 3. Batch-Fetch Tender Requirements
        reqs = db.scalars(
            select(TenderRequirement)
            .where(
                TenderRequirement.tender_id == tender_id,
                TenderRequirement.is_active == True,
            )
            .order_by(TenderRequirement.display_order.asc(), TenderRequirement.created_at.asc())
        ).all()
        reqs_map = {r.id: r for r in reqs}

        # 4. Batch-Fetch Active Compliance Results
        compliance_results = db.scalars(
            select(ComplianceResult)
            .where(
                ComplianceResult.bid_id.in_(dedup_bid_ids),
                ComplianceResult.is_current == True,
            )
        ).all()

        comps_by_bid: Dict[uuid.UUID, Dict[uuid.UUID, ComplianceResult]] = {
            b_id: {} for b_id in dedup_bid_ids
        }
        for cr in compliance_results:
            if cr.tender_requirement_id:
                comps_by_bid[cr.bid_id][cr.tender_requirement_id] = cr

        # 5. Batch-Fetch Active Score Snapshots
        score_snaps = db.scalars(
            select(BidScoreSnapshot)
            .where(
                BidScoreSnapshot.bid_id.in_(dedup_bid_ids),
                BidScoreSnapshot.is_current == True,
            )
        ).all()
        scores_map = {s.bid_id: s for s in score_snaps}

        # 6. Batch-Fetch Active Risk Snapshots
        risk_snaps = db.scalars(
            select(BidRiskSnapshot)
            .where(
                BidRiskSnapshot.bid_id.in_(dedup_bid_ids),
                BidRiskSnapshot.is_current == True,
            )
        ).all()
        risks_map = {r.bid_id: r for r in risk_snaps}

        # 7. Batch-Fetch Latest AI Recommendations
        ai_records = db.scalars(
            select(AIRecommendationRecord)
            .where(
                AIRecommendationRecord.bid_id.in_(dedup_bid_ids),
            )
            .order_by(AIRecommendationRecord.created_at.desc())
        ).all()
        ai_map: Dict[uuid.UUID, AIRecommendationRecord] = {}
        for rec in ai_records:
            if rec.bid_id not in ai_map:
                ai_map[rec.bid_id] = rec

        # 8. Batch-Fetch Shortlist Records
        shortlists = db.scalars(
            select(BidShortlist)
            .where(
                BidShortlist.tender_id == tender_id,
                BidShortlist.bid_id.in_(dedup_bid_ids),
            )
        ).all()
        shortlists_map = {s.bid_id: s for s in shortlists}

        # 9. Batch-Fetch Current Human Decisions (Part 8D)
        decisions = db.scalars(
            select(BidDecision)
            .where(
                BidDecision.tender_id == tender_id,
                BidDecision.bid_id.in_(dedup_bid_ids),
                BidDecision.is_current == True,  # noqa: E712
            )
        ).all()
        decisions_map = {d.bid_id: d for d in decisions}

        # 10. Extract Categories present in this Tender
        present_categories: List[str] = []
        for cat in CATEGORY_ORDER:
            if any(r.category == cat for r in reqs):
                present_categories.append(cat)
        # Any extra categories not in standard list
        for r in reqs:
            if r.category and r.category not in present_categories:
                present_categories.append(r.category)

        # 10. Build Per-Bid Comparison Items
        comparison_bids: List[BidComparisonItem] = []

        for b_id in dedup_bid_ids:
            bid = bids_map[b_id]
            s_snap = scores_map.get(b_id)
            r_snap = risks_map.get(b_id)
            ai_rec = ai_map.get(b_id)
            shortlist = shortlists_map.get(b_id)
            bid_comps = comps_by_bid.get(b_id, {})

            # Shortlist Info
            is_shortlisted = bool(shortlist and shortlist.is_shortlisted)
            shortlist_reason = shortlist.reason if shortlist else None
            shortlisted_at = shortlist.updated_at if shortlist else None

            # Compliance Counts & Lists
            mand_failures: List[str] = []
            crit_findings: List[CriticalFindingComparisonItem] = []
            review_items: List[str] = []
            pending_items: List[str] = []

            for r in reqs:
                cr = bid_comps.get(r.id)
                status_val = cr.compliance_status if cr else "NOT_EVALUATED"

                if status_val == "FAIL":
                    if r.is_mandatory:
                        mand_failures.append(f"[{r.code}] {r.name}")
                    if r.is_critical:
                        # Check matching override description
                        override_match = None
                        if r_snap and r_snap.applied_overrides:
                            for ov in r_snap.applied_overrides:
                                if ov.get("rule_code") == r.code:
                                    override_match = f"{ov.get('override_type')} (Floor: {ov.get('risk_floor')})"
                                    break

                        crit_findings.append(
                            CriticalFindingComparisonItem(
                                requirement_code=r.code,
                                requirement_name=r.name,
                                category=r.category,
                                compliance_status="FAIL",
                                is_mandatory=r.is_mandatory,
                                is_critical=True,
                                risk_override=override_match,
                                finding_reason=cr.reason if cr and cr.reason else "Critical tender clause failed verification.",
                            )
                        )
                elif status_val == "REVIEW":
                    review_items.append(f"[{r.code}] {cr.reason if cr and cr.reason else 'Human review required'}")
                elif status_val == "PENDING" or status_val == "NOT_EVALUATED":
                    pending_items.append(f"[{r.code}] {r.name} verification pending")

            # Check if active blacklisting override applied without explicit rule failure
            if r_snap and r_snap.override_applied and r_snap.applied_overrides:
                for ov in r_snap.applied_overrides:
                    ov_code = ov.get("rule_code")
                    if not any(cf.requirement_code == ov_code for cf in crit_findings):
                        crit_findings.append(
                            CriticalFindingComparisonItem(
                                requirement_code=ov_code or "OVERRIDE",
                                requirement_name=ov.get("override_type") or "Critical Integrity Floor",
                                category="INTEGRITY",
                                compliance_status="FAIL",
                                is_mandatory=True,
                                is_critical=True,
                                risk_override=f"{ov.get('override_type')} (Floor: {ov.get('risk_floor')})",
                                finding_reason=ov.get("reason") or "Critical risk floor adjustment applied.",
                            )
                        )

            # Completeness & Status Derivation
            is_score_done = bool(s_snap and s_snap.scoring_complete)
            is_risk_done = bool(r_snap and r_snap.risk_complete)
            is_eval_complete = is_score_done and is_risk_done and len(pending_items) == 0

            # Staleness
            stale_components: List[str] = []
            if s_snap and getattr(s_snap, "is_stale", False):
                stale_components.append("SCORE")
            if r_snap and getattr(r_snap, "is_stale", False):
                stale_components.append("RISK")
            if ai_rec and getattr(ai_rec, "is_stale", False):
                stale_components.append("AI")

            human_review_required = (
                len(review_items) > 0
                or (s_snap.is_provisional if s_snap else False)
                or (r_snap.is_provisional if r_snap else False)
                or len(crit_findings) > 0
            )

            if not s_snap and not r_snap:
                eval_status = "NOT_STARTED"
            elif not is_eval_complete or (s_snap and s_snap.is_provisional) or (r_snap and r_snap.is_provisional):
                eval_status = "PROVISIONAL"
            elif human_review_required:
                eval_status = "REVIEW_REQUIRED"
            elif "AI" in stale_components or (ai_rec and getattr(ai_rec, "is_stale", False)):
                eval_status = "AI_STALE"
            else:
                eval_status = "EVALUATION_COMPLETE"

            # AI Status derivation
            if not ai_rec:
                ai_status_val = "NOT_GENERATED"
            elif getattr(ai_rec, "is_stale", False) or "AI" in stale_components:
                ai_status_val = "STALE"
            else:
                ai_status_val = "CURRENT"

            # Build Category Scores map for this bid
            bid_cat_scores: Dict[str, CategoryScoreComparisonValue] = {}
            raw_category_scores = s_snap.category_scores if s_snap and s_snap.category_scores else {}

            for cat in present_categories:
                cat_reqs = [r for r in reqs if r.category == cat]
                cat_data = raw_category_scores.get(cat, {}) if isinstance(raw_category_scores, dict) else {}

                total_cat_rules = len(cat_reqs)
                passed_cat = sum(1 for r in cat_reqs if (comps_by_bid[b_id].get(r.id) and comps_by_bid[b_id][r.id].compliance_status == "PASS"))
                failed_cat = sum(1 for r in cat_reqs if (comps_by_bid[b_id].get(r.id) and comps_by_bid[b_id][r.id].compliance_status == "FAIL"))
                review_cat = sum(1 for r in cat_reqs if (comps_by_bid[b_id].get(r.id) and comps_by_bid[b_id][r.id].compliance_status == "REVIEW"))
                pending_cat = sum(1 for r in cat_reqs if (comps_by_bid[b_id].get(r.id) and comps_by_bid[b_id][r.id].compliance_status == "PENDING"))

                earned_w = float(cat_data.get("earned_weight", 0.0))
                elig_w = float(cat_data.get("eligible_weight", 0.0))
                raw_score = cat_data.get("raw_score")
                if raw_score is None:
                    raw_score = cat_data.get("score")
                score_val = float(raw_score) if raw_score is not None else None
                is_na = bool(elig_w == 0.0 or score_val is None)

                bid_cat_scores[cat] = CategoryScoreComparisonValue(
                    category=cat,
                    score=score_val if not is_na else None,
                    earned_weight=earned_w,
                    eligible_weight=elig_w,
                    is_na=is_na,
                    total_rules=total_cat_rules,
                    passed_rules=passed_cat,
                    failed_rules=failed_cat,
                    review_rules=review_cat,
                    pending_rules=pending_cat,
                )

            bidder_org = bid.bidder_organization
            legal_name = bidder_org.name if bidder_org else "Unknown Bidder"
            trade_name = bidder_org.trade_name if bidder_org else None

            item = BidComparisonItem(
                bid_id=bid.id,
                bid_number=bid.bid_number,
                bidder_organization_id=bid.bidder_organization_id,
                bidder_legal_name=legal_name,
                trade_name=trade_name,
                submitted_at=bid.submitted_at,
                quoted_amount=bid.quoted_amount,
                currency=bid.currency,
                is_shortlisted=is_shortlisted,
                shortlist_reason=shortlist_reason,
                shortlisted_at=shortlisted_at,
                overall_score=float(s_snap.overall_score) if s_snap and s_snap.overall_score is not None else None,
                is_score_provisional=s_snap.is_provisional if s_snap else False,
                scoring_complete=is_score_done,
                earned_weight=float(s_snap.earned_weight) if s_snap and s_snap.earned_weight is not None else 0.0,
                eligible_weight=float(s_snap.eligible_weight) if s_snap and s_snap.eligible_weight is not None else 0.0,
                base_risk_score=float(r_snap.base_risk_score) if r_snap and r_snap.base_risk_score is not None else None,
                base_risk_level=r_snap.base_risk_level if r_snap else None,
                adjusted_risk_score=float(r_snap.adjusted_risk_score) if r_snap and r_snap.adjusted_risk_score is not None else None,
                adjusted_risk_level=r_snap.adjusted_risk_level if r_snap else (r_snap.base_risk_level if r_snap else None),
                override_applied=r_snap.override_applied if r_snap else False,
                applied_overrides=r_snap.applied_overrides if r_snap and r_snap.applied_overrides else [],
                is_risk_provisional=r_snap.is_provisional if r_snap else False,
                risk_complete=is_risk_done,
                mandatory_failure_count=len(mand_failures),
                mandatory_failures=mand_failures,
                critical_failure_count=len(crit_findings),
                critical_findings=crit_findings,
                review_count=len(review_items),
                review_items=review_items,
                pending_count=len(pending_items),
                pending_items=pending_items,
                ai_recommendation=ai_rec.recommendation if ai_rec else None,
                ai_status=ai_status_val,
                ai_summary=ai_rec.summary if ai_rec else None,
                ai_confidence=ai_rec.confidence_label if ai_rec else None,
                evaluation_status=eval_status,
                is_evaluation_complete=is_eval_complete,
                stale_components=stale_components,
                category_scores=bid_cat_scores,
                human_decision_status=decisions_map[b_id].decision if b_id in decisions_map else "NOT_DECIDED",
            )
            comparison_bids.append(item)

        # 11. Build Category Comparison Rows
        category_rows: List[CategoryComparisonRow] = []
        for cat in present_categories:
            bid_scores_map: Dict[str, CategoryScoreComparisonValue] = {}
            score_values: List[Optional[float]] = []

            for c_bid in comparison_bids:
                val = c_bid.category_scores.get(cat)
                if val:
                    bid_scores_map[str(c_bid.bid_id)] = val
                    score_values.append(val.score if not val.is_na else None)

            # Check if all bids have exact same score/N/A
            all_match = len(score_values) > 0 and all(s == score_values[0] for s in score_values)

            category_rows.append(
                CategoryComparisonRow(
                    category_code=cat,
                    display_name=CATEGORY_DISPLAY_NAMES.get(cat, cat.replace("_", " ").title()),
                    bid_scores=bid_scores_map,
                    all_match=all_match,
                )
            )

        # 12. Build Detailed Requirement Comparison Rows
        requirement_rows: List[RequirementComparisonRow] = []

        for req in reqs:
            bid_results_map: Dict[str, RequirementBidResultItem] = {}
            status_list: List[str] = []
            actual_list: List[Any] = []
            has_fail = False
            has_rev = False

            for c_bid in comparison_bids:
                cr = comps_by_bid[c_bid.bid_id].get(req.id)
                if cr:
                    c_status = cr.compliance_status
                    act_val = cr.actual_value
                    exp_val = cr.expected_value
                    op = cr.operator
                    reason = cr.reason
                    evidence = cr.evidence
                    src_ids = cr.source_verification_ids or []

                    summary_str = None
                    if isinstance(evidence, dict):
                        summary_str = evidence.get("summary") or evidence.get("details") or str(evidence)
                    elif evidence:
                        summary_str = str(evidence)

                    res_item = RequirementBidResultItem(
                        bid_id=c_bid.bid_id,
                        compliance_status=c_status,
                        actual_value=act_val,
                        expected_value=exp_val,
                        operator=op,
                        reason=reason,
                        evidence_summary=summary_str,
                        has_evidence=bool(evidence or src_ids),
                        source_verification_ids=[str(i) for i in src_ids],
                    )
                else:
                    c_status = "NOT_EVALUATED"
                    res_item = RequirementBidResultItem(
                        bid_id=c_bid.bid_id,
                        compliance_status="NOT_EVALUATED",
                        actual_value=None,
                        expected_value=req.expected_value,
                        operator=req.operator,
                        reason="Evaluation result not generated.",
                        evidence_summary=None,
                        has_evidence=False,
                        source_verification_ids=[],
                    )

                bid_results_map[str(c_bid.bid_id)] = res_item
                status_list.append(c_status)
                actual_list.append(str(res_item.actual_value))

                if c_status == "FAIL":
                    has_fail = True
                elif c_status in ("REVIEW", "PENDING"):
                    has_rev = True

            # Difference calculation: All match if identical status and actual value
            all_match = (
                len(status_list) > 0
                and all(st == status_list[0] for st in status_list)
                and all(act == actual_list[0] for act in actual_list)
            )

            has_crit_issue = bool(req.is_critical and (has_fail or has_rev))

            requirement_rows.append(
                RequirementComparisonRow(
                    requirement_id=req.id,
                    code=req.code,
                    name=req.name,
                    category=req.category,
                    requirement_type=req.requirement_type,
                    is_mandatory=req.is_mandatory,
                    is_critical=req.is_critical,
                    weight=float(req.weight) if req.weight is not None else 10.0,
                    expected_value=req.expected_value,
                    operator=req.operator,
                    bid_results=bid_results_map,
                    all_match=all_match,
                    has_failure=has_fail,
                    has_review=has_rev,
                    has_critical_issue=has_crit_issue,
                )
            )

        # 13. Determine Highlights (Informational only)
        best_score_bid = max(
            [b for b in comparison_bids if b.overall_score is not None],
            key=lambda x: x.overall_score,
            default=None,
        )
        lowest_risk_bid = min(
            [b for b in comparison_bids if b.adjusted_risk_score is not None],
            key=lambda x: x.adjusted_risk_score,
            default=None,
        )
        lowest_price_bid = min(
            [b for b in comparison_bids if b.quoted_amount is not None],
            key=lambda x: x.quoted_amount,
            default=None,
        )

        highlights = ComparisonHighlights(
            highest_compliance_score_bid_id=best_score_bid.bid_id if best_score_bid else None,
            lowest_risk_score_bid_id=lowest_risk_bid.bid_id if lowest_risk_bid else None,
            lowest_quoted_amount_bid_id=lowest_price_bid.bid_id if lowest_price_bid else None,
        )

        proc_org_name = tender.organization.name if tender.organization else "Procuring Entity"

        logger.info(
            f"[Part 8B] Generated comparison for tender '{tender.tender_number}' with {len(comparison_bids)} bids."
        )

        return BidComparisonResponse(
            tender_id=tender.id,
            tender_number=tender.tender_number,
            tender_title=tender.title,
            tender_status=tender.status,
            procurement_organization_name=proc_org_name,
            submission_end_date=tender.submission_end_date,
            total_compared_bids=len(comparison_bids),
            bids=comparison_bids,
            categories=category_rows,
            requirements=requirement_rows,
            highlights=highlights,
            generated_at=datetime.now(timezone.utc),
        )

    @classmethod
    def add_to_shortlist(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> ShortlistRecordResponse:
        """
        Marks a submitted bid as SHORTLISTED for further review by the authorized Procurement Officer.
        This is a human-controlled decision support action and does NOT constitute qualification or award.
        """
        tender, profile = cls._verify_procurement_access(db, user, tender_id)

        bid = db.scalars(
            select(Bid).where(
                Bid.id == bid_id,
                Bid.tender_id == tender_id,
                Bid.is_active == True,
            )
        ).first()
        if not bid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid not found for this tender.",
            )

        # Upsert shortlist record
        shortlist = db.scalars(
            select(BidShortlist).where(
                BidShortlist.tender_id == tender_id,
                BidShortlist.bid_id == bid_id,
            )
        ).first()

        now_utc = datetime.now(timezone.utc)
        if not shortlist:
            shortlist = BidShortlist(
                tender_id=tender_id,
                bid_id=bid_id,
                is_shortlisted=True,
                reason=reason,
                shortlisted_by_id=user.id,
                created_at=now_utc,
                updated_at=now_utc,
            )
            db.add(shortlist)
        else:
            shortlist.is_shortlisted = True
            if reason is not None:
                shortlist.reason = reason
            shortlist.shortlisted_by_id = user.id
            shortlist.updated_at = now_utc

        db.flush()

        # Record Audit Event
        AuditService.record_event(
            db,
            RecordAuditEventDTO(
                organization_id=tender.organization_id,
                tender_id=tender.id,
                bid_id=bid.id,
                actor_user_id=user.id,
                actor_profile_id=profile.id if profile else None,
                actor_name=profile.full_name if profile else user.email,
                actor_role=profile.role.name if (profile and profile.role) else "PROCUREMENT_OFFICER",
                actor_source=AuditActorSource.HUMAN,
                event_type=AuditEventType.BID_SHORTLISTED,
                entity_type=AuditEntityType.BID_SHORTLIST,
                entity_id=shortlist.id,
                action="SHORTLIST_ADD",
                summary=f"Bid '{bid.bid_number}' added to shortlist for tender '{tender.tender_number}'.",
                metadata={
                    "reason": reason,
                    "bid_number": bid.bid_number,
                    "tender_number": tender.tender_number,
                },
            ),
        )

        db.commit()
        db.refresh(shortlist)

        logger.info(
            f"[Part 8B] Bid '{bid.bid_number}' shortlisted by officer '{user.email}' on tender '{tender.tender_number}'."
        )

        return ShortlistRecordResponse(
            id=shortlist.id,
            tender_id=shortlist.tender_id,
            bid_id=shortlist.bid_id,
            is_shortlisted=shortlist.is_shortlisted,
            reason=shortlist.reason,
            shortlisted_by_id=shortlist.shortlisted_by_id,
            shortlisted_by_name=user.profile.full_name if user.profile else user.email,
            created_at=shortlist.created_at,
            updated_at=shortlist.updated_at,
        )

    @classmethod
    def remove_from_shortlist(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> ShortlistRecordResponse:
        """
        Removes a bid from the shortlist.
        """
        tender, profile = cls._verify_procurement_access(db, user, tender_id)

        bid = db.scalars(
            select(Bid).where(
                Bid.id == bid_id,
                Bid.tender_id == tender_id,
                Bid.is_active == True,
            )
        ).first()
        if not bid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid not found for this tender.",
            )

        shortlist = db.scalars(
            select(BidShortlist).where(
                BidShortlist.tender_id == tender_id,
                BidShortlist.bid_id == bid_id,
            )
        ).first()

        now_utc = datetime.now(timezone.utc)
        if not shortlist:
            shortlist = BidShortlist(
                tender_id=tender_id,
                bid_id=bid_id,
                is_shortlisted=False,
                reason=reason,
                shortlisted_by_id=user.id,
                created_at=now_utc,
                updated_at=now_utc,
            )
            db.add(shortlist)
        else:
            shortlist.is_shortlisted = False
            if reason is not None:
                shortlist.reason = reason
            shortlist.shortlisted_by_id = user.id
            shortlist.updated_at = now_utc

        db.flush()

        # Record Audit Event
        AuditService.record_event(
            db,
            RecordAuditEventDTO(
                organization_id=tender.organization_id,
                tender_id=tender.id,
                bid_id=bid.id,
                actor_user_id=user.id,
                actor_profile_id=profile.id if profile else None,
                actor_name=profile.full_name if profile else user.email,
                actor_role=profile.role.name if (profile and profile.role) else "PROCUREMENT_OFFICER",
                actor_source=AuditActorSource.HUMAN,
                event_type=AuditEventType.BID_REMOVED_FROM_SHORTLIST,
                entity_type=AuditEntityType.BID_SHORTLIST,
                entity_id=shortlist.id,
                action="SHORTLIST_REMOVE",
                summary=f"Bid '{bid.bid_number}' removed from shortlist for tender '{tender.tender_number}'.",
                metadata={
                    "reason": reason,
                    "bid_number": bid.bid_number,
                    "tender_number": tender.tender_number,
                },
            ),
        )

        db.commit()
        db.refresh(shortlist)

        logger.info(
            f"[Part 8B] Bid '{bid.bid_number}' removed from shortlist by officer '{user.email}'."
        )

        return ShortlistRecordResponse(
            id=shortlist.id,
            tender_id=shortlist.tender_id,
            bid_id=shortlist.bid_id,
            is_shortlisted=shortlist.is_shortlisted,
            reason=shortlist.reason,
            shortlisted_by_id=shortlist.shortlisted_by_id,
            shortlisted_by_name=user.profile.full_name if user.profile else user.email,
            created_at=shortlist.created_at,
            updated_at=shortlist.updated_at,
        )

    @classmethod
    def get_tender_shortlists(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
    ) -> List[ShortlistRecordResponse]:
        """
        Retrieves all active shortlist records for a tender.
        """
        tender, profile = cls._verify_procurement_access(db, user, tender_id)

        shortlists = db.scalars(
            select(BidShortlist)
            .where(
                BidShortlist.tender_id == tender_id,
                BidShortlist.is_shortlisted == True,
            )
            .order_by(BidShortlist.updated_at.desc())
        ).all()

        results: List[ShortlistRecordResponse] = []
        for s in shortlists:
            results.append(
                ShortlistRecordResponse(
                    id=s.id,
                    tender_id=s.tender_id,
                    bid_id=s.bid_id,
                    is_shortlisted=s.is_shortlisted,
                    reason=s.reason,
                    shortlisted_by_id=s.shortlisted_by_id,
                    shortlisted_by_name=s.shortlisted_by.profile.full_name if s.shortlisted_by and s.shortlisted_by.profile else None,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
            )
        return results
