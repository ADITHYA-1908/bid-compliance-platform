"""
Part 3D Automated Bid Document Upload Test Suite
Validates:
1. Role-based access control (Only BIDDER allowed; PROCUREMENT_OFFICER gets 403, unauthenticated gets 401).
2. File safety validation (Oversized >10MB rejected, .exe/.sh executables blocked, empty files rejected).
3. Valid document formats (PDF, PNG, DOCX) uploaded successfully to private storage.
4. Requirement mapping and readiness progress calculation (total_required, uploaded_required, missing_required).
5. Automatic replacement & versioning when uploading new file for same requirement.
6. Explicit PUT document replacement with version increment.
7. DELETE soft-removal of document and recalculation of missing requirements.
8. Cross-bidder tenant isolation (Bidder B cannot access or modify Bidder A's documents -> 404).
9. Secure download streaming and signed access generation.
10. Non-DRAFT bid protection (mutation blocked if bid is not in DRAFT status).
"""

import io
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.security import create_access_token, hash_password
from app.db.session import get_session_factory
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User

client = TestClient(app)


def get_token(user_id: uuid.UUID, email: str) -> str:
    """Helper to generate a JWT access token for testing."""
    return create_access_token(subject=str(user_id), email=email)


def setup_bidder_with_profile(db, email_prefix: str) -> Tuple[User, Profile, Organization]:
    """Helper to provision a complete bidder with 100% profile readiness."""
    uid = uuid.uuid4().hex[:8]
    email = f"{email_prefix}_{uid}@test.local"

    bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
    if not bidder_role:
        bidder_role = Role(name="BIDDER", description="Bidder role")
        db.add(bidder_role)
        db.commit()

    org = Organization(
        name=f"Enterprise Solutions {uid.upper()} Pvt Ltd",
        trade_name=f"Enterprise Solutions {uid.upper()}",
        organization_type="PRIVATE_LIMITED",
        business_category="MEDIUM",
        pan_number=f"ABCDE{uid[:4].upper()}Z",
        gstin=f"27ABCDE{uid[:4].upper()}Z1Z5",
        registered_address="Plot 42, Cyber Gateway",
        city="Mumbai",
        state="Maharashtra",
        pincode="400001",
        country="India",
        official_phone="+919876543210",
        official_email=email,
        is_active=True,
    )

    db.add(org)
    db.commit()
    db.refresh(org)

    prof = Profile(
        organization_id=org.id,
        role_id=bidder_role.id,
        email=email,
        full_name=f"Authorized Bidder {uid}",
        phone="+919876543210",
        designation="Director of Tenders",
        is_active=True,
    )

    db.add(prof)
    db.commit()
    db.refresh(prof)

    user = User(
        email=email,
        password_hash=hash_password("TestPassword123!"),
        profile_id=prof.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user, prof, org


def setup_open_tender_with_requirements(db) -> Tuple[Tender, List[TenderRequirement]]:
    """Helper to provision an OPEN tender with 2 mandatory document requirements."""
    uid = uuid.uuid4().hex[:8]
    officer_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
    if not officer_role:
        officer_role = Role(name="PROCUREMENT_OFFICER", description="Procurement Officer")
        db.add(officer_role)
        db.commit()

    buyer_org = Organization(
        name=f"Ministry of Transport {uid}",
        organization_type="Government Ministry",
        is_active=True,
    )
    db.add(buyer_org)
    db.commit()

    buyer_prof = Profile(
        organization_id=buyer_org.id,
        email=f"proc_{uid}@transport.gov.local",
        full_name="Procurement Director",
        is_active=True,
    )
    db.add(buyer_prof)
    db.commit()

    now = datetime.now(timezone.utc)
    tender = Tender(
        organization_id=buyer_org.id,
        created_by_profile_id=buyer_prof.id,
        tender_number=f"GEM/2026/B/{uid.upper()}",
        title=f"Supply of Hardware Equipment {uid}",
        category="IT & Telecom",
        procurement_type="Goods",
        estimated_value=Decimal("5000000.00"),
        status="OPEN",
        submission_start_date=now - timedelta(days=2),
        submission_end_date=now + timedelta(days=15),
        is_active=True,
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)


    req1 = TenderRequirement(
        tender_id=tender.id,
        code="REQ_GST_PROOF",
        name="Valid GST Registration Certificate",
        requirement_type="DOCUMENT",
        category="STATUTORY",
        operator="EXISTS",
        is_mandatory=True,
        display_order=1,
        is_active=True,
    )
    req2 = TenderRequirement(
        tender_id=tender.id,
        code="REQ_OEM_AUTH",
        name="Manufacturer Authorization Form (MAF)",
        requirement_type="DOCUMENT",
        category="TECHNICAL",
        operator="EXISTS",
        is_mandatory=True,
        display_order=2,
        is_active=True,
    )
    db.add_all([req1, req2])
    db.commit()
    db.refresh(req1)
    db.refresh(req2)

    return tender, [req1, req2]


def test_01_role_authorization_and_unauthenticated():
    """Validates that unauthenticated and non-bidder users are blocked from document endpoints."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "bidder_auth")
        tender, reqs = setup_open_tender_with_requirements(db)

        # Create a draft bid for bidder
        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)

        fake_bid_id = str(bid.id)

        # 1. Unauthenticated request -> 401
        res = client.get(f"/api/v1/bidder/bids/{fake_bid_id}/documents")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

        # 2. Procurement Officer token -> 403 Forbidden
        po_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
        po_email = f"po_test_{uuid.uuid4().hex[:6]}@test.local"
        po_prof = Profile(
            email=po_email,
            full_name="Procurement Officer Test",
            role_id=po_role.id,
            is_active=True,
        )
        db.add(po_prof)
        db.commit()
        db.refresh(po_prof)

        po_user = User(
            email=po_email,
            password_hash=hash_password("TestPassword123!"),
            profile_id=po_prof.id,
            is_active=True,
        )
        db.add(po_user)
        db.commit()
        db.refresh(po_user)


        po_token = get_token(po_user.id, po_user.email)
        res = client.get(
            f"/api/v1/bidder/bids/{fake_bid_id}/documents",
            headers={"Authorization": f"Bearer {po_token}"},
        )
        assert res.status_code == 403, f"Expected 403 for PO, got {res.status_code}"

        # Upload attempt by PO -> 403
        files = {"file": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")}
        data = {"document_type": "PAN"}
        res = client.post(
            f"/api/v1/bidder/bids/{fake_bid_id}/documents",
            headers={"Authorization": f"Bearer {po_token}"},
            files=files,
            data=data,
        )
        assert res.status_code == 403, f"Expected 403 for PO upload, got {res.status_code}"
    finally:
        db.close()


def test_02_file_validation_oversized_and_executable_blocked():
    """Validates that empty files, oversized files, and dangerous executables are rejected."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "bidder_val")
        tender, reqs = setup_open_tender_with_requirements(db)

        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)

        token = get_token(user_bidder.id, user_bidder.email)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Executable file .exe -> 400
        exe_file = {"file": ("malware.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload")}
        res = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files=exe_file,
            data={"document_type": "TECHNICAL_DOCUMENT"},
        )
        assert res.status_code == 400
        assert "Executable" in res.json()["detail"] or "prohibited" in res.json()["detail"]

        # 2. Script file .sh -> 400
        sh_file = {"file": ("script.sh", b"#!/bin/bash\necho hello", "text/x-shellscript")}
        res = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files=sh_file,
            data={"document_type": "TECHNICAL_DOCUMENT"},
        )
        assert res.status_code == 400

        # 3. Empty file -> 400
        empty_file = {"file": ("empty.pdf", b"", "application/pdf")}
        res = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files=empty_file,
            data={"document_type": "PAN"},
        )
        assert res.status_code == 400
        assert "empty" in res.json()["detail"].lower()

        # 4. Oversized file (>10MB) -> 400
        oversized_bytes = b"0" * (11 * 1024 * 1024)  # 11MB
        big_file = {"file": ("large_doc.pdf", oversized_bytes, "application/pdf")}
        res = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files=big_file,
            data={"document_type": "FINANCIAL_STATEMENT"},
        )
        assert res.status_code == 400
        assert "exceeds maximum allowed size" in res.json()["detail"]
    finally:
        db.close()


def test_03_valid_file_uploads_pdf_png_docx():
    """Validates successful upload of valid document formats (PDF, PNG, DOCX)."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "bidder_valid_up")
        tender, reqs = setup_open_tender_with_requirements(db)

        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)

        token = get_token(user_bidder.id, user_bidder.email)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Upload PDF
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Company PAN) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        pdf_file = {"file": ("company_pan.pdf", pdf_content, "application/pdf")}
        res = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files=pdf_file,
            data={"document_type": "PAN", "notes": "Official PAN Card copy"},
        )
        assert res.status_code == 201, f"PDF upload failed: {res.text}"
        data_pdf = res.json()
        assert data_pdf["document_type"] == "PAN"
        assert data_pdf["original_filename"] == "company_pan.pdf"
        assert data_pdf["file_size"] == len(pdf_content)
        assert data_pdf["status"] == "UPLOADED"
        assert data_pdf["version"] == 1
        assert data_pdf["is_active"] is True

        # 2. Upload PNG
        png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        png_file = {"file": ("gst_cert.png", png_content, "image/png")}
        res = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files=png_file,
            data={"document_type": "GST_CERTIFICATE", "notes": "GST Registration"},
        )
        assert res.status_code == 201
        data_png = res.json()
        assert data_png["document_type"] == "GST_CERTIFICATE"
        assert data_png["original_filename"] == "gst_cert.png"

        # 3. Upload DOCX
        docx_content = b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00dummy docx content for testing"
        docx_file = {"file": ("tech_specs.docx", docx_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        res = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files=docx_file,
            data={"document_type": "TECHNICAL_DOCUMENT"},
        )
        assert res.status_code == 201
        data_docx = res.json()
        assert data_docx["document_type"] == "TECHNICAL_DOCUMENT"
    finally:
        db.close()


def test_04_requirement_mapping_and_summary_progress():
    """Validates requirement-linked uploads and automatic progress calculation."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "bidder_req_map")
        tender, reqs = setup_open_tender_with_requirements(db)
        req_gst, req_oem = reqs[0], reqs[1]

        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)

        token = get_token(user_bidder.id, user_bidder.email)
        headers = {"Authorization": f"Bearer {token}"}

        # Check initial empty documents summary
        res = client.get(f"/api/v1/bidder/bids/{bid.id}/documents", headers=headers)
        assert res.status_code == 200
        summary = res.json()["summary"]
        assert summary["total_required"] == 2
        assert summary["uploaded_required"] == 0
        assert summary["missing_required"] == 2
        assert summary["is_ready_for_submission"] is False

        # 1. Upload 1st required document (GST Proof)
        pdf_file = {"file": ("gst_proof.pdf", b"%PDF-1.4 GST Document", "application/pdf")}
        res = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files=pdf_file,
            data={
                "document_type": "GST_CERTIFICATE",
                "tender_requirement_id": str(req_gst.id),
                "notes": "GST certificate 2026",
            },
        )
        assert res.status_code == 201
        doc_gst = res.json()
        assert doc_gst["tender_requirement_id"] == str(req_gst.id)
        assert doc_gst["requirement_code"] == req_gst.code
        assert doc_gst["document_name"] == req_gst.name

        # Check updated progress (1 of 2 uploaded)
        res = client.get(f"/api/v1/bidder/bids/{bid.id}/documents", headers=headers)
        summary = res.json()["summary"]
        assert summary["total_required"] == 2
        assert summary["uploaded_required"] == 1
        assert summary["missing_required"] == 1
        assert summary["is_ready_for_submission"] is False

        # 2. Upload 2nd required document (OEM Authorization)
        pdf_file2 = {"file": ("oem_auth.pdf", b"%PDF-1.4 OEM Auth Document", "application/pdf")}
        res = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files=pdf_file2,
            data={
                "document_type": "OEM_AUTHORIZATION",
                "tender_requirement_id": str(req_oem.id),
            },
        )
        assert res.status_code == 201

        # Check full completion (2 of 2 uploaded, ready for submission)
        res = client.get(f"/api/v1/bidder/bids/{bid.id}/documents", headers=headers)
        summary = res.json()["summary"]
        assert summary["total_required"] == 2
        assert summary["uploaded_required"] == 2
        assert summary["missing_required"] == 0
        assert summary["is_ready_for_submission"] is True
    finally:
        db.close()


def test_05_duplicate_requirement_auto_replacement():
    """Validates that uploading a new document for an existing requirement replaces the previous version."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "bidder_dup_rep")
        tender, reqs = setup_open_tender_with_requirements(db)
        req_gst = reqs[0]

        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)

        token = get_token(user_bidder.id, user_bidder.email)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Upload initial GST document (v1)
        res1 = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files={"file": ("gst_v1.pdf", b"%PDF-1.4 v1", "application/pdf")},
            data={"document_type": "GST_CERTIFICATE", "tender_requirement_id": str(req_gst.id)},
        )
        assert res1.status_code == 201
        doc1 = res1.json()
        assert doc1["version"] == 1
        assert doc1["is_active"] is True

        # 2. Upload revised GST document for same requirement (v2)
        res2 = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files={"file": ("gst_v2_updated.pdf", b"%PDF-1.4 v2 updated", "application/pdf")},
            data={"document_type": "GST_CERTIFICATE", "tender_requirement_id": str(req_gst.id)},
        )
        assert res2.status_code == 201
        doc2 = res2.json()
        assert doc2["version"] == 2
        assert doc2["is_active"] is True
        assert doc2["original_filename"] == "gst_v2_updated.pdf"

        # 3. Verify in database that doc1 was marked REPLACED and is inactive
        doc1_db = db.scalars(select(BidDocument).where(BidDocument.id == uuid.UUID(doc1["id"]))).one()
        assert doc1_db.is_active is False
        assert doc1_db.status == "REPLACED"

        # 4. Listing active documents shows only doc2
        res_list = client.get(f"/api/v1/bidder/bids/{bid.id}/documents", headers=headers)
        active_items = res_list.json()["items"]
        assert len(active_items) == 1
        assert active_items[0]["id"] == doc2["id"]

        # 5. Listing with include_inactive=true shows both versions
        res_all = client.get(f"/api/v1/bidder/bids/{bid.id}/documents?include_inactive=true", headers=headers)
        all_items = res_all.json()["items"]
        assert len(all_items) == 2
    finally:
        db.close()


def test_06_replace_document_endpoint():
    """Validates the explicit PUT /api/v1/bidder/bids/{bid_id}/documents/{document_id} endpoint."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "bidder_put_rep")
        tender, reqs = setup_open_tender_with_requirements(db)

        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)

        token = get_token(user_bidder.id, user_bidder.email)
        headers = {"Authorization": f"Bearer {token}"}

        # Upload initial doc
        res_init = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files={"file": ("initial.pdf", b"%PDF-1.4 initial content", "application/pdf")},
            data={"document_type": "TURNOVER_CERTIFICATE"},
        )
        assert res_init.status_code == 201
        doc_init = res_init.json()

        # Replace via PUT
        res_put = client.put(
            f"/api/v1/bidder/bids/{bid.id}/documents/{doc_init['id']}",
            headers=headers,
            files={"file": ("ca_certified_turnover.pdf", b"%PDF-1.4 CA Certified content", "application/pdf")},
            data={"notes": "CA Certified revised turnover certificate"},
        )
        assert res_put.status_code == 200
        doc_replaced = res_put.json()
        assert doc_replaced["version"] == 2
        assert doc_replaced["original_filename"] == "ca_certified_turnover.pdf"
        assert doc_replaced["notes"] == "CA Certified revised turnover certificate"
        assert doc_replaced["is_active"] is True

        # Old doc is marked replaced in db
        old_db = db.scalars(select(BidDocument).where(BidDocument.id == uuid.UUID(doc_init["id"]))).one()
        assert old_db.is_active is False
        assert old_db.status == "REPLACED"
    finally:
        db.close()


def test_07_remove_document_soft_delete():
    """Validates soft deletion of uploaded documents and recalculated progress."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "bidder_del_doc")
        tender, reqs = setup_open_tender_with_requirements(db)
        req_gst = reqs[0]

        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)

        token = get_token(user_bidder.id, user_bidder.email)
        headers = {"Authorization": f"Bearer {token}"}

        # Upload document
        res_up = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files={"file": ("gst.pdf", b"%PDF-1.4 GST", "application/pdf")},
            data={"document_type": "GST_CERTIFICATE", "tender_requirement_id": str(req_gst.id)},
        )
        assert res_up.status_code == 201
        doc_id = res_up.json()["id"]

        # Verify summary has 1 uploaded
        res_list = client.get(f"/api/v1/bidder/bids/{bid.id}/documents", headers=headers)
        assert res_list.json()["summary"]["uploaded_required"] == 1

        # Delete document via DELETE endpoint
        res_del = client.delete(f"/api/v1/bidder/bids/{bid.id}/documents/{doc_id}", headers=headers)
        assert res_del.status_code == 200
        del_data = res_del.json()
        assert del_data["is_active"] is False
        assert del_data["status"] == "REMOVED"

        # Verify summary reflects 0 uploaded required and 2 missing
        res_list_after = client.get(f"/api/v1/bidder/bids/{bid.id}/documents", headers=headers)
        assert res_list_after.json()["summary"]["uploaded_required"] == 0
        assert res_list_after.json()["summary"]["missing_required"] == 2
        assert len(res_list_after.json()["items"]) == 0
    finally:
        db.close()


def test_08_cross_bidder_isolation():
    """Validates that Bidder B cannot list, view, download, replace, or remove Bidder A's documents."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_a, prof_a, org_a = setup_bidder_with_profile(db, "bidder_a_iso")
        user_b, prof_b, org_b = setup_bidder_with_profile(db, "bidder_b_iso")
        tender, reqs = setup_open_tender_with_requirements(db)

        # Bidder A's Bid
        bid_a = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_a.id,
            created_by_profile_id=prof_a.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid_a)
        db.commit()
        db.refresh(bid_a)

        token_a = get_token(user_a.id, user_a.email)
        token_b = get_token(user_b.id, user_b.email)

        # Bidder A uploads a document
        res_up = client.post(
            f"/api/v1/bidder/bids/{bid_a.id}/documents",
            headers={"Authorization": f"Bearer {token_a}"},
            files={"file": ("secret_quote.pdf", b"%PDF-1.4 confidential data", "application/pdf")},
            data={"document_type": "COMMERCIAL_DOCUMENT"},
        )
        assert res_up.status_code == 201
        doc_a_id = res_up.json()["id"]

        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 1. Bidder B tries to list Bidder A's documents -> 404
        res = client.get(f"/api/v1/bidder/bids/{bid_a.id}/documents", headers=headers_b)
        assert res.status_code == 404

        # 2. Bidder B tries to read Bidder A's document detail -> 404
        res = client.get(f"/api/v1/bidder/bids/{bid_a.id}/documents/{doc_a_id}", headers=headers_b)
        assert res.status_code == 404

        # 3. Bidder B tries to download Bidder A's document -> 404
        res = client.get(f"/api/v1/bidder/bids/{bid_a.id}/documents/{doc_a_id}/download", headers=headers_b)
        assert res.status_code == 404

        # 4. Bidder B tries to replace Bidder A's document -> 404
        res = client.put(
            f"/api/v1/bidder/bids/{bid_a.id}/documents/{doc_a_id}",
            headers=headers_b,
            files={"file": ("hacked.pdf", b"%PDF-1.4 hacked", "application/pdf")},
        )
        assert res.status_code == 404

        # 5. Bidder B tries to remove Bidder A's document -> 404
        res = client.delete(f"/api/v1/bidder/bids/{bid_a.id}/documents/{doc_a_id}", headers=headers_b)
        assert res.status_code == 404
    finally:
        db.close()


def test_09_download_and_signed_url():
    """Validates binary streaming download and signed download URL generation."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "bidder_dl_test")
        tender, reqs = setup_open_tender_with_requirements(db)

        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)

        token = get_token(user_bidder.id, user_bidder.email)
        headers = {"Authorization": f"Bearer {token}"}

        file_bytes = b"%PDF-1.4 Verification Test Document Content with special bytes \x00\x01\x02"
        res_up = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files={"file": ("pan_card.pdf", file_bytes, "application/pdf")},
            data={"document_type": "PAN"},
        )
        assert res_up.status_code == 201
        doc_id = res_up.json()["id"]

        # 1. Download streaming endpoint
        res_dl = client.get(f"/api/v1/bidder/bids/{bid.id}/documents/{doc_id}/download", headers=headers)
        assert res_dl.status_code == 200
        assert res_dl.content == file_bytes
        assert "application/pdf" in res_dl.headers.get("content-type", "")
        assert 'filename="pan_card.pdf"' in res_dl.headers.get("content-disposition", "")

        # 2. Download URL endpoint
        res_url = client.get(f"/api/v1/bidder/bids/{bid.id}/documents/{doc_id}/download-url", headers=headers)
        assert res_url.status_code == 200
        assert res_url.json()["filename"] == "pan_card.pdf"
        assert res_url.json()["mime_type"] == "application/pdf"
    finally:
        db.close()


def test_10_non_draft_bid_mutation_blocked():
    """Validates that document mutations are blocked when bid status is not DRAFT (e.g. SUBMITTED)."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "bidder_locked_bid")
        tender, reqs = setup_open_tender_with_requirements(db)

        # Create a SUBMITTED bid
        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="SUBMITTED",
            is_active=True,
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)

        # Add an initial document in DB directly
        doc = BidDocument(
            bid_id=bid.id,
            uploaded_by_profile_id=prof_bidder.id,
            document_type="PAN",
            document_name="PAN Card",
            original_filename="pan.pdf",
            storage_path=f"bids/{bid.id}/test/pan.pdf",
            mime_type="application/pdf",
            file_size=1024,
            status="UPLOADED",
            is_active=True,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        token = get_token(user_bidder.id, user_bidder.email)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Upload rejected -> 400
        res = client.post(
            f"/api/v1/bidder/bids/{bid.id}/documents",
            headers=headers,
            files={"file": ("new.pdf", b"%PDF-1.4 test", "application/pdf")},
            data={"document_type": "GST_CERTIFICATE"},
        )
        assert res.status_code == 400
        assert "DRAFT" in res.json()["detail"]

        # 2. Replace rejected -> 400
        res = client.put(
            f"/api/v1/bidder/bids/{bid.id}/documents/{doc.id}",
            headers=headers,
            files={"file": ("rep.pdf", b"%PDF-1.4 rep", "application/pdf")},
        )
        assert res.status_code == 400
        assert "DRAFT" in res.json()["detail"]

        # 3. Remove rejected -> 400
        res = client.delete(f"/api/v1/bidder/bids/{bid.id}/documents/{doc.id}", headers=headers)
        assert res.status_code == 400
        assert "DRAFT" in res.json()["detail"]
    finally:
        db.close()


if __name__ == "__main__":
    print("Running Part 3D Bid Document Upload Test Suite...")
    test_01_role_authorization_and_unauthenticated()
    print("PASS: test_01_role_authorization_and_unauthenticated")
    test_02_file_validation_oversized_and_executable_blocked()
    print("PASS: test_02_file_validation_oversized_and_executable_blocked")
    test_03_valid_file_uploads_pdf_png_docx()
    print("PASS: test_03_valid_file_uploads_pdf_png_docx")
    test_04_requirement_mapping_and_summary_progress()
    print("PASS: test_04_requirement_mapping_and_summary_progress")
    test_05_duplicate_requirement_auto_replacement()
    print("PASS: test_05_duplicate_requirement_auto_replacement")
    test_06_replace_document_endpoint()
    print("PASS: test_06_replace_document_endpoint")
    test_07_remove_document_soft_delete()
    print("PASS: test_07_remove_document_soft_delete")
    test_08_cross_bidder_isolation()
    print("PASS: test_08_cross_bidder_isolation")
    test_09_download_and_signed_url()
    print("PASS: test_09_download_and_signed_url")
    test_10_non_draft_bid_mutation_blocked()
    print("PASS: test_10_non_draft_bid_mutation_blocked")
    print("\nALL 10 PART 3D TESTS PASSED SUCCESSFULLY!")
