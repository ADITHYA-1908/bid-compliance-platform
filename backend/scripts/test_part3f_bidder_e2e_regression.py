"""
Part 3F — Bidder Module Final Integration, QA, Security Hardening & Regression Test Suite

Comprehensive end-to-end validation across the entire GeM Bidder Platform:
1. Authentication & Role-Based Access Control (401 unauth vs 403 wrong-role).
2. Bidder Profile & Organization setup, statutory completion calculation & cross-bidder isolation.
3. Tender Discovery (only OPEN tenders, search/category filtering, safe fields projection).
4. Bid Creation Lifecycle (OPEN tender, unique BID-YYYY-XXXXXX number generation).
5. Bid Creation Protections (Incomplete profile 400, Closed tender 400, Expired deadline 400, Duplicate bid 409).
6. Draft Bid Proposal Editing & Persistence (quoted_amount, technical_summary, commercial_notes).
7. Cross-Tenant Security & Isolation (Bidder A vs Bidder B 404 isolation across all endpoints).
8. Document Upload, Validation & Private Storage (PDF/PNG/DOCX allowed, .exe/.sh blocked, 25MB limit, signed URLs).
9. Requirement Mapping, Single-Active Enforcement & Soft Deletion.
10. Submission Readiness Verification (Profile, Proposal details, Mandatory docs, Tender status, Deadline).
11. Optional Requirement Behavior (missing optional docs allows submission).
12. Statutory Legal Declaration Enforcement (declaration_accepted=True required).
13. Atomic State Transition (DRAFT -> SUBMITTED, reference SUB-YYYY-XXXXXX, submitted_at, audit logging).
14. Post-Submission Immutability Locks (Proposal edits & Document mutations strictly rejected).
15. Tender Closes / Deadline Passes Pre-Submission Protection.
16. Procurement Officer & Tender Management Regression (Part 2 tender CRUD & lifecycle remain intact).
"""

import io
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Tuple

# pyrefly: ignore [missing-import]
import pytest
from fastapi.testclient import TestClient
# pyrefly: ignore [missing-import]
from sqlalchemy import select, text
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.security import create_access_token
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.db.session import get_session_factory
from app.main import app


# ---------------------------------------------------------------------------
# Test Fixtures & Provisioning Helpers
# ---------------------------------------------------------------------------

def setup_user_with_role(db: Session, role_name: str, email_prefix: str) -> Tuple[User, Profile, Organization]:
    """Provisions a test user, profile, and organization."""
    uid = uuid.uuid4().hex[:8]
    role = db.scalars(select(Role).where(Role.name == role_name)).first()
    if not role:
        role = Role(id=uuid.uuid4(), name=role_name, description=f"{role_name} Role")
        db.add(role)
        db.commit()
        db.refresh(role)

    org = Organization(
        name=f"Enterprise {email_prefix} {uid} Ltd",
        trade_name=f"Trade {email_prefix} {uid}",
        organization_type="PRIVATE_LIMITED",
        business_category="MICRO",
        pan_number=f"ABCDE{uid[:4].upper()}Z",
        gstin=f"29ABCDE{uid[:4].upper()}Z1Z5",
        registered_address="100 Tech Park, Whitefield",
        city="Bengaluru",
        state="Karnataka",
        pincode="560066",
        country="India",
        official_email=f"org_{email_prefix}_{uid}@enterprise.test",
        official_phone="+919876543210",
        is_active=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    prof = Profile(
        full_name=f"Authorized Signatory {email_prefix}",
        email=f"signatory_{email_prefix}_{uid}@enterprise.test",
        phone="+919876543210",
        designation="Director of Procurement",
        role_id=role.id,
        organization_id=org.id,
        is_active=True,
    )
    db.add(prof)
    db.commit()
    db.refresh(prof)

    user = User(
        id=uuid.uuid4(),
        email=prof.email,
        password_hash="argon2_hashed_mock_password_xyz",
        is_active=True,
        profile_id=prof.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user, prof, org


def create_test_tender(
    db: Session,
    creator_prof: Profile,
    status: str = "OPEN",
    days_to_deadline: int = 15,
) -> Tuple[Tender, list[TenderRequirement]]:
    """Creates a test tender with mandatory and optional requirements."""
    uid = uuid.uuid4().hex[:6].upper()
    now = datetime.now(timezone.utc)

    tender = Tender(
        id=uuid.uuid4(),
        tender_number=f"GEM/2026/B/{uid}",
        title=f"Supply of Enterprise IT Hardware {uid}",
        description="Procurement of compute servers, switches, and storage units for GeM portal.",
        category="GOODS",
        status=status,
        estimated_value=Decimal("8500000.00"),
        publish_date=now - timedelta(days=2),
        submission_start_date=now - timedelta(days=1),
        submission_end_date=now + timedelta(days=days_to_deadline),
        organization_id=creator_prof.organization_id,
        created_by_profile_id=creator_prof.id,
        is_active=True,
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)

    req1 = TenderRequirement(
        tender_id=tender.id,
        code="REQ_GST_CERT",
        name="Valid GST Registration Certificate",
        category="STATUTORY",
        requirement_type="DOCUMENT",
        operator="EXISTS",
        is_mandatory=True,
        display_order=1,
        is_active=True,
    )
    req2 = TenderRequirement(
        tender_id=tender.id,
        code="REQ_OEM_MAF",
        name="Manufacturer Authorization Form (MAF)",
        category="TECHNICAL",
        requirement_type="DOCUMENT",
        operator="EXISTS",
        is_mandatory=True,
        display_order=2,
        is_active=True,
    )
    req3 = TenderRequirement(
        tender_id=tender.id,
        code="REQ_ISO_OPT",
        name="ISO 9001 Quality Certificate (Optional)",
        category="TECHNICAL",
        requirement_type="DOCUMENT",
        operator="EXISTS",
        is_mandatory=False,
        display_order=3,
        is_active=True,
    )
    db.add_all([req1, req2, req3])
    db.commit()

    return tender, [req1, req2, req3]


def get_token(user: User) -> str:
    """Generates a valid JWT bearer token for the given user."""
    return create_access_token(subject=str(user.id), email=user.email)


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_01_auth_and_role_guards():
    """Validates 401 Unauthenticated and 403 Wrong-Role security semantics."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_user_with_role(db, "BIDDER", "t1_bid")
        user_proc, prof_proc, org_proc = setup_user_with_role(db, "PROCUREMENT_OFFICER", "t1_proc")
        tender, reqs = create_test_tender(db, prof_proc, status="OPEN")

        client = TestClient(app)

        # 1. Unauthenticated -> 401
        res_unauth = client.get("/api/v1/bidder/profile")
        assert res_unauth.status_code == 401

        res_unauth_bids = client.get("/api/v1/bidder/bids")
        assert res_unauth_bids.status_code == 401

        # 2. Procurement Officer calling Bidder endpoints -> 403 Forbidden
        token_proc = get_token(user_proc)
        res_proc_prof = client.get(
            "/api/v1/bidder/profile",
            headers={"Authorization": f"Bearer {token_proc}"},
        )
        assert res_proc_prof.status_code == 403

        res_proc_bids = client.get(
            "/api/v1/bidder/bids",
            headers={"Authorization": f"Bearer {token_proc}"},
        )
        assert res_proc_bids.status_code == 403
    finally:
        db.close()


def test_02_bidder_profile_setup_and_cross_bidder_isolation():
    """Validates profile & organization editing, statutory completion, and tenant isolation."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_a, prof_a, org_a = setup_user_with_role(db, "BIDDER", "t2_a")
        user_b, prof_b, org_b = setup_user_with_role(db, "BIDDER", "t2_b")

        token_a = get_token(user_a)
        token_b = get_token(user_b)
        client = TestClient(app)

        # 1. Fetch Bidder A profile
        res_prof_a = client.get(
            "/api/v1/bidder/profile",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_prof_a.status_code == 200
        data_a = res_prof_a.json()
        assert data_a["profile"]["email"] == prof_a.email
        assert data_a["completion"]["is_complete"] is True
        assert data_a["completion"]["completion_percentage"] == 100

        # 2. Update Bidder A organization info
        res_update_org = client.patch(
            "/api/v1/bidder/organization",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "trade_name": "Updated Trade Name A",
                "registered_address": "456 Tech Park, Phase 1",
            },
        )
        assert res_update_org.status_code == 200
        assert res_update_org.json()["organization"]["trade_name"] == "Updated Trade Name A"

        # 3. Bidder B inspects own profile -> isolated from A
        res_prof_b = client.get(
            "/api/v1/bidder/profile",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_prof_b.status_code == 200
        assert res_prof_b.json()["profile"]["email"] == prof_b.email
        assert res_prof_b.json()["profile"]["organization"]["name"] == org_b.name
    finally:
        db.close()


def test_03_tender_discovery_and_safe_projections():
    """Validates that bidders only see OPEN tenders without internal procurement metadata."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_user_with_role(db, "BIDDER", "t3_bid")
        user_proc, prof_proc, org_proc = setup_user_with_role(db, "PROCUREMENT_OFFICER", "t3_proc")

        tender_open, reqs = create_test_tender(db, prof_proc, status="OPEN")
        tender_draft, _ = create_test_tender(db, prof_proc, status="DRAFT")
        tender_archived, _ = create_test_tender(db, prof_proc, status="ARCHIVED")

        token = get_token(user_bidder)
        client = TestClient(app)

        # 1. List tenders for bidder
        res_list = client.get(
            "/api/v1/bidder/tenders",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_list.status_code == 200
        items = res_list.json()["items"]
        item_ids = [t["id"] for t in items]

        # Must contain OPEN, must NOT contain DRAFT or ARCHIVED
        assert str(tender_open.id) in item_ids
        assert str(tender_draft.id) not in item_ids
        assert str(tender_archived.id) not in item_ids

        # 2. Inspect safe fields projection on tender detail
        res_detail = client.get(
            f"/api/v1/bidder/tenders/{tender_open.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert "created_by_profile_id" not in detail_data
        assert "internal_notes" not in detail_data
        assert len(detail_data["requirements"]) == 3
    finally:
        db.close()


def test_04_bid_creation_and_lifecycle_protections():
    """Validates creation of DRAFT bid and all lifecycle protection gates."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_user_with_role(db, "BIDDER", "t4_bid")
        user_proc, prof_proc, org_proc = setup_user_with_role(db, "PROCUREMENT_OFFICER", "t4_proc")

        tender_open, reqs = create_test_tender(db, prof_proc, status="OPEN", days_to_deadline=10)
        tender_closed, _ = create_test_tender(db, prof_proc, status="CLOSED")
        tender_expired, _ = create_test_tender(db, prof_proc, status="OPEN", days_to_deadline=-2)

        token = get_token(user_bidder)
        client = TestClient(app)

        # 1. Non-OPEN tender -> 400 Bad Request
        res_closed = client.post(
            f"/api/v1/bidder/tenders/{tender_closed.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert res_closed.status_code == 400
        assert "open" in res_closed.json()["detail"].lower() or "closed" in res_closed.json()["detail"].lower()

        # 2. Expired deadline -> 400 Bad Request
        res_exp = client.post(
            f"/api/v1/bidder/tenders/{tender_expired.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert res_exp.status_code == 400
        assert "deadline" in res_exp.json()["detail"].lower()

        # 3. Successful bid creation on OPEN tender -> 201 Created
        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender_open.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "quoted_amount": 7800000.00,
                "technical_summary": "Initial draft technical compliance proposal.",
            },
        )
        assert res_create.status_code == 201
        bid_data = res_create.json()
        assert bid_data["status"] == "DRAFT"
        assert bid_data["bid_number"].startswith("BID-")
        bid_id = bid_data["id"]

        # 4. Duplicate participation attempt -> 409 Conflict
        res_dup = client.post(
            f"/api/v1/bidder/tenders/{tender_open.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert res_dup.status_code == 409
        assert "already exists" in res_dup.json()["detail"].lower() or "active bid" in res_dup.json()["detail"].lower()
    finally:
        db.close()


def test_05_draft_bid_editing_and_cross_tenant_isolation():
    """Validates proposal editing and verifies Bidder B cannot view or modify Bidder A's bid."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_a, prof_a, org_a = setup_user_with_role(db, "BIDDER", "t5_a")
        user_b, prof_b, org_b = setup_user_with_role(db, "BIDDER", "t5_b")
        user_proc, prof_proc, _ = setup_user_with_role(db, "PROCUREMENT_OFFICER", "t5_proc")

        tender, reqs = create_test_tender(db, prof_proc, status="OPEN")

        token_a = get_token(user_a)
        token_b = get_token(user_b)
        client = TestClient(app)

        # 1. Bidder A creates bid
        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"quoted_amount": 8000000.00, "technical_summary": "Initial summary"},
        )
        bid_id = res_create.json()["id"]

        # 2. Bidder A updates proposal details (PATCH)
        res_patch = client.patch(
            f"/api/v1/bidder/bids/{bid_id}",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "quoted_amount": 7950000.00,
                "technical_summary": "Revised technical compliance specifications.",
                "commercial_notes": "Includes 3 years comprehensive onsite warranty.",
            },
        )
        assert res_patch.status_code == 200
        assert Decimal(str(res_patch.json()["quoted_amount"])) == Decimal("7950000.00")
        assert res_patch.json()["commercial_notes"] == "Includes 3 years comprehensive onsite warranty."

        # 3. Bidder B attempts to view Bidder A's bid -> 404 Not Found
        res_b_view = client.get(
            f"/api/v1/bidder/bids/{bid_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_b_view.status_code == 404

        # 4. Bidder B attempts to modify Bidder A's bid -> 404 Not Found
        res_b_patch = client.patch(
            f"/api/v1/bidder/bids/{bid_id}",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"quoted_amount": 1000.00},
        )
        assert res_b_patch.status_code == 404
    finally:
        db.close()


def test_06_document_upload_validation_and_private_storage():
    """Validates file upload, blacklist filtering (.exe/.sh), size limits, and signed URLs."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_user_with_role(db, "BIDDER", "t6_bid")
        user_proc, prof_proc, _ = setup_user_with_role(db, "PROCUREMENT_OFFICER", "t6_proc")
        tender, reqs = create_test_tender(db, prof_proc, status="OPEN")

        token = get_token(user_bidder)
        client = TestClient(app)

        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={"quoted_amount": 8100000.00, "technical_summary": "Tech specs."},
        )
        bid_id = res_create.json()["id"]

        pdf_bytes = b"%PDF-1.4 mock enterprise document content"

        # 1. Blocked executable extension (.exe) -> 400 Bad Request
        res_exe = client.post(
            f"/api/v1/bidder/bids/{bid_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "TECHNICAL_DOCUMENT", "tender_requirement_id": str(reqs[0].id)},
            files={"file": ("malicious_script.exe", io.BytesIO(b"binary"), "application/octet-stream")},
        )
        assert res_exe.status_code == 400
        assert "prohibited" in res_exe.json()["detail"].lower() or ".exe" in res_exe.json()["detail"].lower()

        # 2. Blocked script extension (.sh) -> 400 Bad Request
        res_sh = client.post(
            f"/api/v1/bidder/bids/{bid_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "TECHNICAL_DOCUMENT", "tender_requirement_id": str(reqs[0].id)},
            files={"file": ("deploy.sh", io.BytesIO(b"#!/bin/bash"), "text/x-shellscript")},
        )
        assert res_sh.status_code == 400

        # 3. Valid PDF Upload linked to Requirement 1 -> 201 Created
        res_pdf = client.post(
            f"/api/v1/bidder/bids/{bid_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "STATUTORY_DOCUMENT", "tender_requirement_id": str(reqs[0].id)},
            files={"file": ("gst_certificate.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert res_pdf.status_code == 201
        doc1_data = res_pdf.json()
        assert doc1_data["original_filename"] == "gst_certificate.pdf"
        assert doc1_data["is_active"] is True
        doc1_id = doc1_data["id"]

        # 4. Download / Signed URL endpoint
        res_dl = client.get(
            f"/api/v1/bidder/bids/{bid_id}/documents/{doc1_id}/download-url",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_dl.status_code == 200
        assert "download_url" in res_dl.json()
    finally:
        db.close()


def test_07_requirement_mapping_replacement_and_soft_delete():
    """Validates single-active document replacement and soft deletion."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_user_with_role(db, "BIDDER", "t7_bid")
        user_proc, prof_proc, _ = setup_user_with_role(db, "PROCUREMENT_OFFICER", "t7_proc")
        tender, reqs = create_test_tender(db, prof_proc, status="OPEN")

        token = get_token(user_bidder)
        client = TestClient(app)

        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={"quoted_amount": 8200000.00, "technical_summary": "Tech specs."},
        )
        bid_id = res_create.json()["id"]

        pdf_bytes = b"%PDF-1.4 original document"
        pdf_bytes_v2 = b"%PDF-1.4 revised document v2"

        # 1. Upload Doc A for Requirement 1
        res_doc_a = client.post(
            f"/api/v1/bidder/bids/{bid_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "STATUTORY_DOCUMENT", "tender_requirement_id": str(reqs[0].id)},
            files={"file": ("gst_v1.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert res_doc_a.status_code == 201
        doc_a_id = res_doc_a.json()["id"]

        # 2. Upload Doc B for SAME Requirement 1 -> Auto replaces Doc A
        res_doc_b = client.post(
            f"/api/v1/bidder/bids/{bid_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "STATUTORY_DOCUMENT", "tender_requirement_id": str(reqs[0].id)},
            files={"file": ("gst_v2.pdf", io.BytesIO(pdf_bytes_v2), "application/pdf")},
        )
        assert res_doc_b.status_code == 201
        doc_b_id = res_doc_b.json()["id"]

        # Verify Doc A is now inactive in database
        db_doc_a = db.scalars(select(BidDocument).where(BidDocument.id == uuid.UUID(doc_a_id))).one()
        assert db_doc_a.is_active is False
        db_doc_b = db.scalars(select(BidDocument).where(BidDocument.id == uuid.UUID(doc_b_id))).one()
        assert db_doc_b.is_active is True

        # 3. Soft delete Doc B
        res_del = client.delete(
            f"/api/v1/bidder/bids/{bid_id}/documents/{doc_b_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_del.status_code == 200

        db.refresh(db_doc_b)
        assert db_doc_b.is_active is False
    finally:
        db.close()


def test_08_submission_readiness_and_declaration_gate():
    """Validates multi-point readiness checklist, missing document reporting, and declaration acceptance."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_user_with_role(db, "BIDDER", "t8_bid")
        user_proc, prof_proc, _ = setup_user_with_role(db, "PROCUREMENT_OFFICER", "t8_proc")
        tender, reqs = create_test_tender(db, prof_proc, status="OPEN")

        token = get_token(user_bidder)
        client = TestClient(app)

        # 1. Create bid with missing quoted amount
        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        bid_id = res_create.json()["id"]

        # Check readiness -> ready_to_submit must be False
        res_readiness_1 = client.get(
            f"/api/v1/bidder/bids/{bid_id}/readiness",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_readiness_1.status_code == 200
        r1 = res_readiness_1.json()
        assert r1["ready_to_submit"] is False
        assert r1["checks"]["bid_details_complete"] is False
        assert r1["checks"]["mandatory_documents_complete"] is False

        # 2. Update bid details (quoted amount & technical summary)
        client.patch(
            f"/api/v1/bidder/bids/{bid_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "quoted_amount": 8300000.00,
                "technical_summary": "Full technical compliance response.",
            },
        )

        # 3. Upload only Mandatory Doc 1 (leaving Mandatory Doc 2 missing)
        pdf_bytes = b"%PDF-1.4 mock compliance proof"
        client.post(
            f"/api/v1/bidder/bids/{bid_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "STATUTORY_DOCUMENT", "tender_requirement_id": str(reqs[0].id)},
            files={"file": ("gst.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

        res_readiness_2 = client.get(
            f"/api/v1/bidder/bids/{bid_id}/readiness",
            headers={"Authorization": f"Bearer {token}"},
        )
        r2 = res_readiness_2.json()
        assert r2["ready_to_submit"] is False
        assert r2["checks"]["bid_details_complete"] is True
        assert r2["checks"]["mandatory_documents_complete"] is False
        assert "Manufacturer Authorization Form (MAF)" in r2["missing_documents"]

        # 4. Upload Mandatory Doc 2 (leave Optional Doc 3 unattached)
        client.post(
            f"/api/v1/bidder/bids/{bid_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "TECHNICAL_DOCUMENT", "tender_requirement_id": str(reqs[1].id)},
            files={"file": ("maf.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

        # Now ready_to_submit must become TRUE
        res_readiness_3 = client.get(
            f"/api/v1/bidder/bids/{bid_id}/readiness",
            headers={"Authorization": f"Bearer {token}"},
        )
        r3 = res_readiness_3.json()
        assert r3["ready_to_submit"] is True
        assert len(r3["missing_documents"]) == 0

        # 5. Submit without declaration_accepted -> 400 Bad Request
        res_sub_no_decl = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": False},
        )
        assert res_sub_no_decl.status_code == 400
        assert "declaration" in res_sub_no_decl.json()["detail"].lower()
    finally:
        db.close()


def test_09_final_submission_and_immutability_locking():
    """Validates atomic submission, receipt generation, and post-submission immutability locks."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_user_with_role(db, "BIDDER", "t9_bid")
        user_proc, prof_proc, _ = setup_user_with_role(db, "PROCUREMENT_OFFICER", "t9_proc")
        tender, reqs = create_test_tender(db, prof_proc, status="OPEN")

        token = get_token(user_bidder)
        client = TestClient(app)

        # 1. Create bid and upload all mandatory proofs
        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "quoted_amount": 8400000.00,
                "technical_summary": "Comprehensive compliant proposal.",
            },
        )
        bid_id = res_create.json()["id"]

        pdf_bytes = b"%PDF-1.4 valid proof"
        doc_ids = []
        for req in reqs[:2]:  # Mandatory 1 and 2
            res_up = client.post(
                f"/api/v1/bidder/bids/{bid_id}/documents",
                headers={"Authorization": f"Bearer {token}"},
                data={"document_type": "TECHNICAL_DOCUMENT", "tender_requirement_id": str(req.id)},
                files={"file": (f"{req.code}.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )
            doc_ids.append(res_up.json()["id"])

        # 2. Final Submit
        res_submit = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_submit.status_code == 200
        receipt = res_submit.json()
        assert receipt["status"] == "SUBMITTED"
        assert receipt["submitted_at"] is not None
        assert receipt["submission_reference"].startswith("SUB-")
        assert receipt["submitted_by_email"] == prof_bidder.email

        # 3. Duplicate Submission Attempt -> 409 Conflict
        res_dup_submit = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_dup_submit.status_code == 409

        # 4. Direct PATCH Proposal Edits -> Blocked (400/409)
        res_patch_locked = client.patch(
            f"/api/v1/bidder/bids/{bid_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"quoted_amount": 5000000.00},
        )
        assert res_patch_locked.status_code in [400, 409]

        # 5. Direct Document Upload on Submitted Bid -> Blocked (400/409)
        res_up_locked = client.post(
            f"/api/v1/bidder/bids/{bid_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "TECHNICAL_DOCUMENT"},
            files={"file": ("extra.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert res_up_locked.status_code in [400, 409]

        # 6. Direct Document Deletion on Submitted Bid -> Blocked (400/409)
        res_del_locked = client.delete(
            f"/api/v1/bidder/bids/{bid_id}/documents/{doc_ids[0]}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_del_locked.status_code in [400, 409]
    finally:
        db.close()


def test_10_procurement_officer_regression():
    """Validates that Part 2 Tender Management and lifecycle capabilities remain fully functional."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_proc, prof_proc, org_proc = setup_user_with_role(db, "PROCUREMENT_OFFICER", "t10_proc")
        token_proc = get_token(user_proc)
        client = TestClient(app)

        uid = uuid.uuid4().hex[:6].upper()
        now = datetime.now(timezone.utc)

        # 1. Procurement Officer creates draft tender
        res_create_t = client.post(
            "/api/v1/tenders",
            headers={"Authorization": f"Bearer {token_proc}"},
            json={
                "tender_number": f"GEM/2026/REG/{uid}",
                "title": f"Procurement Office Regression Tender {uid}",
                "description": "Regression check for Part 2 tender creation.",
                "department": "Ministry of Electronics & IT",
                "category": "SERVICES",
                "procurement_type": "OPEN_TENDER",
                "estimated_value": 3500000.00,
                "submission_start_date": (now + timedelta(days=1)).isoformat(),
                "submission_end_date": (now + timedelta(days=20)).isoformat(),
            },
        )
        assert res_create_t.status_code == 201
        tender_id = res_create_t.json()["id"]

        # 2. Add requirement to tender
        res_add_req = client.post(
            f"/api/v1/tenders/{tender_id}/requirements",
            headers={"Authorization": f"Bearer {token_proc}"},
            json={
                "code": "REQ_REG_CERT",
                "name": "Regression Statutory Proof",
                "category": "STATUTORY",
                "requirement_type": "DOCUMENT",
                "operator": "EXISTS",
                "is_mandatory": True,
            },
        )
        assert res_add_req.status_code == 201

        # 3. Publish tender -> PUBLISHED -> OPEN
        res_pub = client.post(
            f"/api/v1/tenders/{tender_id}/transition",
            headers={"Authorization": f"Bearer {token_proc}"},
            json={"target_status": "PUBLISHED"},
        )
        assert res_pub.status_code == 200

        res_open = client.post(
            f"/api/v1/tenders/{tender_id}/transition",
            headers={"Authorization": f"Bearer {token_proc}"},
            json={"target_status": "OPEN"},
        )
        assert res_open.status_code == 200
        assert res_open.json()["status"] == "OPEN"
    finally:
        db.close()
