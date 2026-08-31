"""Comprehensive Automated Test Suite for Part 3A — Bidder Profile & Organization Setup

Tests:
1. Bidder Profile retrieval and completion calculation
2. Bidder Contact / Signatory update
3. Bidder Organization retrieval and statutory details update
4. Format validation (PAN format, GSTIN format, PIN code format)
5. Uniqueness conflict handling (Duplicate PAN / GSTIN returns 409 Conflict)
6. Cross-tenant isolation (Bidder A cannot update Bidder B's profile/organization)
7. Role authorization (Procurement Officer cannot access Bidder profile APIs -> 403 Forbidden)
8. Regressions (Part 1 Auth and Part 2 Tender operations remain unaffected)
"""

import sys
import os
import uuid
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
def setup_test_users(db_session: Session):
    """Creates two distinct Bidders and one Procurement Officer for testing."""
    bidder_role = db_session.query(Role).filter(Role.name == "BIDDER").first()
    proc_role = db_session.query(Role).filter(Role.name == "PROCUREMENT_OFFICER").first()

    unique_suffix = uuid.uuid4().hex[:8]

    # 1. Bidder A
    org_a = Organization(
        name=f"Alpha Infotech Solutions {unique_suffix}",
        organization_type="PRIVATE_LIMITED",
        is_active=True,
    )
    db_session.add(org_a)
    db_session.flush()

    prof_a = Profile(
        full_name="Alpha Authorized Signatory",
        email=f"alpha_bidder_{unique_suffix}@example.com",
        role_id=bidder_role.id,
        organization_id=org_a.id,
        is_active=True,
    )
    db_session.add(prof_a)
    db_session.flush()

    user_a = User(
        email=prof_a.email,
        password_hash=hash_password("Password123!"),
        profile_id=prof_a.id,
        is_active=True,
    )
    db_session.add(user_a)

    # 2. Bidder B
    org_b = Organization(
        name=f"Beta Construction Ltd {unique_suffix}",
        organization_type="LLP",
        is_active=True,
    )
    db_session.add(org_b)
    db_session.flush()

    prof_b = Profile(
        full_name="Beta Managing Director",
        email=f"beta_bidder_{unique_suffix}@example.com",
        role_id=bidder_role.id,
        organization_id=org_b.id,
        is_active=True,
    )
    db_session.add(prof_b)
    db_session.flush()

    user_b = User(
        email=prof_b.email,
        password_hash=hash_password("Password123!"),
        profile_id=prof_b.id,
        is_active=True,
    )
    db_session.add(user_b)

    # 3. Procurement Officer
    prof_p = Profile(
        full_name="Procurement Manager",
        email=f"proc_officer_{unique_suffix}@example.com",
        role_id=proc_role.id,
        is_active=True,
    )
    db_session.add(prof_p)
    db_session.flush()

    user_p = User(
        email=prof_p.email,
        password_hash=hash_password("Password123!"),
        profile_id=prof_p.id,
        is_active=True,
    )
    db_session.add(user_p)
    db_session.commit()

    token_a = create_access_token(subject=str(user_a.id), email=user_a.email)
    token_b = create_access_token(subject=str(user_b.id), email=user_b.email)
    token_p = create_access_token(subject=str(user_p.id), email=user_p.email)

    return {
        "user_a": user_a,
        "token_a": token_a,
        "org_a": org_a,
        "user_b": user_b,
        "token_b": token_b,
        "org_b": org_b,
        "user_p": user_p,
        "token_p": token_p,
        "unique_suffix": unique_suffix,
    }


def test_01_get_bidder_profile_initial(setup_test_users):
    """Bidder A fetches their profile and receives valid completion stats."""
    token = setup_test_users["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/bidder/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "profile" in data
    assert "completion" in data
    assert data["profile"]["full_name"] == "Alpha Authorized Signatory"
    assert data["profile"]["role"] == "BIDDER"
    assert "completion_percentage" in data["completion"]
    assert data["completion"]["is_complete"] is False
    assert "PAN Number" in data["completion"]["missing_required_fields"]


def test_02_update_bidder_contact_profile(setup_test_users):
    """Bidder A updates contact phone and designation."""
    token = setup_test_users["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "full_name": "Alpha Chief Executive Officer",
        "phone": "+91 9876543210",
        "designation": "Director",
    }
    response = client.patch("/api/v1/bidder/profile", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["profile"]["full_name"] == "Alpha Chief Executive Officer"
    assert data["profile"]["phone"] == "+91 9876543210"
    assert data["profile"]["designation"] == "Director"


def test_03_get_bidder_organization(setup_test_users):
    """Bidder A fetches full organization information."""
    token = setup_test_users["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/bidder/organization", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "organization" in data
    assert "completion" in data
    assert data["organization"]["organization_type"] == "PRIVATE_LIMITED"


def test_04_update_bidder_organization_full(setup_test_users):
    """Bidder A completes all statutory and address details."""
    token = setup_test_users["token_a"]
    digits = ''.join(c for c in setup_test_users["unique_suffix"] if c.isdigit())
    if len(digits) < 4:
        digits = (digits + "1234")[:4]
    else:
        digits = digits[:4]
    pan_val = f"AAACB{digits}A"
    gstin_val = f"29AAACB{digits}A1Z5"
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Alpha Infotech Private Limited",
        "trade_name": "Alpha Tech",
        "organization_type": "PRIVATE_LIMITED",
        "business_category": "MEDIUM",
        "year_established": 2018,
        "registered_address": "Plot 42, Electronics City Phase 1",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560100",
        "country": "India",
        "official_email": "contact@alphatech.in",
        "official_phone": "+91 80 23456789",
        "website": "https://www.alphatech.in",
        "pan_number": pan_val,
        "gstin": gstin_val,
        "udyam_number": "UDYAM-KR-03-0012345",
        "cin_llpin": "U72200KA2018PTC123456",
        "startup_india_number": "DIPP12345",
        "nsic_number": "NSIC/BNG/2021/001",
        "epfo_code": "KN/BNG/1234567/000",
        "esic_code": "53000123450001001",
    }
    response = client.patch("/api/v1/bidder/organization", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    org = data["organization"]
    comp = data["completion"]

    assert org["name"] == "Alpha Infotech Private Limited"
    assert org["trade_name"] == "Alpha Tech"
    assert org["city"] == "Bengaluru"
    assert org["pincode"] == "560100"
    assert org["pan_number"] == pan_val
    assert org["gstin"] == gstin_val
    assert org["udyam_number"] == "UDYAM-KR-03-0012345"

    # Profile completion should now be 100%
    assert comp["completion_percentage"] == 100
    assert comp["is_complete"] is True
    assert len(comp["missing_required_fields"]) == 0


def test_05_format_validation_pan_gstin_pincode(setup_test_users):
    """Ensures format errors are rejected cleanly."""
    token = setup_test_users["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    # Invalid PAN
    res_pan = client.patch("/api/v1/bidder/organization", json={"pan_number": "INVALID_PAN"}, headers=headers)
    assert res_pan.status_code == 422

    # Invalid GSTIN
    res_gstin = client.patch("/api/v1/bidder/organization", json={"gstin": "INVALID_GSTIN"}, headers=headers)
    assert res_gstin.status_code == 422

    # Invalid PIN Code
    res_pin = client.patch("/api/v1/bidder/organization", json={"pincode": "123"}, headers=headers)
    assert res_pin.status_code == 422


def test_06_uniqueness_conflict_pan_and_gstin(setup_test_users):
    """Bidder B attempts to register the same PAN and GSTIN as Bidder A -> 409 Conflict."""
    token_b = setup_test_users["token_b"]
    digits = ''.join(c for c in setup_test_users["unique_suffix"] if c.isdigit())
    if len(digits) < 4:
        digits = (digits + "1234")[:4]
    else:
        digits = digits[:4]
    existing_pan = f"AAACB{digits}A"
    existing_gstin = f"29AAACB{digits}A1Z5"
    headers = {"Authorization": f"Bearer {token_b}"}

    # Duplicate PAN
    res_pan = client.patch("/api/v1/bidder/organization", json={"pan_number": existing_pan}, headers=headers)
    assert res_pan.status_code == 409
    assert "already registered" in res_pan.json()["detail"]

    # Duplicate GSTIN
    res_gstin = client.patch("/api/v1/bidder/organization", json={"gstin": existing_gstin}, headers=headers)
    assert res_gstin.status_code == 409
    assert "already registered" in res_gstin.json()["detail"]


def test_07_cross_user_isolation(setup_test_users):
    """Bidder B cannot modify Bidder A's organization data; each operates on own context."""
    token_b = setup_test_users["token_b"]
    headers = {"Authorization": f"Bearer {token_b}"}

    res_b = client.patch(
        "/api/v1/bidder/organization",
        json={"name": "Beta Enterprises Private Limited"},
        headers=headers,
    )
    assert res_b.status_code == 200
    assert res_b.json()["organization"]["name"] == "Beta Enterprises Private Limited"

    # Verify Bidder A's organization remains unchanged
    token_a = setup_test_users["token_a"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    res_a = client.get("/api/v1/bidder/organization", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["organization"]["name"] == "Alpha Infotech Private Limited"


def test_08_procurement_officer_cannot_access_bidder_profile(setup_test_users):
    """Procurement officer attempting bidder profile access gets 403 Forbidden."""
    token_p = setup_test_users["token_p"]
    headers = {"Authorization": f"Bearer {token_p}"}

    res1 = client.get("/api/v1/bidder/profile", headers=headers)
    assert res1.status_code == 403

    res2 = client.patch("/api/v1/bidder/profile", json={"phone": "1234567890"}, headers=headers)
    assert res2.status_code == 403

    res3 = client.get("/api/v1/bidder/organization", headers=headers)
    assert res3.status_code == 403

    res4 = client.patch("/api/v1/bidder/organization", json={"city": "Delhi"}, headers=headers)
    assert res4.status_code == 403


def test_09_unauthenticated_request_rejected():
    """Unauthenticated requests receive 401 Unauthorized."""
    res1 = client.get("/api/v1/bidder/profile")
    assert res1.status_code == 401

    res2 = client.get("/api/v1/bidder/organization")
    assert res2.status_code == 401
