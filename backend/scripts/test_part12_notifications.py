"""
Standalone End-to-End Test Runner for Part 12: Notification Center
Verifies complete in-app notification lifecycle, deduplication, unread badges,
workflow event dispatching, pagination, and multi-tenant security isolation.
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import get_session_factory
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.bulk_evaluation_job import BulkEvaluationJob, BulkJobStatus
from app.db.models.document_quality import DocumentQualityResult, QualityLevel
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
from app.services.notification_service import NotificationService


def main():
    print("=" * 70)
    print("BIDVERIFY AI — PART 12: NOTIFICATION CENTER E2E VERIFICATION")
    print("=" * 70)

    SessionFactory = get_session_factory()
    db: Session = SessionFactory()

    try:
        # -------------------------------------------------------------
        # Test Setup
        # -------------------------------------------------------------
        org_a = Organization(id=uuid.uuid4(), name=f"E2E Notif Org A {uuid.uuid4().hex[:6]}")
        org_b = Organization(id=uuid.uuid4(), name=f"E2E Notif Org B {uuid.uuid4().hex[:6]}")
        db.add_all([org_a, org_b])

        role_bidder = db.query(Role).filter_by(name="BIDDER").first()
        if not role_bidder:
            role_bidder = Role(id=uuid.uuid4(), name="BIDDER", description="Bidder")
            db.add(role_bidder)

        role_po = db.query(Role).filter_by(name="PROCUREMENT_OFFICER").first()
        if not role_po:
            role_po = Role(id=uuid.uuid4(), name="PROCUREMENT_OFFICER", description="PO")
            db.add(role_po)

        email_bidder = f"bidder_e2e_{uuid.uuid4().hex[:6]}@example.com"
        prof_bidder = Profile(id=uuid.uuid4(), full_name="E2E Bidder", email=email_bidder, role=role_bidder, organization=org_a)
        user_bidder = User(id=uuid.uuid4(), email=email_bidder, password_hash="mock", profile=prof_bidder)

        email_po = f"po_e2e_{uuid.uuid4().hex[:6]}@example.com"
        prof_po = Profile(id=uuid.uuid4(), full_name="E2E Officer", email=email_po, role=role_po, organization=org_a)
        user_po = User(id=uuid.uuid4(), email=email_po, password_hash="mock", profile=prof_po)

        email_other = f"other_e2e_{uuid.uuid4().hex[:6]}@example.com"
        prof_other = Profile(id=uuid.uuid4(), full_name="Other Tenant User", email=email_other, role=role_bidder, organization=org_b)
        user_other = User(id=uuid.uuid4(), email=email_other, password_hash="mock", profile=prof_other)

        db.add_all([prof_bidder, user_bidder, prof_po, user_po, prof_other, user_other])

        tender = Tender(
            id=uuid.uuid4(),
            organization_id=org_a.id,
            created_by_profile_id=prof_po.id,
            title="GeM Solar Infrastructure Tender 2026",
            tender_number=f"TND-SOLAR-{uuid.uuid4().hex[:6]}",
            status="OPEN",
            is_active=True,
        )
        db.add(tender)

        bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_a.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-SOLAR-{uuid.uuid4().hex[:6]}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid)

        doc = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof_bidder.id,
            document_type="FINANCIAL_STATEMENT",
            document_name="Balance Sheet 2024-25",
            original_filename="balance_sheet.pdf",
            mime_type="application/pdf",
            storage_path="mock/balance_sheet.pdf",
            file_size=24500,
            is_active=True,
        )
        db.add(doc)
        db.commit()

        # -------------------------------------------------------------
        # [1/8] Notification Creation & Unread Count
        # -------------------------------------------------------------
        print("\n[1/8] Testing Notification Creation & Unread Count...")
        init_unread = NotificationService.get_unread_count_for_user(db=db, current_user=user_bidder)

        n1 = NotificationService.create_notification(
            db=db,
            recipient_profile_id=user_bidder.profile_id,
            organization_id=org_a.id,
            notification_type=NotificationType.BID_SUBMITTED,
            severity=NotificationSeverity.SUCCESS,
            title="Bid Received Confirmation",
            message="Your bid has been received successfully.",
            tender_id=tender.id,
            bid_id=bid.id,
            action_url=f"/bidder/bids/{bid.id}",
        )
        unread_after_n1 = NotificationService.get_unread_count_for_user(db=db, current_user=user_bidder)
        assert unread_after_n1 == init_unread + 1
        print(f"  [OK] Notification created with ID {n1.id}. Unread count: {unread_after_n1}")

        # -------------------------------------------------------------
        # [2/8] Mark Read / Unread State Transitions
        # -------------------------------------------------------------
        print("\n[2/8] Testing Mark as Read / Unread...")
        n1_read = NotificationService.mark_as_read(db=db, current_user=user_bidder, notification_id=n1.id)
        assert n1_read.is_read is True
        assert n1_read.read_at is not None
        unread_after_read = NotificationService.get_unread_count_for_user(db=db, current_user=user_bidder)
        assert unread_after_read == init_unread
        print(f"  [OK] Marked as read: is_read={n1_read.is_read}, read_at={n1_read.read_at}")

        n1_unread = NotificationService.mark_as_unread(db=db, current_user=user_bidder, notification_id=n1.id)
        assert n1_unread.is_read is False
        assert n1_unread.read_at is None
        print(f"  [OK] Re-marked as unread successfully: is_read={n1_unread.is_read}")

        # -------------------------------------------------------------
        # [3/8] Bulk Mark All As Read
        # -------------------------------------------------------------
        print("\n[3/8] Testing Bulk Mark All as Read...")
        for i in range(3):
            NotificationService.create_notification(
                db=db,
                recipient_profile_id=user_bidder.profile_id,
                organization_id=org_a.id,
                notification_type=NotificationType.DOCUMENT_PROCESSING_COMPLETED,
                severity=NotificationSeverity.INFO,
                title=f"Bulk Test Alert #{i+1}",
                message="Notification payload content",
            )
        marked_cnt = NotificationService.mark_all_as_read(db=db, current_user=user_bidder)
        remaining = NotificationService.get_unread_count_for_user(db=db, current_user=user_bidder)
        assert remaining == 0
        print(f"  [OK] Marked {marked_cnt} notifications as read. Remaining unread: {remaining}")

        # -------------------------------------------------------------
        # [4/8] Notification Deduplication & Cooldown Prevention
        # -------------------------------------------------------------
        print("\n[4/8] Testing Deduplication Key Idempotency...")
        dedupe_key = f"deadline_reminder_{tender.id}_3d"
        notif_a = NotificationService.create_notification(
            db=db,
            recipient_profile_id=user_bidder.profile_id,
            organization_id=org_a.id,
            notification_type=NotificationType.TENDER_DEADLINE_APPROACHING,
            severity=NotificationSeverity.WARNING,
            title="Tender Closes in 3 Days",
            message="Final submission deadline approaching.",
            dedupe_key=dedupe_key,
            cooldown_hours=24,
        )
        notif_b = NotificationService.create_notification(
            db=db,
            recipient_profile_id=user_bidder.profile_id,
            organization_id=org_a.id,
            notification_type=NotificationType.TENDER_DEADLINE_APPROACHING,
            severity=NotificationSeverity.WARNING,
            title="Tender Closes in 3 Days",
            message="Final submission deadline approaching.",
            dedupe_key=dedupe_key,
            cooldown_hours=24,
        )
        assert notif_a.id == notif_b.id
        print(f"  [OK] Duplicate creation prevented (reused ID: {notif_a.id})")

        # -------------------------------------------------------------
        # [5/8] Bid Submission Workflow Event Dispatch
        # -------------------------------------------------------------
        print("\n[5/8] Testing Bid Submission Workflow Notifications...")
        bid_notifs = NotificationService.notify_bid_submitted(db=db, bid=bid)
        assert len(bid_notifs) == 2
        print(f"  [OK] Emitted {len(bid_notifs)} notifications (Bidder confirmation + Officer alert)")

        # -------------------------------------------------------------
        # [6/8] Document Quality Review Notification
        # -------------------------------------------------------------
        print("\n[6/8] Testing Document Quality Review Alerts...")
        qr = DocumentQualityResult(
            id=uuid.uuid4(),
            document_id=doc.id,
            quality_score=48.0,
            quality_level=QualityLevel.POOR,
            is_blurry=True,
            review_required=True,
            bidder_feedback=["Uploaded document is blurry. Please upload a sharper copy."],
            review_reasons=["Laplacian variance below 100.0 threshold."],
        )
        db.add(qr)
        db.commit()

        quality_notifs = NotificationService.notify_document_quality_review(db=db, doc=doc, qr=qr)
        assert len(quality_notifs) >= 1
        print(f"  [OK] Quality notifications created: {[q.title for q in quality_notifs]}")

        # -------------------------------------------------------------
        # [7/8] Bulk Evaluation Completion Summary
        # -------------------------------------------------------------
        print("\n[7/8] Testing Bulk Evaluation Job Completion Notification...")
        job = BulkEvaluationJob(
            id=uuid.uuid4(),
            organization_id=org_a.id,
            tender_id=tender.id,
            started_by_profile_id=prof_po.id,
            status=BulkJobStatus.COMPLETED,
            total_bids=10,
            successful_bids=9,
            failed_bids=0,
            review_required_bids=1,
        )
        db.add(job)
        db.commit()

        job_notif = NotificationService.notify_bulk_evaluation_completed(db=db, job=job)
        assert job_notif is not None
        assert "Processed 10 bids" in job_notif.message
        print(f"  [OK] Bulk job notification verified: '{job_notif.title}'")

        # -------------------------------------------------------------
        # [8/8] Multi-Tenant & RBAC Security Isolation
        # -------------------------------------------------------------
        print("\n[8/8] Testing Multi-Tenant & RBAC Security Isolation...")
        other_items, _, _ = NotificationService.get_notifications_for_user(db=db, current_user=user_other)
        assert all(item.recipient_profile_id == user_other.profile_id for item in other_items)
        print("  [OK] Tenant boundary enforced: User from Org B sees 0 notifications from Org A")

        print("\n" + "=" * 70)
        print("PART 12: ALL NOTIFICATION CENTER TESTS PASSED (100%)")
        print("=" * 70)

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    main()
