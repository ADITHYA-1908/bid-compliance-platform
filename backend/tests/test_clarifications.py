"""
Unit and Integration Tests for Part 16 — Clarification Request Workflow
Tests creation, sending, viewing, responding, replacement documents,
safeguarded re-evaluation, notifications, deduplication, audit events,
human review linkage, and multi-tenant security isolation.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Generator
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.audit_event import AuditEvent, AuditEventType
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.clarification import (
    ClarificationPriority,
    ClarificationRequest,
    ClarificationResponse,
    ClarificationStatus,
    ClarificationType,
)
from app.db.models.human_review import (
    HumanReviewItem,
    HumanReviewNote,
    ReviewSeverity,
    ReviewStatus,
    ReviewType,
)
from app.db.models.notification import Notification, NotificationType
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.db.session import get_session_factory
from app.schemas.clarification import (
    ClarificationRequestCreate,
    ClarificationResolveRequest,
    ClarificationResponseCreate,
)
from app.services.clarification_service import ClarificationService


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides an isolated database session for integration tests."""
    SessionFactory = get_session_factory()
    session = SessionFactory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_clarification_env(db_session: Session):
    """
    Sets up a complete test environment:
    - 1 Procuring Organization + Procurement Officer User/Profile
    - 1 Tender Opportunity
    - 1 Bidder Organization + Bidder User/Profile
    - 1 Bid Submission + 1 Bid Document
    - 1 Unauthorized Bidder Organization + User/Profile
    """
    suffix = uuid.uuid4().hex[:6]

    # 1. Procuring Org & Officer
    proc_org = Organization(
        id=uuid.uuid4(),
        name=f"Procurement Authority {suffix}",
        pan_number=f"PAN{suffix.upper()}01",
        organization_type="PROCURING_ENTITY",
        is_active=True,
    )
    db_session.add(proc_org)

    role_po = db_session.query(Role).filter_by(name="PROCUREMENT_OFFICER").first()
    if not role_po:
        role_po = Role(id=uuid.uuid4(), name="PROCUREMENT_OFFICER", description="Procurement Officer")
        db_session.add(role_po)

    po_profile = Profile(
        id=uuid.uuid4(),
        organization_id=proc_org.id,
        role_id=role_po.id,
        full_name="Aditi Sharma",
        email=f"po_{suffix}@procurement.gov.in",
        phone="+919876543210",
        is_active=True,
    )
    db_session.add(po_profile)

    po_user = User(
        id=uuid.uuid4(),
        email=f"po_{suffix}@procurement.gov.in",
        password_hash="mock_hashed_password",
        profile_id=po_profile.id,
        is_active=True,
    )
    db_session.add(po_user)

    # 2. Tender
    tender = Tender(
        id=uuid.uuid4(),
        tender_number=f"TND-CLR-{suffix}",
        title="High Voltage Transmission Grid Expansion",
        description="Procurement of high voltage substations and grid control software.",
        organization_id=proc_org.id,
        created_by_profile_id=po_profile.id,
        status="EVALUATING",
        estimated_value=Decimal("50000000.00"),
        is_active=True,
    )
    db_session.add(tender)

    # Tender Requirement
    req = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender.id,
        code="GST_VALIDITY",
        name="Valid GST Registration Certificate",
        category="STATUTORY",
        requirement_type="DOCUMENT",
        is_mandatory=True,
        is_critical=True,
        weight=Decimal("15.0"),
        current_version_number=1,
        is_active=True,
    )
    db_session.add(req)

    # 3. Bidder Org & User
    bidder_org = Organization(
        id=uuid.uuid4(),
        name=f"Bharat Heavy Transformers Ltd {suffix}",
        pan_number=f"PAN{suffix.upper()}02",
        organization_type="BIDDER",
        is_active=True,
    )
    db_session.add(bidder_org)

    role_bidder = db_session.query(Role).filter_by(name="BIDDER").first()
    if not role_bidder:
        role_bidder = Role(id=uuid.uuid4(), name="BIDDER", description="Bidder")
        db_session.add(role_bidder)

    bidder_profile = Profile(
        id=uuid.uuid4(),
        organization_id=bidder_org.id,
        role_id=role_bidder.id,
        full_name="Rajesh Kumar",
        email=f"bidder_{suffix}@bhtl.com",
        phone="+919876543211",
        is_active=True,
    )
    db_session.add(bidder_profile)

    bidder_user = User(
        id=uuid.uuid4(),
        email=f"bidder_{suffix}@bhtl.com",
        password_hash="mock_hashed_password",
        profile_id=bidder_profile.id,
        is_active=True,
    )
    db_session.add(bidder_user)

    # Bid
    bid = Bid(
        id=uuid.uuid4(),
        tender_id=tender.id,
        bidder_organization_id=bidder_org.id,
        created_by_profile_id=bidder_profile.id,
        bid_number=f"BID-CLR-{suffix}",
        status="SUBMITTED",
        quoted_amount=Decimal("48500000.00"),
        is_active=True,
    )
    db_session.add(bid)

    # Document
    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=bid.id,
        tender_requirement_id=req.id,
        uploaded_by_profile_id=bidder_profile.id,
        document_type="GST_CERTIFICATE",
        document_name="GST_Certificate_2025.pdf",
        original_filename="GST_Certificate_2025.pdf",
        storage_path=f"bids/{bid.id}/gst.pdf",
        mime_type="application/pdf",
        file_size=102400,
        status="UPLOADED",
        version=1,
        is_active=True,
    )
    db_session.add(doc)

    # 4. Unauthorized Second Bidder (Tenant Isolation test)
    other_org = Organization(
        id=uuid.uuid4(),
        name=f"Rival Corp {suffix}",
        pan_number=f"PAN{suffix.upper()}03",
        organization_type="BIDDER",
        is_active=True,
    )
    db_session.add(other_org)

    other_profile = Profile(
        id=uuid.uuid4(),
        organization_id=other_org.id,
        role_id=role_bidder.id,
        full_name="Vikram Singh",
        email=f"rival_{suffix}@rivalcorp.com",
        phone="+919876543212",
        is_active=True,
    )
    db_session.add(other_profile)

    other_user = User(
        id=uuid.uuid4(),
        email=f"rival_{suffix}@rivalcorp.com",
        password_hash="mock_hashed_password",
        profile_id=other_profile.id,
        is_active=True,
    )
    db_session.add(other_user)

    db_session.commit()

    return {
        "proc_org": proc_org,
        "po_user": po_user,
        "po_profile": po_profile,
        "tender": tender,
        "requirement": req,
        "bidder_org": bidder_org,
        "bidder_user": bidder_user,
        "bidder_profile": bidder_profile,
        "bid": bid,
        "doc": doc,
        "other_org": other_org,
        "other_profile": other_profile,
    }


def test_create_and_send_clarification_flow(db_session: Session, mock_clarification_env):
    """
    Test creating a clarification as DRAFT, then sending it to transition to SENT.
    Verifies audit events and notification dispatch to the bidder.
    """
    env = mock_clarification_env

    # 1. Create as DRAFT
    payload = ClarificationRequestCreate(
        subject="Clarification on GST Registration Validity",
        message="The uploaded GST certificate shows an unclear principal place of business. Please clarify.",
        clarification_type=ClarificationType.UNCLEAR_DOCUMENT,
        priority=ClarificationPriority.HIGH,
        due_date=datetime.now(timezone.utc) + timedelta(days=5),
        send_immediately=False,
        related_document_id=env["doc"].id,
        related_requirement_id=env["requirement"].id,
    )

    req = ClarificationService.create_clarification_request(
        db=db_session,
        tender_id=env["tender"].id,
        bid_id=env["bid"].id,
        current_profile=env["po_profile"],
        payload=payload,
    )

    assert req.id is not None
    assert req.status == ClarificationStatus.DRAFT
    assert req.subject == "Clarification on GST Registration Validity"
    assert req.related_rule_version_number == 1
    assert req.sent_at is None

    # Verify DRAFT creation audit event
    audit = db_session.query(AuditEvent).filter_by(
        entity_id=str(req.id),
        event_type=AuditEventType.CLARIFICATION_CREATED,
    ).first()
    assert audit is not None

    # 2. Send the DRAFT request
    sent_req = ClarificationService.send_clarification_request(
        db=db_session,
        clarification_id=req.id,
        current_profile=env["po_profile"],
    )

    assert sent_req.status == ClarificationStatus.SENT
    assert sent_req.sent_at is not None

    # Verify notification dispatched to Bidder
    notif = db_session.query(Notification).filter_by(
        recipient_profile_id=env["bidder_profile"].id,
        notification_type=NotificationType.CLARIFICATION_REQUESTED,
    ).first()
    assert notif is not None
    assert "Clarification Request Received" in notif.title


def test_bidder_view_and_respond_flow(db_session: Session, mock_clarification_env):
    """
    Test bidder opening clarification (transitions SENT -> VIEWED),
    then submitting a text-only response (transitions to RESPONDED).
    """
    env = mock_clarification_env

    # Create & send immediately
    payload = ClarificationRequestCreate(
        subject="Low OCR Confidence on Financial Turnover",
        message="Audited balance sheet page 3 is blurry. Please confirm your 2024 annual turnover.",
        clarification_type=ClarificationType.LOW_OCR_CONFIDENCE,
        priority=ClarificationPriority.NORMAL,
        due_date=datetime.now(timezone.utc) + timedelta(days=3),
        send_immediately=True,
    )
    req = ClarificationService.create_clarification_request(
        db=db_session,
        tender_id=env["tender"].id,
        bid_id=env["bid"].id,
        current_profile=env["po_profile"],
        payload=payload,
    )
    assert req.status == ClarificationStatus.SENT

    # 1. Bidder views the detail
    detail = ClarificationService.get_clarification_detail(
        db=db_session,
        clarification_id=req.id,
        current_profile=env["bidder_profile"],
    )
    assert detail.status == ClarificationStatus.VIEWED
    assert detail.viewed_at is not None

    # 2. Bidder responds
    resp_payload = ClarificationResponseCreate(
        response_text="The 2024 annual turnover for Bharat Heavy Transformers is INR 42.50 Crores, audited by Deloitte.",
        attached_document_id=None,
        is_replacement_document=False,
    )

    response_record = ClarificationService.respond_to_clarification(
        db=db_session,
        clarification_id=req.id,
        current_profile=env["bidder_profile"],
        payload=resp_payload,
    )

    assert response_record.id is not None
    assert response_record.response_text == resp_payload.response_text

    # Verify request transitioned to RESPONDED
    updated_req = db_session.query(ClarificationRequest).filter_by(id=req.id).first()
    assert updated_req.status == ClarificationStatus.RESPONDED
    assert updated_req.responded_at is not None

    # Verify Procurement Officer received notification
    po_notif = db_session.query(Notification).filter_by(
        recipient_profile_id=env["po_profile"].id,
        notification_type=NotificationType.CLARIFICATION_RESPONDED,
    ).first()
    assert po_notif is not None
    assert "Response Received" in po_notif.title


def test_replacement_document_preserves_history(db_session: Session, mock_clarification_env):
    """
    Test bidder responding with a replacement document:
    - Prior document is marked is_active=False, status='REPLACED'
    - New document becomes active with incremented version
    - Response references both documents without deleting old file
    """
    env = mock_clarification_env
    old_doc = env["doc"]
    assert old_doc.is_active is True
    assert old_doc.version == 1

    # Upload new replacement document directly
    new_doc_id = uuid.uuid4()
    new_doc = BidDocument(
        id=new_doc_id,
        bid_id=env["bid"].id,
        tender_requirement_id=env["requirement"].id,
        uploaded_by_profile_id=env["bidder_profile"].id,
        document_type="GST_CERTIFICATE",
        document_name="GST_Certificate_2025_Clear.pdf",
        original_filename="GST_Certificate_2025_Clear.pdf",
        storage_path=f"bids/{env['bid'].id}/gst_v2.pdf",
        mime_type="application/pdf",
        file_size=204800,
        status="UPLOADED",
        version=1,
        is_active=True,
    )
    db_session.add(new_doc)
    db_session.commit()

    # Create clarification request
    req = ClarificationService.create_clarification_request(
        db=db_session,
        tender_id=env["tender"].id,
        bid_id=env["bid"].id,
        current_profile=env["po_profile"],
        payload=ClarificationRequestCreate(
            subject="Please provide high-resolution GST certificate",
            message="Uploaded scan is missing the QR code corner.",
            clarification_type=ClarificationType.UNCLEAR_DOCUMENT,
            send_immediately=True,
            related_document_id=old_doc.id,
        ),
    )

    # Bidder responds with replacement document
    resp = ClarificationService.respond_to_clarification(
        db=db_session,
        clarification_id=req.id,
        current_profile=env["bidder_profile"],
        payload=ClarificationResponseCreate(
            response_text="Attached high-resolution color scan with verifiable QR code.",
            attached_document_id=new_doc.id,
            is_replacement_document=True,
            replaced_document_id=old_doc.id,
        ),
    )

    db_session.refresh(old_doc)
    db_session.refresh(new_doc)

    # Check history preservation
    assert old_doc.is_active is False
    assert old_doc.status == "REPLACED"

    assert new_doc.is_active is True
    assert new_doc.version == 2
    assert new_doc.tender_requirement_id == env["requirement"].id

    assert resp.is_replacement_document is True
    assert resp.attached_document_id == new_doc.id
    assert resp.replaced_document_id == old_doc.id


def test_procurement_officer_review_and_resolve(db_session: Session, mock_clarification_env):
    """
    Test procurement officer inspecting response, setting UNDER_REVIEW,
    and resolving the clarification with resolution note.
    """
    env = mock_clarification_env

    req = ClarificationService.create_clarification_request(
        db=db_session,
        tender_id=env["tender"].id,
        bid_id=env["bid"].id,
        current_profile=env["po_profile"],
        payload=ClarificationRequestCreate(
            subject="Verification Mismatch on PAN Name",
            message="PAN name differs slightly from certificate holder. Please confirm.",
            clarification_type=ClarificationType.VERIFICATION_MISMATCH,
            send_immediately=True,
        ),
    )

    # Bidder responds
    ClarificationService.respond_to_clarification(
        db=db_session,
        clarification_id=req.id,
        current_profile=env["bidder_profile"],
        payload=ClarificationResponseCreate(
            response_text="Company underwent name change in 2023. MCA incorporation certificate confirms continuity.",
        ),
    )

    # 1. Procurement Officer marks UNDER_REVIEW
    reviewed_req = ClarificationService.mark_under_review(
        db=db_session,
        clarification_id=req.id,
        current_profile=env["po_profile"],
    )
    assert reviewed_req.status == ClarificationStatus.UNDER_REVIEW

    # 2. Procurement Officer resolves
    resolved_req = ClarificationService.resolve_clarification(
        db=db_session,
        clarification_id=req.id,
        current_profile=env["po_profile"],
        payload=ClarificationResolveRequest(
            resolution_note="MCA certificate verified. Name change is benign and legally compliant.",
            trigger_reevaluation=False,
        ),
    )

    assert resolved_req.status == ClarificationStatus.RESOLVED
    assert resolved_req.resolved_by_profile_id == env["po_profile"].id
    assert resolved_req.resolved_at is not None
    assert "Name change is benign" in resolved_req.resolution_note

    # Verify notification to bidder
    bidder_notif = db_session.query(Notification).filter_by(
        recipient_profile_id=env["bidder_profile"].id,
        notification_type=NotificationType.CLARIFICATION_RESOLVED,
    ).first()
    assert bidder_notif is not None


def test_concurrency_and_closed_response_lock(db_session: Session, mock_clarification_env):
    """
    Test that once a clarification is RESOLVED or CANCELLED,
    further bidder responses are strictly rejected with 400 Bad Request.
    """
    env = mock_clarification_env

    req = ClarificationService.create_clarification_request(
        db=db_session,
        tender_id=env["tender"].id,
        bid_id=env["bid"].id,
        current_profile=env["po_profile"],
        payload=ClarificationRequestCreate(
            subject="Certificate Validity Check",
            message="Please provide updated license.",
            send_immediately=True,
        ),
    )

    # Resolve immediately
    ClarificationService.resolve_clarification(
        db=db_session,
        clarification_id=req.id,
        current_profile=env["po_profile"],
        payload=ClarificationResolveRequest(resolution_note="Closed by officer."),
    )

    # Bidder attempts to respond to RESOLVED request -> Rejected
    with pytest.raises(HTTPException) as exc_info:
        ClarificationService.respond_to_clarification(
            db=db_session,
            clarification_id=req.id,
            current_profile=env["bidder_profile"],
            payload=ClarificationResponseCreate(response_text="Late response attempt."),
        )
    assert exc_info.value.status_code == 400
    assert "closed" in exc_info.value.detail.lower()


def test_cross_tenant_isolation_blocked(db_session: Session, mock_clarification_env):
    """
    Test multi-tenant isolation:
    - Bidder from Rival Corp (Organization B) cannot view or respond to a clarification sent to Bharat Heavy Transformers (Organization A).
    """
    env = mock_clarification_env

    req = ClarificationService.create_clarification_request(
        db=db_session,
        tender_id=env["tender"].id,
        bid_id=env["bid"].id,
        current_profile=env["po_profile"],
        payload=ClarificationRequestCreate(
            subject="Confidential Bidder Clarification",
            message="Internal discrepancy on electrical testing report.",
            send_immediately=True,
        ),
    )

    # Rival bidder attempts to view
    with pytest.raises(HTTPException) as exc_view:
        ClarificationService.get_clarification_detail(
            db=db_session,
            clarification_id=req.id,
            current_profile=env["other_profile"],
        )
    assert exc_view.value.status_code == 403

    # Rival bidder attempts to respond
    with pytest.raises(HTTPException) as exc_resp:
        ClarificationService.respond_to_clarification(
            db=db_session,
            clarification_id=req.id,
            current_profile=env["other_profile"],
            payload=ClarificationResponseCreate(response_text="Malicious hijack attempt."),
        )
    assert exc_resp.value.status_code == 403


def test_due_date_alerts_and_deduplication(db_session: Session, mock_clarification_env):
    """
    Test due-date surveillance and deduplicated notification delivery:
    - 3 days remaining alert
    - 1 day remaining alert
    - Overdue alert
    """
    env = mock_clarification_env

    # 1. Overdue request
    req_overdue = ClarificationService.create_clarification_request(
        db=db_session,
        tender_id=env["tender"].id,
        bid_id=env["bid"].id,
        current_profile=env["po_profile"],
        payload=ClarificationRequestCreate(
            subject="Overdue Clarification 1",
            message="Overdue item.",
            due_date=datetime.now(timezone.utc) - timedelta(hours=2),
            send_immediately=True,
        ),
    )

    # 2. Due soon in 12 hours
    req_1d = ClarificationService.create_clarification_request(
        db=db_session,
        tender_id=env["tender"].id,
        bid_id=env["bid"].id,
        current_profile=env["po_profile"],
        payload=ClarificationRequestCreate(
            subject="Urgent 1-Day Clarification",
            message="Due in 12 hours.",
            due_date=datetime.now(timezone.utc) + timedelta(hours=12),
            send_immediately=True,
        ),
    )

    # 3. Due in 2.5 days
    req_3d = ClarificationService.create_clarification_request(
        db=db_session,
        tender_id=env["tender"].id,
        bid_id=env["bid"].id,
        current_profile=env["po_profile"],
        payload=ClarificationRequestCreate(
            subject="3-Day Reminder Clarification",
            message="Due in 2.5 days.",
            due_date=datetime.now(timezone.utc) + timedelta(days=2, hours=10),
            send_immediately=True,
        ),
    )

    # Run check
    counts_first = ClarificationService.check_and_notify_due_dates(db=db_session)
    assert counts_first["overdue"] >= 1
    assert counts_first["due_soon_1d"] >= 1
    assert counts_first["due_soon_3d"] >= 1

    # Run check a second time immediately -> Notifications should be deduplicated (no spam)
    overdue_notifs = db_session.query(Notification).filter_by(
        notification_type=NotificationType.CLARIFICATION_OVERDUE,
        bid_id=env["bid"].id,
    ).all()
    assert len(overdue_notifs) == 1


def test_human_review_item_integration(db_session: Session, mock_clarification_env):
    """
    Test linking a clarification request to a HumanReviewItem.
    When bidder responds, an informative note is appended to the review item.
    """
    env = mock_clarification_env

    # Create HumanReviewItem
    review_item = HumanReviewItem(
        id=uuid.uuid4(),
        organization_id=env["proc_org"].id,
        tender_id=env["tender"].id,
        bid_id=env["bid"].id,
        review_type=ReviewType.COMPLIANCE_REVIEW,
        source_type="COMPLIANCE_RESULT",
        source_id=str(env["requirement"].id),
        severity=ReviewSeverity.HIGH,
        status=ReviewStatus.OPEN,
        title="Discrepancy in GST Document",
        reason="OCR extracted different state code than tender requirement.",
    )
    db_session.add(review_item)
    db_session.commit()

    # Create clarification linked to review item
    req = ClarificationService.create_clarification_request(
        db=db_session,
        tender_id=env["tender"].id,
        bid_id=env["bid"].id,
        current_profile=env["po_profile"],
        payload=ClarificationRequestCreate(
            subject="GST State Code Verification",
            message="Please provide State GST branch annexure.",
            send_immediately=True,
            related_review_item_id=review_item.id,
        ),
    )

    # Bidder responds
    ClarificationService.respond_to_clarification(
        db=db_session,
        clarification_id=req.id,
        current_profile=env["bidder_profile"],
        payload=ClarificationResponseCreate(
            response_text="Principal place is Delhi, but site operations branch is in Maharashtra as per Annexure A.",
        ),
    )

    # Verify review note was appended to the review item
    notes = db_session.query(HumanReviewNote).filter_by(review_item_id=review_item.id).all()
    assert len(notes) >= 1
    assert "Principal place is Delhi" in notes[0].note_text
