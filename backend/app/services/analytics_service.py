"""
Analytics and Impact Aggregation Service for BidVerify AI (Part 13)
Executes efficient, multi-tenant scoped SQL aggregations across Tenders, Bids,
Compliance Results, Verification Records, Risk Snapshots, Document Quality Results (Part 11),
Duplicate Matches (Part 10), Bulk Verification Jobs (Part 9), Human Reviews (Part 8C),
and Final Human Qualification Decisions (Part 8D).
"""

import csv
import io
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import (
    and_,
    case,
    desc,
    func,
    or_,
    select,
)
from sqlalchemy.orm import Session

from app.db.models.bid import Bid
from app.db.models.bid_decision import BidDecision, BidDecisionStatus
from app.db.models.bid_document import BidDocument
from app.db.models.bulk_evaluation_job import BulkEvaluationJob, BulkJobStatus
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus
from app.db.models.document_duplicate_match import (
    DocumentDuplicateMatch,
    DuplicateMatchStatus,
    DuplicateMatchType,
)
from app.db.models.document_processing import DocumentProcessing
from app.db.models.document_quality import DocumentQualityResult, QualityLevel
from app.db.models.human_review import HumanReviewItem, ReviewStatus, ReviewType
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.validation_run import ValidationRun, ValidationStatus
from app.db.models.verification_record import VerificationRecord
from app.verification.types import VerificationStatus as VerStatus

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Centralized analytics engine executing multi-tenant safe aggregations.
    """

    @classmethod
    def _apply_tender_scope(
        cls,
        query,
        model,
        org_id: Optional[uuid.UUID] = None,
        tender_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_column_name: str = "created_at",
    ):
        """
        Applies multi-tenant organization filtering, tender scoping, and date bounds.
        """
        conditions = []

        if tender_id:
            if hasattr(model, "tender_id"):
                conditions.append(model.tender_id == tender_id)
            elif hasattr(model, "id") and model == Tender:
                conditions.append(model.id == tender_id)

        if org_id:
            if hasattr(model, "organization_id"):
                conditions.append(model.organization_id == org_id)
            elif model == Tender:
                conditions.append(model.organization_id == org_id)
            elif model == Bid:
                # Scoped via tender's organization
                subquery_tenders = select(Tender.id).where(Tender.organization_id == org_id)
                conditions.append(Bid.tender_id.in_(subquery_tenders))
            elif hasattr(model, "tender_id"):
                subquery_tenders = select(Tender.id).where(Tender.organization_id == org_id)
                conditions.append(model.tender_id.in_(subquery_tenders))

        if start_date:
            date_col = getattr(model, date_column_name, None)
            if date_col is not None:
                conditions.append(date_col >= start_date)

        if end_date:
            date_col = getattr(model, date_column_name, None)
            if date_col is not None:
                conditions.append(date_col <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        return query

    # =========================================================================
    # 1. OVERVIEW KPIS & IMPACT
    # =========================================================================

    @classmethod
    def get_overview_kpis(
        cls,
        db: Session,
        org_id: Optional[uuid.UUID] = None,
        tender_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Aggregates high-level procurement KPI counters and impact savings.
        """
        # 1. Tenders count
        t_query = select(
            func.count(Tender.id).label("total_tenders"),
            func.count(case((Tender.status == "PUBLISHED", Tender.id))).label("active_tenders"),
            func.count(case((Tender.status == "CLOSED", Tender.id))).label("closed_tenders"),
        )
        t_query = cls._apply_tender_scope(t_query, Tender, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        t_res = db.execute(t_query).first()
        total_tenders = t_res.total_tenders if t_res else 0
        active_tenders = t_res.active_tenders if t_res else 0

        # 2. Bids count
        b_query = select(
            func.count(Bid.id).label("total_bids"),
            func.count(case((Bid.status.in_(["SUBMITTED", "UNDER_EVALUATION", "EVALUATED", "QUALIFIED", "DISQUALIFIED"]), Bid.id))).label("submitted_bids"),
            func.count(case((Bid.status.in_(["EVALUATED", "QUALIFIED", "DISQUALIFIED"]), Bid.id))).label("evaluated_bids"),
        )
        b_query = cls._apply_tender_scope(b_query, Bid, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        b_res = db.execute(b_query).first()
        total_bids = b_res.total_bids if b_res else 0
        submitted_bids = b_res.submitted_bids if b_res else 0
        evaluated_bids = b_res.evaluated_bids if b_res else 0

        # 3. Compliance rate (from current compliance results)
        comp_query = select(
            func.count(ComplianceResult.id).label("total_comp"),
            func.count(case((ComplianceResult.compliance_status == ComplianceStatus.PASS, ComplianceResult.id))).label("passed_comp"),
            func.count(case((ComplianceResult.compliance_status == ComplianceStatus.FAIL, ComplianceResult.id))).label("failed_comp"),
            func.count(case((ComplianceResult.compliance_status == ComplianceStatus.REVIEW, ComplianceResult.id))).label("review_comp"),
        ).where(ComplianceResult.is_current == True)  # noqa: E712
        comp_query = cls._apply_tender_scope(comp_query, ComplianceResult, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        comp_res = db.execute(comp_query).first()
        total_comp = comp_res.total_comp if comp_res else 0
        passed_comp = comp_res.passed_comp if comp_res else 0
        compliance_rate = round((passed_comp / total_comp) * 100, 1) if total_comp > 0 else None

        # 4. Reviews workload
        rev_query = select(
            func.count(HumanReviewItem.id).label("total_reviews"),
            func.count(case((HumanReviewItem.status == ReviewStatus.OPEN, HumanReviewItem.id))).label("open_reviews"),
            func.count(case((HumanReviewItem.status == ReviewStatus.IN_REVIEW, HumanReviewItem.id))).label("in_review_reviews"),
            func.count(case((HumanReviewItem.status == ReviewStatus.RESOLVED, HumanReviewItem.id))).label("resolved_reviews"),
        )
        rev_query = cls._apply_tender_scope(rev_query, HumanReviewItem, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        rev_res = db.execute(rev_query).first()
        open_reviews = (rev_res.open_reviews + rev_res.in_review_reviews) if rev_res else 0

        # 5. Risk High/Critical Bids (from current risk snapshots)
        risk_query = select(
            func.count(BidRiskSnapshot.id).label("total_risk"),
            func.count(case((BidRiskSnapshot.adjusted_risk_level.in_(["HIGH", "CRITICAL"]), BidRiskSnapshot.id))).label("high_critical_risk"),
            func.avg(BidRiskSnapshot.adjusted_risk_score).label("avg_risk_score"),
        ).where(BidRiskSnapshot.is_current == True)  # noqa: E712
        risk_query = cls._apply_tender_scope(risk_query, BidRiskSnapshot, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        risk_res = db.execute(risk_query).first()
        high_critical_risk = risk_res.high_critical_risk if risk_res else 0
        avg_risk_score = round(float(risk_res.avg_risk_score), 1) if risk_res and risk_res.avg_risk_score is not None else None

        # 6. Document Quality Alerts (Part 11)
        dq_query = select(
            func.count(DocumentQualityResult.id).label("total_docs_quality"),
            func.count(case((DocumentQualityResult.quality_level.in_([QualityLevel.POOR, QualityLevel.UNUSABLE]), DocumentQualityResult.id))).label("poor_unusable_docs"),
            func.avg(DocumentQualityResult.quality_score).label("avg_quality_score"),
        )
        if org_id or tender_id:
            # Join via BidDocument -> Bid
            dq_query = dq_query.join(BidDocument, DocumentQualityResult.document_id == BidDocument.id).join(Bid, BidDocument.bid_id == Bid.id)
            if tender_id:
                dq_query = dq_query.where(Bid.tender_id == tender_id)
            if org_id:
                sub_tenders = select(Tender.id).where(Tender.organization_id == org_id)
                dq_query = dq_query.where(Bid.tender_id.in_(sub_tenders))
        if start_date:
            dq_query = dq_query.where(DocumentQualityResult.created_at >= start_date)
        if end_date:
            dq_query = dq_query.where(DocumentQualityResult.created_at <= end_date)

        dq_res = db.execute(dq_query).first()
        poor_quality_docs = dq_res.poor_unusable_docs if dq_res else 0
        avg_quality_score = round(float(dq_res.avg_quality_score), 1) if dq_res and dq_res.avg_quality_score is not None else None

        # 7. Duplicate Alerts (Part 10)
        dup_query = select(func.count(DocumentDuplicateMatch.id).label("total_duplicates"))
        dup_query = cls._apply_tender_scope(dup_query, DocumentDuplicateMatch, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        dup_res = db.execute(dup_query).first()
        duplicate_alerts = dup_res.total_duplicates if dup_res else 0

        # 8. Empirical Impact Savings (from latest completed ValidationRun if present)
        val_run = db.scalars(
            select(ValidationRun)
            .where(ValidationRun.status == ValidationStatus.COMPLETED.value)
            .order_by(desc(ValidationRun.created_at))
            .limit(1)
        ).first()

        impact_data = None
        if val_run and val_run.total_cases > 0:
            impact_data = {
                "measured_time_reduction_percentage": round(val_run.time_reduction_percentage, 1),
                "avg_automated_time_ms": round(val_run.average_processing_time_ms, 2),
                "avg_manual_baseline_sec": round(val_run.average_manual_time_sec, 1),
                "total_validation_cases": val_run.total_cases,
                "dataset_version": val_run.dataset_version,
            }

        # 9. Certificate Validity (Part 14)
        from app.db.models.document_validity import DocumentValidityRecord, ValidityStatus
        cert_query = select(
            func.count(DocumentValidityRecord.id).label("total_certs"),
            func.count(case((DocumentValidityRecord.validity_status == ValidityStatus.EXPIRED.value, DocumentValidityRecord.id))).label("expired_certs"),
            func.count(case((DocumentValidityRecord.validity_status == ValidityStatus.EXPIRING_SOON.value, DocumentValidityRecord.id))).label("expiring_soon_certs"),
        ).where(DocumentValidityRecord.is_current == True)
        if org_id:
            cert_query = cert_query.where(DocumentValidityRecord.organization_id == org_id)
        if tender_id:
            cert_query = cert_query.join(Bid, DocumentValidityRecord.bid_id == Bid.id).where(Bid.tender_id == tender_id)
        cert_res = db.execute(cert_query).first()
        expired_certs = cert_res.expired_certs if cert_res else 0
        expiring_soon_certs = cert_res.expiring_soon_certs if cert_res else 0

        return {
            "total_tenders": total_tenders,
            "active_tenders": active_tenders,
            "total_bids": total_bids,
            "submitted_bids": submitted_bids,
            "evaluated_bids": evaluated_bids,
            "compliance_rate_percentage": compliance_rate,
            "open_reviews_count": open_reviews,
            "high_critical_risk_bids": high_critical_risk,
            "average_risk_score": avg_risk_score,
            "poor_quality_documents_count": poor_quality_docs,
            "average_quality_score": avg_quality_score,
            "duplicate_alerts_count": duplicate_alerts,
            "expired_certificates_count": expired_certs,
            "expiring_soon_certificates_count": expiring_soon_certs,
            "procurement_impact": impact_data,
        }

    # =========================================================================
    # 2. COMPLIANCE & FAILURE REASON ANALYTICS
    # =========================================================================

    @classmethod
    def get_compliance_analytics(
        cls,
        db: Session,
        org_id: Optional[uuid.UUID] = None,
        tender_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculates compliance status breakdown, mandatory failure stats, and top failed requirements.
        """
        # Status Distribution
        query = select(
            ComplianceResult.compliance_status,
            func.count(ComplianceResult.id).label("count"),
        ).where(ComplianceResult.is_current == True)  # noqa: E712
        query = cls._apply_tender_scope(query, ComplianceResult, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        query = query.group_by(ComplianceResult.compliance_status)

        rows = db.execute(query).all()
        distribution: Dict[str, int] = {
            ComplianceStatus.PASS: 0,
            ComplianceStatus.FAIL: 0,
            ComplianceStatus.REVIEW: 0,
            ComplianceStatus.NOT_APPLICABLE: 0,
            ComplianceStatus.PENDING: 0,
        }
        total_evaluations = 0
        for r in rows:
            if r.compliance_status in distribution:
                distribution[r.compliance_status] = r.count
            total_evaluations += r.count

        passed_count = distribution.get(ComplianceStatus.PASS, 0)
        overall_compliance_rate = round((passed_count / total_evaluations) * 100, 1) if total_evaluations > 0 else None

        # Mandatory Requirement Failures
        mand_query = select(func.count(ComplianceResult.id)).where(
            and_(
                ComplianceResult.is_current == True,  # noqa: E712
                ComplianceResult.is_mandatory == True,
                ComplianceResult.compliance_status == ComplianceStatus.FAIL,
            )
        )
        mand_query = cls._apply_tender_scope(mand_query, ComplianceResult, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        mandatory_failures = db.scalar(mand_query) or 0

        # Top Failed Requirements (joined with TenderRequirement)
        failed_req_query = (
            select(
                TenderRequirement.code.label("requirement_code"),
                TenderRequirement.name.label("title"),
                TenderRequirement.category,
                func.count(ComplianceResult.id).label("fail_count"),
            )
            .join(TenderRequirement, ComplianceResult.tender_requirement_id == TenderRequirement.id)
            .where(
                and_(
                    ComplianceResult.is_current == True,  # noqa: E712
                    ComplianceResult.compliance_status == ComplianceStatus.FAIL,
                )
            )
        )
        failed_req_query = cls._apply_tender_scope(failed_req_query, ComplianceResult, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        failed_req_query = failed_req_query.group_by(
            TenderRequirement.code,
            TenderRequirement.name,
            TenderRequirement.category,
        ).order_by(desc("fail_count")).limit(8)

        failed_req_rows = db.execute(failed_req_query).all()
        top_failed_requirements = [
            {
                "requirement_code": r.requirement_code or "N/A",
                "title": r.title,
                "category": r.category,
                "fail_count": r.fail_count,
            }
            for r in failed_req_rows
        ]

        # Common Failure Reasons (derived from actual recorded failure reasons)
        reasons_query = select(ComplianceResult.reason).where(
            and_(
                ComplianceResult.is_current == True,  # noqa: E712
                ComplianceResult.compliance_status == ComplianceStatus.FAIL,
                ComplianceResult.reason != None,  # noqa: E711
            )
        )
        reasons_query = cls._apply_tender_scope(reasons_query, ComplianceResult, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        reason_texts = db.scalars(reasons_query.limit(100)).all()

        common_failure_categories: Dict[str, int] = {}
        for r_text in reason_texts:
            rt_lower = r_text.lower()
            if "gst" in rt_lower:
                cat = "GST Validation Failure"
            elif "pan" in rt_lower:
                cat = "PAN Verification Failure"
            elif "turnover" in rt_lower or "financial" in rt_lower:
                cat = "Turnover / Net Worth Below Threshold"
            elif "oem" in rt_lower or "authorization" in rt_lower:
                cat = "OEM Authorization Missing / Expired"
            elif "local content" in rt_lower or "make in india" in rt_lower:
                cat = "Local Content Percentage Failure"
            elif "expired" in rt_lower or "validity" in rt_lower:
                cat = "Expired Certificate / Validity"
            elif "missing" in rt_lower or "not uploaded" in rt_lower:
                cat = "Missing Mandatory Document"
            elif "quality" in rt_lower or "blurry" in rt_lower:
                cat = "Poor Document Quality"
            else:
                cat = "Other Technical Non-Compliance"
            common_failure_categories[cat] = common_failure_categories.get(cat, 0) + 1

        sorted_reasons = [
            {"reason": k, "count": v}
            for k, v in sorted(common_failure_categories.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            "distribution": distribution,
            "total_evaluations": total_evaluations,
            "overall_compliance_rate": overall_compliance_rate,
            "mandatory_failures_count": mandatory_failures,
            "top_failed_requirements": top_failed_requirements,
            "common_failure_reasons": sorted_reasons,
        }

    # =========================================================================
    # 3. RISK ANALYTICS
    # =========================================================================

    @classmethod
    def get_risk_analytics(
        cls,
        db: Session,
        org_id: Optional[uuid.UUID] = None,
        tender_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculates risk tier distributions, average scores, and override signals.
        """
        query = select(
            BidRiskSnapshot.adjusted_risk_level,
            func.count(BidRiskSnapshot.id).label("count"),
            func.avg(BidRiskSnapshot.adjusted_risk_score).label("avg_adjusted"),
            func.avg(BidRiskSnapshot.base_risk_score).label("avg_base"),
        ).where(BidRiskSnapshot.is_current == True)  # noqa: E712
        query = cls._apply_tender_scope(query, BidRiskSnapshot, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        query = query.group_by(BidRiskSnapshot.adjusted_risk_level)

        rows = db.execute(query).all()

        distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        total_risk_snapshots = 0
        sum_scores = 0.0

        for r in rows:
            level = (r.adjusted_risk_level or "LOW").upper()
            if level in distribution:
                distribution[level] = r.count
            total_risk_snapshots += r.count
            if r.avg_adjusted is not None:
                sum_scores += float(r.avg_adjusted) * r.count

        avg_risk_score = round(sum_scores / total_risk_snapshots, 1) if total_risk_snapshots > 0 else None

        # Overrides telemetry
        overrides_query = select(
            func.count(case((BidRiskSnapshot.override_applied == True, BidRiskSnapshot.id))).label("overrides_count"),
        ).where(BidRiskSnapshot.is_current == True)  # noqa: E712
        overrides_query = cls._apply_tender_scope(overrides_query, BidRiskSnapshot, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        ov_res = db.execute(overrides_query).first()
        overrides_count = ov_res.overrides_count if ov_res else 0

        return {
            "distribution": distribution,
            "total_risk_evaluated_bids": total_risk_snapshots,
            "average_risk_score": avg_risk_score,
            "overrides_applied_count": overrides_count,
        }

    # =========================================================================
    # 4. VERIFICATION ANALYTICS
    # =========================================================================

    @classmethod
    def get_verification_analytics(
        cls,
        db: Session,
        org_id: Optional[uuid.UUID] = None,
        tender_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculates verification outcomes and breakdowns by verification type / external source.
        """
        # Status Distribution
        status_query = select(
            VerificationRecord.verification_status,
            func.count(VerificationRecord.id).label("count"),
        )
        if org_id or tender_id:
            status_query = status_query.join(Bid, VerificationRecord.bid_id == Bid.id)
            if tender_id:
                status_query = status_query.where(Bid.tender_id == tender_id)
            if org_id:
                sub_tenders = select(Tender.id).where(Tender.organization_id == org_id)
                status_query = status_query.where(Bid.tender_id.in_(sub_tenders))
        if start_date:
            status_query = status_query.where(VerificationRecord.created_at >= start_date)
        if end_date:
            status_query = status_query.where(VerificationRecord.created_at <= end_date)

        status_query = status_query.group_by(VerificationRecord.verification_status)
        status_rows = db.execute(status_query).all()

        status_distribution = {
            "VERIFIED": 0,
            "NOT_VERIFIED": 0,
            "NEEDS_REVIEW": 0,
            "UNAVAILABLE": 0,
            "FAILED": 0,
            "PENDING": 0,
        }
        total_verifications = 0
        for r in status_rows:
            st = r.verification_status.upper()
            if st in status_distribution:
                status_distribution[st] = r.count
            total_verifications += r.count

        # Source / Type Breakdown
        type_query = select(
            VerificationRecord.verification_type,
            func.count(VerificationRecord.id).label("total"),
            func.count(case((VerificationRecord.verification_status == "VERIFIED", VerificationRecord.id))).label("verified_count"),
            func.count(case((VerificationRecord.verification_status.in_(["FAILED", "NOT_VERIFIED"]), VerificationRecord.id))).label("failed_count"),
            func.count(case((VerificationRecord.verification_status == "NEEDS_REVIEW", VerificationRecord.id))).label("review_count"),
        )
        if org_id or tender_id:
            type_query = type_query.join(Bid, VerificationRecord.bid_id == Bid.id)
            if tender_id:
                type_query = type_query.where(Bid.tender_id == tender_id)
            if org_id:
                sub_tenders = select(Tender.id).where(Tender.organization_id == org_id)
                type_query = type_query.where(Bid.tender_id.in_(sub_tenders))
        if start_date:
            type_query = type_query.where(VerificationRecord.created_at >= start_date)
        if end_date:
            type_query = type_query.where(VerificationRecord.created_at <= end_date)

        type_query = type_query.group_by(VerificationRecord.verification_type)
        type_rows = db.execute(type_query).all()

        source_breakdown = [
            {
                "verification_type": r.verification_type,
                "total": r.total,
                "verified": r.verified_count,
                "failed": r.failed_count,
                "review_required": r.review_count,
                "success_rate": round((r.verified_count / max(r.total, 1)) * 100, 1),
            }
            for r in type_rows
        ]

        return {
            "status_distribution": status_distribution,
            "total_verifications": total_verifications,
            "source_breakdown": source_breakdown,
        }

    # =========================================================================
    # 5. DOCUMENT QUALITY ANALYTICS (PART 11)
    # =========================================================================

    @classmethod
    def get_document_quality_analytics(
        cls,
        db: Session,
        org_id: Optional[uuid.UUID] = None,
        tender_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Aggregates Document Quality check tiers and diagnostics.
        """
        query = select(
            DocumentQualityResult.quality_level,
            func.count(DocumentQualityResult.id).label("count"),
            func.avg(DocumentQualityResult.quality_score).label("avg_score"),
            func.count(case((DocumentQualityResult.is_blurry == True, DocumentQualityResult.id))).label("blurry_count"),
            func.count(case((DocumentQualityResult.has_blank_pages == True, DocumentQualityResult.id))).label("blank_count"),
            func.count(case((DocumentQualityResult.has_low_resolution_pages == True, DocumentQualityResult.id))).label("low_res_count"),
        )
        if org_id or tender_id:
            query = query.join(BidDocument, DocumentQualityResult.document_id == BidDocument.id).join(Bid, BidDocument.bid_id == Bid.id)
            if tender_id:
                query = query.where(Bid.tender_id == tender_id)
            if org_id:
                sub_tenders = select(Tender.id).where(Tender.organization_id == org_id)
                query = query.where(Bid.tender_id.in_(sub_tenders))
        if start_date:
            query = query.where(DocumentQualityResult.created_at >= start_date)
        if end_date:
            query = query.where(DocumentQualityResult.created_at <= end_date)

        query = query.group_by(DocumentQualityResult.quality_level)
        rows = db.execute(query).all()

        distribution = {
            QualityLevel.GOOD: 0,
            QualityLevel.ACCEPTABLE: 0,
            QualityLevel.POOR: 0,
            QualityLevel.UNUSABLE: 0,
        }
        total_docs = 0
        sum_scores = 0.0
        blurry_total = 0
        blank_total = 0
        low_res_total = 0

        for r in rows:
            level = r.quality_level.upper() if r.quality_level else QualityLevel.GOOD
            if level in distribution:
                distribution[level] = r.count
            total_docs += r.count
            if r.avg_score is not None:
                sum_scores += float(r.avg_score) * r.count
            blurry_total += r.blurry_count
            blank_total += r.blank_count
            low_res_total += r.low_res_count

        avg_score = round(sum_scores / total_docs, 1) if total_docs > 0 else None

        return {
            "distribution": distribution,
            "total_documents_analyzed": total_docs,
            "average_quality_score": avg_score,
            "diagnostics": {
                "blurry_documents": blurry_total,
                "blank_page_documents": blank_total,
                "low_resolution_documents": low_res_total,
            },
        }

    # =========================================================================
    # 6. DUPLICATE & REUSE DETECTION ANALYTICS (PART 10)
    # =========================================================================

    @classmethod
    def get_duplicate_analytics(
        cls,
        db: Session,
        org_id: Optional[uuid.UUID] = None,
        tender_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculates duplicate and cross-bid document reuse telemetry.
        """
        # Match Type breakdown
        type_query = select(
            DocumentDuplicateMatch.match_type,
            func.count(DocumentDuplicateMatch.id).label("count"),
        )
        type_query = cls._apply_tender_scope(type_query, DocumentDuplicateMatch, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        type_query = type_query.group_by(DocumentDuplicateMatch.match_type)
        type_rows = db.execute(type_query).all()

        match_types = {
            DuplicateMatchType.EXACT_FILE_DUPLICATE: 0,
            DuplicateMatchType.CONTENT_DUPLICATE: 0,
            DuplicateMatchType.STRUCTURED_DATA_MATCH: 0,
            DuplicateMatchType.HIGH_SIMILARITY: 0,
            DuplicateMatchType.POSSIBLE_REUSE: 0,
        }
        total_matches = 0
        for r in type_rows:
            if r.match_type in match_types:
                match_types[r.match_type] = r.count
            total_matches += r.count

        # Review Status breakdown
        st_query = select(
            DocumentDuplicateMatch.status,
            func.count(DocumentDuplicateMatch.id).label("count"),
        )
        st_query = cls._apply_tender_scope(st_query, DocumentDuplicateMatch, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        st_query = st_query.group_by(DocumentDuplicateMatch.status)
        st_rows = db.execute(st_query).all()

        statuses = {
            DuplicateMatchStatus.DETECTED: 0,
            DuplicateMatchStatus.REVIEW_REQUIRED: 0,
            DuplicateMatchStatus.CONFIRMED_BENIGN: 0,
            DuplicateMatchStatus.CONFIRMED_REUSE: 0,
            DuplicateMatchStatus.DISMISSED: 0,
        }
        for r in st_rows:
            if r.status in statuses:
                statuses[r.status] = r.count

        return {
            "total_duplicate_alerts": total_matches,
            "match_type_distribution": match_types,
            "status_distribution": statuses,
        }

    # =========================================================================
    # 7. BULK EVALUATION ANALYTICS (PART 9)
    # =========================================================================

    @classmethod
    def get_bulk_analytics(
        cls,
        db: Session,
        org_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Aggregates batch verification job progression and throughput metrics.
        """
        query = select(
            BulkEvaluationJob.status,
            func.count(BulkEvaluationJob.id).label("count"),
            func.sum(BulkEvaluationJob.total_bids).label("total_bids_sum"),
            func.sum(BulkEvaluationJob.processed_bids).label("processed_bids_sum"),
            func.sum(BulkEvaluationJob.failed_bids).label("failed_bids_sum"),
        )
        if org_id:
            query = query.where(BulkEvaluationJob.organization_id == org_id)
        if start_date:
            query = query.where(BulkEvaluationJob.created_at >= start_date)
        if end_date:
            query = query.where(BulkEvaluationJob.created_at <= end_date)

        query = query.group_by(BulkEvaluationJob.status)
        rows = db.execute(query).all()

        status_distribution = {
            BulkJobStatus.QUEUED: 0,
            BulkJobStatus.RUNNING: 0,
            BulkJobStatus.COMPLETED: 0,
            BulkJobStatus.PARTIALLY_COMPLETED: 0,
            BulkJobStatus.FAILED: 0,
            BulkJobStatus.CANCELLED: 0,
        }
        total_jobs = 0
        total_bids_processed = 0

        for r in rows:
            if r.status in status_distribution:
                status_distribution[r.status] = r.count
            total_jobs += r.count
            if r.processed_bids_sum:
                total_bids_processed += int(r.processed_bids_sum)

        completed_jobs = status_distribution.get(BulkJobStatus.COMPLETED, 0)
        success_rate = round((completed_jobs / total_jobs) * 100, 1) if total_jobs > 0 else None

        return {
            "total_jobs": total_jobs,
            "status_distribution": status_distribution,
            "total_bids_processed": total_bids_processed,
            "job_success_rate": success_rate,
        }

    # =========================================================================
    # 8. HUMAN REVIEW & FINAL HUMAN DECISION ANALYTICS (PART 8C & 8D)
    # =========================================================================

    @classmethod
    def get_human_review_and_decision_analytics(
        cls,
        db: Session,
        org_id: Optional[uuid.UUID] = None,
        tender_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculates human review queue status, reasons, and authoritative human qualification decisions.
        """
        # 1. Human Review Queue Status
        rev_st_query = select(
            HumanReviewItem.status.label("review_status"),
            func.count(HumanReviewItem.id).label("count"),
        )
        rev_st_query = cls._apply_tender_scope(rev_st_query, HumanReviewItem, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        rev_st_query = rev_st_query.group_by(HumanReviewItem.status)
        rev_st_rows = db.execute(rev_st_query).all()

        review_status_dist = {
            ReviewStatus.OPEN: 0,
            ReviewStatus.IN_REVIEW: 0,
            ReviewStatus.RESOLVED: 0,
            ReviewStatus.ESCALATED: 0,
        }
        total_reviews = 0
        for r in rev_st_rows:
            if r.review_status in review_status_dist:
                review_status_dist[r.review_status] = r.count
            total_reviews += r.count

        # 2. Human Review Reasons
        rev_type_query = select(
            HumanReviewItem.review_type,
            func.count(HumanReviewItem.id).label("count"),
        )
        rev_type_query = cls._apply_tender_scope(rev_type_query, HumanReviewItem, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        rev_type_query = rev_type_query.group_by(HumanReviewItem.review_type)
        rev_type_rows = db.execute(rev_type_query).all()

        review_types = [
            {"review_type": r.review_type, "count": r.count}
            for r in rev_type_rows
        ]

        # 3. Final Human Decisions (Part 8D)
        dec_query = select(
            BidDecision.decision.label("decision_status"),
            func.count(BidDecision.id).label("count"),
        ).where(BidDecision.is_current == True)  # noqa: E712
        dec_query = cls._apply_tender_scope(dec_query, BidDecision, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        dec_query = dec_query.group_by(BidDecision.decision)
        dec_rows = db.execute(dec_query).all()

        decisions_dist = {
            BidDecisionStatus.NOT_DECIDED.value: 0,
            BidDecisionStatus.UNDER_REVIEW.value: 0,
            BidDecisionStatus.QUALIFIED.value: 0,
            BidDecisionStatus.DISQUALIFIED.value: 0,
        }
        total_decisions = 0
        for r in dec_rows:
            if r.decision_status in decisions_dist:
                decisions_dist[r.decision_status] = r.count
            total_decisions += r.count

        # 4. Disqualification Category Breakdown
        disq_query = select(
            BidDecision.category.label("disqualification_category"),
            func.count(BidDecision.id).label("count"),
        ).where(
            and_(
                BidDecision.is_current == True,  # noqa: E712
                BidDecision.decision == BidDecisionStatus.DISQUALIFIED.value,
                BidDecision.category != None,  # noqa: E711
            )
        )
        disq_query = cls._apply_tender_scope(disq_query, BidDecision, org_id=org_id, tender_id=tender_id, start_date=start_date, end_date=end_date)
        disq_query = disq_query.group_by(BidDecision.category)
        disq_rows = db.execute(disq_query).all()

        disqualification_categories = [
            {"category": r.disqualification_category, "count": r.count}
            for r in disq_rows
        ]

        return {
            "total_reviews": total_reviews,
            "review_status_distribution": review_status_dist,
            "review_types_breakdown": review_types,
            "total_human_decisions": total_decisions,
            "decision_status_distribution": decisions_dist,
            "disqualification_categories": disqualification_categories,
        }

    # =========================================================================
    # 9. TIME SERIES ACTIVITY TRENDS
    # =========================================================================

    @classmethod
    def get_time_trends(
        cls,
        db: Session,
        org_id: Optional[uuid.UUID] = None,
        tender_id: Optional[uuid.UUID] = None,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Generates daily time-series counts for bid submissions and evaluation completions.
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Group bids by date(created_at)
        b_query = select(
            func.date_trunc("day", Bid.created_at).label("day"),
            func.count(Bid.id).label("submitted_bids"),
            func.count(case((Bid.status.in_(["EVALUATED", "QUALIFIED", "DISQUALIFIED"]), Bid.id))).label("evaluated_bids"),
        ).where(Bid.created_at >= cutoff_date)
        b_query = cls._apply_tender_scope(b_query, Bid, org_id=org_id, tender_id=tender_id)
        b_query = b_query.group_by(func.date_trunc("day", Bid.created_at)).order_by("day")

        rows = db.execute(b_query).all()

        trend_map: Dict[str, Dict[str, int]] = {}
        # Pre-fill all dates
        for i in range(days + 1):
            d_str = (cutoff_date + timedelta(days=i)).strftime("%Y-%m-%d")
            trend_map[d_str] = {"submitted_bids": 0, "evaluated_bids": 0}

        for r in rows:
            if r.day:
                d_str = r.day.strftime("%Y-%m-%d")
                trend_map[d_str] = {
                    "submitted_bids": r.submitted_bids,
                    "evaluated_bids": r.evaluated_bids,
                }

        return [
            {"date": k, "submitted_bids": v["submitted_bids"], "evaluated_bids": v["evaluated_bids"]}
            for k, v in sorted(trend_map.items())
        ]

    # =========================================================================
    # 10. TENDER SPECIFIC DRILLDOWN
    # =========================================================================

    @classmethod
    def get_tender_specific_analytics(
        cls,
        db: Session,
        tender_id: uuid.UUID,
        org_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Aggregates comprehensive metrics for a specific tender.
        """
        tender_query = select(Tender).where(Tender.id == tender_id)
        if org_id:
            tender_query = tender_query.where(Tender.organization_id == org_id)
        tender = db.scalars(tender_query).first()
        if not tender:
            raise ValueError(f"Tender '{tender_id}' not found or access unauthorized.")

        kpis = cls.get_overview_kpis(db=db, org_id=org_id, tender_id=tender_id)
        compliance = cls.get_compliance_analytics(db=db, org_id=org_id, tender_id=tender_id)
        risk = cls.get_risk_analytics(db=db, org_id=org_id, tender_id=tender_id)
        verif = cls.get_verification_analytics(db=db, org_id=org_id, tender_id=tender_id)
        reviews_and_decisions = cls.get_human_review_and_decision_analytics(db=db, org_id=org_id, tender_id=tender_id)

        return {
            "tender_id": tender.id,
            "tender_number": tender.tender_number,
            "title": tender.title,
            "status": tender.status,
            "estimated_amount": float(tender.estimated_value) if tender.estimated_value else None,
            "overview_kpis": kpis,
            "compliance_analytics": compliance,
            "risk_analytics": risk,
            "verification_analytics": verif,
            "human_reviews_and_decisions": reviews_and_decisions,
        }

    # =========================================================================
    # 11. CSV EXPORT
    # =========================================================================

    @classmethod
    def export_analytics_csv(
        cls,
        db: Session,
        org_id: Optional[uuid.UUID] = None,
        tender_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        """
        Exports comprehensive analytics telemetry as CSV string.
        """
        kpis = cls.get_overview_kpis(db, org_id, tender_id, start_date, end_date)
        comp = cls.get_compliance_analytics(db, org_id, tender_id, start_date, end_date)
        risk = cls.get_risk_analytics(db, org_id, tender_id, start_date, end_date)
        dq = cls.get_document_quality_analytics(db, org_id, tender_id, start_date, end_date)
        dup = cls.get_duplicate_analytics(db, org_id, tender_id, start_date, end_date)
        reviews_dec = cls.get_human_review_and_decision_analytics(db, org_id, tender_id, start_date, end_date)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["=== BIDVERIFY AI PROCUREMENT ANALYTICS & IMPACT REPORT ==="])
        writer.writerow(["Generated At", datetime.now(timezone.utc).isoformat()])
        writer.writerow([])

        writer.writerow(["--- 1. OVERVIEW KPIS ---"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Tenders", kpis["total_tenders"]])
        writer.writerow(["Active Tenders", kpis["active_tenders"]])
        writer.writerow(["Total Bids", kpis["total_bids"]])
        writer.writerow(["Submitted Bids", kpis["submitted_bids"]])
        writer.writerow(["Evaluated Bids", kpis["evaluated_bids"]])
        writer.writerow(["Compliance Rate (%)", kpis["compliance_rate_percentage"] or "N/A"])
        writer.writerow(["Open Reviews", kpis["open_reviews_count"]])
        writer.writerow(["High / Critical Risk Bids", kpis["high_critical_risk_bids"]])
        writer.writerow(["Average Risk Score", kpis["average_risk_score"] or "N/A"])
        writer.writerow(["Poor / Unusable Quality Documents", kpis["poor_quality_documents_count"]])
        writer.writerow(["Duplicate / Reuse Alerts", kpis["duplicate_alerts_count"]])
        writer.writerow([])

        writer.writerow(["--- 2. COMPLIANCE STATUS BREAKDOWN ---"])
        writer.writerow(["Status", "Count"])
        for st, cnt in comp["distribution"].items():
            writer.writerow([st, cnt])
        writer.writerow([])

        writer.writerow(["--- 3. RISK LEVEL DISTRIBUTION ---"])
        writer.writerow(["Level", "Count"])
        for lvl, cnt in risk["distribution"].items():
            writer.writerow([lvl, cnt])
        writer.writerow([])

        writer.writerow(["--- 4. DOCUMENT QUALITY TIERS (PART 11) ---"])
        writer.writerow(["Tier", "Count"])
        for qtier, cnt in dq["distribution"].items():
            writer.writerow([qtier, cnt])
        writer.writerow([])

        writer.writerow(["--- 5. FINAL HUMAN QUALIFICATION DECISIONS (PART 8D) ---"])
        writer.writerow(["Decision", "Count"])
        for dec, cnt in reviews_dec["decision_status_distribution"].items():
            writer.writerow([dec, cnt])

        return output.getvalue()
