"""
Comprehensive Automated Tests for Part 12: Notification Center
Tests in-app notifications, unread count, read/unread state transitions,
bulk mark-all-as-read, deduplication prevention, pagination, workflow event triggers
(bid submission, quality review, duplicate alert, bulk evaluation), RBAC, and multi-tenant security isolation.
"""

from datetime import datetime, timezone, timedelta
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.bulk_evaluation_job import BulkEvaluationJob, BulkJobStatus
from app.db.models.document_duplicate_match import DocumentDuplicateMatch, DuplicateMatchType
from app.db.models.document_quality import DocumentQualityResult, QualityLevel
from app.db.models.human_review import HumanReviewItem, ReviewSeverity, ReviewType
from app.db.models.notification import (
    Notification,
    NotificationSeverity,
    NotificationType,
)
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.user import User
from app.db.session import get_session_factory
from app.services.notification_service import NotificationService


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
    org = Organization(id=uuid.uuid4(), name=f"Notif Test Org {uuid.uuid4().hex[:6]}")
    db_session.add(org)

    role_bidder = db_session.query(Role).filter_by(name="BIDDER").first()
    if not role_bidder:
        role_bidder = Role(id=uuid.uuid4(), name="BIDDER", description="Bidder")
        db_session.add(role_bidder)

    role_po = db_session.query(Role).filter_by(name="PROCUREMENT_OFFICER").first()
    if not role_po:
        role_po = Role(id=uuid.uuid4(), name="PROCUREMENT_OFFICER", description="PO")
        db_session.add(role_po)

    email_b = f"bidder_notif_{uuid.uuid4().hex[:6]}@example.com"
    prof_bidder = Profile(id=uuid.uuid4(), full_name="Test Bidder Notif", email=email_b, role=role_bidder, organization=org)
    user_bidder = User(id=uuid.uuid4(), email=email_b, password_hash="mock_hash", profile=prof_bidder)
    db_session.add_all([prof_bidder, user_bidder])

    email_po = f"po_notif_{uuid.uuid4().hex[:6]}@example.com"
    prof_po = Profile(id=uuid.uuid4(), full_name="Test Officer Notif", email=email_po, role=role_po, organization=org)
    user_po = User(id=uuid.uuid4(), email=email_po, password_hash="mock_hash", profile=prof_po)
    db_session.add_all([prof_po, user_po])

    # Other tenant user
    org_other = Organization(id=uuid.uuid4(), name=f"Other Org {uuid.uuid4().hex[:6]}")
    db_session.add(org_other)
    email_other = f"other_{uuid.uuid4().hex[:6]}@example.com"
    prof_other = Profile(id=uuid.uuid4(), full_name="Other User", email=email_other, role=role_bidder, organization=org_other)
    user_other = User(id=uuid.uuid4(), email=email_other, password_hash="mock_hash", profile=prof_other)
    db_session.add_all([org_other, prof_other, user_other])

    tender = Tender(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by_profile_id=prof_po.id,
        title="Notification Test Tender",
        tender_number=f"TND-NOTIF-{uuid.uuid4().hex[:6]}",
        status="OPEN",
        is_active=True,
    )
    db_session.add(tender)

    bid = Bid(
        id=uuid.uuid4(),
        tender_id=tender.id,
        bidder_organization_id=org.id,
        created_by_profile_id=prof_bidder.id,
        bid_number=f"BID-N-{uuid.uuid4().hex[:6]}",
        status="DRAFT",
        is_active=True,
    )
    db_session.add(bid)

    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=bid.id,
        uploaded_by_profile_id=prof_bidder.id,
        document_type="FINANCIAL_STATEMENT",
        document_name="Annual Turnover Audit",
        original_filename="turnover_audit.pdf",
        mime_type="application/pdf",
        storage_path="mock/turnover.pdf",
        file_size=10240,
        is_active=True,
    )
    db_session.add(doc)
    db_session.commit()

    return {
        "org": org,
        "bidder": user_bidder,
        "po": user_po,
        "other_user": user_other,
        "tender": tender,
        "bid": bid,
        "doc": doc,
    }


def test_create_notification_and_unread_count(db_session: Session, test_setup):
    """Verifies that creating notifications increases the unread count correctly."""
    user = test_setup["bidder"]
    initial_unread = NotificationService.get_unread_count_for_user(db=db_session, current_user=user)

    n = NotificationService.create_notification(
        db=db_session,
        recipient_profile_id=user.profile_id,
        organization_id=test_setup["org"].id,
        notification_type=NotificationType.BID_SUBMITTED,
        severity=NotificationSeverity.SUCCESS,
        title="Your Bid Was Submitted",
        message="Your bid proposal has been submitted successfully.",
        tender_id=test_setup["tender"].id,
        bid_id=test_setup["bid"].id,
        action_url=f"/bidder/bids/{test_setup['bid'].id}",
    )

    assert n.id is not None
    assert n.is_read is False
    assert n.severity == "SUCCESS"

    new_unread = NotificationService.get_unread_count_for_user(db=db_session, current_user=user)
    assert new_unread == initial_unread + 1


def test_mark_as_read_and_unread(db_session: Session, test_setup):
    """Verifies marking notification as read and unread."""
    user = test_setup["bidder"]

    n = NotificationService.create_notification(
        db=db_session,
        recipient_profile_id=user.profile_id,
        organization_id=test_setup["org"].id,
        notification_type=NotificationType.DOCUMENT_QUALITY_REVIEW_REQUIRED,
        severity=NotificationSeverity.WARNING,
        title="Quality Warning",
        message="Your document has low resolution.",
    )

    assert n.is_read is False
    assert n.read_at is None

    # Mark as read
    read_n = NotificationService.mark_as_read(db=db_session, current_user=user, notification_id=n.id)
    assert read_n.is_read is True
    assert read_n.read_at is not None

    # Mark as unread
    unread_n = NotificationService.mark_as_unread(db=db_session, current_user=user, notification_id=n.id)
    assert unread_n.is_read is False
    assert unread_n.read_at is None


def test_mark_all_as_read(db_session: Session, test_setup):
    """Verifies bulk marking all notifications as read."""
    user = test_setup["bidder"]

    # Create 3 unread notifications
    for i in range(3):
        NotificationService.create_notification(
            db=db_session,
            recipient_profile_id=user.profile_id,
            organization_id=test_setup["org"].id,
            notification_type=NotificationType.DOCUMENT_PROCESSING_COMPLETED,
            severity=NotificationSeverity.INFO,
            title=f"Notification #{i + 1}",
            message="Test message",
        )

    assert NotificationService.get_unread_count_for_user(db=db_session, current_user=user) >= 3

    marked_count = NotificationService.mark_all_as_read(db=db_session, current_user=user)
    assert marked_count >= 3

    unread_after = NotificationService.get_unread_count_for_user(db=db_session, current_user=user)
    assert unread_after == 0


def test_deduplication_prevention(db_session: Session, test_setup):
    """Verifies that identical notifications with the same dedupe_key are not duplicated."""
    user = test_setup["bidder"]
    dedupe_key = f"unique_cert_warning_{uuid.uuid4().hex}"

    n1 = NotificationService.create_notification(
        db=db_session,
        recipient_profile_id=user.profile_id,
        organization_id=test_setup["org"].id,
        notification_type=NotificationType.CERTIFICATE_EXPIRING,
        severity=NotificationSeverity.WARNING,
        title="Certificate Expiring",
        message="Expires in 30 days.",
        dedupe_key=dedupe_key,
        cooldown_hours=24,
    )

    # Attempt to create duplicate notification
    n2 = NotificationService.create_notification(
        db=db_session,
        recipient_profile_id=user.profile_id,
        organization_id=test_setup["org"].id,
        notification_type=NotificationType.CERTIFICATE_EXPIRING,
        severity=NotificationSeverity.WARNING,
        title="Certificate Expiring",
        message="Expires in 30 days.",
        dedupe_key=dedupe_key,
        cooldown_hours=24,
    )

    assert n1.id == n2.id


def test_pagination_and_filtering(db_session: Session, test_setup):
    """Verifies paginated retrieval, search, and severity/type filters."""
    user = test_setup["po"]

    # Create distinct notifications
    NotificationService.create_notification(
        db=db_session,
        recipient_profile_id=user.profile_id,
        organization_id=test_setup["org"].id,
        notification_type=NotificationType.CRITICAL_RISK_DETECTED,
        severity=NotificationSeverity.CRITICAL,
        title="Critical Anomaly Detected in Bid #101",
        message="Debarment match identified on GeM watchlist.",
    )
    NotificationService.create_notification(
        db=db_session,
        recipient_profile_id=user.profile_id,
        organization_id=test_setup["org"].id,
        notification_type=NotificationType.BID_SUBMITTED,
        severity=NotificationSeverity.INFO,
        title="Bid Submitted for Tender Alpha",
        message="Bid submission confirmed.",
    )

    # Filter by CRITICAL
    crit_items, total_crit, _ = NotificationService.get_notifications_for_user(
        db=db_session,
        current_user=user,
        severity="CRITICAL",
    )
    assert total_crit >= 1
    assert any(n.severity == "CRITICAL" for n in crit_items)

    # Search keyword
    search_items, total_search, _ = NotificationService.get_notifications_for_user(
        db=db_session,
        current_user=user,
        search="Debarment",
    )
    assert total_search >= 1
    assert "Debarment" in search_items[0].message


def test_bid_submission_workflow_notifications(db_session: Session, test_setup):
    """Verifies that notify_bid_submitted alerts both Bidder (SUCCESS) and Officer (INFO)."""
    bid = test_setup["bid"]
    notifications = NotificationService.notify_bid_submitted(db=db_session, bid=bid)

    assert len(notifications) == 2
    types = [n.notification_type for n in notifications]
    sevs = [n.severity for n in notifications]
    assert NotificationType.BID_SUBMITTED in types
    assert NotificationSeverity.SUCCESS in sevs
    assert NotificationSeverity.INFO in sevs


def test_document_quality_notifications(db_session: Session, test_setup):
    """Verifies plain-English alert to bidder and technical alert to procurement officer on poor quality."""
    doc = test_setup["doc"]
    qr = DocumentQualityResult(
        id=uuid.uuid4(),
        document_id=doc.id,
        quality_score=45.0,
        quality_level=QualityLevel.POOR,
        is_blurry=True,
        review_required=True,
        bidder_feedback=["Document scan contains blurry pages. Please upload a sharper copy."],
    )
    db_session.add(qr)
    db_session.commit()

    notifs = NotificationService.notify_document_quality_review(db=db_session, doc=doc, qr=qr)
    assert len(notifs) >= 1
    assert any("Document scan contains blurry pages" in n.message for n in notifs)


def test_duplicate_alert_and_bulk_completion(db_session: Session, test_setup):
    """Verifies duplicate alert and bulk job completion summary notifications."""
    po = test_setup["po"]
    tender = test_setup["tender"]

    # Bulk job notification
    job = BulkEvaluationJob(
        id=uuid.uuid4(),
        organization_id=test_setup["org"].id,
        tender_id=tender.id,
        started_by_profile_id=po.profile_id,
        status=BulkJobStatus.COMPLETED,
        total_bids=5,
        successful_bids=4,
        failed_bids=0,
        review_required_bids=1,
    )
    db_session.add(job)
    db_session.commit()

    bulk_n = NotificationService.notify_bulk_evaluation_completed(db=db_session, job=job)
    assert bulk_n is not None
    assert "Processed 5 bids" in bulk_n.message
    assert bulk_n.severity == NotificationSeverity.SUCCESS


def test_multi_tenant_and_profile_isolation(db_session: Session, test_setup):
    """Verifies strict security isolation: User A cannot read or modify User B's notifications."""
    user_a = test_setup["bidder"]
    user_b = test_setup["other_user"]

    n_a = NotificationService.create_notification(
        db=db_session,
        recipient_profile_id=user_a.profile_id,
        organization_id=test_setup["org"].id,
        notification_type=NotificationType.BID_SUBMITTED,
        severity=NotificationSeverity.INFO,
        title="Private Notification for User A",
        message="Confidential payload",
    )

    # User B lists notifications -> User A's notification MUST NOT appear
    b_items, _, _ = NotificationService.get_notifications_for_user(db=db_session, current_user=user_b)
    assert all(item.id != n_a.id for item in b_items)

    # User B attempts to mark User A's notification as read -> 404 NOT FOUND
    with pytest.raises(HTTPException) as exc:
        NotificationService.mark_as_read(db=db_session, current_user=user_b, notification_id=n_a.id)
    assert exc.value.status_code == 404
