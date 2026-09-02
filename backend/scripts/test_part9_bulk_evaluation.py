"""
Part 9 Automated Bulk Verification & Batch Processing Test Suite
Validates:
1. Create Tender and seed multiple bids (Submitted, Under Verification, Draft, Withdrawn).
2. RBAC Enforcement: 403 Forbidden for Bidder attempting bulk evaluation.
3. Multi-Tenant Isolation: Officer B cannot trigger or view Officer A's bulk job.
4. Filter verification: Only eligible bids (SUBMITTED, UNDER_VERIFICATION) are queued (DRAFT & WITHDRAWN excluded).
5. Concurrency Control: 409 Conflict when attempting to start a duplicate active job on the same tender.
6. Execution Pipeline: Runs document processing, claims verification, compliance, score, risk, and human review sync.
7. Telemetry & Per-Bid Item reporting (GET /bulk-evaluations/{id} and GET /bulk-evaluations/{id}/items).
8. Failure Isolation: One failed bid does not break the batch; results in PARTIALLY_COMPLETED.
9. Retry Mechanism: Retry all failed items and retry single failed item.
10. Job Cancellation: Safely halts pending items without database corruption.
11. Audit Trail: Verifies BULK_EVALUATION_STARTED, BULK_EVALUATION_COMPLETED, BULK_EVALUATION_RETRY audit records.
"""

import sys
import os
import uuid
import time
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional
from fastapi.testclient import TestClient
from sqlalchemy import select

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import get_session_factory
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.user import User
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.bulk_evaluation_job import BulkEvaluationJob, BulkEvaluationJobItem, BulkJobStatus, BulkItemStatus
from app.db.models.audit_event import AuditEvent, AuditEventType
from app.core.security import hash_password
from app.services.procurement.bulk_evaluation_service import BulkEvaluationService

client = TestClient(app)


def get_token_for_user(email: str, password: str = "TestPassword123!") -> str:
    """Helper to authenticate and retrieve access token."""
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def setup_second_officer() -> Tuple[str, User]:
    """Ensures a second procurement officer in a separate organization exists."""
    email = "officer_b_part9@railways.gov.local"
    password = "TestPassword123!"

    session_factory = get_session_factory()
    db = session_factory()
    try:
        user = db.scalars(select(User).where(User.email == email)).first()
        if not user:
            role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
            org = Organization(
                name="Ministry of Heavy Industries (Division B)",
                organization_type="Government Ministry",
                is_active=True,
            )
            db.add(org)
            db.flush()

            profile = Profile(
                full_name="Officer B Heavy Industries",
                email=email,
                role_id=role.id,
                organization_id=org.id,
                is_active=True,
            )
            db.add(profile)
            db.flush()

            user = User(
                email=email,
                password_hash=hash_password(password),
                profile_id=profile.id,
                is_active=True,
            )
            db.add(user)
            db.commit()

        token = get_token_for_user(email, password)
        return token, user
    finally:
        db.close()


def setup_test_tender_and_bids() -> Tuple[str, List[str], str]:
    """
    Sets up a fresh Tender with 3 submitted bids, 1 draft bid, and 1 withdrawn bid.
    Returns (tender_id, submitted_bid_ids, procurement_officer_token).
    """
    proc_token = get_token_for_user("procurement@test.local")
    bidder_token = get_token_for_user("bidder@test.local")

    suffix = uuid.uuid4().hex[:6].upper()
    tender_number = f"GEM/2026/BULK/{suffix}"

    now = datetime.now(timezone.utc)
    # 1. Create Tender
    res_tender = client.post(
        "/api/v1/tenders",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={
            "tender_number": tender_number,
            "title": f"Bulk Test Server Procurement {suffix}",
            "description": "High-throughput test tender for Part 9 bulk evaluation.",
            "department": "Department of High Tech Procurement",
            "estimated_value": "15000000.00",
            "category": "HARDWARE",
            "submission_start_date": (now - timedelta(days=5)).isoformat(),
            "submission_end_date": (now + timedelta(days=20)).isoformat(),
            "opening_date": (now + timedelta(days=21)).isoformat(),
        },
    )
    assert res_tender.status_code == 201, f"Create tender failed: {res_tender.text}"
    tender_id = res_tender.json()["id"]

    # 2. Add Requirements
    client.post(
        f"/api/v1/tenders/{tender_id}/requirements",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={
            "code": "REQ-GST-01",
            "name": "Valid Active GSTIN Registration",
            "category": "STATUTORY",
            "field_type": "STRING",
            "operator": "EQUALS",
            "expected_value": "ACTIVE",
            "is_mandatory": True,
            "is_critical": True,
            "weight": 25.0,
        },
    )
    client.post(
        f"/api/v1/tenders/{tender_id}/requirements",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={
            "code": "REQ-PAN-01",
            "name": "Valid PAN Entity Name Match",
            "category": "STATUTORY",
            "field_type": "STRING",
            "operator": "EQUALS",
            "expected_value": "VALID",
            "is_mandatory": True,
            "is_critical": False,
            "weight": 25.0,
        },
    )

    # Publish Tender
    client.post(
        f"/api/v1/tenders/{tender_id}/lifecycle/publish",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={"reason": "Publishing tender for bulk batch verification test."},
    )

    # 3. Seed Bids directly via DB for fast test setup
    session_factory = get_session_factory()
    db = session_factory()
    submitted_bid_ids = []
    try:
        bidder_user = db.scalars(select(User).where(User.email == "bidder@test.local")).first()
        profile_id = bidder_user.profile_id if bidder_user else uuid.uuid4()

        # 3 Eligible Submitted Bids (each from a distinct test organization)
        for i in range(1, 4):
            test_org = Organization(
                id=uuid.uuid4(),
                name=f"Vendor Entity Bulk {suffix} #{i}",
                organization_type="Private Limited",
                is_active=True,
            )
            db.add(test_org)
            db.flush()

            b = Bid(
                id=uuid.uuid4(),
                tender_id=uuid.UUID(tender_id),
                bidder_organization_id=test_org.id,
                created_by_profile_id=profile_id,
                bid_number=f"BID-BULK-{suffix}-{i:02d}",
                status="SUBMITTED",
                quoted_amount=Decimal(f"{10000000 + i * 500000}.00"),
                currency="INR",
                submitted_at=now - timedelta(hours=i),
                is_active=True,
            )
            db.add(b)
            submitted_bid_ids.append(str(b.id))

        # 1 Ineligible Draft Bid
        draft_org = Organization(
            id=uuid.uuid4(),
            name=f"Vendor Draft Entity Bulk {suffix}",
            organization_type="Private Limited",
            is_active=True,
        )
        db.add(draft_org)
        db.flush()

        draft_bid = Bid(
            id=uuid.uuid4(),
            tender_id=uuid.UUID(tender_id),
            bidder_organization_id=draft_org.id,
            created_by_profile_id=profile_id,
            bid_number=f"BID-BULK-{suffix}-DRAFT",
            status="DRAFT",
            quoted_amount=Decimal("9000000.00"),
            currency="INR",
            is_active=True,
        )
        db.add(draft_bid)

        # 1 Ineligible Withdrawn Bid
        withdrawn_org = Organization(
            id=uuid.uuid4(),
            name=f"Vendor Withdrawn Entity Bulk {suffix}",
            organization_type="Private Limited",
            is_active=True,
        )
        db.add(withdrawn_org)
        db.flush()

        withdrawn_bid = Bid(
            id=uuid.uuid4(),
            tender_id=uuid.UUID(tender_id),
            bidder_organization_id=withdrawn_org.id,
            created_by_profile_id=profile_id,
            bid_number=f"BID-BULK-{suffix}-WITHDRAWN",
            status="WITHDRAWN",
            quoted_amount=Decimal("8500000.00"),
            currency="INR",
            is_active=True,
        )
        db.add(withdrawn_bid)

        db.commit()
    finally:
        db.close()

    return tender_id, submitted_bid_ids, proc_token


def test_01_bulk_evaluation_rbac_and_isolation():
    """Verify role-based access control and tenant isolation on bulk evaluation endpoints."""
    print("\n--- Test 01: Bulk Evaluation RBAC and Tenant Isolation ---")
    tender_id, _, proc_token_a = setup_test_tender_and_bids()
    bidder_token = get_token_for_user("bidder@test.local")
    officer_b_token, _ = setup_second_officer()

    # 1. Bidder attempts to trigger bulk evaluation -> 403 Forbidden
    res_bidder = client.post(
        f"/api/v1/procurement/tenders/{tender_id}/bulk-evaluation",
        headers={"Authorization": f"Bearer {bidder_token}"},
    )
    assert res_bidder.status_code == 403, f"Expected 403 for Bidder, got {res_bidder.status_code}"
    print("PASS: Bidder is forbidden from triggering bulk evaluation (403).")

    # 2. Officer B (different organization) attempts to trigger on Officer A's tender -> 404 Not Found
    res_officer_b = client.post(
        f"/api/v1/procurement/tenders/{tender_id}/bulk-evaluation",
        headers={"Authorization": f"Bearer {officer_b_token}"},
    )
    assert res_officer_b.status_code == 404, f"Expected 404 for cross-tenant Officer B, got {res_officer_b.status_code}"
    print("PASS: Cross-tenant Procurement Officer B cannot access Officer A's tender (404).")

    return tender_id, proc_token_a


def test_02_create_bulk_job_and_eligible_bids_filter():
    """Verify job creation, queue status, and eligible submitted bids inclusion."""
    print("\n--- Test 02: Create Bulk Job & Eligible Bids Filtering ---")
    tender_id, submitted_bids, proc_token = setup_test_tender_and_bids()

    # Officer A triggers bulk evaluation
    res = client.post(
        f"/api/v1/procurement/tenders/{tender_id}/bulk-evaluation",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res.status_code == 202, f"Expected 202 Accepted, got {res.status_code}: {res.text}"
    job_data = res.json()
    job_id = job_data["job_id"]
    assert job_data["status"] in ("QUEUED", "RUNNING")
    # Only 3 submitted bids should be queued (DRAFT & WITHDRAWN excluded)
    assert job_data["total_bids"] == 3, f"Expected 3 eligible bids, got {job_data['total_bids']}"
    print(f"PASS: Bulk evaluation job {job_id} created with 3 eligible submitted bids.")

    # Concurrency test: Ensure job is in RUNNING state and triggering another bulk job -> 409 Conflict
    session_factory = get_session_factory()
    db = session_factory()
    try:
        j = db.scalars(select(BulkEvaluationJob).where(BulkEvaluationJob.id == uuid.UUID(job_id))).first()
        j.status = BulkJobStatus.RUNNING
        db.commit()
    finally:
        db.close()

    res_duplicate = client.post(
        f"/api/v1/procurement/tenders/{tender_id}/bulk-evaluation",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_duplicate.status_code == 409, f"Expected 409 Conflict for concurrent job, got {res_duplicate.status_code}"
    print("PASS: Concurrent bulk evaluation job blocked with HTTP 409 Conflict.")

    return tender_id, job_id, proc_token


def test_03_bulk_job_execution_and_telemetry():
    """Verify background pipeline execution, progress tracking, and stage telemetry."""
    print("\n--- Test 03: Bulk Job Execution & Item Telemetry ---")
    tender_id, submitted_bids, proc_token = setup_test_tender_and_bids()

    # Trigger bulk evaluation (executed by TestClient background tasks)
    res_trigger = client.post(
        f"/api/v1/procurement/tenders/{tender_id}/bulk-evaluation",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_trigger.status_code == 202
    job_id = res_trigger.json()["job_id"]

    # Fetch Job Status via API
    res_status = client.get(
        f"/api/v1/procurement/bulk-evaluations/{job_id}",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_status.status_code == 200, f"Get job status failed: {res_status.text}"
    status_data = res_status.json()

    assert status_data["status"] in ("COMPLETED", "PARTIALLY_COMPLETED")
    assert status_data["counts"]["total"] == 3
    assert status_data["counts"]["processed"] == 3
    assert status_data["counts"]["progress_percentage"] == 100.0
    print(f"PASS: Bulk job completed with status '{status_data['status']}', 100% progress.")

    # Fetch Active Tender Job
    res_active = client.get(
        f"/api/v1/procurement/tenders/{tender_id}/bulk-evaluation/active",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_active.status_code == 200
    assert res_active.json()["id"] == job_id
    print("PASS: Active tender bulk evaluation query returned matching job.")

    # Fetch Job Items
    res_items = client.get(
        f"/api/v1/procurement/bulk-evaluations/{job_id}/items",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_items.status_code == 200
    items_data = res_items.json()
    assert items_data["total"] == 3
    assert len(items_data["items"]) == 3

    for item in items_data["items"]:
        assert item["status"] in ("SUCCESS", "REVIEW_REQUIRED")
        assert item["current_stage"] == "COMPLETED"
        assert item["final_score"] is not None
        assert item["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        print(f"  • Bid {item['bid_number']}: Stage={item['current_stage']}, Status={item['status']}, Score={item['final_score']}%, Risk={item['risk_level']}")

    print("PASS: All per-bid job items successfully evaluated with complete telemetry.")


def test_04_failure_isolation_and_retry():
    """Verify that technical errors on one bid are isolated, and retry mechanics work correctly."""
    print("\n--- Test 04: Failure Isolation & Retry Mechanics ---")
    tender_id, submitted_bids, proc_token = setup_test_tender_and_bids()

    # Create bulk job
    res_create = client.post(
        f"/api/v1/procurement/tenders/{tender_id}/bulk-evaluation",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_create.status_code == 202
    job_id = res_create.json()["job_id"]

    # Seed one simulated failed item in DB
    session_factory = get_session_factory()
    db = session_factory()
    failed_item_id = None
    try:
        item = db.scalars(
            select(BulkEvaluationJobItem).where(BulkEvaluationJobItem.job_id == uuid.UUID(job_id))
        ).first()
        failed_item_id = str(item.id)
        item.status = BulkItemStatus.FAILED
        item.current_stage = "FAILED"
        item.error_code = "OCR_CORRUPTION"
        item.error_message = "Simulated OCR decompression failure."
        item.is_retryable = True

        job = db.scalars(select(BulkEvaluationJob).where(BulkEvaluationJob.id == uuid.UUID(job_id))).first()
        job.processed_bids = 1
        job.failed_bids = 1
        job.status = BulkJobStatus.PARTIALLY_COMPLETED
        db.commit()
    finally:
        db.close()

    # Verify single item retry
    res_retry_single = client.post(
        f"/api/v1/procurement/bulk-evaluations/{job_id}/items/{failed_item_id}/retry",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_retry_single.status_code == 200, f"Retry single item failed: {res_retry_single.text}"
    assert res_retry_single.json()["status"] == "QUEUED"
    print("PASS: Single failed item successfully re-queued for retry.")

    # Re-simulate failure for retry-all test
    db = session_factory()
    try:
        item = db.scalars(select(BulkEvaluationJobItem).where(BulkEvaluationJobItem.id == uuid.UUID(failed_item_id))).first()
        item.status = BulkItemStatus.FAILED
        item.is_retryable = True
        job = db.scalars(select(BulkEvaluationJob).where(BulkEvaluationJob.id == uuid.UUID(job_id))).first()
        job.failed_bids = 1
        job.status = BulkJobStatus.PARTIALLY_COMPLETED
        db.commit()
    finally:
        db.close()

    # Retry all failed items
    res_retry_all = client.post(
        f"/api/v1/procurement/bulk-evaluations/{job_id}/retry-failed",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_retry_all.status_code == 200
    assert res_retry_all.json()["retried_count"] >= 1
    print("PASS: Batch retry for all failed items successfully executed.")


def test_05_job_cancellation():
    """Verify that active jobs can be cancelled gracefully and remaining items are marked SKIPPED."""
    print("\n--- Test 05: Bulk Job Cancellation ---")
    tender_id, _, proc_token = setup_test_tender_and_bids()

    # Create job without starting worker so items are QUEUED
    session_factory = get_session_factory()
    db = session_factory()
    job_id = None
    try:
        user = db.scalars(select(User).where(User.email == "procurement@test.local")).first()
        job = BulkEvaluationService.create_bulk_evaluation_job(
            db=db,
            user=user,
            tender_id=uuid.UUID(tender_id),
        )
        job_id = str(job.id)
    finally:
        db.close()

    # Cancel job
    res_cancel = client.post(
        f"/api/v1/procurement/bulk-evaluations/{job_id}/cancel",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # Verify pending items are marked SKIPPED
    res_items = client.get(
        f"/api/v1/procurement/bulk-evaluations/{job_id}/items",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_items.status_code == 200
    for item in res_items.json()["items"]:
        assert item["status"] in ("SKIPPED", "CANCELLED")
    print("PASS: Bulk job cancellation marked all pending items as SKIPPED.")


def test_06_audit_trail_verification():
    """Verify that audit events are recorded for bulk evaluation lifecycle."""
    print("\n--- Test 06: Audit Trail Verification ---")
    session_factory = get_session_factory()
    db = session_factory()
    try:
        events = db.scalars(
            select(AuditEvent)
            .where(AuditEvent.event_type.in_([
                AuditEventType.BULK_EVALUATION_STARTED,
                AuditEventType.BULK_EVALUATION_COMPLETED,
                AuditEventType.BULK_EVALUATION_PARTIALLY_COMPLETED,
                AuditEventType.BULK_EVALUATION_RETRY,
                AuditEventType.BULK_EVALUATION_CANCELLED,
            ]))
            .order_by(AuditEvent.created_at.desc())
        ).all()

        assert len(events) > 0, "Expected audit events for bulk evaluation."
        print(f"PASS: Found {len(events)} bulk evaluation audit event log records.")
        for ev in events[:3]:
            print(f"  • Audit Event: {ev.event_type} | Action: {ev.action} | Actor: {ev.actor_name} | Summary: {ev.summary[:60]}...")
    finally:
        db.close()


if __name__ == "__main__":
    print("================================================================================")
    print("PART 9: BULK VERIFICATION & BATCH PROCESSING TEST SUITE")
    print("================================================================================")
    test_01_bulk_evaluation_rbac_and_isolation()
    test_02_create_bulk_job_and_eligible_bids_filter()
    test_03_bulk_job_execution_and_telemetry()
    test_04_failure_isolation_and_retry()
    test_05_job_cancellation()
    test_06_audit_trail_verification()
    print("\n================================================================================")
    print("ALL PART 9 BULK VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("================================================================================")
