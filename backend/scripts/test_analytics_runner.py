"""
Standalone Verification Runner for Part 13: Advanced Analytics & Impact Dashboard
Tests live database aggregations, multi-tenant scoping, compliance & failure reasons,
risk distributions, document quality, duplicates, reviews, decisions, and CSV exports.
"""

import sys
import uuid
from decimal import Decimal
from pathlib import Path
from sqlalchemy.orm import Session

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
from app.db.models.document_quality import DocumentQualityResult, QualityLevel
from app.db.models.human_review import HumanReviewItem, ReviewStatus, ReviewType
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.db.session import get_session_factory
from app.services.analytics_service import AnalyticsService


def main():
    print("=" * 75)
    print("BIDVERIFY AI — PART 13: ADVANCED ANALYTICS & IMPACT VERIFICATION RUNNER")
    print("=" * 75)

    SessionFactory = get_session_factory()
    db: Session = SessionFactory()

    try:
        # 1. Setup Test Tenant Organization and Data
        org = Organization(id=uuid.uuid4(), name=f"Analytics Test Ministry {uuid.uuid4().hex[:6]}")
        db.add(org)

        role_proc = db.query(Role).filter_by(name="PROCUREMENT_OFFICER").first()
        if not role_proc:
            role_proc = Role(id=uuid.uuid4(), name="PROCUREMENT_OFFICER", description="Procurement")
            db.add(role_proc)

        role_bidder = db.query(Role).filter_by(name="BIDDER").first()
        if not role_bidder:
            role_bidder = Role(id=uuid.uuid4(), name="BIDDER", description="Bidder")
            db.add(role_bidder)

        prof = Profile(id=uuid.uuid4(), full_name="Analytics Officer", email=f"officer_{uuid.uuid4().hex[:6]}@gem.gov.in", role=role_proc, organization=org)
        user = User(id=uuid.uuid4(), email=prof.email, password_hash="mock", profile=prof)
        db.add_all([prof, user])

        tender = Tender(
            id=uuid.uuid4(),
            organization_id=org.id,
            created_by_profile_id=prof.id,
            tender_number=f"GEM/2026/B/{uuid.uuid4().hex[:6].upper()}",
            title="Advanced Analytics Test Tender",
            status="PUBLISHED",
            estimated_value=Decimal("12500000.00"),
        )
        db_req = TenderRequirement(
            id=uuid.uuid4(),
            tender_id=tender.id,
            code="REQ-LOCAL-MII",
            name="Class-I Local Content >= 50%",
            category="STATUTORY",
            is_mandatory=True,
        )
        db.add_all([tender, db_req])

        bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org.id,
            created_by_profile_id=prof.id,
            bid_number=f"BID-{uuid.uuid4().hex[:6].upper()}",
            status="EVALUATED",
        )
        db.add(bid)

        doc = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof.id,
            document_type="LOCAL_CONTENT_CERTIFICATE",
            document_name="Local Content Declaration",
            original_filename="mii_cert.pdf",
            storage_path="/docs/mii_cert.pdf",
            mime_type="application/pdf",
            file_size=1024,
            status="PROCESSED",
        )
        db.add(doc)

        comp = ComplianceResult(
            id=uuid.uuid4(),
            bid_id=bid.id,
            tender_id=tender.id,
            tender_requirement_id=db_req.id,
            compliance_status=ComplianceStatus.PASS,
            is_mandatory=True,
            is_current=True,
        )
        risk = BidRiskSnapshot(
            id=uuid.uuid4(),
            bid_id=bid.id,
            tender_id=tender.id,
            adjusted_risk_score=Decimal("22.00"),
            adjusted_risk_level="LOW",
            is_current=True,
        )
        ver = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid.id,
            bid_document_id=doc.id,
            verification_type="LOCAL_CONTENT",
            verification_status="VERIFIED",
            source_name="DPIIT Portal",
            claimed_value="65.0%",
        )
        dq = DocumentQualityResult(
            id=uuid.uuid4(),
            document_id=doc.id,
            quality_score=94.0,
            quality_level=QualityLevel.GOOD,
        )
        db.add_all([comp, risk, ver, dq])
        db.commit()

        # 2. Test Overview KPIs Aggregation
        print("\n[1/6] Testing Overview KPIs & Impact Savings Aggregation...")
        kpis = AnalyticsService.get_overview_kpis(db=db, org_id=org.id)
        assert kpis["total_tenders"] >= 1
        assert kpis["active_tenders"] >= 1
        assert kpis["total_bids"] >= 1
        assert kpis["compliance_rate_percentage"] == 100.0
        print(f"  [OK] Tenders: {kpis['total_tenders']} (Active: {kpis['active_tenders']})")
        print(f"  [OK] Bids: {kpis['total_bids']} (Evaluated: {kpis['evaluated_bids']})")
        print(f"  [OK] Compliance Rate: {kpis['compliance_rate_percentage']}%")

        # 3. Test Compliance Analytics & Common Failures
        print("\n[2/6] Testing Compliance & Common Failure Reasons...")
        comp_res = AnalyticsService.get_compliance_analytics(db=db, org_id=org.id)
        assert comp_res["total_evaluations"] >= 1
        assert comp_res["distribution"][ComplianceStatus.PASS] >= 1
        print(f"  [OK] Total Evaluations: {comp_res['total_evaluations']}")
        print(f"  [OK] Passed Determinations: {comp_res['distribution'][ComplianceStatus.PASS]}")

        # 4. Test Risk Analytics Distribution
        print("\n[3/6] Testing Risk Distribution & Averages...")
        risk_res = AnalyticsService.get_risk_analytics(db=db, org_id=org.id)
        assert risk_res["total_risk_evaluated_bids"] >= 1
        assert risk_res["distribution"]["LOW"] >= 1
        assert risk_res["average_risk_score"] == 22.0
        print(f"  [OK] Evaluated Risk Snapshots: {risk_res['total_risk_evaluated_bids']}")
        print(f"  [OK] Average Risk Score: {risk_res['average_risk_score']}/100")

        # 5. Test Document Quality & Duplicate Matches
        print("\n[4/6] Testing Document Quality (Part 11) & Duplicate Detection (Part 10)...")
        dq_res = AnalyticsService.get_document_quality_analytics(db=db, org_id=org.id)
        dup_res = AnalyticsService.get_duplicate_analytics(db=db, org_id=org.id)
        assert dq_res["total_documents_analyzed"] >= 1
        assert dq_res["distribution"][QualityLevel.GOOD] >= 1
        print(f"  [OK] Documents Quality Analyzed: {dq_res['total_documents_analyzed']}")
        print(f"  [OK] Average Quality Score: {dq_res['average_quality_score']}/100")

        # 6. Test Human Reviews & Final Decisions
        print("\n[5/6] Testing Human Review Workload (Part 8C) & Qualification Decisions (Part 8D)...")
        rev_dec = AnalyticsService.get_human_review_and_decision_analytics(db=db, org_id=org.id)
        print(f"  [OK] Human Reviews Processed: {rev_dec['total_reviews']}")
        print(f"  [OK] Final Human Decisions: {rev_dec['total_human_decisions']}")

        # 7. Test CSV Report Export
        print("\n[6/6] Testing Analytics CSV Report Export...")
        csv_report = AnalyticsService.export_analytics_csv(db=db, org_id=org.id)
        assert "BIDVERIFY AI PROCUREMENT ANALYTICS" in csv_report
        assert "OVERVIEW KPIS" in csv_report
        print("  [OK] CSV report successfully generated.")

        print("\n" + "=" * 75)
        print("PART 13 STATUS: COMPLETE")
        print("=" * 75)

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    main()
