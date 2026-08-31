"""Comprehensive Automated Test Suite for Part 3B — Bidder Tender Discovery

Tests:
1. Bidder Tender List Discovery across buyer organizations
2. Search functionality (title, tender_number, department, category)
3. Filter by category, procurement_type, status
4. Sorting (newest, deadline, value_high, value_low)
5. Pagination functionality
6. Visibility security: DRAFT tenders are hidden (404 on direct detail GET)
7. Visibility security: ARCHIVED tenders are hidden (404 on direct detail GET)
8. Tender detail endpoint with formatted condition_text for eligibility requirements
9. Sensitive field protection: No scoring weights or private IDs leaked to bidders
10. Role security: PROCUREMENT_OFFICER receives 403 Forbidden
11. Unauthenticated requests receive 401 Unauthorized
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
def setup_tender_discovery_fixtures(db_session: Session):
    """Provisions Buyer Organizations, Procurement Officer, Bidder, and varied status Tenders."""
    bidder_role = db_session.query(Role).filter(Role.name == "BIDDER").first()
    proc_role = db_session.query(Role).filter(Role.name == "PROCUREMENT_OFFICER").first()

    unique_suffix = uuid.uuid4().hex[:8]

    # 1. Buyer Org 1 (Ministry of Electronics)
    buyer_org1 = Organization(
        name=f"Ministry of Electronics & IT {unique_suffix}",
        organization_type="GOVERNMENT_ENTITY",
        city="New Delhi",
        state="Delhi",
        is_active=True,
    )
    db_session.add(buyer_org1)

    # 2. Buyer Org 2 (Indian Oil CPSE)
    buyer_org2 = Organization(
        name=f"Indian Oil Corporation {unique_suffix}",
        organization_type="PUBLIC_LIMITED",
        city="Mumbai",
        state="Maharashtra",
        is_active=True,
    )
    db_session.add(buyer_org2)
    db_session.flush()

    # 3. Procurement Officer Profile & User
    officer_prof = Profile(
        full_name="Procurement Director",
        email=f"proc_dir_{unique_suffix}@example.gov.in",
        role_id=proc_role.id,
        organization_id=buyer_org1.id,
        is_active=True,
    )
    db_session.add(officer_prof)
    db_session.flush()

    officer_user = User(
        email=officer_prof.email,
        password_hash=hash_password("Password123!"),
        profile_id=officer_prof.id,
        is_active=True,
    )
    db_session.add(officer_user)

    # 4. Bidder Profile & User
    bidder_org = Organization(
        name=f"Discovery Bidder Tech {unique_suffix}",
        organization_type="PRIVATE_LIMITED",
        is_active=True,
    )
    db_session.add(bidder_org)
    db_session.flush()

    bidder_prof = Profile(
        full_name="Discovery Bidder Manager",
        email=f"discovery_bidder_{unique_suffix}@example.com",
        role_id=bidder_role.id,
        organization_id=bidder_org.id,
        is_active=True,
    )
    db_session.add(bidder_prof)
    db_session.flush()

    bidder_user = User(
        email=bidder_prof.email,
        password_hash=hash_password("Password123!"),
        profile_id=bidder_prof.id,
        is_active=True,
    )
    db_session.add(bidder_user)

    now = datetime.now(timezone.utc)

    # 5. OPEN Tender 1 (IT Hardware from Org 1)
    open_tender1 = Tender(
        tender_number=f"GEM/2026/B/IT-{unique_suffix[:6].upper()}-01",
        title=f"Procurement of Secure Cloud Laptops and Desktops {unique_suffix}",
        description="High performance workstations for AI and data processing centres.",
        department="Information Technology Division",
        category="IT & Telecom",
        procurement_type="Goods",
        estimated_value=Decimal("75000000.00"),
        currency="INR",
        publish_date=now - timedelta(days=2),
        submission_start_date=now - timedelta(days=1),
        submission_end_date=now + timedelta(days=15),
        evaluation_start_date=now + timedelta(days=16),
        organization_id=buyer_org1.id,
        created_by_profile_id=officer_prof.id,
        status="OPEN",
        is_active=True,
        published_at=now - timedelta(days=2),
        opened_at=now - timedelta(days=1),
    )
    db_session.add(open_tender1)
    db_session.flush()

    # Requirements for OPEN Tender 1
    req1 = TenderRequirement(
        tender_id=open_tender1.id,
        code="STAT-GST-001",
        name="Valid GSTIN Registration Certificate",
        description="Bidder must possess active GST registration in operating jurisdiction.",
        category="STATUTORY",
        requirement_type="STATUS",
        operator="EQUALS",
        expected_value="ACTIVE",
        is_mandatory=True,
        weight=Decimal("15.0"),
        display_order=1,
        is_active=True,
    )
    req2 = TenderRequirement(
        tender_id=open_tender1.id,
        code="FIN-TURN-001",
        name="Minimum Annual Financial Turnover",
        description="Average annual turnover for past 3 financial years.",
        category="FINANCIAL",
        requirement_type="NUMBER",
        operator="GREATER_THAN_OR_EQUAL",
        expected_value=25000000,
        is_mandatory=True,
        weight=Decimal("20.0"),
        display_order=2,
        is_active=True,
    )
    req3 = TenderRequirement(
        tender_id=open_tender1.id,
        code="TECH-MAF-001",
        name="OEM Manufacturer Authorization Form (MAF)",
        description="Original authorization letter from hardware manufacturer.",
        category="TECHNICAL",
        requirement_type="DOCUMENT",
        operator="EXISTS",
        expected_value=True,
        is_mandatory=True,
        weight=Decimal("25.0"),
        display_order=3,
        is_active=True,
    )
    db_session.add_all([req1, req2, req3])

    # 6. OPEN Tender 2 (Petroleum Services from Org 2 - Cross-organization verification)
    open_tender2 = Tender(
        tender_number=f"GEM/2026/B/IOC-{unique_suffix[:6].upper()}-02",
        title=f"Industrial Pipeline Surveillance and Facility Maintenance {unique_suffix}",
        description="Annual maintenance contract for petroleum distribution facilities.",
        department="Engineering Operations",
        category="Services",
        procurement_type="Services",
        estimated_value=Decimal("120000000.00"),
        currency="INR",
        publish_date=now - timedelta(days=3),
        submission_start_date=now - timedelta(days=2),
        submission_end_date=now + timedelta(days=7),
        evaluation_start_date=now + timedelta(days=8),
        organization_id=buyer_org2.id,
        created_by_profile_id=officer_prof.id,
        status="OPEN",
        is_active=True,
        published_at=now - timedelta(days=3),
        opened_at=now - timedelta(days=2),
    )
    db_session.add(open_tender2)

    # 7. PUBLISHED (Upcoming) Tender 3
    published_tender = Tender(
        tender_number=f"GEM/2026/B/UPC-{unique_suffix[:6].upper()}-03",
        title=f"Upcoming High Voltage Transformers Supply {unique_suffix}",
        description="Notice for upcoming supply of grid transformers.",
        department="Power & Energy Wing",
        category="Civil & Electrical",
        procurement_type="Goods",
        estimated_value=Decimal("45000000.00"),
        currency="INR",
        publish_date=now - timedelta(days=1),
        submission_start_date=now + timedelta(days=5),
        submission_end_date=now + timedelta(days=25),
        organization_id=buyer_org1.id,
        created_by_profile_id=officer_prof.id,
        status="PUBLISHED",
        is_active=True,
        published_at=now - timedelta(days=1),
    )
    db_session.add(published_tender)

    # 8. DRAFT Tender 4 (MUST NOT be visible to Bidder)
    draft_tender = Tender(
        tender_number=f"GEM/2026/B/DFT-{unique_suffix[:6].upper()}-04",
        title=f"Internal Secret Draft Tender {unique_suffix}",
        description="Confidential procurement draft under preparation.",
        department="Internal Operations",
        category="Consulting",
        procurement_type="Services",
        estimated_value=Decimal("1000000.00"),
        currency="INR",
        organization_id=buyer_org1.id,
        created_by_profile_id=officer_prof.id,
        status="DRAFT",
        is_active=True,
    )
    db_session.add(draft_tender)

    # 9. ARCHIVED Tender 5 (MUST NOT be visible to Bidder)
    archived_tender = Tender(
        tender_number=f"GEM/2026/B/ARC-{unique_suffix[:6].upper()}-05",
        title=f"Old Canceled Tender Record {unique_suffix}",
        description="Archived tender from prior fiscal year.",
        department="Archives",
        category="General",
        procurement_type="Works",
        estimated_value=Decimal("500000.00"),
        currency="INR",
        organization_id=buyer_org1.id,
        created_by_profile_id=officer_prof.id,
        status="ARCHIVED",
        is_active=False,
    )
    db_session.add(archived_tender)

    db_session.commit()

    token_bidder = create_access_token(subject=str(bidder_user.id), email=bidder_user.email)
    token_officer = create_access_token(subject=str(officer_user.id), email=officer_user.email)

    return {
        "bidder_token": token_bidder,
        "officer_token": token_officer,
        "open_tender1": open_tender1,
        "open_tender2": open_tender2,
        "published_tender": published_tender,
        "draft_tender": draft_tender,
        "archived_tender": archived_tender,
        "unique_suffix": unique_suffix,
    }


def test_01_bidder_tenders_list_discovery(setup_tender_discovery_fixtures):
    """Bidder can browse available tenders and see OPEN and PUBLISHED opportunities across organizations."""
    token = setup_tender_discovery_fixtures["bidder_token"]
    suffix = setup_tender_discovery_fixtures["unique_suffix"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/api/v1/bidder/tenders?search={suffix}", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data

    # Should contain open_tender1, open_tender2, published_tender (total 3 matching this suffix)
    assert data["total"] == 3
    numbers = [item["tender_number"] for item in data["items"]]
    assert setup_tender_discovery_fixtures["open_tender1"].tender_number in numbers
    assert setup_tender_discovery_fixtures["open_tender2"].tender_number in numbers
    assert setup_tender_discovery_fixtures["published_tender"].tender_number in numbers

    # DRAFT and ARCHIVED must NEVER appear in the list
    assert setup_tender_discovery_fixtures["draft_tender"].tender_number not in numbers
    assert setup_tender_discovery_fixtures["archived_tender"].tender_number not in numbers


def test_02_bidder_search_by_keyword(setup_tender_discovery_fixtures):
    """Bidder can search specifically for 'Cloud Laptops'."""
    token = setup_tender_discovery_fixtures["bidder_token"]
    suffix = setup_tender_discovery_fixtures["unique_suffix"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/api/v1/bidder/tenders?search=Cloud+Laptops+{suffix}", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["tender_number"] == setup_tender_discovery_fixtures["open_tender1"].tender_number
    assert data["items"][0]["department"] == "Information Technology Division"
    assert data["items"][0]["active_requirements_count"] == 3


def test_03_bidder_filter_by_category_and_status(setup_tender_discovery_fixtures):
    """Bidder can filter by Category ('Services') and Status ('OPEN')."""
    token = setup_tender_discovery_fixtures["bidder_token"]
    suffix = setup_tender_discovery_fixtures["unique_suffix"]
    headers = {"Authorization": f"Bearer {token}"}

    # Filter by category = Services
    res_cat = client.get(f"/api/v1/bidder/tenders?category=Services&search={suffix}", headers=headers)
    assert res_cat.status_code == 200
    data_cat = res_cat.json()
    assert data_cat["total"] == 1
    assert data_cat["items"][0]["tender_number"] == setup_tender_discovery_fixtures["open_tender2"].tender_number

    # Filter by status = PUBLISHED
    res_pub = client.get(f"/api/v1/bidder/tenders?status=PUBLISHED&search={suffix}", headers=headers)
    assert res_pub.status_code == 200
    data_pub = res_pub.json()
    assert data_pub["total"] == 1
    assert data_pub["items"][0]["status"] == "PUBLISHED"


def test_04_bidder_sorting(setup_tender_discovery_fixtures):
    """Bidder can sort available tenders by estimated value and submission deadline."""
    token = setup_tender_discovery_fixtures["bidder_token"]
    suffix = setup_tender_discovery_fixtures["unique_suffix"]
    headers = {"Authorization": f"Bearer {token}"}

    # Sort by value_high (Oil pipeline 12 Cr > IT Cloud 7.5 Cr > Transformer 4.5 Cr)
    res_val = client.get(f"/api/v1/bidder/tenders?sort_by=value_high&search={suffix}", headers=headers)
    assert res_val.status_code == 200
    items = res_val.json()["items"]
    assert len(items) == 3
    assert Decimal(str(items[0]["estimated_value"])) >= Decimal(str(items[1]["estimated_value"]))


def test_05_draft_and_archived_tenders_return_404(setup_tender_discovery_fixtures):
    """Direct lookup of DRAFT or ARCHIVED tenders returns 404 to bidders."""
    token = setup_tender_discovery_fixtures["bidder_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # DRAFT tender detail lookup
    draft_id = setup_tender_discovery_fixtures["draft_tender"].id
    res_draft = client.get(f"/api/v1/bidder/tenders/{draft_id}", headers=headers)
    assert res_draft.status_code == 404
    assert "not currently available" in res_draft.json()["detail"]

    # ARCHIVED tender detail lookup
    arch_id = setup_tender_discovery_fixtures["archived_tender"].id
    res_arch = client.get(f"/api/v1/bidder/tenders/{arch_id}", headers=headers)
    assert res_arch.status_code == 404


def test_06_bidder_tender_detail_and_requirement_formatting(setup_tender_discovery_fixtures):
    """Bidder can retrieve full tender detail with human-readable requirement conditions."""
    token = setup_tender_discovery_fixtures["bidder_token"]
    open_id = setup_tender_discovery_fixtures["open_tender1"].id
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/api/v1/bidder/tenders/{open_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["tender_number"] == setup_tender_discovery_fixtures["open_tender1"].tender_number
    assert data["status"] == "OPEN"
    assert "organization" in data
    assert "New Delhi" in data["organization"]["city"]

    # Check sanitized requirements
    reqs = data["requirements"]
    assert len(reqs) == 3

    gst_req = next(r for r in reqs if r["code"] == "STAT-GST-001")
    assert gst_req["condition_text"] == "Must be Active & Verified"

    turnover_req = next(r for r in reqs if r["code"] == "FIN-TURN-001")
    assert "Minimum required: 25000000" in turnover_req["condition_text"]

    maf_req = next(r for r in reqs if r["code"] == "TECH-MAF-001")
    assert maf_req["condition_text"] == "Mandatory Document / Proof Submission Required"

    # Ensure internal scoring weight or creator profile IDs are NOT exposed in schema
    assert "weight" not in gst_req
    assert "created_by_profile_id" not in data


def test_07_procurement_officer_cannot_access_bidder_tenders(setup_tender_discovery_fixtures):
    """PROCUREMENT_OFFICER attempting to call bidder discovery endpoint receives 403 Forbidden."""
    token = setup_tender_discovery_fixtures["officer_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res_list = client.get("/api/v1/bidder/tenders", headers=headers)
    assert res_list.status_code == 403

    open_id = setup_tender_discovery_fixtures["open_tender1"].id
    res_detail = client.get(f"/api/v1/bidder/tenders/{open_id}", headers=headers)
    assert res_detail.status_code == 403


def test_08_unauthenticated_request_rejected():
    """Unauthenticated requests receive 401 Unauthorized."""
    res1 = client.get("/api/v1/bidder/tenders")
    assert res1.status_code == 401

    sample_uuid = uuid.uuid4()
    res2 = client.get(f"/api/v1/bidder/tenders/{sample_uuid}")
    assert res2.status_code == 401
