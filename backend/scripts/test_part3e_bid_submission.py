"""
Part 3E Automated Test Suite: Bid Review & Final Submission Workflow
Tests readiness evaluations, mandatory document validation, declaration enforcement,
atomic DRAFT -> SUBMITTED transition, post-submission mutation locking, and cross-tenant security.
"""

import io
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.main import app


def get_session_factory():
    engine = create_engine(settings.DATABASE_URL)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def setup_bidder_with_profile(
    db: Session,
    suffix: str,
    make_incomplete: bool = False,
) -> tuple[User, Profile, Organization]:
    """Helper to provision a clean bidder user, profile, and organization."""
    uid = uuid.uuid4().hex[:8]
    role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
    if not role:
        role = Role(id=uuid.uuid4(), name="BIDDER", description="Bidder")
        db.add(role)
        db.commit()
        db.refresh(role)

    org = Organization(
        name=f"Enterprise {suffix} {uid}",
        trade_name=f"Trade {suffix} {uid}",
        organization_type="PRIVATE_LIMITED",
        business_category="MICRO",
        pan_number=f"ABCDE{uid[:4].upper()}Z" if not make_incomplete else None,
        gstin=f"29ABCDE{uid[:4].upper()}Z1Z5",
        registered_address="123 Industrial Estate, Phase II",
        city="Bengaluru",
        state="Karnataka",
        pincode="560001",
        country="India",
        official_email=f"org_{suffix}_{uid}@test.local",
        official_phone="+919876543210",
        is_active=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    prof = Profile(
        full_name=f"Authorized Bidder {suffix}",
        email=f"bidder_{suffix}_{uid}@test.local",
        phone="+919876543210",
        designation="Managing Director",
        role_id=role.id,
        organization_id=org.id,
        is_active=True,
    )
    db.add(prof)
    db.commit()
    db.refresh(prof)

    user = User(
        email=prof.email,
        password_hash=hash_password("TestPassword123!"),
        profile_id=prof.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user, prof, org


def setup_procurement_officer(db: Session) -> tuple[User, Profile, Organization]:
    """Helper to provision a procurement officer user."""
    uid = uuid.uuid4().hex[:8]
    role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
    if not role:
        role = Role(id=uuid.uuid4(), name="PROCUREMENT_OFFICER", description="Officer")
        db.add(role)
        db.commit()
        db.refresh(role)

    org = Organization(
        name=f"Govt Buyer Dept {uid}",
        organization_type="GOVERNMENT_ENTITY",
        is_active=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    prof = Profile(
        full_name="Procurement Officer",
        email=f"proc_{uid}@test.local",
        role_id=role.id,
        organization_id=org.id,
        is_active=True,
    )
    db.add(prof)
    db.commit()
    db.refresh(prof)

    user = User(
        email=prof.email,
        password_hash=hash_password("TestPassword123!"),
        profile_id=prof.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user, prof, org


def setup_open_tender_with_requirements(
    db: Session,
    days_to_deadline: int = 15,
    tender_status: str = "OPEN",
) -> tuple[Tender, list[TenderRequirement]]:
    """Creates a sample OPEN tender with mandatory and optional requirements."""
    buyer_user, buyer_prof, buyer_org = setup_procurement_officer(db)
    uid = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)

    tender = Tender(
        organization_id=buyer_org.id,
        created_by_profile_id=buyer_prof.id,
        tender_number=f"GEM/2026/B/{uid.upper()}",
        title=f"Supply of Hardware Equipment {uid}",
        category="IT & Telecom",
        procurement_type="Goods",
        estimated_value=Decimal("5000000.00"),
        status=tender_status,
        submission_start_date=now - timedelta(days=2),
        submission_end_date=now + timedelta(days=days_to_deadline),
        is_active=True,
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)

    # Mandatory Document 1
    req1 = TenderRequirement(
        tender_id=tender.id,
        code="REQ_GST_PROOF",
        name="Valid GST Registration Certificate",
        category="STATUTORY",
        requirement_type="DOCUMENT",
        operator="EXISTS",
        is_mandatory=True,
        display_order=1,
        is_active=True,
    )
    # Mandatory Document 2
    req2 = TenderRequirement(
        tender_id=tender.id,
        code="REQ_OEM_MAF",
        name="OEM Authorization Form (MAF)",
        category="TECHNICAL",
        requirement_type="DOCUMENT",
        operator="EXISTS",
        is_mandatory=True,
        display_order=2,
        is_active=True,
    )
    # Optional Document 3
    req3 = TenderRequirement(
        tender_id=tender.id,
        code="REQ_ISO_CERT",
        name="ISO 9001 Quality Certificate",
        category="TECHNICAL",
        requirement_type="DOCUMENT",
        operator="EXISTS",
        is_mandatory=False,
        display_order=3,
        is_active=True,
    )

    db.add_all([req1, req2, req3])
    db.commit()
    db.refresh(req1)
    db.refresh(req2)
    db.refresh(req3)

    return tender, [req1, req2, req3]


def get_auth_token(user: User) -> str:
    return create_access_token(subject=str(user.id), email=user.email)


def test_01_role_authorization_and_unauthenticated():
    """Validates that unauthenticated and non-bidder roles are blocked from submission endpoints."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "sub_auth")
        user_proc, _, _ = setup_procurement_officer(db)
        tender, reqs = setup_open_tender_with_requirements(db)

        # Create draft bid
        token_bidder = get_auth_token(user_bidder)
        token_proc = get_auth_token(user_proc)

        client = TestClient(app)
        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token_bidder}"},
            json={},
        )
        assert res_create.status_code == 201
        bid_id = res_create.json()["id"]

        # 1. Unauthenticated checks
        res_unauth_readiness = client.get(f"/api/v1/bidder/bids/{bid_id}/readiness")
        assert res_unauth_readiness.status_code == 401

        res_unauth_submit = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            json={"declaration_accepted": True},
        )
        assert res_unauth_submit.status_code == 401

        # 2. Procurement Officer checks
        res_proc_readiness = client.get(
            f"/api/v1/bidder/bids/{bid_id}/readiness",
            headers={"Authorization": f"Bearer {token_proc}"},
        )
        assert res_proc_readiness.status_code == 403

        res_proc_submit = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token_proc}"},
            json={"declaration_accepted": True},
        )
        assert res_proc_submit.status_code == 403
    finally:
        db.close()


def test_02_readiness_checklist_reports_all_criteria():
    """Validates that the readiness API returns granular check statuses for a draft bid."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "sub_ready_init")
        tender, reqs = setup_open_tender_with_requirements(db)

        token = get_auth_token(user_bidder)
        client = TestClient(app)

        # Create draft bid without details
        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert res_create.status_code == 201
        bid_id = res_create.json()["id"]

        # Call readiness endpoint
        res_readiness = client.get(
            f"/api/v1/bidder/bids/{bid_id}/readiness",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_readiness.status_code == 200
        data = res_readiness.json()

        assert data["ready_to_submit"] is False
        assert data["checks"]["profile_complete"] is True
        assert data["checks"]["bid_details_complete"] is False
        assert data["checks"]["mandatory_documents_complete"] is False
        assert data["checks"]["tender_open"] is True
        assert data["checks"]["deadline_valid"] is True

        # Verify missing fields & documents listed
        assert len(data["missing_required_fields"]) >= 2
        assert len(data["missing_documents"]) == 2
        assert "Valid GST Registration Certificate" in data["missing_documents"]
        assert "OEM Authorization Form (MAF)" in data["missing_documents"]
        # Optional document not in missing list
        assert "ISO 9001 Quality Certificate" not in data["missing_documents"]
    finally:
        db.close()


def test_03_incomplete_profile_blocks_submission():
    """Validates that a bidder whose organization profile is incomplete is blocked from final submission."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        # Create bidder with missing PAN (incomplete profile)
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(
            db, "sub_incomp_prof", make_incomplete=True
        )
        tender, reqs = setup_open_tender_with_requirements(db)

        # Force bid insertion directly in db to simulate state
        bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",

            status="DRAFT",
            quoted_amount=Decimal("4500000.00"),
            technical_summary="Detailed technical compliance response.",
            is_active=True,
        )
        db.add(bid)
        db.commit()

        token = get_auth_token(user_bidder)
        client = TestClient(app)

        res_submit = client.post(
            f"/api/v1/bidder/bids/{bid.id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_submit.status_code == 400
        assert "profile is incomplete" in res_submit.json()["detail"].lower()
    finally:
        db.close()


def test_04_missing_required_bid_fields_blocks_submission():
    """Validates that submission fails when quoted_amount or technical_summary is missing."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "sub_missing_fld")
        tender, reqs = setup_open_tender_with_requirements(db)

        token = get_auth_token(user_bidder)
        client = TestClient(app)

        # 1. Create bid without quoted_amount or technical_summary
        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert res_create.status_code == 201
        bid_id = res_create.json()["id"]

        # Upload mandatory documents
        pdf_bytes = b"%PDF-1.4 dummy document bytes"
        for req in reqs[:2]:  # 2 mandatory
            client.post(
                f"/api/v1/bidder/bids/{bid_id}/documents",
                headers={"Authorization": f"Bearer {token}"},
                data={"document_type": "GST_CERTIFICATE", "tender_requirement_id": str(req.id)},
                files={"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )

        # Attempt submit without quote/technical summary
        res_submit = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_submit.status_code == 400
        assert "required details missing" in res_submit.json()["detail"].lower()

        # Update quoted_amount only
        client.patch(
            f"/api/v1/bidder/bids/{bid_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"quoted_amount": 4800000.00},
        )

        res_submit2 = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_submit2.status_code == 400
        assert "technical" in res_submit2.json()["detail"].lower()
    finally:
        db.close()


def test_05_missing_mandatory_documents_blocks_submission():
    """Validates that submission is blocked when one or more mandatory documents are missing."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "sub_missing_doc")
        tender, reqs = setup_open_tender_with_requirements(db)

        token = get_auth_token(user_bidder)
        client = TestClient(app)

        # Create complete proposal details
        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "quoted_amount": 4500000.00,
                "technical_summary": "Comprehensive technical architecture with full OEM support.",
            },
        )
        assert res_create.status_code == 201
        bid_id = res_create.json()["id"]

        # Upload only 1 of the 2 mandatory documents (GST uploaded, OEM missing)
        pdf_bytes = b"%PDF-1.4 sample file content"
        res_up1 = client.post(
            f"/api/v1/bidder/bids/{bid_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "GST_CERTIFICATE", "tender_requirement_id": str(reqs[0].id)},
            files={"file": ("gst.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert res_up1.status_code == 201

        # Check readiness
        res_readiness = client.get(
            f"/api/v1/bidder/bids/{bid_id}/readiness",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = res_readiness.json()
        assert data["ready_to_submit"] is False
        assert data["checks"]["mandatory_documents_complete"] is False
        assert "OEM Authorization Form (MAF)" in data["missing_documents"]

        # Attempt submit
        res_submit = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_submit.status_code == 400
        assert "missing mandatory documents" in res_submit.json()["detail"].lower()
        assert "OEM Authorization" in res_submit.json()["detail"]
    finally:
        db.close()


def test_06_optional_documents_missing_allows_submission():
    """Validates that omitting non-mandatory optional documents does not prevent final submission."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "sub_opt_pass")
        tender, reqs = setup_open_tender_with_requirements(db)

        token = get_auth_token(user_bidder)
        client = TestClient(app)

        # Create proposal with complete fields
        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "quoted_amount": 4750000.00,
                "technical_summary": "Full compliance offering with certified Tier-1 components.",
            },
        )
        assert res_create.status_code == 201
        bid_id = res_create.json()["id"]

        # Upload only the 2 mandatory requirements (leave reqs[2] optional ISO certificate empty)
        pdf_bytes = b"%PDF-1.4 valid binary payload"
        for req in reqs[:2]:
            client.post(
                f"/api/v1/bidder/bids/{bid_id}/documents",
                headers={"Authorization": f"Bearer {token}"},
                data={"document_type": "TECHNICAL_DOCUMENT", "tender_requirement_id": str(req.id)},
                files={"file": (f"{req.code.lower()}.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )

        # Verify readiness is True
        res_readiness = client.get(
            f"/api/v1/bidder/bids/{bid_id}/readiness",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_readiness.status_code == 200
        assert res_readiness.json()["ready_to_submit"] is True
        assert len(res_readiness.json()["missing_documents"]) == 0

        # Submit final bid
        res_submit = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_submit.status_code == 200
        assert res_submit.json()["status"] == "SUBMITTED"
    finally:
        db.close()


def test_07_declaration_required_for_submission():
    """Validates that final submission rejects requests where declaration_accepted is False."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "sub_decl_req")
        tender, reqs = setup_open_tender_with_requirements(db)

        token = get_auth_token(user_bidder)
        client = TestClient(app)

        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "quoted_amount": 4200000.00,
                "technical_summary": "Full technical compliance response.",
            },
        )
        assert res_create.status_code == 201
        bid_id = res_create.json()["id"]

        pdf_bytes = b"%PDF-1.4 file content"
        for req in reqs[:2]:
            client.post(
                f"/api/v1/bidder/bids/{bid_id}/documents",
                headers={"Authorization": f"Bearer {token}"},
                data={"document_type": "TECHNICAL_DOCUMENT", "tender_requirement_id": str(req.id)},
                files={"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )

        # Attempt submit with declaration_accepted = False
        res_submit = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": False},
        )
        assert res_submit.status_code == 400
        assert "declaration" in res_submit.json()["detail"].lower()
    finally:
        db.close()


def test_08_successful_final_submission_and_receipt():
    """Validates atomic submission, timestamp persistence, reference generation, and database audit state."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "sub_success")
        tender, reqs = setup_open_tender_with_requirements(db)

        token = get_auth_token(user_bidder)
        client = TestClient(app)

        # 1. Create draft proposal
        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "quoted_amount": 4900000.00,
                "currency": "INR",
                "technical_summary": "Enterprise grade hardware deployment with 3-year OEM warranty.",
                "commercial_notes": "Prices inclusive of all GST and freight.",
                "remarks": "Delivery within 30 days from LOA.",
            },
        )
        assert res_create.status_code == 201
        bid_id = res_create.json()["id"]

        # 2. Upload mandatory documents
        pdf_bytes = b"%PDF-1.4 valid submission document"
        for req in reqs[:2]:
            res_up = client.post(
                f"/api/v1/bidder/bids/{bid_id}/documents",
                headers={"Authorization": f"Bearer {token}"},
                data={"document_type": "TECHNICAL_DOCUMENT", "tender_requirement_id": str(req.id)},
                files={"file": (f"{req.code}.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )
            assert res_up.status_code == 201

        # 3. Verify readiness
        res_readiness = client.get(
            f"/api/v1/bidder/bids/{bid_id}/readiness",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_readiness.json()["ready_to_submit"] is True

        # 4. Submit final bid
        res_submit = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_submit.status_code == 200
        data = res_submit.json()

        assert data["status"] == "SUBMITTED"
        assert data["submitted_at"] is not None
        assert data["submission_reference"].startswith("SUB-")
        assert data["submitted_by_email"] == prof_bidder.email
        assert data["tender_title"] == tender.title
        assert data["bidder_organization_name"] == org_bidder.name
        assert Decimal(str(data["quoted_amount"])) == Decimal("4900000.00")

        # 5. Verify direct database record
        db_bid = db.scalars(select(Bid).where(Bid.id == uuid.UUID(bid_id))).one()
        assert db_bid.status == "SUBMITTED"
        assert db_bid.submitted_at is not None
        assert db_bid.submitted_by_profile_id == prof_bidder.id
        assert db_bid.declaration_accepted is True
        assert db_bid.submission_reference == data["submission_reference"]
    finally:
        db.close()


def test_09_duplicate_submission_prevented_409():
    """Validates that calling the submit endpoint on an already SUBMITTED bid returns 409 Conflict."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "sub_dup_blk")
        tender, reqs = setup_open_tender_with_requirements(db)

        token = get_auth_token(user_bidder)
        client = TestClient(app)

        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "quoted_amount": 4200000.00,
                "technical_summary": "Full technical compliance proposal.",
            },
        )
        bid_id = res_create.json()["id"]

        pdf_bytes = b"%PDF-1.4 file content"
        for req in reqs[:2]:
            client.post(
                f"/api/v1/bidder/bids/{bid_id}/documents",
                headers={"Authorization": f"Bearer {token}"},
                data={"document_type": "TECHNICAL_DOCUMENT", "tender_requirement_id": str(req.id)},
                files={"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )

        # 1st Submission -> Success
        res_sub1 = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_sub1.status_code == 200

        # 2nd Submission -> 409 Conflict
        res_sub2 = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_sub2.status_code == 409
        assert "already been submitted" in res_sub2.json()["detail"].lower()
    finally:
        db.close()


def test_10_post_submission_mutation_locked():
    """Validates that after final submission, all proposal field edits and document mutations are rejected."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "sub_lock_test")
        tender, reqs = setup_open_tender_with_requirements(db)

        token = get_auth_token(user_bidder)
        client = TestClient(app)

        res_create = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "quoted_amount": 4500000.00,
                "technical_summary": "Full technical compliance proposal.",
            },
        )
        bid_id = res_create.json()["id"]

        pdf_bytes = b"%PDF-1.4 file content"
        doc_ids = []
        for req in reqs[:2]:
            res_up = client.post(
                f"/api/v1/bidder/bids/{bid_id}/documents",
                headers={"Authorization": f"Bearer {token}"},
                data={"document_type": "TECHNICAL_DOCUMENT", "tender_requirement_id": str(req.id)},
                files={"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )
            doc_ids.append(res_up.json()["id"])

        # Submit final bid
        res_submit = client.post(
            f"/api/v1/bidder/bids/{bid_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_submit.status_code == 200

        # 1. Attempt to edit proposal details -> Blocked
        res_patch = client.patch(
            f"/api/v1/bidder/bids/{bid_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"quoted_amount": 3900000.00},
        )
        assert res_patch.status_code in [400, 409]
        assert "DRAFT" in res_patch.json()["detail"]

        # 2. Attempt to upload new document -> Blocked
        res_up_locked = client.post(
            f"/api/v1/bidder/bids/{bid_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"document_type": "COMMERCIAL_DOCUMENT"},
            files={"file": ("extra.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert res_up_locked.status_code in [400, 409]

        # 3. Attempt to replace document -> Blocked
        res_rep_locked = client.put(
            f"/api/v1/bidder/bids/{bid_id}/documents/{doc_ids[0]}",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("new_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert res_rep_locked.status_code in [400, 409]

        # 4. Attempt to remove document -> Blocked
        res_del_locked = client.delete(
            f"/api/v1/bidder/bids/{bid_id}/documents/{doc_ids[0]}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_del_locked.status_code in [400, 409]
    finally:
        db.close()


def test_11_expired_deadline_and_closed_tender_blocks_submission():
    """Validates that final submission is rejected if tender is closed or past deadline."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_bidder, prof_bidder, org_bidder = setup_bidder_with_profile(db, "sub_expired_tst")
        token = get_auth_token(user_bidder)
        client = TestClient(app)

        # 1. Tender with expired deadline
        tender_expired, reqs_exp = setup_open_tender_with_requirements(db, days_to_deadline=-1)

        # Insert draft bid directly in db
        bid_exp = Bid(
            id=uuid.uuid4(),
            tender_id=tender_expired.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            quoted_amount=Decimal("4500000.00"),
            technical_summary="Technical proposal.",
            is_active=True,
        )
        db.add(bid_exp)
        db.commit()

        # Attempt submit on expired tender
        res_exp_submit = client.post(
            f"/api/v1/bidder/bids/{bid_exp.id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_exp_submit.status_code == 400
        assert "deadline" in res_exp_submit.json()["detail"].lower()

        # 2. Tender in CLOSED status
        tender_closed, reqs_cls = setup_open_tender_with_requirements(
            db, days_to_deadline=10, tender_status="CLOSED"
        )
        bid_closed = Bid(
            id=uuid.uuid4(),
            tender_id=tender_closed.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",

            status="DRAFT",
            quoted_amount=Decimal("4500000.00"),
            technical_summary="Technical proposal.",
            is_active=True,
        )
        db.add(bid_closed)
        db.commit()

        res_cls_submit = client.post(
            f"/api/v1/bidder/bids/{bid_closed.id}/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={"declaration_accepted": True},
        )
        assert res_cls_submit.status_code == 400
        assert "not open" in res_cls_submit.json()["detail"].lower()
    finally:
        db.close()


def test_12_cross_bidder_submission_isolation():
    """Validates that Bidder B cannot view readiness or submit Bidder A's bid."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user_a, _, _ = setup_bidder_with_profile(db, "bidder_a_sub")
        user_b, _, _ = setup_bidder_with_profile(db, "bidder_b_sub")
        tender, reqs = setup_open_tender_with_requirements(db)

        token_a = get_auth_token(user_a)
        token_b = get_auth_token(user_b)
        client = TestClient(app)

        # Bidder A creates bid
        res_create_a = client.post(
            f"/api/v1/bidder/tenders/{tender.id}/bids",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "quoted_amount": 4200000.00,
                "technical_summary": "Bidder A Technical proposal.",
            },
        )
        assert res_create_a.status_code == 201
        bid_a_id = res_create_a.json()["id"]

        # Bidder B attempts to check readiness of Bid A -> 404
        res_b_readiness = client.get(
            f"/api/v1/bidder/bids/{bid_a_id}/readiness",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_b_readiness.status_code == 404

        # Bidder B attempts to submit Bid A -> 404
        res_b_submit = client.post(
            f"/api/v1/bidder/bids/{bid_a_id}/submit",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"declaration_accepted": True},
        )
        assert res_b_submit.status_code == 404
    finally:
        db.close()
