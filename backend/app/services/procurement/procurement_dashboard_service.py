"""
Procurement Dashboard Service for Part 8A: Procurement Evaluation Dashboard Foundation
Provides high-performance aggregation and retrieval of procurement officer dashboard summaries,
tender evaluation progress statistics, and paginated bid evaluation listings with search, filter,
and sorting capabilities.
"""

import math
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.bid import Bid
from app.db.models.bid_shortlist import BidShortlist
from app.db.models.bid_decision import BidDecision
from app.db.models.compliance_result import ComplianceResult
from app.db.models.organization import Organization
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender import Tender
from app.db.models.user import User
from app.schemas.procurement_dashboard import (
    BidEvaluationListItem,
    ProcurementDashboardCounts,
    ProcurementDashboardSummaryResponse,
    TenderBidEvaluationsListResponse,
    TenderEvaluationOverviewItem,
)


class ProcurementDashboardService:
    """Service handling Procurement Officer dashboard and tender evaluation overview operations."""

    @staticmethod
    def _verify_procurement_officer_org(user: User) -> uuid.UUID:
        """Verifies officer profile and extracts procuring organization ID."""
        if not user.profile or not user.profile.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no associated procuring organization.",
            )
        return user.profile.organization_id

    @classmethod
    def get_dashboard_summary(
        cls,
        db: Session,
        user: User,
    ) -> ProcurementDashboardSummaryResponse:
        """
        Aggregates procurement officer home dashboard metrics and active tender evaluation statuses.
        """
        org_id = cls._verify_procurement_officer_org(user)

        # 1. Fetch all active tenders owned by this organization
        tenders = db.scalars(
            select(Tender)
            .where(
                Tender.organization_id == org_id,
                Tender.is_active == True,
            )
            .order_by(Tender.created_at.desc())
        ).all()

        tender_ids = [t.id for t in tenders]

        if not tender_ids:
            return ProcurementDashboardSummaryResponse(
                counts=ProcurementDashboardCounts(),
                tenders=[],
            )

        # 2. Fetch all submitted bids for these tenders
        submitted_bids = db.scalars(
            select(Bid)
            .where(
                Bid.tender_id.in_(tender_ids),
                Bid.status == "SUBMITTED",
                Bid.is_active == True,
            )
        ).all()

        bid_ids = [b.id for b in submitted_bids]
        bids_by_tender: Dict[uuid.UUID, List[Bid]] = {t_id: [] for t_id in tender_ids}
        for b in submitted_bids:
            bids_by_tender[b.tender_id].append(b)

        # 3. Batch-fetch active evaluation snapshots for these submitted bids
        scores_by_bid: Dict[uuid.UUID, BidScoreSnapshot] = {}
        risks_by_bid: Dict[uuid.UUID, BidRiskSnapshot] = {}
        ai_by_bid: Dict[uuid.UUID, AIRecommendationRecord] = {}

        if bid_ids:
            score_snaps = db.scalars(
                select(BidScoreSnapshot).where(
                    BidScoreSnapshot.bid_id.in_(bid_ids),
                    BidScoreSnapshot.is_current == True,
                )
            ).all()
            for s in score_snaps:
                scores_by_bid[s.bid_id] = s

            risk_snaps = db.scalars(
                select(BidRiskSnapshot).where(
                    BidRiskSnapshot.bid_id.in_(bid_ids),
                    BidRiskSnapshot.is_current == True,
                )
            ).all()
            for r in risk_snaps:
                risks_by_bid[r.bid_id] = r

            ai_recs = db.scalars(
                select(AIRecommendationRecord)
                .where(AIRecommendationRecord.bid_id.in_(bid_ids))
                .order_by(AIRecommendationRecord.created_at.desc())
            ).all()
            for a in ai_recs:
                if a.bid_id not in ai_by_bid:
                    ai_by_bid[a.bid_id] = a

        # 4. Compute per-tender statistics and overall counts
        tender_overview_items: List[TenderEvaluationOverviewItem] = []
        
        overall_active_tenders = len(tenders)
        overall_open_tenders = 0
        overall_closed_under_eval = 0
        overall_submitted_bids = len(submitted_bids)
        overall_review_required = 0
        overall_critical_risk = 0
        overall_pending_evals = 0
        overall_eval_completed = 0

        for t in tenders:
            t_status = t.status.upper() if t.status else "DRAFT"
            if t_status == "OPEN":
                overall_open_tenders += 1
            elif t_status in ("CLOSED", "UNDER_EVALUATION", "EVALUATION"):
                overall_closed_under_eval += 1

            t_bids = bids_by_tender.get(t.id, [])
            total_bids = len(t_bids)
            evaluated_count = 0
            pending_count = 0
            review_req_count = 0
            critical_risk_count = 0

            for b in t_bids:
                s_snap = scores_by_bid.get(b.id)
                r_snap = risks_by_bid.get(b.id)
                
                # Check deterministic evaluation completeness
                is_score_done = bool(s_snap and s_snap.scoring_complete)
                is_risk_done = bool(r_snap and r_snap.risk_complete)
                is_complete = is_score_done and is_risk_done

                if is_complete:
                    evaluated_count += 1
                    overall_eval_completed += 1
                else:
                    pending_count += 1
                    overall_pending_evals += 1

                # Check critical risk level
                if r_snap and r_snap.adjusted_risk_level == "CRITICAL":
                    critical_risk_count += 1
                    overall_critical_risk += 1

                # Check human review requirement
                has_review = False
                if s_snap and s_snap.is_provisional:
                    has_review = True
                if r_snap and (r_snap.is_provisional or r_snap.override_applied or r_snap.adjusted_risk_level == "CRITICAL"):
                    has_review = True
                if has_review:
                    review_req_count += 1
                    overall_review_required += 1

            progress_pct = round((evaluated_count / total_bids * 100.0), 1) if total_bids > 0 else 0.0

            tender_overview_items.append(
                TenderEvaluationOverviewItem(
                    tender_id=t.id,
                    tender_number=t.tender_number,
                    title=t.title,
                    category=t.category,
                    department=t.department,
                    status=t.status,
                    estimated_value=t.estimated_value,
                    currency=t.currency,
                    submission_end_date=t.submission_end_date,
                    total_submitted_bids=total_bids,
                    evaluated_bids=evaluated_count,
                    pending_bids=pending_count,
                    review_required_bids=review_req_count,
                    critical_risk_bids=critical_risk_count,
                    evaluation_progress_percentage=progress_pct,
                    created_at=t.created_at,
                )
            )

        counts = ProcurementDashboardCounts(
            active_tenders=overall_active_tenders,
            open_tenders=overall_open_tenders,
            closed_under_evaluation=overall_closed_under_eval,
            total_submitted_bids=overall_submitted_bids,
            bids_requiring_review=overall_review_required,
            critical_risk_bids=overall_critical_risk,
            pending_evaluations=overall_pending_evals,
            evaluation_completed_bids=overall_eval_completed,
        )

        return ProcurementDashboardSummaryResponse(
            counts=counts,
            tenders=tender_overview_items,
        )

    @classmethod
    def get_tender_bid_evaluations(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        risk_level: Optional[str] = None,
        review_required: Optional[bool] = None,
        critical_only: Optional[bool] = None,
        recommendation: Optional[str] = None,
        shortlisted_only: Optional[bool] = None,
        sort_by: str = "submitted_at",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 10,
    ) -> TenderBidEvaluationsListResponse:
        """
        Retrieves the paginated, filtered, and sorted evaluation matrix for all submitted bids of a tender.
        """
        org_id = cls._verify_procurement_officer_org(user)

        # 1. Verify Tender existence and ownership
        tender = db.scalar(
            select(Tender)
            .options(joinedload(Tender.organization))
            .where(
                Tender.id == tender_id,
                Tender.is_active == True,
            )
        )

        if not tender or tender.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tender not found or access denied.",
            )

        proc_org_name = tender.organization.name if tender.organization else "Procurement Entity"

        # 2. Query submitted bids for this tender with joined bidder organization
        stmt = (
            select(Bid)
            .options(joinedload(Bid.bidder_organization))
            .where(
                Bid.tender_id == tender.id,
                Bid.status == "SUBMITTED",
                Bid.is_active == True,
            )
        )

        # Optional search on Bid Number, Legal Name, Trade Name, GSTIN, PAN
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.join(Bid.bidder_organization).where(
                or_(
                    func.lower(Bid.bid_number).like(term),
                    func.lower(Organization.name).like(term),
                    func.lower(Organization.trade_name).like(term),
                    func.lower(Organization.gstin).like(term),
                    func.lower(Organization.pan_number).like(term),
                )
            )

        all_submitted_bids = db.scalars(stmt).all()
        bid_ids = [b.id for b in all_submitted_bids]

        # 3. Batch-fetch all evaluation records for these bids
        scores_by_bid: Dict[uuid.UUID, BidScoreSnapshot] = {}
        risks_by_bid: Dict[uuid.UUID, BidRiskSnapshot] = {}
        ai_by_bid: Dict[uuid.UUID, AIRecommendationRecord] = {}
        shortlists_by_bid: Dict[uuid.UUID, BidShortlist] = {}
        compliance_by_bid: Dict[uuid.UUID, List[ComplianceResult]] = {b_id: [] for b_id in bid_ids}

        if bid_ids:
            score_snaps = db.scalars(
                select(BidScoreSnapshot).where(
                    BidScoreSnapshot.bid_id.in_(bid_ids),
                    BidScoreSnapshot.is_current == True,
                )
            ).all()
            for s in score_snaps:
                scores_by_bid[s.bid_id] = s

            risk_snaps = db.scalars(
                select(BidRiskSnapshot).where(
                    BidRiskSnapshot.bid_id.in_(bid_ids),
                    BidRiskSnapshot.is_current == True,
                )
            ).all()
            for r in risk_snaps:
                risks_by_bid[r.bid_id] = r

            ai_recs = db.scalars(
                select(AIRecommendationRecord)
                .where(AIRecommendationRecord.bid_id.in_(bid_ids))
                .order_by(AIRecommendationRecord.created_at.desc())
            ).all()
            for a in ai_recs:
                if a.bid_id not in ai_by_bid:
                    ai_by_bid[a.bid_id] = a

            shortlists = db.scalars(
                select(BidShortlist).where(
                    BidShortlist.tender_id == tender.id,
                    BidShortlist.bid_id.in_(bid_ids),
                )
            ).all()
            for sl in shortlists:
                shortlists_by_bid[sl.bid_id] = sl

            decisions_by_bid: Dict[uuid.UUID, BidDecision] = {}
            decisions = db.scalars(
                select(BidDecision).where(
                    BidDecision.tender_id == tender.id,
                    BidDecision.bid_id.in_(bid_ids),
                    BidDecision.is_current == True,  # noqa: E712
                )
            ).all()
            for d in decisions:
                decisions_by_bid[d.bid_id] = d

            comp_results = db.scalars(
                select(ComplianceResult).where(
                    ComplianceResult.bid_id.in_(bid_ids),
                    ComplianceResult.is_current == True,
                )
            ).all()
            for c in comp_results:
                compliance_by_bid[c.bid_id].append(c)

        # 4. Map bids to BidEvaluationListItem and derive statuses
        evaluated_bids_count = 0
        transformed_items: List[BidEvaluationListItem] = []

        for b in all_submitted_bids:
            s_snap = scores_by_bid.get(b.id)
            r_snap = risks_by_bid.get(b.id)
            ai_rec = ai_by_bid.get(b.id)
            sl_rec = shortlists_by_bid.get(b.id)
            is_shortlisted = bool(sl_rec and sl_rec.is_shortlisted)
            comps = compliance_by_bid.get(b.id, [])

            # Counts from compliance results
            mand_fails = sum(
                1 for c in comps
                if (getattr(c, "compliance_status", None) or getattr(c, "status", None)) == "FAIL" and c.is_mandatory
            )
            crit_fails = sum(
                1 for c in comps
                if ((getattr(c, "compliance_status", None) or getattr(c, "status", None)) == "FAIL" and c.is_critical)
                or getattr(c, "critical_failure", False)
            )
            rev_items = sum(
                1 for c in comps
                if (getattr(c, "compliance_status", None) or getattr(c, "status", None)) == "REVIEW"
            )
            pending_items = sum(
                1 for c in comps
                if (getattr(c, "compliance_status", None) or getattr(c, "status", None)) == "PENDING"
            )

            # Supplement from score snapshot if available
            if s_snap:
                mand_fails = max(mand_fails, s_snap.mandatory_failures_count or 0)
                crit_fails = max(crit_fails, s_snap.critical_failures_count or 0)

            # Risk and overrides
            override_applied = r_snap.override_applied if r_snap else False
            has_crit_findings = crit_fails > 0 or override_applied
            crit_findings_count = crit_fails + (1 if override_applied else 0)

            # Completeness & Human Review
            is_score_done = bool(s_snap and s_snap.scoring_complete)
            is_risk_done = bool(r_snap and r_snap.risk_complete)
            is_complete = is_score_done and is_risk_done and pending_items == 0
            if is_complete:
                evaluated_bids_count += 1

            human_review_required = (
                rev_items > 0
                or (s_snap.is_provisional if s_snap else False)
                or (r_snap.is_provisional if r_snap else False)
                or has_crit_findings
            )

            # Staleness detection
            stale_components: List[str] = []
            if s_snap and getattr(s_snap, "is_stale", False):
                stale_components.append("SCORE")
            if r_snap and getattr(r_snap, "is_stale", False):
                stale_components.append("RISK")
            if ai_rec and getattr(ai_rec, "is_stale", False):
                stale_components.append("AI")

            # Derived evaluation status
            if not s_snap and not r_snap:
                eval_status = "NOT_STARTED"
            elif not is_complete or (s_snap and s_snap.is_provisional) or (r_snap and r_snap.is_provisional):
                eval_status = "PROVISIONAL"
            elif human_review_required:
                eval_status = "REVIEW_REQUIRED"
            elif "AI" in stale_components or (ai_rec and getattr(ai_rec, "is_stale", False)):
                eval_status = "AI_STALE"
            else:
                eval_status = "EVALUATION_COMPLETE"

            bidder_org = b.bidder_organization
            legal_name = bidder_org.name if bidder_org else "Unknown Bidder"
            trade_name = bidder_org.trade_name if bidder_org else None

            if not ai_rec:
                ai_status_val = "NOT_GENERATED"
            elif getattr(ai_rec, "is_stale", False) or "AI" in stale_components:
                ai_status_val = "STALE"
            else:
                ai_status_val = "CURRENT"

            item = BidEvaluationListItem(
                bid_id=b.id,
                tender_id=b.tender_id,
                bid_number=b.bid_number,
                bidder_organization_id=b.bidder_organization_id,
                bidder_legal_name=legal_name,
                trade_name=trade_name,
                submitted_at=b.submitted_at,
                quoted_amount=b.quoted_amount,
                currency=b.currency,
                is_shortlisted=is_shortlisted,
                compliance_score=s_snap.overall_score if s_snap else None,
                is_score_provisional=s_snap.is_provisional if s_snap else False,
                base_risk_score=r_snap.base_risk_score if r_snap else None,
                base_risk_level=r_snap.base_risk_level if r_snap else None,
                adjusted_risk_score=r_snap.adjusted_risk_score if r_snap else None,
                adjusted_risk_level=r_snap.adjusted_risk_level if r_snap else None,
                is_risk_provisional=r_snap.is_provisional if r_snap else False,
                mandatory_failures_count=mand_fails,
                critical_failures_count=crit_fails,
                review_items_count=rev_items,
                has_critical_findings=has_crit_findings,
                critical_findings_count=crit_findings_count,
                human_review_required=human_review_required,
                ai_recommendation=ai_rec.recommendation if ai_rec else None,
                ai_status=ai_status_val,
                evaluation_status=eval_status,
                is_evaluation_complete=is_complete,
                stale_components=stale_components,
                human_decision_status=decisions_by_bid[b.id].decision if b.id in decisions_by_bid else "NOT_DECIDED",
            )
            transformed_items.append(item)

        # 5. Apply filters
        filtered_items = transformed_items

        if status_filter and status_filter.strip():
            sf = status_filter.strip().upper()
            filtered_items = [i for i in filtered_items if i.evaluation_status.upper() == sf]

        if risk_level and risk_level.strip():
            rl = risk_level.strip().upper()
            filtered_items = [i for i in filtered_items if (i.adjusted_risk_level or "").upper() == rl]

        if review_required is not None:
            filtered_items = [i for i in filtered_items if i.human_review_required == review_required]

        if critical_only:
            filtered_items = [i for i in filtered_items if i.has_critical_findings]

        if recommendation and recommendation.strip():
            rec_str = recommendation.strip().upper()
            filtered_items = [i for i in filtered_items if (i.ai_recommendation or "").upper() == rec_str]

        if shortlisted_only:
            filtered_items = [i for i in filtered_items if i.is_shortlisted]

        # 6. Apply sorting
        reverse_sort = (sort_dir.lower() == "desc")

        if sort_by in ("score", "compliance_score"):
            filtered_items.sort(
                key=lambda x: (x.compliance_score is not None, x.compliance_score or 0.0),
                reverse=reverse_sort,
            )
        elif sort_by in ("risk", "adjusted_risk_score"):
            filtered_items.sort(
                key=lambda x: (x.adjusted_risk_score is not None, x.adjusted_risk_score or 0.0),
                reverse=reverse_sort,
            )
        elif sort_by in ("review_count", "review_items_count"):
            filtered_items.sort(
                key=lambda x: x.review_items_count,
                reverse=reverse_sort,
            )
        elif sort_by in ("critical_count", "critical_failures_count"):
            filtered_items.sort(
                key=lambda x: x.critical_failures_count,
                reverse=reverse_sort,
            )
        else:  # default submitted_at
            filtered_items.sort(
                key=lambda x: (x.submitted_at is not None, x.submitted_at or datetime.min),
                reverse=reverse_sort,
            )

        # 7. Apply pagination
        total_count = len(filtered_items)
        page_size = max(1, page_size)
        total_pages = max(1, math.ceil(total_count / page_size))
        page = min(max(1, page), total_pages) if total_count > 0 else 1

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = filtered_items[start_idx:end_idx]

        return TenderBidEvaluationsListResponse(
            tender_id=tender.id,
            tender_number=tender.tender_number,
            tender_title=tender.title,
            tender_status=tender.status,
            procurement_organization_name=proc_org_name,
            submission_end_date=tender.submission_end_date,
            total_submitted_bids=len(all_submitted_bids),
            evaluated_bids=evaluated_bids_count,
            bids=paginated_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
