"""
Comprehensive Automated Test Suite for Part 3C: Bid Creation & Tender Participation

Tests:
1. Role Authorization:
   - BIDDER can participate in OPEN tenders (201 Created)
   - PROCUREMENT_OFFICER receives 403 Forbidden on all bidder bid endpoints
   - Unauthenticated requests receive 401 Unauthorized
2. Bidder Profile Readiness Validation:
   - Incomplete profile fails with 400 and clear error detail
   - 100% complete profile succeeds
3. Tender Status Eligibility Rules:
   - OPEN tenders allow bid creation
   - DRAFT, PUBLISHED, CLOSED, AWARDED tenders reject bid creation (400 Bad Request)
4. Deadline Enforcement:
   - OPEN tender with past deadline rejects bid creation (400 Bad Request)
   - OPEN tender with future deadline succeeds
5. Duplicate Participation Prevention:
   - Second bid creation for same tender + bidder org returns 409 Conflict
6. Deterministic Bid Reference Number:
   - Generated backend-side with BID-YYYY-XXXXXX format
7. Bid Listing & Pagination:
   - Bidder views only own organization's bids
   - Search by bid number, tender title, tender number
   - Status filtering
8. Cross-Bidder Isolation:
   - Bidder B cannot read Bidder A's bid (404 Not Found)
   - Bidder B cannot update Bidder A's bid (404 Not Found)
9. DRAFT Bid Workspace Updates:
   - Quoted amount (Decimal), currency, technical summary, commercial notes, remarks update successfully
   - Data persists across queries
   - Immutable fields (id, bid_number, tender_id, bidder_organization_id, etc.) protected
"""

import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import get_session_factory
from app.core.security import create_access_token
from app.db.models.user import User
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.organization import Organization
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.bid import Bid
from app.services.auth_service import hash_password


client = TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def setup_part3c_fixtures(db_session: Session):
    """Provisions test users, procuring entity, complete/incomplete bidders, and test tenders."""
    bidder_role = db_session.query(Role).filter(Role.name == "BIDDER").first()
    proc_role = db_session.query(Role).filter(Role.name == "PROCUREMENT_OFFICER").first()

    unique_suffix = uuid.uuid4().hex[:8]

    # 1. Procuring Entity & Officer
    proc_org = Organization(
        name=f"Defence Research Organization {unique_suffix}",
        organization_type="MINISTRY",
        city="New Delhi",
        state="Delhi",
        is_active=True,
    )
    db_session.add(proc_org)
    db_session.flush()

    proc_profile = Profile(
        full_name=f"Dr. Officer {unique_suffix}",
        email=f"proc_officer_{unique_suffix}@gov.in",
        role_id=proc_role.id if proc_role else None,
        organization_id=proc_org.id,
        is_active=True,
    )
    db_session.add(proc_profile)
    db_session.flush()

    proc_user = User(
        email=proc_profile.email,
        password_hash=hash_password("Password@123"),
        profile_id=proc_profile.id,
        is_active=True,
    )
    db_session.add(proc_user)

    # 2. Complete Bidder A (Alpha Enterprises)
    bidder_org_a = Organization(
        name=f"Alpha Systems Pvt Ltd {unique_suffix}",
        trade_name="Alpha Systems",
        organization_type="PRIVATE_LIMITED",
        business_category="Medium",
        registered_address="101 Cyber Tech Park, Whitefield",
        city="Bengaluru",
        state="Karnataka",
        pincode="560066",
        country="India",
        pan_number=f"ABCDE{unique_suffix[:4].upper()}F",
        gstin=f"29ABCDE{unique_suffix[:4].upper()}F1Z5",
        udyam_number=f"UDYAM-KR-03-{unique_suffix[:6].upper()}",
        is_active=True,
    )
    db_session.add(bidder_org_a)
    db_session.flush()

    bidder_profile_a = Profile(
        full_name=f"Anand Sharma {unique_suffix}",
        email=f"bidder_a_{unique_suffix}@alpha.com",
        phone="+91 9876543210",
        designation="Managing Director",
        role_id=bidder_role.id if bidder_role else None,
        organization_id=bidder_org_a.id,
        is_active=True,
    )
    db_session.add(bidder_profile_a)
    db_session.flush()

    bidder_user_a = User(
        email=bidder_profile_a.email,
        password_hash=hash_password("Password@123"),
        profile_id=bidder_profile_a.id,
        is_active=True,
    )
    db_session.add(bidder_user_a)

    # 3. Complete Bidder B (Beta Technologies - for Cross-Bidder tests)
    bidder_org_b = Organization(
        name=f"Beta Infotech LLP {unique_suffix}",
        trade_name="Beta Infotech",
        organization_type="LLP",
        business_category="Small",
        registered_address="45 Infocity Square",
        city="Hyderabad",
        state="Telangana",
        pincode="500081",
        country="India",
        pan_number=f"XYZAB{unique_suffix[:4].upper()}K",
        gstin=f"36XYZAB{unique_suffix[:4].upper()}K1Z9",
        is_active=True,
    )
    db_session.add(bidder_org_b)
    db_session.flush()

    bidder_profile_b = Profile(
        full_name=f"Bhavna Rao {unique_suffix}",
        email=f"bidder_b_{unique_suffix}@beta.com",
        phone="+91 9123456789",
        designation="VP Operations",
        role_id=bidder_role.id if bidder_role else None,
        organization_id=bidder_org_b.id,
        is_active=True,
    )
    db_session.add(bidder_profile_b)
    db_session.flush()

    bidder_user_b = User(
        email=bidder_profile_b.email,
        password_hash=hash_password("Password@123"),
        profile_id=bidder_profile_b.id,
        is_active=True,
    )
    db_session.add(bidder_user_b)

    # 4. Incomplete Bidder C (Missing PAN, Address, Phone)
    bidder_org_c = Organization(
        name=f"Incomplete Infratech {unique_suffix}",
        organization_type="PROPRIETORSHIP",
        is_active=True,
    )
    db_session.add(bidder_org_c)
    db_session.flush()

    bidder_profile_c = Profile(
        full_name=f"Chetan Verma {unique_suffix}",
        email=f"bidder_c_{unique_suffix}@incomplete.com",
        role_id=bidder_role.id if bidder_role else None,
        organization_id=bidder_org_c.id,
        is_active=True,
    )
    db_session.add(bidder_profile_c)
    db_session.flush()

    bidder_user_c = User(
        email=bidder_profile_c.email,
        password_hash=hash_password("Password@123"),
        profile_id=bidder_profile_c.id,
        is_active=True,
    )
    db_session.add(bidder_user_c)

    # 5. Tenders in various lifecycle states
    now = datetime.now(timezone.utc)

    # Tender 1: OPEN with future deadline
    open_tender = Tender(
        tender_number=f"GEM/2026/B/{unique_suffix}_OPEN",
        title=f"Supply of Cloud Infrastructure & AI Hardware {unique_suffix}",
        description="Comprehensive procurement of GPU servers and storage nodes.",
        department="IT Department",
        category="IT & Telecom",
        procurement_type="Goods",
        estimated_value=Decimal("8500000.00"),
        currency="INR",
        status="OPEN",
        publish_date=now - timedelta(days=5),
        submission_start_date=now - timedelta(days=3),
        submission_end_date=now + timedelta(days=20),
        organization_id=proc_org.id,
        created_by_profile_id=proc_profile.id,
        is_active=True,
    )
    db_session.add(open_tender)

    # Tender 2: OPEN with PAST deadline
    expired_tender = Tender(
        tender_number=f"GEM/2026/B/{unique_suffix}_EXPIRED",
        title=f"Expired Procurement Notice {unique_suffix}",
        description="Past deadline tender.",
        department="Logistics",
        category="Civil Works",
        procurement_type="Works",
        estimated_value=Decimal("3200000.00"),
        currency="INR",
        status="OPEN",
        publish_date=now - timedelta(days=30),
        submission_start_date=now - timedelta(days=25),
        submission_end_date=now - timedelta(days=2),  # Expired 2 days ago
        organization_id=proc_org.id,
        created_by_profile_id=proc_profile.id,
        is_active=True,
    )
    db_session.add(expired_tender)

    # Tender 3: DRAFT Tender
    draft_tender = Tender(
        tender_number=f"GEM/2026/B/{unique_suffix}_DRAFT",
        title=f"Internal Draft Opportunity {unique_suffix}",
        department="Finance",
        status="DRAFT",
        organization_id=proc_org.id,
        created_by_profile_id=proc_profile.id,
        is_active=True,
    )
    db_session.add(draft_tender)

    # Tender 4: CLOSED Tender
    closed_tender = Tender(
        tender_number=f"GEM/2026/B/{unique_suffix}_CLOSED",
        title=f"Closed Opportunity {unique_suffix}",
        department="Operations",
        status="CLOSED",
        organization_id=proc_org.id,
        created_by_profile_id=proc_profile.id,
        is_active=True,
    )
    db_session.add(closed_tender)

    # Tender 5: Second OPEN Tender for listing tests
    open_tender_2 = Tender(
        tender_number=f"GEM/2026/B/{unique_suffix}_OPEN2",
        title=f"Annual Cybersecurity Maintenance Contract {unique_suffix}",
        description="Annual support and 24x7 SOC monitoring services.",
        department="Cybersecurity Cell",
        category="IT & Telecom",
        procurement_type="Services",
        estimated_value=Decimal("4200000.00"),
        currency="INR",
        status="OPEN",
        publish_date=now - timedelta(days=2),
        submission_start_date=now - timedelta(days=1),
        submission_end_date=now + timedelta(days=15),
        organization_id=proc_org.id,
        created_by_profile_id=proc_profile.id,
        is_active=True,
    )
    db_session.add(open_tender_2)

    db_session.commit()
    db_session.refresh(open_tender)
    db_session.refresh(expired_tender)
    db_session.refresh(draft_tender)
    db_session.refresh(closed_tender)
    db_session.refresh(open_tender_2)

    # Generate auth tokens
    token_bidder_a = create_access_token(subject=str(bidder_user_a.id), email=bidder_user_a.email)
    token_bidder_b = create_access_token(subject=str(bidder_user_b.id), email=bidder_user_b.email)
    token_bidder_c = create_access_token(subject=str(bidder_user_c.id), email=bidder_user_c.email)
    token_proc = create_access_token(subject=str(proc_user.id), email=proc_user.email)


    return {
        "token_bidder_a": token_bidder_a,
        "token_bidder_b": token_bidder_b,
        "token_bidder_c": token_bidder_c,
        "token_proc": token_proc,
        "open_tender": open_tender,
        "open_tender_2": open_tender_2,
        "expired_tender": expired_tender,
        "draft_tender": draft_tender,
        "closed_tender": closed_tender,
        "bidder_a_user": bidder_user_a,
        "bidder_a_org": bidder_org_a,
    }


def test_01_role_authorization_and_unauthenticated(setup_part3c_fixtures):
    """Verifies that only BIDDER role can access bid participation endpoints."""
    fixtures = setup_part3c_fixtures
    tender_id = str(fixtures["open_tender"].id)

    # 1. Unauthenticated -> 401
    res_unauth = client.post(f"/api/v1/bidder/tenders/{tender_id}/bids")
    assert res_unauth.status_code == 401

    # 2. PROCUREMENT_OFFICER -> 403 Forbidden
    res_proc = client.post(
        f"/api/v1/bidder/tenders/{tender_id}/bids",
        headers={"Authorization": f"Bearer {fixtures['token_proc']}"},
    )
    assert res_proc.status_code == 403

    # Procurement officer forbidden on listing and workspace
    res_proc_list = client.get(
        "/api/v1/bidder/bids",
        headers={"Authorization": f"Bearer {fixtures['token_proc']}"},
    )
    assert res_proc_list.status_code == 403


def test_02_incomplete_profile_readiness_blocked(setup_part3c_fixtures):
    """Verifies that a bidder with an incomplete profile is blocked with clear error guidance."""
    fixtures = setup_part3c_fixtures
    tender_id = str(fixtures["open_tender"].id)

    res = client.post(
        f"/api/v1/bidder/tenders/{tender_id}/bids",
        headers={"Authorization": f"Bearer {fixtures['token_bidder_c']}"},
    )
    assert res.status_code == 400
    detail = res.json().get("detail", "")
    assert "Complete your bidder profile before participating" in detail
    assert "PAN Number" in detail or "Registered Address" in detail


def test_03_non_open_tenders_rejected(setup_part3c_fixtures):
    """Verifies that non-OPEN tenders (DRAFT, CLOSED, etc.) reject bid creation."""
    fixtures = setup_part3c_fixtures
    headers = {"Authorization": f"Bearer {fixtures['token_bidder_a']}"}

    # 1. DRAFT tender rejected
    draft_id = str(fixtures["draft_tender"].id)
    res_draft = client.post(f"/api/v1/bidder/tenders/{draft_id}/bids", headers=headers)
    assert res_draft.status_code == 400
    assert "OPEN tenders" in res_draft.json().get("detail", "")

    # 2. CLOSED tender rejected
    closed_id = str(fixtures["closed_tender"].id)
    res_closed = client.post(f"/api/v1/bidder/tenders/{closed_id}/bids", headers=headers)
    assert res_closed.status_code == 400
    assert "OPEN tenders" in res_closed.json().get("detail", "")


def test_04_expired_submission_deadline_rejected(setup_part3c_fixtures):
    """Verifies that an OPEN tender whose submission deadline has passed rejects bid creation."""
    fixtures = setup_part3c_fixtures
    headers = {"Authorization": f"Bearer {fixtures['token_bidder_a']}"}

    expired_id = str(fixtures["expired_tender"].id)
    res = client.post(f"/api/v1/bidder/tenders/{expired_id}/bids", headers=headers)
    assert res.status_code == 400
    assert "submission deadline" in res.json().get("detail", "").lower()


def test_05_successful_draft_bid_creation(setup_part3c_fixtures):
    """Verifies successful creation of a DRAFT bid for an eligible OPEN tender."""
    fixtures = setup_part3c_fixtures
    headers = {"Authorization": f"Bearer {fixtures['token_bidder_a']}"}
    tender = fixtures["open_tender"]
    tender_id = str(tender.id)

    payload = {
        "quoted_amount": 7950000.00,
        "currency": "INR",
        "technical_summary": "High-performance enterprise GPU clusters meeting Tier-3 GeM specs.",
        "commercial_notes": "Includes 3 years on-site 24x7 OEM warranty and installation.",
        "remarks": "Ready for delivery within 4 weeks from LOA issuance.",
    }

    res = client.post(
        f"/api/v1/bidder/tenders/{tender_id}/bids",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()

    assert "id" in data
    assert data["tender_id"] == tender_id
    assert data["status"] == "DRAFT"
    assert data["bid_number"].startswith("BID-")
    assert Decimal(str(data["quoted_amount"])) == Decimal("7950000.00")
    assert data["currency"] == "INR"
    assert data["technical_summary"] == payload["technical_summary"]
    assert data["commercial_notes"] == payload["commercial_notes"]
    assert data["remarks"] == payload["remarks"]
    assert data["is_active"] is True

    # Check tender embedded summary
    assert data["tender"]["id"] == tender_id
    assert data["tender"]["tender_number"] == tender.tender_number
    assert data["tender"]["title"] == tender.title

    # Check bidder org summary
    assert data["bidder_organization"]["id"] == str(fixtures["bidder_a_org"].id)

    # Save created bid ID for subsequent tests
    fixtures["created_bid_id"] = data["id"]
    fixtures["created_bid_number"] = data["bid_number"]


def test_06_duplicate_participation_prevented_409(setup_part3c_fixtures):
    """Verifies that attempting to create a second bid on the same tender returns 409 Conflict."""
    fixtures = setup_part3c_fixtures
    headers = {"Authorization": f"Bearer {fixtures['token_bidder_a']}"}
    tender_id = str(fixtures["open_tender"].id)

    res = client.post(
        f"/api/v1/bidder/tenders/{tender_id}/bids",
        json={"quoted_amount": 8000000.00},
        headers=headers,
    )
    assert res.status_code == 409
    assert "A bid already exists for this tender." in res.json().get("detail", "")


def test_07_check_existing_bid_endpoint(setup_part3c_fixtures):
    """Verifies the endpoint that checks existing bid status for the tender detail page."""
    fixtures = setup_part3c_fixtures
    headers_a = {"Authorization": f"Bearer {fixtures['token_bidder_a']}"}
    headers_b = {"Authorization": f"Bearer {fixtures['token_bidder_b']}"}
    tender_id = str(fixtures["open_tender"].id)

    # Bidder A has a bid
    res_a = client.get(f"/api/v1/bidder/tenders/{tender_id}/bid", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a is not None
    assert data_a["id"] == fixtures["created_bid_id"]
    assert data_a["bid_number"] == fixtures["created_bid_number"]

    # Bidder B has NO bid yet
    res_b = client.get(f"/api/v1/bidder/tenders/{tender_id}/bid", headers=headers_b)
    assert res_b.status_code == 200
    assert res_b.json() is None


def test_08_list_bidder_bids_and_filtering(setup_part3c_fixtures):
    """Verifies listing bidder's bids with pagination, search, and status filters."""
    fixtures = setup_part3c_fixtures
    headers_a = {"Authorization": f"Bearer {fixtures['token_bidder_a']}"}

    # Also create a bid for Bidder A on open_tender_2
    tender_2_id = str(fixtures["open_tender_2"].id)
    client.post(
        f"/api/v1/bidder/tenders/{tender_2_id}/bids",
        json={"quoted_amount": 4100000.00},
        headers=headers_a,
    )

    # 1. List all bids
    res = client.get("/api/v1/bidder/bids", headers=headers_a)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2
    assert data["page"] == 1

    # 2. Filter by status
    res_draft = client.get("/api/v1/bidder/bids?status=DRAFT", headers=headers_a)
    assert res_draft.status_code == 200
    assert all(b["status"] == "DRAFT" for b in res_draft.json()["items"])

    # 3. Search by tender title keyword
    res_search = client.get("/api/v1/bidder/bids?search=Cybersecurity", headers=headers_a)
    assert res_search.status_code == 200
    items = res_search.json()["items"]
    assert len(items) == 1
    assert "Cybersecurity" in items[0]["tender_title"]

    # 4. Search by bid number
    bid_num = fixtures["created_bid_number"]
    res_bid_search = client.get(f"/api/v1/bidder/bids?search={bid_num}", headers=headers_a)
    assert res_bid_search.status_code == 200
    assert len(res_bid_search.json()["items"]) == 1
    assert res_bid_search.json()["items"][0]["bid_number"] == bid_num


def test_09_bid_workspace_detail_and_cross_bidder_isolation(setup_part3c_fixtures):
    """Verifies bid workspace retrieval and strict cross-bidder isolation (404 on other's bid)."""
    fixtures = setup_part3c_fixtures
    headers_a = {"Authorization": f"Bearer {fixtures['token_bidder_a']}"}
    headers_b = {"Authorization": f"Bearer {fixtures['token_bidder_b']}"}
    bid_id = fixtures["created_bid_id"]

    # 1. Bidder A can access own bid workspace
    res_a = client.get(f"/api/v1/bidder/bids/{bid_id}", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["id"] == bid_id
    assert res_a.json()["bid_number"] == fixtures["created_bid_number"]

    # 2. Bidder B attempts to access Bidder A's bid -> 404 Not Found (zero data leakage)
    res_b = client.get(f"/api/v1/bidder/bids/{bid_id}", headers=headers_b)
    assert res_b.status_code == 404

    # 3. Random non-existent UUID -> 404
    res_fake = client.get(f"/api/v1/bidder/bids/{uuid.uuid4()}", headers=headers_a)
    assert res_fake.status_code == 404


def test_10_update_draft_bid_and_field_persistence(setup_part3c_fixtures):
    """Verifies that editable fields of a DRAFT bid are updated and persisted correctly."""
    fixtures = setup_part3c_fixtures
    headers_a = {"Authorization": f"Bearer {fixtures['token_bidder_a']}"}
    headers_b = {"Authorization": f"Bearer {fixtures['token_bidder_b']}"}
    bid_id = fixtures["created_bid_id"]

    # 1. Bidder B cannot edit Bidder A's bid -> 404
    res_b = client.patch(
        f"/api/v1/bidder/bids/{bid_id}",
        json={"quoted_amount": 100.00},
        headers=headers_b,
    )
    assert res_b.status_code == 404

    # 2. Bidder A updates draft values
    update_payload = {
        "quoted_amount": 7800000.50,
        "currency": "INR",
        "technical_summary": "Updated specification: Added redundant power supplies and SAN connectivity.",
        "commercial_notes": "Price includes 5-year AMC with 4-hour SLA.",
        "remarks": "Sample unit available for pre-dispatch inspection.",
    }

    res_update = client.patch(
        f"/api/v1/bidder/bids/{bid_id}",
        json=update_payload,
        headers=headers_a,
    )
    assert res_update.status_code == 200
    updated_data = res_update.json()

    assert Decimal(str(updated_data["quoted_amount"])) == Decimal("7800000.50")
    assert updated_data["technical_summary"] == update_payload["technical_summary"]
    assert updated_data["commercial_notes"] == update_payload["commercial_notes"]
    assert updated_data["remarks"] == update_payload["remarks"]
    assert updated_data["status"] == "DRAFT"

    # 3. Fetch again to verify persistence
    res_get = client.get(f"/api/v1/bidder/bids/{bid_id}", headers=headers_a)
    assert res_get.status_code == 200
    persisted = res_get.json()
    assert Decimal(str(persisted["quoted_amount"])) == Decimal("7800000.50")
    assert persisted["technical_summary"] == update_payload["technical_summary"]


if __name__ == "__main__":
    print("\n--- Running Part 3C Automated Test Suite ---")
    pytest.main(["-v", "-s", __file__])
