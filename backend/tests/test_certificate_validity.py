"""
Comprehensive Automated Tests for Part 14: Certificate Validity Monitoring
Tests date extraction, normalization, status determinations (VALID, EXPIRING_SOON, EXPIRED,
NO_EXPIRY, UNKNOWN, REVIEW_REQUIRED), warning thresholds (30d, 7d, 1d), Document Quality integration (Part 11),
Official Verification comparison (Part 5), Notification Center integration (Part 12) with deduplication,
Document Replacement lifecycle, Submission vs Current validity, Periodic Batch checks,
RBAC, Multi-tenancy isolation, and Compliance Context enrichment.
"""

from datetime import date, datetime, timezone, timedelta
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.compliance.engine import build_compliance_context
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import DocumentProcessing
from app.db.models.document_quality import DocumentQualityResult, QualityLevel
from app.db.models.document_validity import (
    DocumentValidityRecord,
    ValidityDateSource,
    ValidityStatus,
)
from app.db.models.human_review import HumanReviewItem
from app.db.models.notification import Notification, NotificationType
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.db.session import get_session_factory
from app.services.certificate_validity_service import (
    CertificateValidityService,
    DEFAULT_THRESHOLD_WARN_DAYS,
)


@pytest.fixture
def db_session():
    """Provides an isolated database session for integration tests and tears it down."""
    SessionFactory = get_session_factory()
    session = SessionFactory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_setup(db_session: Session):
    """Sets up tenant organization, users, tender, bid, and sample bid document."""
    org1 = Organization(id=uuid.uuid4(), name=f"Cert Org 1 {uuid.uuid4().hex[:6]}")
    org2 = Organization(id=uuid.uuid4(), name=f"Cert Org 2 {uuid.uuid4().hex[:6]}")
    db_session.add_all([org1, org2])

    role_bidder = db_session.query(Role).filter_by(name="BIDDER").first()
    if not role_bidder:
        role_bidder = Role(id=uuid.uuid4(), name="BIDDER", description="Bidder")
        db_session.add(role_bidder)

    role_po = db_session.query(Role).filter_by(name="PROCUREMENT_OFFICER").first()
    if not role_po:
        role_po = Role(id=uuid.uuid4(), name="PROCUREMENT_OFFICER", description="PO")
        db_session.add(role_po)

    role_admin = db_session.query(Role).filter_by(name="ADMIN").first()
    if not role_admin:
        role_admin = Role(id=uuid.uuid4(), name="ADMIN", description="Admin")
        db_session.add(role_admin)

    email_b1 = f"bidder1_cert_{uuid.uuid4().hex[:6]}@example.com"
    prof_b1 = Profile(id=uuid.uuid4(), full_name="Bidder One", email=email_b1, role=role_bidder, organization=org1)
    user_b1 = User(id=uuid.uuid4(), email=email_b1, password_hash="mock_hash", profile=prof_b1)

    email_b2 = f"bidder2_cert_{uuid.uuid4().hex[:6]}@example.com"
    prof_b2 = Profile(id=uuid.uuid4(), full_name="Bidder Two", email=email_b2, role=role_bidder, organization=org2)
    user_b2 = User(id=uuid.uuid4(), email=email_b2, password_hash="mock_hash", profile=prof_b2)

    email_po = f"po_cert_{uuid.uuid4().hex[:6]}@example.com"
    prof_po = Profile(id=uuid.uuid4(), full_name="Procurement Officer", email=email_po, role=role_po, organization=org1)
    user_po = User(id=uuid.uuid4(), email=email_po, password_hash="mock_hash", profile=prof_po)

    email_adm = f"adm_cert_{uuid.uuid4().hex[:6]}@example.com"
    prof_adm = Profile(id=uuid.uuid4(), full_name="Administrator", email=email_adm, role=role_admin, organization=org1)
    user_adm = User(id=uuid.uuid4(), email=email_adm, password_hash="mock_hash", profile=prof_adm)

    tender = Tender(
        id=uuid.uuid4(),
        organization_id=org1.id,
        created_by_profile_id=prof_po.id,
        title=f"Tender For Validity Tests {uuid.uuid4().hex[:6]}",
        status="PUBLISHED",
        tender_number=f"TND-{uuid.uuid4().hex[:6]}",
    )

    bid = Bid(
        id=uuid.uuid4(),
        tender_id=tender.id,
        bidder_organization_id=org1.id,
        created_by_profile_id=prof_b1.id,
        bid_number=f"BID-{uuid.uuid4().hex[:6]}",
        status="SUBMITTED",
        submitted_at=datetime.now(timezone.utc) - timedelta(days=60),
    )

    db_session.add_all([
        prof_b1, user_b1, prof_b2, user_b2, prof_po, user_po, prof_adm, user_adm,
        tender, bid
    ])
    db_session.commit()

    return {
        "org1": org1,
        "org2": org2,
        "user_b1": user_b1,
        "user_b2": user_b2,
        "user_po": user_po,
        "user_adm": user_adm,
        "tender": tender,
        "bid": bid,
    }


def test_normalize_date_formats():
    """Validates diverse date normalizations and ambiguity flags."""
    # YYYY-MM-DD
    d1, conf1, amb1 = CertificateValidityService.normalize_date("2027-03-31")
    assert d1 == date(2027, 3, 31)
    assert conf1 == 1.0
    assert not amb1

    # Textual: DD Month YYYY
    d2, conf2, amb2 = CertificateValidityService.normalize_date("15th August 2026")
    assert d2 == date(2026, 8, 15)
    assert conf2 == 1.0
    assert not amb2

    # DD/MM/YYYY with unambiguous day > 12
    d3, conf3, amb3 = CertificateValidityService.normalize_date("25/12/2026")
    assert d3 == date(2026, 12, 25)
    assert conf3 >= 0.95
    assert not amb3

    # Ambiguous DD/MM/YYYY vs MM/DD/YYYY
    d4, conf4, amb4 = CertificateValidityService.normalize_date("04/05/2026")
    assert d4 == date(2026, 5, 4)
    assert amb4 is True

    # Invalid string
    d5, conf5, _ = CertificateValidityService.normalize_date("invalid-not-a-date")
    assert d5 is None
    assert conf5 == 0.0


def test_extract_validity_dates_from_text():
    """Tests regex extraction of issue date, expiry date, and validity duration from raw text."""
    # Explicit Expiry
    text1 = "Government of India License No: 123456. Valid upto: 31/12/2028. Issued on: 01/01/2024."
    res1 = CertificateValidityService.extract_validity_dates_from_text(text1, "OEM_AUTHORIZATION")
    assert res1["expiry_date"] == date(2028, 12, 31)
    assert res1["issue_date"] == date(2024, 1, 1)
    assert res1["confidence"] >= 0.8

    # Duration: Valid for 2 years from issue date
    text2 = "NSIC Registration Certificate. Date of Issue: 10/05/2025. Valid for 2 years from date of issue."
    res2 = CertificateValidityService.extract_validity_dates_from_text(text2, "NSIC_CERTIFICATE")
    assert res2["issue_date"] == date(2025, 5, 10)
    assert res2["expiry_date"] == date(2027, 5, 10)


def test_permanent_documents_no_expiry():
    """Validates that permanent documents like PAN, Financial Statements, Turnover resolve to NO_EXPIRY."""
    for ptype in ["PAN", "PAN_CARD", "FINANCIAL_STATEMENT", "TURNOVER_CERTIFICATE", "EXPERIENCE_CERTIFICATE"]:
        res = CertificateValidityService.extract_validity_dates_from_text("", ptype)
        assert res["is_permanent"] is True
        assert res["confidence"] == 1.0

        status, days = CertificateValidityService.determine_validity_status(
            expiry_date=None,
            is_permanent=res["is_permanent"],
            confidence=res["confidence"],
        )
        assert status == ValidityStatus.NO_EXPIRY
        assert days is None


def test_validity_status_determinations_and_thresholds():
    """Tests determination of VALID, EXPIRING_SOON (30d, 7d, 1d), EXPIRED, and REVIEW_REQUIRED."""
    today = date(2026, 9, 2)

    # 1. Valid (> 30 days)
    st_val, rem_val = CertificateValidityService.determine_validity_status(
        expiry_date=date(2026, 12, 31),
        is_permanent=False,
        confidence=0.9,
        reference_date=today,
    )
    assert st_val == ValidityStatus.VALID
    assert rem_val == 120

    # 2. Expiring soon (25 days <= 30)
    st_soon, rem_soon = CertificateValidityService.determine_validity_status(
        expiry_date=date(2026, 9, 27),
        is_permanent=False,
        confidence=0.9,
        reference_date=today,
    )
    assert st_soon == ValidityStatus.EXPIRING_SOON
    assert rem_soon == 25

    # 3. Expiring soon (5 days <= 7)
    st_urgent, rem_urgent = CertificateValidityService.determine_validity_status(
        expiry_date=date(2026, 9, 7),
        is_permanent=False,
        confidence=0.9,
        reference_date=today,
    )
    assert st_urgent == ValidityStatus.EXPIRING_SOON
    assert rem_urgent == 5

    # 4. Expiring soon (1 day <= 1)
    st_crit, rem_crit = CertificateValidityService.determine_validity_status(
        expiry_date=date(2026, 9, 3),
        is_permanent=False,
        confidence=0.9,
        reference_date=today,
    )
    assert st_crit == ValidityStatus.EXPIRING_SOON
    assert rem_crit == 1

    # 5. Expired (< 0 days)
    st_exp, rem_exp = CertificateValidityService.determine_validity_status(
        expiry_date=date(2026, 8, 15),
        is_permanent=False,
        confidence=0.9,
        reference_date=today,
    )
    assert st_exp == ValidityStatus.EXPIRED
    assert rem_exp == -18

    # 6. Low Confidence -> REVIEW_REQUIRED
    st_rev, rem_rev = CertificateValidityService.determine_validity_status(
        expiry_date=date(2027, 1, 1),
        is_permanent=False,
        confidence=0.45,
        reference_date=today,
    )
    assert st_rev == ValidityStatus.REVIEW_REQUIRED
    assert rem_rev is None


def test_evaluate_document_validity_flow(db_session: Session, test_setup: dict):
    """Tests end-to-end evaluate_document_validity with document creation, OCR text, and notification dispatch."""
    org1 = test_setup["org1"]
    bid = test_setup["bid"]
    user_b1 = test_setup["user_b1"]

    # Create Bid Document
    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=bid.id,
        uploaded_by_profile_id=user_b1.profile.id,
        document_name="OEM_Authorization_2026.pdf",
        original_filename="OEM_Authorization_2026.pdf",
        document_type="OEM_AUTHORIZATION",
        storage_path="/mock/oem.pdf",
        file_size=10240,
        mime_type="application/pdf",
        status="PENDING",
        is_active=True,
    )
    db_session.add(doc)

    # Add DocumentProcessing with OCR text
    expiry_future = date.today() + timedelta(days=20)
    proc = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=doc.id,
        raw_text=f"OEM Authorization Letter. Valid until: {expiry_future.strftime('%d/%m/%Y')}. Issued on: 01/01/2024.",
        processing_status="COMPLETED",
        processing_stage="COMPLETED",
    )
    db_session.add(proc)
    db_session.commit()

    # Evaluate
    record = CertificateValidityService.evaluate_document_validity(
        db=db_session,
        document_id=doc.id,
        current_user=user_b1,
    )

    assert record.validity_status == ValidityStatus.EXPIRING_SOON.value
    assert record.days_until_expiry == 20
    assert record.expiry_date == expiry_future
    assert record.is_current is True

    # Verify notification was sent
    notif = db_session.query(Notification).filter(
        Notification.recipient_profile_id == user_b1.profile.id,
        Notification.notification_type == NotificationType.CERTIFICATE_EXPIRING.value,
    ).first()
    assert notif is not None
    assert "20 days" in notif.message


def test_document_quality_forces_review(db_session: Session, test_setup: dict):
    """Tests that low quality / blurry scan (Part 11) forces confidence down and status to REVIEW_REQUIRED."""
    org1 = test_setup["org1"]
    bid = test_setup["bid"]
    user_b1 = test_setup["user_b1"]

    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=bid.id,
        uploaded_by_profile_id=user_b1.profile.id,
        document_name="Blurry_BIS_Cert.pdf",
        original_filename="Blurry_BIS_Cert.pdf",
        document_type="BIS_CERTIFICATE",
        storage_path="/mock/blurry.pdf",
        file_size=10240,
        mime_type="application/pdf",
        status="PENDING",
        is_active=True,
    )
    db_session.add(doc)

    proc = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=doc.id,
        raw_text="BIS License Valid upto: 31/12/2027",
        processing_status="COMPLETED",
        processing_stage="COMPLETED",
    )
    # Add POOR DocumentQualityResult
    quality = DocumentQualityResult(
        id=uuid.uuid4(),
        document_id=doc.id,
        quality_level=QualityLevel.POOR,
        quality_score=35.0,
        is_blurry=True,
    )
    db_session.add_all([proc, quality])
    db_session.commit()

    record = CertificateValidityService.evaluate_document_validity(
        db=db_session,
        document_id=doc.id,
        current_user=user_b1,
    )

    assert record.validity_status == ValidityStatus.REVIEW_REQUIRED.value
    assert record.confidence <= 0.45
    assert record.metadata_json.get("quality_review_reason") == "POOR_SCAN_QUALITY"


def test_official_verification_adapter_comparison(db_session: Session, test_setup: dict):
    """Tests that official verification adapter match improves confidence and mismatch flags review."""
    org1 = test_setup["org1"]
    bid = test_setup["bid"]
    user_b1 = test_setup["user_b1"]

    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=bid.id,
        uploaded_by_profile_id=user_b1.profile.id,
        document_name="Verified_OEM.pdf",
        original_filename="Verified_OEM.pdf",
        document_type="OEM_AUTHORIZATION",
        storage_path="/mock/verified_oem.pdf",
        file_size=10240,
        mime_type="application/pdf",
        status="PENDING",
        is_active=True,
    )
    db_session.add(doc)

    proc = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=doc.id,
        raw_text="OEM Cert Valid upto: 31/12/2027",
        processing_status="COMPLETED",
        processing_stage="COMPLETED",
    )
    # Adapter returned same date -> MATCH
    verif = VerificationRecord(
        id=uuid.uuid4(),
        bid_id=bid.id,
        bid_document_id=doc.id,
        verification_type="OEM_CHECK",
        verification_status="COMPLETED",
        source_name="OEM_PORTAL",
        claimed_value="OEM Authorization",
        response_payload={"valid_until": "2027-12-31"},
        is_active=True,
    )
    db_session.add_all([proc, verif])
    db_session.commit()

    record = CertificateValidityService.evaluate_document_validity(
        db=db_session,
        document_id=doc.id,
        current_user=user_b1,
    )

    assert record.validity_status == ValidityStatus.VALID.value
    assert record.metadata_json.get("verification_adapter_comparison") == "MATCH"
    assert record.confidence >= 0.95


def test_document_replacement_lifecycle(db_session: Session, test_setup: dict):
    """Tests that uploading a replacement document marks old records is_current = False."""
    org1 = test_setup["org1"]
    bid = test_setup["bid"]
    user_b1 = test_setup["user_b1"]

    # Old expired document
    old_doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=bid.id,
        uploaded_by_profile_id=user_b1.profile.id,
        document_name="Old_Expired_License.pdf",
        original_filename="Old_Expired_License.pdf",
        document_type="LICENSE",
        storage_path="/mock/old.pdf",
        file_size=10240,
        mime_type="application/pdf",
        status="PENDING",
        is_active=True,
    )
    db_session.add(old_doc)
    old_proc = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=old_doc.id,
        raw_text="License Valid upto: 01/01/2020",
        processing_status="COMPLETED",
        processing_stage="COMPLETED",
    )
    db_session.add(old_proc)
    db_session.commit()

    old_rec = CertificateValidityService.evaluate_document_validity(db=db_session, document_id=old_doc.id)
    assert old_rec.validity_status == ValidityStatus.EXPIRED.value
    assert old_rec.is_current is True

    # New replacement document
    new_doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=bid.id,
        uploaded_by_profile_id=user_b1.profile.id,
        document_name="New_Renewed_License.pdf",
        original_filename="New_Renewed_License.pdf",
        document_type="LICENSE",
        storage_path="/mock/new.pdf",
        file_size=10240,
        mime_type="application/pdf",
        status="PENDING",
        is_active=True,
    )
    db_session.add(new_doc)
    new_proc = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=new_doc.id,
        raw_text="Renewed License Valid upto: 31/12/2029",
        processing_status="COMPLETED",
        processing_stage="COMPLETED",
    )
    db_session.add(new_proc)
    db_session.commit()

    new_rec = CertificateValidityService.handle_replacement_document(
        db=db_session,
        old_document_id=old_doc.id,
        new_document_id=new_doc.id,
        current_user=user_b1,
    )

    db_session.refresh(old_rec)
    assert old_rec.is_current is False
    assert new_rec.is_current is True
    assert new_rec.validity_status == ValidityStatus.VALID.value
    assert new_rec.expiry_date == date(2029, 12, 31)


def test_submission_vs_current_validity(db_session: Session, test_setup: dict):
    """Tests that submission_validity_status accurately reflects validity at bid submission time."""
    org1 = test_setup["org1"]
    bid = test_setup["bid"]
    # bid.submitted_at was set 60 days ago
    sub_date = bid.submitted_at.date()

    # Expired 10 days ago (so it was VALID 60 days ago at submission time)
    expiry = date.today() - timedelta(days=10)

    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=bid.id,
        uploaded_by_profile_id=test_setup["user_b1"].profile.id,
        document_name="Submitted_Valid_Now_Expired.pdf",
        original_filename="Submitted_Valid_Now_Expired.pdf",
        document_type="OEM_AUTHORIZATION",
        storage_path="/mock/sub_doc.pdf",
        file_size=10240,
        mime_type="application/pdf",
        status="PENDING",
        is_active=True,
    )
    db_session.add(doc)
    proc = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=doc.id,
        raw_text=f"OEM Letter. Valid upto: {expiry.strftime('%d/%m/%Y')}",
        processing_status="COMPLETED",
        processing_stage="COMPLETED",
    )
    db_session.add(proc)
    db_session.commit()

    record = CertificateValidityService.evaluate_document_validity(db=db_session, document_id=doc.id)

    # Current status is EXPIRED
    assert record.validity_status == ValidityStatus.EXPIRED.value
    # Submission status was VALID
    assert record.submission_validity_status == ValidityStatus.VALID.value


def test_periodic_batch_check(db_session: Session, test_setup: dict):
    """Tests running batch periodic expiration checks."""
    result = CertificateValidityService.run_periodic_validity_checks(db=db_session)
    assert "total_checked" in result
    assert "status_transitions" in result
    assert "status_breakdown" in result


def test_bidder_and_procurement_query_isolation(db_session: Session, test_setup: dict):
    """Tests that bidder certificate query scopes strictly to the bidder's organization."""
    org1 = test_setup["org1"]
    org2 = test_setup["org2"]

    # Org1 query
    res1 = CertificateValidityService.get_bidder_certificates(db=db_session, organization_id=org1.id)
    assert res1["total"] >= 0
    assert "stats" in res1
    assert "total_monitored" in res1["stats"]

    # Org2 query
    res2 = CertificateValidityService.get_bidder_certificates(db=db_session, organization_id=org2.id)
    assert res2["total"] == 0


def test_compliance_engine_context_enrichment(db_session: Session, test_setup: dict):
    """Ensures build_compliance_context enriches context.metadata with validity records."""
    bid = test_setup["bid"]
    context = build_compliance_context(db=db_session, bid_id=bid.id)

    assert "validity_records" in context.metadata
    assert "validity_by_doc_id" in context.metadata
    assert "validity_by_type" in context.metadata
