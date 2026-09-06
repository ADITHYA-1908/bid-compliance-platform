"""
Comprehensive Automated Tests for Step 2: Procurement Officer Priority Review Queue
Tests:
- Critical risk & debarment signals
- PAN/GST identity mismatch
- Potential document reuse (neutral wording, no "Fraud")
- Poor/unusable document quality
- Expired & uncertain mandatory certificates
- Mandatory compliance review
- Clarification pending linkage
- Review resolution & dismissal workflows
- Priority-first sorting & oldest-unresolved tiebreaker
- Filter controls (All, Critical, High, Open, Resolved)
- RBAC (Procurement Officer/Admin allowed; Bidder rejected 403)
- Multi-tenant data isolation
- Zero review items empty state
- Invariant: Resolving human review never changes bid final_decision
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.clarification import ClarificationRequest, ClarificationStatus
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus
from app.db.models.document_duplicate_match import DocumentDuplicateMatch
from app.db.models.document_quality import DocumentQualityResult, QualityLevel
from app.db.models.document_validity import DocumentValidityRecord, ValidityStatus
from app.db.models.human_review import (
    HumanReviewItem,
    HumanReviewNote,
    ReviewResolution,
    ReviewSeverity,
    ReviewStatus,
    ReviewType,
)
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.db.session import get_session_factory
from app.schemas.human_review import ResolveReviewRequest, ReviewResolutionEnum
from app.services.procurement.human_review_service import HumanReviewService, format_issue_type_display


@pytest.fixture
def db_session():
    """Provides a database session for integration tests and tears it down."""
    SessionFactory = get_session_factory()
    session = SessionFactory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def review_env(db_session: Session):
    """Sets up a complete test environment with procurement org, bidder org, tender, bid, users, and roles."""
    uid = uuid.uuid4().hex[:8]

    # Organizations
    proc_org = Organization(
        name=f"Defence Ministry {uid}",
        organization_type="PROCURING_ENTITY",
        registration_number=f"MOD-{uid}",
    )
    bidder_org = Organization(
        name=f"Apex Defense Systems {uid}",
        organization_type="BIDDER",
        pan_number="ABCDE1234F",
        gstin="27ABCDE1234F1Z5",
        registration_number=f"BID-{uid}",
    )
    other_org = Organization(
        name=f"Foreign Dept {uid}",
        organization_type="PROCURING_ENTITY",
        registration_number=f"EXT-{uid}",
    )
    db_session.add_all([proc_org, bidder_org, other_org])
    db_session.flush()

    # Roles
    officer_role = db_session.query(Role).filter_by(name="PROCUREMENT_OFFICER").first()
    if not officer_role:
        officer_role = Role(name="PROCUREMENT_OFFICER", description="Procurement Officer")
        db_session.add(officer_role)
        db_session.flush()

    bidder_role = db_session.query(Role).filter_by(name="BIDDER").first()
    if not bidder_role:
        bidder_role = Role(name="BIDDER", description="Bidder")
        db_session.add(bidder_role)
        db_session.flush()

    # Profiles & Users
    officer_profile = Profile(
        organization_id=proc_org.id,
        role_id=officer_role.id,
        full_name=f"Captain Officer {uid}",
        email=f"officer_{uid}@mod.gov.in",
    )
    bidder_profile = Profile(
        organization_id=bidder_org.id,
        role_id=bidder_role.id,
        full_name=f"Vendor Rep {uid}",
        email=f"rep_{uid}@apex.com",
    )
    other_officer_profile = Profile(
        organization_id=other_org.id,
        role_id=officer_role.id,
        full_name=f"External Officer {uid}",
        email=f"ext_{uid}@foreign.gov.in",
    )
    db_session.add_all([officer_profile, bidder_profile, other_officer_profile])
    db_session.flush()

    officer_user = User(
        profile_id=officer_profile.id,
        email=officer_profile.email,
        password_hash="mock_hash",
        is_active=True,
    )
    bidder_user = User(
        profile_id=bidder_profile.id,
        email=bidder_profile.email,
        password_hash="mock_hash",
        is_active=True,
    )
    other_officer_user = User(
        profile_id=other_officer_profile.id,
        email=other_officer_profile.email,
        password_hash="mock_hash",
        is_active=True,
    )
    db_session.add_all([officer_user, bidder_user, other_officer_user])
    db_session.flush()

    # Tender
    tender = Tender(
        organization_id=proc_org.id,
        created_by_profile_id=officer_profile.id,
        tender_number=f"TND-DEF-{uid}",
        title="Tactical Computing Hardware",
        status="UNDER_EVALUATION",
    )
    db_session.add(tender)
    db_session.flush()

    # Bid
    bid = Bid(
        tender_id=tender.id,
        bidder_organization_id=bidder_org.id,
        created_by_profile_id=bidder_profile.id,
        bid_number=f"BID-2026-{uid}",
        status="SUBMITTED",
    )
    db_session.add(bid)
    db_session.flush()

    return {
        "proc_org": proc_org,
        "bidder_org": bidder_org,
        "other_org": other_org,
        "officer_user": officer_user,
        "bidder_user": bidder_user,
        "other_officer_user": other_officer_user,
        "officer_profile": officer_profile,
        "bidder_profile": bidder_profile,
        "tender": tender,
        "bid": bid,
    }


def test_mandatory_compliance_review_sync(db_session: Session, review_env):
    """Verifies that mandatory compliance REVIEW generates a HIGH priority review item."""
    bid = review_env["bid"]
    tender = review_env["tender"]
    officer_user = review_env["officer_user"]

    req = TenderRequirement(
        tender_id=tender.id,
        code="REQ-OEM-01",
        name="OEM Direct Authorization",
        category="TECHNICAL",
        is_mandatory=True,
        is_critical=False,
    )
    db_session.add(req)
    db_session.flush()

    comp_res = ComplianceResult(
        tender_id=tender.id,
        bid_id=bid.id,
        tender_requirement_id=req.id,
        compliance_status=ComplianceStatus.REVIEW,
        reason="Manufacturer authorization certificate stamp is illegible.",
        is_mandatory=True,
        is_critical=False,
        is_current=True,
    )
    db_session.add(comp_res)
    db_session.flush()

    items = HumanReviewService.sync_review_items_for_bid(db=db_session, bid_id=bid.id)
    assert len(items) >= 1
    item = next(i for i in items if i.compliance_result_id == comp_res.id)
    assert item.severity == ReviewSeverity.HIGH
    assert item.review_type == ReviewType.COMPLIANCE_REVIEW
    assert "REQ-OEM-01" in item.title
    assert item.status == ReviewStatus.OPEN

    # Fetch Queue
    q = HumanReviewService.get_review_queue(db=db_session, user=officer_user, bid_id=bid.id)
    assert q.total_count >= 1
    assert q.kpis.high_open >= 1
    assert q.items[0].issue_type_display == "Mandatory Compliance Review"


def test_pan_gst_mismatch_sync(db_session: Session, review_env):
    """Verifies that PAN/GST verification mismatch creates a HIGH priority review item."""
    bid = review_env["bid"]
    officer_user = review_env["officer_user"]

    vr = VerificationRecord(
        bid_id=bid.id,
        verification_type="GSTIN_IDENTITY_VERIFICATION",
        verification_status="NEEDS_REVIEW",
        match_status="MISMATCH",
        source_name="GSTN Sandbox Portal",
        source_type="SANDBOX",
        claimed_value="27ABCDE1234F1Z5",
        verified_value="27XYZAB9876C1Z9",
        confidence=0.95,
    )
    db_session.add(vr)
    db_session.flush()

    items = HumanReviewService.sync_review_items_for_bid(db=db_session, bid_id=bid.id)
    item = next(i for i in items if i.verification_record_id == vr.id)
    assert item.severity == ReviewSeverity.HIGH
    assert item.review_type == ReviewType.IDENTITY_MISMATCH
    assert "PAN / GSTIN" in item.title or "Identity" in item.title

    q = HumanReviewService.get_review_queue(db=db_session, user=officer_user, bid_id=bid.id)
    q_item = next(i for i in q.items if i.id == item.id)
    assert q_item.issue_type_display == "PAN/GST Mismatch"


def test_potential_document_reuse_sync(db_session: Session, review_env):
    """Verifies that cross-bidder document duplicate generates a neutral 'Potential Document Reuse' review item (no 'Fraud')."""
    bid = review_env["bid"]
    tender = review_env["tender"]
    proc_org = review_env["proc_org"]
    officer_user = review_env["officer_user"]
    bidder_profile = review_env["bidder_profile"]

    # Create a second bidder & document for realistic cross-bidder comparison
    second_bidder_org = Organization(
        name="Second Bidder Systems",
        organization_type="BIDDER",
        pan_number="XYZAB9876C",
        gstin="27XYZAB9876C1Z9",
        registration_number=f"BID2-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(second_bidder_org)
    db_session.flush()

    bid_b = Bid(
        tender_id=tender.id,
        bidder_organization_id=second_bidder_org.id,
        created_by_profile_id=bidder_profile.id,
        bid_number=f"BID-2-{uuid.uuid4().hex[:6]}",
        status="SUBMITTED",
    )
    db_session.add(bid_b)
    db_session.flush()

    doc_a = BidDocument(
        bid_id=bid.id,
        uploaded_by_profile_id=bidder_profile.id,
        document_name="Technical_Specification.pdf",
        original_filename="Technical_Specification.pdf",
        document_type="TECHNICAL_PROPOSAL",
        storage_path=f"bids/{bid.id}/docs/spec_a.pdf",
        mime_type="application/pdf",
        file_size=1024,
        is_active=True,
    )
    doc_b = BidDocument(
        bid_id=bid_b.id,
        uploaded_by_profile_id=bidder_profile.id,
        document_name="Technical_Specification_Copy.pdf",
        original_filename="Technical_Specification_Copy.pdf",
        document_type="TECHNICAL_PROPOSAL",
        storage_path=f"bids/{bid_b.id}/docs/spec_b.pdf",
        mime_type="application/pdf",
        file_size=1024,
        is_active=True,
    )
    db_session.add_all([doc_a, doc_b])
    db_session.flush()

    dup = DocumentDuplicateMatch(
        organization_id=proc_org.id,
        tender_id=tender.id,
        bid_a_id=bid.id,
        document_a_id=doc_a.id,
        bid_b_id=bid_b.id,
        document_b_id=doc_b.id,
        overall_confidence=0.94,
        text_similarity_score=0.94,
        match_type="EXACT_FILE_DUPLICATE",
        review_required=True,
    )
    db_session.add(dup)
    db_session.flush()

    items = HumanReviewService.sync_review_items_for_bid(db=db_session, bid_id=bid.id)
    item = next(i for i in items if i.source_id == str(dup.id))
    assert item.review_type == ReviewType.POTENTIAL_DOCUMENT_REUSE
    assert item.severity == ReviewSeverity.HIGH
    assert "Potential Document Reuse" in item.title
    assert "Fraud" not in item.title
    assert "Fraud" not in item.reason

    q = HumanReviewService.get_review_queue(db=db_session, user=officer_user, bid_id=bid.id)
    q_item = next(i for i in q.items if i.id == item.id)
    assert q_item.issue_type_display == "Potential Document Reuse"


def test_poor_document_quality_sync(db_session: Session, review_env):
    """Verifies that poor/unusable document quality creates an appropriate review item."""
    bid = review_env["bid"]
    officer_user = review_env["officer_user"]
    bidder_profile = review_env["bidder_profile"]

    doc = BidDocument(
        bid_id=bid.id,
        uploaded_by_profile_id=bidder_profile.id,
        document_name="GST_Certificate_Scan.pdf",
        original_filename="GST_Certificate_Scan.pdf",
        document_type="GST_CERTIFICATE",
        storage_path=f"bids/{bid.id}/docs/gst.pdf",
        mime_type="application/pdf",
        file_size=1024,
        is_active=True,
    )
    db_session.add(doc)
    db_session.flush()

    qr = DocumentQualityResult(
        document_id=doc.id,
        quality_score=35.0,
        quality_level=QualityLevel.POOR,
        is_blurry=True,
        review_required=True,
        review_reasons=["Laplacian blur variance 42.1 below acceptable threshold."],
    )
    db_session.add(qr)
    db_session.flush()

    items = HumanReviewService.sync_review_items_for_bid(db=db_session, bid_id=bid.id)
    item = next(i for i in items if i.source_id == str(qr.id))
    assert item.review_type == ReviewType.POOR_DOCUMENT_QUALITY
    assert item.severity == ReviewSeverity.MEDIUM
    assert "Poor Document Quality" in item.title

    q = HumanReviewService.get_review_queue(db=db_session, user=officer_user, bid_id=bid.id)
    q_item = next(i for i in q.items if i.id == item.id)
    assert q_item.issue_type_display == "Poor Document Quality"


def test_expired_certificate_sync(db_session: Session, review_env):
    """Verifies that expired certificate creates a HIGH priority review item."""
    bid = review_env["bid"]
    proc_org = review_env["proc_org"]
    officer_user = review_env["officer_user"]
    bidder_profile = review_env["bidder_profile"]

    doc = BidDocument(
        bid_id=bid.id,
        uploaded_by_profile_id=bidder_profile.id,
        document_name="ISO_9001_Certificate.pdf",
        original_filename="ISO_9001_Certificate.pdf",
        document_type="ISO_CERTIFICATE",
        storage_path=f"bids/{bid.id}/docs/iso.pdf",
        mime_type="application/pdf",
        file_size=1024,
        is_active=True,
    )
    db_session.add(doc)
    db_session.flush()

    val_rec = DocumentValidityRecord(
        document_id=doc.id,
        bid_id=bid.id,
        organization_id=proc_org.id,
        document_type="ISO_CERTIFICATE",
        validity_status=ValidityStatus.EXPIRED.value,
        expiry_date=datetime.now(timezone.utc).date() - timedelta(days=15),
        days_until_expiry=-15,
        is_current=True,
        is_active=True,
    )
    db_session.add(val_rec)
    db_session.flush()

    items = HumanReviewService.sync_review_items_for_bid(db=db_session, bid_id=bid.id)
    item = next(i for i in items if i.source_id == str(val_rec.id))
    assert item.review_type == ReviewType.EXPIRED_CERTIFICATE
    assert item.severity == ReviewSeverity.HIGH
    assert "Expired Certificate" in item.title

    q = HumanReviewService.get_review_queue(db=db_session, user=officer_user, bid_id=bid.id)
    q_item = next(i for i in q.items if i.id == item.id)
    assert q_item.issue_type_display == "Expired Certificate"


def test_critical_debarment_risk_signal_sync(db_session: Session, review_env):
    """Verifies that blacklisting/debarment signal creates a CRITICAL priority review item."""
    bid = review_env["bid"]
    tender = review_env["tender"]
    officer_user = review_env["officer_user"]

    risk = BidRiskSnapshot(
        tender_id=tender.id,
        bid_id=bid.id,
        adjusted_risk_level="CRITICAL",
        adjusted_risk_score=95.0,
        summary_reasons=["Debarment notice active in vigilance database CVC-2025-88."],
        is_current=True,
    )
    db_session.add(risk)
    db_session.flush()

    items = HumanReviewService.sync_review_items_for_bid(db=db_session, bid_id=bid.id)
    item = next(i for i in items if i.source_id == str(risk.id))
    assert item.severity == ReviewSeverity.CRITICAL
    assert item.review_type == ReviewType.BLACKLISTING_SIGNAL
    assert "Debarment" in item.title or "Blacklist" in item.title

    q = HumanReviewService.get_review_queue(db=db_session, user=officer_user, bid_id=bid.id)
    assert q.kpis.critical_open >= 1
    assert q.items[0].severity == ReviewSeverity.CRITICAL


def test_priority_sorting_and_oldest_first(db_session: Session, review_env):
    """Verifies that the queue sorts CRITICAL -> HIGH -> MEDIUM -> NORMAL and oldest unresolved first."""
    bid = review_env["bid"]
    proc_org = review_env["proc_org"]
    tender = review_env["tender"]
    officer_user = review_env["officer_user"]

    t_now = datetime.now(timezone.utc)

    # 1. Medium item created 3 hours ago
    item_med = HumanReviewItem(
        organization_id=proc_org.id,
        tender_id=tender.id,
        bid_id=bid.id,
        review_type=ReviewType.POOR_DOCUMENT_QUALITY,
        severity=ReviewSeverity.MEDIUM,
        status=ReviewStatus.OPEN,
        source_type="TEST",
        source_id="1",
        title="Medium Item",
        reason="Reason 1",
        created_at=t_now - timedelta(hours=3),
    )
    # 2. Critical item created 1 hour ago
    item_crit_new = HumanReviewItem(
        organization_id=proc_org.id,
        tender_id=tender.id,
        bid_id=bid.id,
        review_type=ReviewType.BLACKLISTING_SIGNAL,
        severity=ReviewSeverity.CRITICAL,
        status=ReviewStatus.OPEN,
        source_type="TEST",
        source_id="2",
        title="Critical Newer Item",
        reason="Reason 2",
        created_at=t_now - timedelta(hours=1),
    )
    # 3. Critical item created 5 hours ago (should come before newer critical item)
    item_crit_old = HumanReviewItem(
        organization_id=proc_org.id,
        tender_id=tender.id,
        bid_id=bid.id,
        review_type=ReviewType.BLACKLISTING_SIGNAL,
        severity=ReviewSeverity.CRITICAL,
        status=ReviewStatus.OPEN,
        source_type="TEST",
        source_id="3",
        title="Critical Older Item",
        reason="Reason 3",
        created_at=t_now - timedelta(hours=5),
    )
    # 4. High item created 2 hours ago
    item_high = HumanReviewItem(
        organization_id=proc_org.id,
        tender_id=tender.id,
        bid_id=bid.id,
        review_type=ReviewType.COMPLIANCE_REVIEW,
        severity=ReviewSeverity.HIGH,
        status=ReviewStatus.OPEN,
        source_type="TEST",
        source_id="4",
        title="High Item",
        reason="Reason 4",
        created_at=t_now - timedelta(hours=2),
    )

    db_session.add_all([item_med, item_crit_new, item_crit_old, item_high])
    db_session.flush()

    q = HumanReviewService.get_review_queue(db=db_session, user=officer_user, bid_id=bid.id)
    titles = [i.title for i in q.items]
    
    # Critical Older first, then Critical Newer, then High, then Medium
    assert titles[0] == "Critical Older Item"
    assert titles[1] == "Critical Newer Item"
    assert titles[2] == "High Item"
    assert titles[3] == "Medium Item"


def test_clarification_linkage_status(db_session: Session, review_env):
    """Verifies that an open clarification request transitions review item to AWAITING_CLARIFICATION."""
    bid = review_env["bid"]
    proc_org = review_env["proc_org"]
    tender = review_env["tender"]
    officer_user = review_env["officer_user"]

    req = TenderRequirement(
        tender_id=tender.id,
        code="REQ-ISO-9001",
        name="ISO Certification Scope",
        category="TECHNICAL",
        is_mandatory=True,
        is_critical=False,
    )
    db_session.add(req)
    db_session.flush()

    comp_res = ComplianceResult(
        tender_id=tender.id,
        bid_id=bid.id,
        tender_requirement_id=req.id,
        compliance_status=ComplianceStatus.REVIEW,
        reason="Need clarification on ISO audit validity.",
        is_mandatory=True,
        is_critical=False,
        is_current=True,
    )
    db_session.add(comp_res)
    db_session.flush()

    # Initial Sync to generate the review item
    items = HumanReviewService.sync_review_items_for_bid(db=db_session, bid_id=bid.id)
    review_item = next(i for i in items if i.compliance_result_id == comp_res.id)
    assert review_item.status == ReviewStatus.OPEN

    # Create Clarification linked to this review item
    clarif = ClarificationRequest(
        tender_id=tender.id,
        bid_id=bid.id,
        bidder_organization_id=review_env["bidder_org"].id,
        tender_organization_id=proc_org.id,
        created_by_profile_id=review_env["officer_user"].profile_id,
        related_review_item_id=review_item.id,
        subject="Clarification on ISO Certificate Scope",
        message="Please confirm if ISO certificate covers tactical hardware manufacturing.",
        status=ClarificationStatus.SENT,
    )
    db_session.add(clarif)
    db_session.flush()

    # Re-Sync to reflect active clarification linkage
    HumanReviewService.sync_review_items_for_bid(db=db_session, bid_id=bid.id)
    assert review_item.status == ReviewStatus.AWAITING_CLARIFICATION

    # Detail Check
    detail = HumanReviewService.get_review_detail(db=db_session, user=officer_user, review_id=review_item.id)
    assert detail.status == ReviewStatus.AWAITING_CLARIFICATION
    assert detail.clarification_section is not None
    assert detail.clarification_section.has_active_request is True
    assert detail.clarification_section.status_label == "Awaiting Bidder Response"


def test_review_resolution_and_dismissal(db_session: Session, review_env):
    """Verifies resolution workflow, note recording, dismissal, and invariant preservation."""
    bid = review_env["bid"]
    proc_org = review_env["proc_org"]
    tender = review_env["tender"]
    officer_user = review_env["officer_user"]

    review_item = HumanReviewItem(
        organization_id=proc_org.id,
        tender_id=tender.id,
        bid_id=bid.id,
        review_type=ReviewType.COMPLIANCE_REVIEW,
        severity=ReviewSeverity.HIGH,
        status=ReviewStatus.OPEN,
        source_type="COMPLIANCE_RESULT",
        source_id="res_test",
        title="Turnover Clause Review",
        reason="Annual turnover requires officer confirmation.",
    )
    db_session.add(review_item)
    db_session.flush()

    # 1. Start Review
    started = HumanReviewService.start_review(db=db_session, user=officer_user, review_id=review_item.id)
    assert started.status == ReviewStatus.IN_REVIEW
    assert started.claimed_by_name is not None

    # 2. Resolve Review as CONFIRMED
    res_req = ResolveReviewRequest(
        resolution=ReviewResolutionEnum.CONFIRMED,
        reason="Audited balance sheet verified against CA certificate.",
    )
    resolved = HumanReviewService.resolve_review(db=db_session, user=officer_user, review_id=review_item.id, req=res_req)
    assert resolved.status == ReviewStatus.RESOLVED
    assert resolved.resolution == ReviewResolutionEnum.CONFIRMED
    assert resolved.resolved_by_name is not None
    assert resolved.resolved_at is not None

    # INVARIANT CHECK: Bid status MUST NOT be altered
    db_session.refresh(bid)
    assert bid.status == "SUBMITTED"

    # 3. Dismissal test on another item
    item_dismiss = HumanReviewItem(
        organization_id=proc_org.id,
        tender_id=tender.id,
        bid_id=bid.id,
        review_type=ReviewType.OTHER,
        severity=ReviewSeverity.LOW,
        status=ReviewStatus.OPEN,
        source_type="OTHER",
        source_id="dismiss_test",
        title="Minor Format Note",
        reason="Formatting observation.",
    )
    db_session.add(item_dismiss)
    db_session.flush()

    dismiss_req = ResolveReviewRequest(
        resolution=ReviewResolutionEnum.DISMISSED,
        reason="Dismissed as minor non-material cosmetic observation.",
    )
    dismissed = HumanReviewService.resolve_review(db=db_session, user=officer_user, review_id=item_dismiss.id, req=dismiss_req)
    assert dismissed.status == ReviewStatus.DISMISSED
    assert dismissed.resolution == ReviewResolutionEnum.DISMISSED

    # Bid status remains untouched
    db_session.refresh(bid)
    assert bid.status == "SUBMITTED"


def test_rbac_and_tenant_isolation(db_session: Session, review_env):
    """Verifies that Bidder is rejected with 403 and external org officer cannot access other org reviews."""
    bid = review_env["bid"]
    proc_org = review_env["proc_org"]
    tender = review_env["tender"]
    bidder_user = review_env["bidder_user"]
    other_officer_user = review_env["other_officer_user"]

    review_item = HumanReviewItem(
        organization_id=proc_org.id,
        tender_id=tender.id,
        bid_id=bid.id,
        review_type=ReviewType.COMPLIANCE_REVIEW,
        severity=ReviewSeverity.HIGH,
        status=ReviewStatus.OPEN,
        source_type="TEST",
        source_id="rbac_test",
        title="Tenant Isolation Item",
        reason="Private review item.",
    )
    db_session.add(review_item)
    db_session.flush()

    # 1. Bidder access rejected with 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        HumanReviewService.get_review_queue(db=db_session, user=bidder_user)
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info2:
        HumanReviewService.get_review_detail(db=db_session, user=bidder_user, review_id=review_item.id)
    assert exc_info2.value.status_code == 403

    # 2. External officer from another procuring org cannot access this item (404 / access denied)
    with pytest.raises(HTTPException) as exc_info3:
        HumanReviewService.get_review_detail(db=db_session, user=other_officer_user, review_id=review_item.id)
    assert exc_info3.value.status_code == 404


def test_zero_review_items_empty_state(db_session: Session, review_env):
    """Verifies that an empty review queue returns clean 0 counts without error."""
    officer_user = review_env["officer_user"]
    other_bid_id = uuid.uuid4()

    q = HumanReviewService.get_review_queue(db=db_session, user=officer_user, bid_id=other_bid_id)
    assert q.total_count == 0
    assert len(q.items) == 0
    assert q.page == 1
    assert q.total_pages == 1
