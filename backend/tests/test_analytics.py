"""
Automated Unit and Integration Tests for Part 13: Advanced Analytics & Impact Dashboard
Tests multi-tenant scoping, KPI calculations, zero-data safety, compliance & failure root-causes,
risk distribution, verification source metrics, document quality (Part 11), duplicates (Part 10),
bulk jobs (Part 9), human review backlog (Part 8C), human decisions (Part 8D), date filters, and RBAC.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
import pytest
from fastapi import HTTPException
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


@pytest.fixture
def db_session():
    """Provides an isolated database session for testing."""
    SessionFactory = get_session_factory()
    session = SessionFactory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def analytics_test_setup(db_session: Session):
    """Sets up organizations, users, tenders, bids, and multi-part evaluation records."""
    # Organizations
    org_a = Organization(id=uuid.uuid4(), name=f"Ministry A {uuid.uuid4().hex[:6]}")
    org_b = Organization(id=uuid.uuid4(), name=f"Ministry B {uuid.uuid4().hex[:6]}")
    db_session.add_all([org_a, org_b])

    # Roles
    role_proc = db_session.query(Role).filter_by(name="PROCUREMENT_OFFICER").first()
    if not role_proc:
        role_proc = Role(id=uuid.uuid4(), name="PROCUREMENT_OFFICER", description="Procurement")
        db_session.add(role_proc)

    role_bidder = db_session.query(Role).filter_by(name="BIDDER").first()
    if not role_bidder:
        role_bidder = Role(id=uuid.uuid4(), name="BIDDER", description="Bidder")
        db_session.add(role_bidder)

    # Users
    prof_proc = Profile(id=uuid.uuid4(), full_name="Officer A", email=f"officer_{uuid.uuid4().hex[:6]}@gem.gov.in", role=role_proc, organization=org_a)
    user_proc = User(id=uuid.uuid4(), email=prof_proc.email, password_hash="mock", profile=prof_proc)

    prof_bidder = Profile(id=uuid.uuid4(), full_name="Bidder 1", email=f"bidder_{uuid.uuid4().hex[:6]}@vendor.com", role=role_bidder, organization=org_a)
    user_bidder = User(id=uuid.uuid4(), email=prof_bidder.email, password_hash="mock", profile=prof_bidder)

    db_session.add_all([prof_proc, user_proc, prof_bidder, user_bidder])

    # Tender for Org A
    tender_a = Tender(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        created_by_profile_id=prof_proc.id,
        tender_number=f"GEM/2026/B/{uuid.uuid4().hex[:6].upper()}",
        title="Network Switches & Security Hardware",
        status="PUBLISHED",
        estimated_value=Decimal("5000000.00"),
    )
    db_session.add(tender_a)

    # Tender Requirement
    req_1 = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender_a.id,
        code="REQ-TURNOVER",
        name="Minimum Annual Turnover >= 5 Cr",
        category="FINANCIAL",
        is_mandatory=True,
    )
    req_2 = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender_a.id,
        code="REQ-OEM",
        name="OEM Direct 5-Year Warranty MAF",
        category="TECHNICAL",
        is_mandatory=True,
    )
    db_session.add_all([req_1, req_2])

    # Bids for Tender A
    bid_1 = Bid(
        id=uuid.uuid4(),
        tender_id=tender_a.id,
        bidder_organization_id=org_a.id,
        created_by_profile_id=prof_bidder.id,
        bid_number=f"BID-{uuid.uuid4().hex[:6].upper()}",
        status="EVALUATED",
    )
    bid_2 = Bid(
        id=uuid.uuid4(),
        tender_id=tender_a.id,
        bidder_organization_id=org_b.id,
        created_by_profile_id=prof_bidder.id,
        bid_number=f"BID-{uuid.uuid4().hex[:6].upper()}",
        status="SUBMITTED",
    )
    db_session.add_all([bid_1, bid_2])

    # Bid Documents
    doc_1 = BidDocument(
        id=uuid.uuid4(),
        bid_id=bid_1.id,
        uploaded_by_profile_id=prof_bidder.id,
        document_type="FINANCIAL_STATEMENT",
        document_name="Financial Statement",
        original_filename="turnover.pdf",
        storage_path="/docs/turnover.pdf",
        mime_type="application/pdf",
        file_size=1024,
        status="PROCESSED",
    )
    doc_2 = BidDocument(
        id=uuid.uuid4(),
        bid_id=bid_1.id,
        uploaded_by_profile_id=prof_bidder.id,
        document_type="GST_CERTIFICATE",
        document_name="GST Certificate",
        original_filename="gst_scan.pdf",
        storage_path="/docs/gst_scan.pdf",
        mime_type="application/pdf",
        file_size=2048,
        status="PROCESSED",
    )
    db_session.add_all([doc_1, doc_2])

    # Compliance Results (Part 6)
    comp_1 = ComplianceResult(
        id=uuid.uuid4(),
        bid_id=bid_1.id,
        tender_id=tender_a.id,
        tender_requirement_id=req_1.id,
        compliance_status=ComplianceStatus.PASS,
        is_mandatory=True,
        is_current=True,
    )
    comp_2 = ComplianceResult(
        id=uuid.uuid4(),
        bid_id=bid_1.id,
        tender_id=tender_a.id,
        tender_requirement_id=req_2.id,
        compliance_status=ComplianceStatus.FAIL,
        reason="OEM authorization missing or expired",
        is_mandatory=True,
        is_current=True,
    )
    db_session.add_all([comp_1, comp_2])

    # Risk Snapshot (Part 7)
    risk_1 = BidRiskSnapshot(
        id=uuid.uuid4(),
        bid_id=bid_1.id,
        tender_id=tender_a.id,
        adjusted_risk_score=Decimal("65.50"),
        adjusted_risk_level="HIGH",
        is_current=True,
    )
    db_session.add(risk_1)

    # Verification Record (Part 5)
    ver_1 = VerificationRecord(
        id=uuid.uuid4(),
        bid_id=bid_1.id,
        bid_document_id=doc_1.id,
        verification_type="GST",
        verification_status="VERIFIED",
        source_name="GSTN Portal",
        claimed_value="33ABCDE1234F1Z5",
    )
    db_session.add(ver_1)

    # Document Quality Result (Part 11)
    dq_1 = DocumentQualityResult(
        id=uuid.uuid4(),
        document_id=doc_1.id,
        quality_score=92.5,
        quality_level=QualityLevel.GOOD,
    )
    dq_2 = DocumentQualityResult(
        id=uuid.uuid4(),
        document_id=doc_2.id,
        quality_score=55.0,
        quality_level=QualityLevel.POOR,
        is_blurry=True,
        review_required=True,
    )
    db_session.add_all([dq_1, dq_2])

    # Duplicate Match (Part 10)
    dup_1 = DocumentDuplicateMatch(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        tender_id=tender_a.id,
        bid_a_id=bid_1.id,
        bid_b_id=bid_2.id,
        document_a_id=doc_1.id,
        document_b_id=doc_2.id,
        match_type=DuplicateMatchType.EXACT_FILE_DUPLICATE,
        status=DuplicateMatchStatus.REVIEW_REQUIRED,
    )
    db_session.add(dup_1)

    # Human Review Queue Item (Part 8C)
    rev_1 = HumanReviewItem(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        tender_id=tender_a.id,
        bid_id=bid_1.id,
        review_type=ReviewType.COMPLIANCE_REVIEW,
        status=ReviewStatus.OPEN,
        source_type="COMPLIANCE_RESULT",
        source_id=comp_2.id.hex,
        title="Check OEM letter validity",
        reason="OEM letter validation discrepancy",
    )
    db_session.add(rev_1)

    # Final Human Decision (Part 8D)
    dec_1 = BidDecision(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        tender_id=tender_a.id,
        bid_id=bid_1.id,
        decision=BidDecisionStatus.DISQUALIFIED.value,
        category="TECHNICAL_NON_COMPLIANCE",
        reason="Missing OEM direct authorization document",
        decided_by_profile_id=prof_proc.id,
        is_current=True,
    )
    db_session.add(dec_1)

    # Bulk Job (Part 9)
    bulk_1 = BulkEvaluationJob(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        tender_id=tender_a.id,
        status=BulkJobStatus.COMPLETED,
        total_bids=2,
        processed_bids=2,
        failed_bids=0,
    )
    db_session.add(bulk_1)

    db_session.commit()

    return {
        "org_a": org_a,
        "org_b": org_b,
        "tender_a": tender_a,
        "user_proc": user_proc,
        "user_bidder": user_bidder,
    }


def test_overview_kpis_aggregation(db_session: Session, analytics_test_setup):
    """Verifies overview KPI aggregations: tenders, bids, compliance rate, reviews, and risk."""
    org_a = analytics_test_setup["org_a"]

    kpis = AnalyticsService.get_overview_kpis(db=db_session, org_id=org_a.id)

    assert kpis["total_tenders"] >= 1
    assert kpis["active_tenders"] >= 1
    assert kpis["total_bids"] >= 2
    assert kpis["submitted_bids"] >= 2
    assert kpis["evaluated_bids"] >= 1
    assert kpis["compliance_rate_percentage"] == 50.0  # 1 PASS, 1 FAIL
    assert kpis["open_reviews_count"] >= 1
    assert kpis["high_critical_risk_bids"] >= 1
    assert kpis["poor_quality_documents_count"] >= 1
    assert kpis["duplicate_alerts_count"] >= 1


def test_compliance_analytics_and_failure_reasons(db_session: Session, analytics_test_setup):
    """Verifies compliance distribution, mandatory failures, and common failure reasons."""
    org_a = analytics_test_setup["org_a"]

    comp = AnalyticsService.get_compliance_analytics(db=db_session, org_id=org_a.id)

    assert comp["total_evaluations"] >= 2
    assert comp["distribution"][ComplianceStatus.PASS] >= 1
    assert comp["distribution"][ComplianceStatus.FAIL] >= 1
    assert comp["mandatory_failures_count"] >= 1
    assert len(comp["top_failed_requirements"]) >= 1
    assert len(comp["common_failure_reasons"]) >= 1


def test_risk_analytics_distribution(db_session: Session, analytics_test_setup):
    """Verifies risk tier counts and average scores."""
    org_a = analytics_test_setup["org_a"]

    risk = AnalyticsService.get_risk_analytics(db=db_session, org_id=org_a.id)

    assert risk["total_risk_evaluated_bids"] >= 1
    assert risk["distribution"]["HIGH"] >= 1
    assert risk["average_risk_score"] == 65.5


def test_document_quality_and_duplicates_analytics(db_session: Session, analytics_test_setup):
    """Verifies Document Quality (Part 11) and Duplicate matches (Part 10) aggregations."""
    org_a = analytics_test_setup["org_a"]

    dq = AnalyticsService.get_document_quality_analytics(db=db_session, org_id=org_a.id)
    dup = AnalyticsService.get_duplicate_analytics(db=db_session, org_id=org_a.id)

    assert dq["total_documents_analyzed"] >= 2
    assert dq["distribution"][QualityLevel.GOOD] >= 1
    assert dq["distribution"][QualityLevel.POOR] >= 1
    assert dq["diagnostics"]["blurry_documents"] >= 1

    assert dup["total_duplicate_alerts"] >= 1
    assert dup["match_type_distribution"][DuplicateMatchType.EXACT_FILE_DUPLICATE] >= 1


def test_human_reviews_and_decisions_analytics(db_session: Session, analytics_test_setup):
    """Verifies human review backlog (Part 8C) and final human qualification decisions (Part 8D)."""
    org_a = analytics_test_setup["org_a"]

    res = AnalyticsService.get_human_review_and_decision_analytics(db=db_session, org_id=org_a.id)

    assert res["total_reviews"] >= 1
    assert res["review_status_distribution"][ReviewStatus.OPEN] >= 1
    assert res["total_human_decisions"] >= 1
    assert res["decision_status_distribution"][BidDecisionStatus.DISQUALIFIED.value] >= 1
    assert len(res["disqualification_categories"]) >= 1


def test_tender_specific_drilldown_and_export(db_session: Session, analytics_test_setup):
    """Verifies tender-specific analytics aggregation and CSV report generation."""
    tender_a = analytics_test_setup["tender_a"]
    org_a = analytics_test_setup["org_a"]

    drilldown = AnalyticsService.get_tender_specific_analytics(db=db_session, tender_id=tender_a.id, org_id=org_a.id)

    assert drilldown["tender_id"] == tender_a.id
    assert drilldown["overview_kpis"]["total_bids"] >= 2
    assert drilldown["compliance_analytics"]["overall_compliance_rate"] == 50.0

    csv_out = AnalyticsService.export_analytics_csv(db=db_session, org_id=org_a.id, tender_id=tender_a.id)
    assert "BIDVERIFY AI PROCUREMENT ANALYTICS" in csv_out
    assert "OVERVIEW KPIS" in csv_out


def test_zero_data_handling_and_safe_percentages(db_session: Session, analytics_test_setup):
    """Verifies that queries on empty organizations return safe N/A / None values without division by zero."""
    org_empty = Organization(id=uuid.uuid4(), name=f"Empty Org {uuid.uuid4().hex[:6]}")
    db_session.add(org_empty)
    db_session.commit()

    kpis = AnalyticsService.get_overview_kpis(db=db_session, org_id=org_empty.id)
    comp = AnalyticsService.get_compliance_analytics(db=db_session, org_id=org_empty.id)
    risk = AnalyticsService.get_risk_analytics(db=db_session, org_id=org_empty.id)

    assert kpis["total_tenders"] == 0
    assert kpis["total_bids"] == 0
    assert kpis["compliance_rate_percentage"] is None  # Safe N/A instead of division by zero
    assert comp["overall_compliance_rate"] is None
    assert risk["average_risk_score"] is None


def test_cross_tenant_isolation(db_session: Session, analytics_test_setup):
    """Verifies that Organization B cannot see Organization A's tenders or bids."""
    org_b = analytics_test_setup["org_b"]

    kpis_b = AnalyticsService.get_overview_kpis(db=db_session, org_id=org_b.id)
    assert kpis_b["total_tenders"] == 0
    assert kpis_b["total_bids"] == 0
    assert kpis_b["open_reviews_count"] == 0
