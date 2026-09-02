"""
Procurement Report Service
Generates structured Tender Evaluation Summaries, Bid Compliance Dossiers,
and downloadable vector PDF reports for procurement committees and audit bodies.
"""

import io
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

import pymupdf  # PyMuPDF for vector PDF rendering

from app.db.models.audit_event import AuditEvent
from app.db.models.bid import Bid
from app.db.models.bid_decision import BidDecision
from app.db.models.bid_shortlist import BidShortlist
from app.db.models.compliance_result import ComplianceResult
from app.db.models.human_review import HumanReviewItem, ReviewStatus
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender import Tender
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.schemas.procurement_report import (
    BidEvaluationReportResponse,
    ReportAISection,
    ReportAuditEventSummaryItem,
    ReportBidInfo,
    ReportBidderInfo,
    ReportComplianceSection,
    ReportDecisionHistoryItem,
    ReportDefectItem,
    ReportFinalDecisionSection,
    ReportHumanReviewItem,
    ReportRiskSection,
    ReportScoreSection,
    ReportTenderInfo,
    TenderReportResponse,
    TenderSummaryBidItem,
)
from app.services.audit.audit_service import AuditService, EVENT_LABEL_MAP
from app.services.evaluation.bid_evaluation_service import BidEvaluationService
from app.services.procurement.bid_decision_service import BidDecisionService

logger = logging.getLogger(__name__)


def _verify_report_access(
    db: Session,
    user: User,
    tender_id: uuid.UUID,
    bid_id: Optional[uuid.UUID] = None,
) -> Tuple[Tender, Optional[Bid], Profile, Role]:
    """
    Enforces multi-tenant authorization for procurement report generation.
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
            detail="Procurement reports are restricted to authorized Procurement Officers and Admins.",
        )

    tender = db.scalars(
        select(Tender).options(joinedload(Tender.organization)).where(Tender.id == tender_id)
    ).first()
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found or access denied.",
        )

    if role.name != "ADMIN" and tender.organization_id != profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found or access denied.",
        )

    bid = None
    if bid_id:
        bid = db.scalars(
            select(Bid)
            .options(
                joinedload(Bid.tender),
                joinedload(Bid.bidder_organization),
            )
            .where(Bid.id == bid_id, Bid.tender_id == tender_id)
        ).first()
        if not bid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid not found or access denied.",
            )

    return tender, bid, profile, role


class ProcurementReportService:
    """
    Service generating structured reports and PDF exports from deterministic facts.
    """

    @classmethod
    def get_tender_summary_report(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
    ) -> TenderReportResponse:
        """
        Builds a comprehensive Tender Evaluation Summary Report DTO.
        """
        tender, _, profile, _ = _verify_report_access(db, user, tender_id)

        # 1. Fetch all bids for tender
        bids = db.scalars(
            select(Bid)
            .options(joinedload(Bid.bidder_organization))
            .where(Bid.tender_id == tender_id, Bid.status == "SUBMITTED")
            .order_by(Bid.submitted_at.asc())
        ).all()

        bid_ids = [b.id for b in bids]

        # 2. Batch-fetch scores, risks, decisions, shortlists, reviews
        scores_map: Dict[uuid.UUID, BidScoreSnapshot] = {}
        if bid_ids:
            score_snaps = db.scalars(
                select(BidScoreSnapshot).where(
                    BidScoreSnapshot.bid_id.in_(bid_ids),
                    BidScoreSnapshot.is_current == True,  # noqa: E712
                )
            ).all()
            for s in score_snaps:
                scores_map[s.bid_id] = s

        risks_map: Dict[uuid.UUID, BidRiskSnapshot] = {}
        if bid_ids:
            risk_snaps = db.scalars(
                select(BidRiskSnapshot).where(
                    BidRiskSnapshot.bid_id.in_(bid_ids),
                    BidRiskSnapshot.is_current == True,  # noqa: E712
                )
            ).all()
            for r in risk_snaps:
                risks_map[r.bid_id] = r

        decisions_map: Dict[uuid.UUID, BidDecision] = {}
        if bid_ids:
            decisions = db.scalars(
                select(BidDecision).where(
                    BidDecision.bid_id.in_(bid_ids),
                    BidDecision.is_current == True,  # noqa: E712
                )
            ).all()
            for d in decisions:
                decisions_map[d.bid_id] = d

        shortlists_set = set()
        if bid_ids:
            shortlist_rows = db.scalars(
                select(BidShortlist.bid_id).where(
                    BidShortlist.tender_id == tender_id,
                    BidShortlist.is_shortlisted == True,  # noqa: E712
                )
            ).all()
            shortlists_set = set(shortlist_rows)

        # 3. Aggregate metrics
        total_submitted = len(bids)
        total_evaluated = 0
        total_qualified = 0
        total_disqualified = 0
        total_under_review = 0
        total_not_decided = 0
        total_shortlisted = len(shortlists_set)

        risk_dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        score_values: List[float] = []
        total_critical_defects = 0
        total_open_reviews = 0

        bids_items: List[TenderSummaryBidItem] = []

        for b in bids:
            score_snap = scores_map.get(b.id)
            risk_snap = risks_map.get(b.id)
            dec = decisions_map.get(b.id)
            is_sh = b.id in shortlists_set

            score_val = float(score_snap.overall_score) if score_snap and score_snap.overall_score is not None else None
            if score_val is not None:
                score_values.append(score_val)

            risk_lvl = risk_snap.adjusted_risk_level if risk_snap else "LOW"
            if risk_lvl in risk_dist:
                risk_dist[risk_lvl] += 1

            if score_snap and score_snap.scoring_complete:
                total_evaluated += 1

            dec_status = dec.decision if dec else "NOT_DECIDED"
            if dec_status == "QUALIFIED":
                total_qualified += 1
            elif dec_status == "DISQUALIFIED":
                total_disqualified += 1
            elif dec_status == "UNDER_REVIEW":
                total_under_review += 1
            else:
                total_not_decided += 1

            crit_count = score_snap.critical_failures_count if score_snap else 0
            total_critical_defects += crit_count

            # Count open reviews for bid
            open_rev_count = db.scalar(
                select(func.count(HumanReviewItem.id)).where(
                    HumanReviewItem.bid_id == b.id,
                    HumanReviewItem.is_active == True,  # noqa: E712
                    HumanReviewItem.status.in_([ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.ESCALATED]),
                )
            ) or 0
            total_open_reviews += open_rev_count

            bids_items.append(
                TenderSummaryBidItem(
                    bid_id=b.id,
                    bid_number=b.bid_number,
                    bidder_name=b.bidder_organization.name if b.bidder_organization else "Unknown Bidder",
                    quoted_amount=float(b.quoted_amount) if b.quoted_amount is not None else None,
                    compliance_score=score_val,
                    adjusted_risk_level=risk_lvl,
                    human_decision_status=dec_status,
                    is_shortlisted=is_sh,
                    critical_defects_count=crit_count,
                    open_reviews_count=open_rev_count,
                )
            )

        avg_score = round(sum(score_values) / len(score_values), 2) if score_values else None

        return TenderReportResponse(
            tender=ReportTenderInfo(
                tender_id=tender.id,
                tender_number=tender.tender_number,
                title=tender.title,
                status=tender.status,
                organization_name=tender.organization.name if tender.organization else "Procurement Entity",
                category=tender.category,
                procurement_type=tender.procurement_type,
                currency=tender.currency,
                estimated_value=float(tender.estimated_value) if tender.estimated_value is not None else None,
                published_at=tender.publish_date,
                submission_end_date=tender.submission_end_date,
            ),
            total_bids_submitted=total_submitted,
            total_bids_evaluated=total_evaluated,
            total_qualified=total_qualified,
            total_disqualified=total_disqualified,
            total_under_review=total_under_review,
            total_not_decided=total_not_decided,
            total_shortlisted=total_shortlisted,
            risk_distribution=risk_dist,
            average_compliance_score=avg_score,
            total_critical_defects=total_critical_defects,
            total_open_reviews=total_open_reviews,
            bids=bids_items,
            generated_at=datetime.now(timezone.utc),
            generated_by=profile.full_name or "Procurement Officer",
        )

    @classmethod
    def get_bid_evaluation_report(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
    ) -> BidEvaluationReportResponse:
        """
        Builds a comprehensive Bid Evaluation Dossier without mutating evaluations or running LLMs.
        """
        tender, bid, profile, _ = _verify_report_access(db, user, tender_id, bid_id)

        # 1. Fetch Unified Evaluation
        eval_summary = BidEvaluationService.get_unified_evaluation(db, user, bid_id)
        comp = eval_summary.compliance
        score = eval_summary.score
        risk = eval_summary.risk
        ai = eval_summary.ai_recommendation

        # 2. Fetch Shortlist state
        shortlist_row = db.scalars(
            select(BidShortlist).where(
                BidShortlist.bid_id == bid_id,
                BidShortlist.is_shortlisted == True,  # noqa: E712
            )
        ).first()

        # 3. Fetch Current Decision & History
        current_decision = BidDecisionService.get_current_decision(db, user, tender_id, bid_id)
        raw_history = BidDecisionService.get_decision_history(db, user, tender_id, bid_id)
        decision_history = [
            ReportDecisionHistoryItem(
                decision_version=h.decision_version,
                decision=h.decision.value,
                reason=h.reason,
                decided_by_name=h.decided_by_name,
                decided_at=h.decided_at,
                is_current=h.is_current,
                superseded_at=h.superseded_at,
            )
            for h in raw_history
        ]

        # 4. Fetch Human Review Items
        review_rows = db.scalars(
            select(HumanReviewItem)
            .options(joinedload(HumanReviewItem.resolved_by_profile), joinedload(HumanReviewItem.notes))
            .where(HumanReviewItem.bid_id == bid_id, HumanReviewItem.is_active == True)  # noqa: E712
            .order_by(HumanReviewItem.created_at.desc())
        ).all()

        human_reviews = [
            ReportHumanReviewItem(
                id=r.id,
                review_type=r.review_type,
                severity=r.severity,
                status=r.status,
                resolution=r.resolution,
                reason=r.resolution_reason,
                resolved_by_name=r.resolved_by_profile.full_name if r.resolved_by_profile else None,
                resolved_at=r.resolved_at,
                notes_count=len(r.notes),
            )
            for r in review_rows
        ]

        # 5. Fetch Mandatory Failures & Critical Findings from raw results
        comp_results = db.scalars(
            select(ComplianceResult)
            .options(joinedload(ComplianceResult.tender_requirement))
            .where(ComplianceResult.bid_id == bid_id, ComplianceResult.is_current == True)  # noqa: E712
        ).all()

        mandatory_failures: List[ReportDefectItem] = []
        critical_findings: List[ReportDefectItem] = []

        for cr in comp_results:
            req = cr.tender_requirement
            item = ReportDefectItem(
                requirement_code=req.code if req else "REQ_CODE",
                requirement_name=req.name if req else "Requirement",
                category=req.category if req else "GENERAL",
                compliance_status=cr.compliance_status,
                is_mandatory=cr.is_mandatory,
                is_critical=cr.is_critical,
                reason=cr.reason,
            )
            if cr.is_mandatory and cr.compliance_status == "FAIL":
                mandatory_failures.append(item)
            if cr.is_critical and (cr.compliance_status == "FAIL" or cr.critical_failure):
                critical_findings.append(item)

        # 6. Check for Mock / Sandbox Verifications
        verif_records = db.scalars(
            select(VerificationRecord).where(VerificationRecord.bid_id == bid_id)
        ).all()
        has_mock = any(
            v.source_type == "MOCK"
            or "mock" in (v.source_name or "").lower()
            or "sandbox" in (v.source_name or "").lower()
            for v in verif_records
        )
        mock_disclaimer = (
            "NOTICE: One or more external verification registries were queried in MOCK / SANDBOX mode for "
            "development demonstration and testing purposes. Results do not represent live government API calls."
            if has_mock
            else None
        )

        # 7. Collect Staleness Warnings
        stale_warnings: List[str] = []
        if score.is_stale or "SCORE" in eval_summary.stale_components:
            stale_warnings.append("Compliance Score calculation is stale relative to latest requirement inputs.")
        if risk.is_stale or "RISK" in eval_summary.stale_components:
            stale_warnings.append("Risk assessment is stale. Re-evaluation is recommended.")
        if ai and (ai.is_stale or "AI" in eval_summary.stale_components):
            stale_warnings.append("AI Recommendation synthesis is stale and may not reflect recent review resolutions.")
        if current_decision.is_stale:
            stale_warnings.append(f"Current Human Decision is flagged STALE: {current_decision.stale_reason}")

        # 8. Fetch Key Audit Timeline
        timeline_events = AuditService.get_bid_timeline(db, user, tender_id, bid_id)
        audit_summary = [
            ReportAuditEventSummaryItem(
                event_type=e.event_type,
                event_label=e.event_label,
                action=e.action,
                actor_name=e.actor.name or e.actor.source,
                actor_source=e.actor.source,
                summary=e.summary,
                created_at=e.created_at,
            )
            for e in timeline_events
        ]

        # 9. Build Sections
        bidder_org = bid.bidder_organization

        return BidEvaluationReportResponse(
            tender=ReportTenderInfo(
                tender_id=tender.id,
                tender_number=tender.tender_number,
                title=tender.title,
                status=tender.status,
                organization_name=tender.organization.name if tender.organization else "Procurement Entity",
                category=tender.category,
                procurement_type=tender.procurement_type,
                currency=tender.currency,
                estimated_value=float(tender.estimated_value) if tender.estimated_value is not None else None,
                published_at=tender.publish_date,
                submission_end_date=tender.submission_end_date,
            ),
            bidder=ReportBidderInfo(
                organization_id=bidder_org.id if bidder_org else uuid.uuid4(),
                name=bidder_org.name if bidder_org else "Unknown Bidder",
                pan_number=bidder_org.pan_number if bidder_org else None,
                gstin=bidder_org.gstin if bidder_org else None,
                udyam_number=bidder_org.udyam_number if bidder_org else None,
                business_type=(bidder_org.organization_type or bidder_org.business_category) if bidder_org else None,
                state=bidder_org.state if bidder_org else None,
                city=bidder_org.city if bidder_org else None,
            ),
            bid=ReportBidInfo(
                bid_id=bid.id,
                bid_number=bid.bid_number,
                status=bid.status,
                submitted_at=bid.submitted_at,
                quoted_amount=float(bid.quoted_amount) if bid.quoted_amount is not None else None,
                currency=bid.currency,
                is_shortlisted=shortlist_row is not None,
                shortlist_reason=shortlist_row.reason if shortlist_row else None,
            ),
            compliance=ReportComplianceSection(
                evaluation_complete=comp.evaluation_complete,
                evaluation_version=comp.evaluation_version,
                total_requirements=comp.total_requirements,
                passed_count=comp.pass_count,
                failed_count=comp.fail_count,
                review_count=comp.review_count,
                pending_count=comp.pending_count,
                not_applicable_count=comp.not_applicable_count,
                mandatory_failures_count=comp.mandatory_failures_count,
                critical_failures_count=comp.critical_failures_count,
            ),
            score=ReportScoreSection(
                overall_compliance_score=score.overall_compliance_score,
                score_type=score.score_type,
                scoring_complete=score.scoring_complete,
                earned_weight=score.earned_weight,
                eligible_weight=score.eligible_weight,
                category_scores=score.category_scores,
                scoring_version=score.scoring_version,
                is_stale=score.is_stale or ("SCORE" in eval_summary.stale_components),
            ),
            risk=ReportRiskSection(
                base_risk_score=risk.base_risk_score,
                base_risk_level=risk.base_risk_level,
                adjusted_risk_score=risk.adjusted_risk_score,
                adjusted_risk_level=risk.adjusted_risk_level,
                override_applied=risk.override_applied,
                applied_overrides=risk.applied_overrides,
                risk_complete=risk.risk_complete,
                risk_version=risk.risk_version,
                is_stale=risk.is_stale or ("RISK" in eval_summary.stale_components),
            ),
            mandatory_failures=mandatory_failures,
            critical_findings=critical_findings,
            human_reviews=human_reviews,
            ai_recommendation=(
                ReportAISection(
                    recommendation=ai.recommendation,
                    recommendation_reason=ai.recommendation_reason,
                    summary=ai.summary,
                    strengths=ai.strengths,
                    concerns=ai.concerns,
                    model_provider=ai.model_provider,
                    model_name=ai.model_name,
                    prompt_version=ai.prompt_version,
                    guardrail_applied=ai.guardrail_applied,
                    guardrail_reason=ai.guardrail_reason,
                    confidence_label=ai.confidence_label,
                    is_stale=ai.is_stale or ("AI" in eval_summary.stale_components),
                )
                if ai and ai.status != "NOT_GENERATED"
                else None
            ),
            final_human_decision=ReportFinalDecisionSection(
                decision=current_decision.decision.value,
                reason=current_decision.reason,
                decision_summary=current_decision.decision_summary,
                category=current_decision.category,
                decided_by_name=current_decision.decided_by.full_name if current_decision.decided_by else None,
                decided_by_role=current_decision.decided_by.role_name if current_decision.decided_by else None,
                decided_at=current_decision.decided_at,
                decision_version=current_decision.decision_version,
                is_current=current_decision.is_current,
                is_stale=current_decision.is_stale,
                stale_reason=current_decision.stale_reason,
            ),
            decision_history=decision_history,
            stale_warnings=stale_warnings,
            mock_verification_disclaimer=mock_disclaimer,
            audit_timeline=audit_summary,
            generated_at=datetime.now(timezone.utc),
            generated_by=profile.full_name or "Procurement Officer",
        )

    @classmethod
    def generate_bid_evaluation_pdf(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
    ) -> bytes:
        """
        Generates a clean vector PDF report for the proposal evaluation dossier using PyMuPDF.
        """
        report = cls.get_bid_evaluation_report(db, user, tender_id, bid_id)

        doc = pymupdf.open()
        
        # PAGE 1: Overview, Scores, Risk, and Final Human Decision
        page1 = doc.new_page(width=595, height=842)  # A4 standard
        
        # Title Header
        page1.insert_text((40, 45), "Government e-Marketplace (GeM) — Compliance Dossier", fontsize=10, fontname="helv", color=(0.4, 0.4, 0.4))
        page1.insert_text((40, 65), "Bid Compliance Verification & Evaluation Report", fontsize=16, fontname="hebo", color=(0.1, 0.2, 0.4))
        page1.draw_line((40, 75), (555, 75), color=(0.2, 0.3, 0.5), width=1.5)

        # Metadata Row
        page1.insert_text((40, 95), f"Tender Number: {report.tender.tender_number}", fontsize=9, fontname="hebo")
        page1.insert_text((40, 110), f"Tender Title: {report.tender.title[:65]}", fontsize=9, fontname="helv")
        page1.insert_text((40, 125), f"Department/Entity: {report.tender.organization_name}", fontsize=9, fontname="helv")

        page1.insert_text((340, 95), f"Bid Number: {report.bid.bid_number}", fontsize=9, fontname="hebo")
        page1.insert_text((340, 110), f"Bidder: {report.bidder.name[:35]}", fontsize=9, fontname="helv")
        page1.insert_text((340, 125), f"PAN: {report.bidder.pan_number or 'N/A'}  |  GSTIN: {report.bidder.gstin or 'N/A'}", fontsize=9, fontname="helv")

        # Stale warning banner if applicable
        y_cursor = 145
        if report.stale_warnings:
            page1.draw_rect((40, y_cursor, 555, y_cursor + 20), color=(0.9, 0.6, 0.1), fill=(1.0, 0.95, 0.85))
            page1.insert_text((48, y_cursor + 14), f"WARNING: {report.stale_warnings[0][:80]}", fontsize=8.5, fontname="hebo", color=(0.6, 0.3, 0.0))
            y_cursor += 30

        # Section: Deterministic Scores & Risk Posture
        page1.draw_rect((40, y_cursor, 555, y_cursor + 85), color=(0.8, 0.8, 0.8), fill=(0.96, 0.97, 0.99))
        page1.insert_text((55, y_cursor + 20), "COMPLIANCE SCORE", fontsize=9, fontname="hebo", color=(0.2, 0.3, 0.5))
        score_txt = f"{report.score.overall_compliance_score:.1f}%" if report.score.overall_compliance_score is not None else "N/A"
        page1.insert_text((55, y_cursor + 45), score_txt, fontsize=20, fontname="hebo", color=(0.1, 0.4, 0.2))
        page1.insert_text((55, y_cursor + 65), f"Rules: {report.compliance.passed_count} Pass / {report.compliance.failed_count} Fail / {report.compliance.review_count} Rev", fontsize=8, fontname="helv")

        page1.insert_text((220, y_cursor + 20), "ADJUSTED RISK", fontsize=9, fontname="hebo", color=(0.2, 0.3, 0.5))
        risk_txt = f"{report.risk.adjusted_risk_level or 'LOW'}"
        risk_color = (0.7, 0.1, 0.1) if risk_txt in ("HIGH", "CRITICAL") else (0.1, 0.4, 0.2)
        page1.insert_text((220, y_cursor + 45), risk_txt, fontsize=18, fontname="hebo", color=risk_color)
        page1.insert_text((220, y_cursor + 65), f"Overrides: {'Applied' if report.risk.override_applied else 'None'}", fontsize=8, fontname="helv")

        page1.insert_text((380, y_cursor + 20), "FINAL HUMAN DECISION", fontsize=9, fontname="hebo", color=(0.2, 0.3, 0.5))
        dec_txt = report.final_human_decision.decision
        dec_color = (0.1, 0.4, 0.2) if dec_txt == "QUALIFIED" else ((0.7, 0.1, 0.1) if dec_txt == "DISQUALIFIED" else (0.5, 0.3, 0.1))
        page1.insert_text((380, y_cursor + 45), dec_txt, fontsize=18, fontname="hebo", color=dec_color)
        page1.insert_text((380, y_cursor + 65), f"Version: v{report.final_human_decision.decision_version}", fontsize=8, fontname="helv")

        y_cursor += 105

        # Section: Final Human Decision Details
        page1.insert_text((40, y_cursor), "Authoritative Human Procurement Decision", fontsize=12, fontname="hebo", color=(0.1, 0.2, 0.4))
        page1.draw_line((40, y_cursor + 5), (555, y_cursor + 5), color=(0.8, 0.8, 0.8))
        y_cursor += 20

        page1.insert_text((40, y_cursor), f"Deciding Officer: {report.final_human_decision.decided_by_name or 'Not Decided'} ({report.final_human_decision.decided_by_role or 'Procurement Officer'})", fontsize=9, fontname="hebo")
        page1.insert_text((340, y_cursor), f"Decision Date: {report.final_human_decision.decided_at.strftime('%Y-%m-%d %H:%M UTC') if report.final_human_decision.decided_at else 'Pending'}", fontsize=9, fontname="helv")
        y_cursor += 15

        if report.final_human_decision.category:
            page1.insert_text((40, y_cursor), f"Disqualification Category: {report.final_human_decision.category}", fontsize=9, fontname="hebo", color=(0.7, 0.1, 0.1))
            y_cursor += 15

        page1.insert_text((40, y_cursor), "Justification Reason:", fontsize=9, fontname="hebo")
        y_cursor += 12
        reason_txt = report.final_human_decision.reason or "No final decision has been recorded yet. Bid remains under evaluation."
        # Split text into chunks
        for line_chunk in [reason_txt[i:i+90] for i in range(0, min(len(reason_txt), 270), 90)]:
            page1.insert_text((40, y_cursor), line_chunk, fontsize=8.5, fontname="helv")
            y_cursor += 12

        y_cursor += 15

        # Section: Category Compliance Scores
        page1.insert_text((40, y_cursor), "Compliance Scores by Category", fontsize=12, fontname="hebo", color=(0.1, 0.2, 0.4))
        page1.draw_line((40, y_cursor + 5), (555, y_cursor + 5), color=(0.8, 0.8, 0.8))
        y_cursor += 20

        for cat, cat_data in list(report.score.category_scores.items())[:6]:
            cat_score = cat_data.get("percentage_score")
            score_str = f"{cat_score:.1f}%" if cat_score is not None else "N/A"
            page1.insert_text((50, y_cursor), f"• {cat.replace('_', ' ').title()}:", fontsize=8.5, fontname="hebo")
            page1.insert_text((180, y_cursor), score_str, fontsize=8.5, fontname="helv")
            page1.insert_text((240, y_cursor), f"Rules Passed: {cat_data.get('passed_count', 0)}/{cat_data.get('total_count', 0)}", fontsize=8.5, fontname="helv")
            y_cursor += 14

        y_cursor += 15

        # Section: Advisory AI Recommendation
        if report.ai_recommendation:
            page1.insert_text((40, y_cursor), "AI-Assisted Evaluation Recommendation (Advisory Guidance Only)", fontsize=12, fontname="hebo", color=(0.1, 0.2, 0.4))
            page1.draw_line((40, y_cursor + 5), (555, y_cursor + 5), color=(0.8, 0.8, 0.8))
            y_cursor += 20

            page1.insert_text((40, y_cursor), f"AI Recommendation: {report.ai_recommendation.recommendation or 'N/A'}", fontsize=9, fontname="hebo", color=(0.2, 0.3, 0.6))
            page1.insert_text((300, y_cursor), f"Model: {report.ai_recommendation.model_name or 'Standard'}", fontsize=8.5, fontname="helv")
            y_cursor += 14

            ai_summary = report.ai_recommendation.summary or report.ai_recommendation.recommendation_reason or ""
            for line_chunk in [ai_summary[i:i+90] for i in range(0, min(len(ai_summary), 180), 90)]:
                page1.insert_text((40, y_cursor), line_chunk, fontsize=8, fontname="helv", color=(0.3, 0.3, 0.3))
                y_cursor += 11

            y_cursor += 8
            page1.insert_text((40, y_cursor), f"Disclaimer: {report.ai_recommendation.advisory_disclaimer[:95]}", fontsize=7.5, fontname="helv", color=(0.5, 0.5, 0.5))

        # Footer Page 1
        page1.insert_text((40, 815), f"Generated on {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')} by {report.generated_by}", fontsize=7.5, fontname="helv", color=(0.5, 0.5, 0.5))
        page1.insert_text((480, 815), "Page 1 of 2", fontsize=7.5, fontname="helv", color=(0.5, 0.5, 0.5))

        # PAGE 2: Defects, Human Reviews, and Audit Timeline
        page2 = doc.new_page(width=595, height=842)
        page2.insert_text((40, 45), f"Bid Compliance Dossier — {report.bid.bid_number} ({report.bidder.name[:30]})", fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4))
        page2.insert_text((40, 65), "Defects, Review Resolutions & Chronological Audit Trail", fontsize=14, fontname="hebo", color=(0.1, 0.2, 0.4))
        page2.draw_line((40, 75), (555, 75), color=(0.2, 0.3, 0.5), width=1.5)

        y2 = 95

        # Critical Findings & Mandatory Failures
        page2.insert_text((40, y2), "Mandatory Failures & Critical Findings", fontsize=11, fontname="hebo", color=(0.1, 0.2, 0.4))
        page2.draw_line((40, y2 + 4), (555, y2 + 4), color=(0.8, 0.8, 0.8))
        y2 += 16

        all_defects = report.critical_findings + [m for m in report.mandatory_failures if m not in report.critical_findings]
        if all_defects:
            for d in all_defects[:5]:
                page2.insert_text((50, y2), f"• [{d.requirement_code}] {d.requirement_name[:40]}", fontsize=8.5, fontname="hebo", color=(0.7, 0.1, 0.1))
                page2.insert_text((340, y2), f"Status: {d.compliance_status} | Mandatory: {d.is_mandatory}", fontsize=8, fontname="helv")
                y2 += 12
                if d.reason:
                    page2.insert_text((60, y2), f"Reason: {d.reason[:80]}", fontsize=7.5, fontname="helv", color=(0.3, 0.3, 0.3))
                    y2 += 11
        else:
            page2.insert_text((50, y2), "No mandatory failures or critical defects identified. All mandatory conditions satisfied.", fontsize=8.5, fontname="helv", color=(0.1, 0.4, 0.2))
            y2 += 15

        y2 += 10

        # Human Review Queue Resolutions
        page2.insert_text((40, y2), "Human Review Inspections & Resolutions", fontsize=11, fontname="hebo", color=(0.1, 0.2, 0.4))
        page2.draw_line((40, y2 + 4), (555, y2 + 4), color=(0.8, 0.8, 0.8))
        y2 += 16

        if report.human_reviews:
            for hr in report.human_reviews[:4]:
                page2.insert_text((50, y2), f"• {hr.review_type} (Severity: {hr.severity})", fontsize=8.5, fontname="hebo")
                page2.insert_text((240, y2), f"Resolution: {hr.resolution or 'OPEN'}", fontsize=8.5, fontname="hebo", color=(0.1, 0.4, 0.2) if hr.resolution == "CONFIRMED" else (0.4, 0.4, 0.4))
                page2.insert_text((400, y2), f"By: {hr.resolved_by_name or 'Pending'}", fontsize=8, fontname="helv")
                y2 += 12
                if hr.reason:
                    page2.insert_text((60, y2), f"Justification: {hr.reason[:80]}", fontsize=7.5, fontname="helv", color=(0.3, 0.3, 0.3))
                    y2 += 11
        else:
            page2.insert_text((50, y2), "No human review items raised for this proposal.", fontsize=8.5, fontname="helv")
            y2 += 15

        y2 += 10

        # Chronological Audit Trail
        page2.insert_text((40, y2), "Chronological Procurement Audit Trail", fontsize=11, fontname="hebo", color=(0.1, 0.2, 0.4))
        page2.draw_line((40, y2 + 4), (555, y2 + 4), color=(0.8, 0.8, 0.8))
        y2 += 16

        for evt in report.audit_timeline[:12]:
            dt_str = evt.created_at.strftime("%m-%d %H:%M")
            page2.insert_text((50, y2), dt_str, fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
            page2.insert_text((110, y2), f"{evt.event_label}", fontsize=8, fontname="hebo")
            page2.insert_text((260, y2), f"Actor: {evt.actor_name} ({evt.actor_source})", fontsize=7.5, fontname="helv")
            page2.insert_text((420, y2), f"{evt.summary[:30]}", fontsize=7.5, fontname="helv", color=(0.3, 0.3, 0.3))
            y2 += 13

        if report.mock_verification_disclaimer:
            y2 = max(y2 + 10, 750)
            page2.draw_rect((40, y2, 555, y2 + 30), color=(0.7, 0.7, 0.7), fill=(0.95, 0.95, 0.95))
            page2.insert_text((48, y2 + 12), report.mock_verification_disclaimer[:90], fontsize=7.5, fontname="helv", color=(0.4, 0.4, 0.4))
            page2.insert_text((48, y2 + 22), report.mock_verification_disclaimer[90:180], fontsize=7.5, fontname="helv", color=(0.4, 0.4, 0.4))

        # Footer Page 2
        page2.insert_text((40, 815), f"BidVerify AI Platform — Confidential Procurement Audit Record", fontsize=7.5, fontname="helv", color=(0.5, 0.5, 0.5))
        page2.insert_text((480, 815), "Page 2 of 2", fontsize=7.5, fontname="helv", color=(0.5, 0.5, 0.5))

        pdf_bytes = doc.write()
        doc.close()
        return pdf_bytes

    @classmethod
    def generate_tender_summary_pdf(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
    ) -> bytes:
        """
        Generates an executive Tender Evaluation Summary PDF report.
        """
        report = cls.get_tender_summary_report(db, user, tender_id)

        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)

        # Header
        page.insert_text((40, 45), "Government e-Marketplace (GeM) — Evaluation Summary", fontsize=10, fontname="helv", color=(0.4, 0.4, 0.4))
        page.insert_text((40, 65), "Tender Compliance & Evaluation Summary Report", fontsize=16, fontname="hebo", color=(0.1, 0.2, 0.4))
        page.draw_line((40, 75), (555, 75), color=(0.2, 0.3, 0.5), width=1.5)

        # Tender Details
        page.insert_text((40, 95), f"Tender Number: {report.tender.tender_number}", fontsize=9, fontname="hebo")
        page.insert_text((40, 110), f"Title: {report.tender.title[:65]}", fontsize=9, fontname="helv")
        page.insert_text((40, 125), f"Organization: {report.tender.organization_name}", fontsize=9, fontname="helv")

        page.insert_text((340, 95), f"Status: {report.tender.status}", fontsize=9, fontname="hebo")
        page.insert_text((340, 110), f"Category: {report.tender.category or 'GOODS'}", fontsize=9, fontname="helv")
        page.insert_text((340, 125), f"Currency: {report.tender.currency}", fontsize=9, fontname="helv")

        # KPI Dashboard Cards
        y = 150
        page.draw_rect((40, y, 155, y + 60), color=(0.8, 0.8, 0.8), fill=(0.96, 0.97, 0.99))
        page.insert_text((55, y + 18), "TOTAL BIDS", fontsize=8.5, fontname="hebo", color=(0.2, 0.3, 0.5))
        page.insert_text((55, y + 42), f"{report.total_bids_submitted}", fontsize=18, fontname="hebo", color=(0.1, 0.2, 0.4))
        page.insert_text((55, y + 54), f"Evaluated: {report.total_bids_evaluated}", fontsize=7.5, fontname="helv")

        page.draw_rect((170, y, 285, y + 60), color=(0.8, 0.8, 0.8), fill=(0.96, 0.97, 0.99))
        page.insert_text((185, y + 18), "QUALIFIED", fontsize=8.5, fontname="hebo", color=(0.1, 0.4, 0.2))
        page.insert_text((185, y + 42), f"{report.total_qualified}", fontsize=18, fontname="hebo", color=(0.1, 0.4, 0.2))
        page.insert_text((185, y + 54), f"Disqualified: {report.total_disqualified}", fontsize=7.5, fontname="helv")

        page.draw_rect((300, y, 415, y + 60), color=(0.8, 0.8, 0.8), fill=(0.96, 0.97, 0.99))
        page.insert_text((315, y + 18), "UNDER REVIEW", fontsize=8.5, fontname="hebo", color=(0.6, 0.4, 0.1))
        page.insert_text((315, y + 42), f"{report.total_under_review}", fontsize=18, fontname="hebo", color=(0.6, 0.4, 0.1))
        page.insert_text((315, y + 54), f"Shortlisted: {report.total_shortlisted}", fontsize=7.5, fontname="helv")

        page.draw_rect((430, y, 555, y + 60), color=(0.8, 0.8, 0.8), fill=(0.96, 0.97, 0.99))
        page.insert_text((445, y + 18), "AVG SCORE", fontsize=8.5, fontname="hebo", color=(0.2, 0.3, 0.5))
        avg_str = f"{report.average_compliance_score:.1f}%" if report.average_compliance_score is not None else "N/A"
        page.insert_text((445, y + 42), avg_str, fontsize=18, fontname="hebo", color=(0.1, 0.2, 0.4))
        page.insert_text((445, y + 54), f"Defects: {report.total_critical_defects}", fontsize=7.5, fontname="helv")

        # Table Header
        y = 230
        page.insert_text((40, y), "Submitted Proposals Evaluation Summary", fontsize=12, fontname="hebo", color=(0.1, 0.2, 0.4))
        page.draw_line((40, y + 5), (555, y + 5), color=(0.2, 0.3, 0.5), width=1)
        y += 20

        # Table Columns
        page.insert_text((45, y), "Bid Number", fontsize=8.5, fontname="hebo")
        page.insert_text((140, y), "Bidder Name", fontsize=8.5, fontname="hebo")
        page.insert_text((290, y), "Score", fontsize=8.5, fontname="hebo")
        page.insert_text((340, y), "Risk", fontsize=8.5, fontname="hebo")
        page.insert_text((400, y), "Decision", fontsize=8.5, fontname="hebo")
        page.insert_text((490, y), "Shortlist", fontsize=8.5, fontname="hebo")
        y += 6
        page.draw_line((40, y), (555, y), color=(0.8, 0.8, 0.8))
        y += 12

        for b in report.bids:
            score_txt = f"{b.compliance_score:.1f}%" if b.compliance_score is not None else "N/A"
            dec_col = (0.1, 0.4, 0.2) if b.human_decision_status == "QUALIFIED" else ((0.7, 0.1, 0.1) if b.human_decision_status == "DISQUALIFIED" else (0.4, 0.4, 0.4))
            
            page.insert_text((45, y), b.bid_number[:15], fontsize=8, fontname="helv")
            page.insert_text((140, y), b.bidder_name[:25], fontsize=8, fontname="helv")
            page.insert_text((290, y), score_txt, fontsize=8, fontname="helv")
            page.insert_text((340, y), b.adjusted_risk_level or "LOW", fontsize=8, fontname="helv")
            page.insert_text((400, y), b.human_decision_status, fontsize=8, fontname="hebo", color=dec_col)
            page.insert_text((490, y), "Yes" if b.is_shortlisted else "No", fontsize=8, fontname="helv")
            y += 15

        # Footer
        page.insert_text((40, 815), f"Generated on {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')} by {report.generated_by}", fontsize=7.5, fontname="helv", color=(0.5, 0.5, 0.5))
        page.insert_text((480, 815), "Page 1 of 1", fontsize=7.5, fontname="helv", color=(0.5, 0.5, 0.5))

        pdf_bytes = doc.write()
        doc.close()
        return pdf_bytes
