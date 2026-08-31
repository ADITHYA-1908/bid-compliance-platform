"""
Part 2B Automated Tender CRUD Backend API Test Suite
Validates:
1. Create tender as PROCUREMENT_OFFICER (auto-assigns ownership, DRAFT status)
2. 409 Conflict on duplicate tender_number
3. 422 Validation error on invalid date ranges
4. 403 Forbidden for BIDDER on POST, PATCH, DELETE
5. 401 Unauthorized for unauthenticated requests
6. Organization-scoped list with pagination and search
7. Cross-organization isolation (Officer B cannot access Officer A's tender)
8. Partial updates (PATCH) on DRAFT tenders
9. Soft delete / archive (DELETE) and query filtering
"""

import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
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
from app.core.security import hash_password

client = TestClient(app)


def get_token_for_user(email: str, password: str = "TestPassword123!") -> str:
    """Helper to authenticate and retrieve access token."""
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def ensure_second_procurement_officer() -> str:
    """Provisions a second procurement officer in a distinct organization for isolation tests."""
    email = "officer_b@railways.gov.local"
    password = "TestPassword123!"

    session_factory = get_session_factory()
    db = session_factory()
    try:
        user = db.scalars(select(User).where(User.email == email)).first()
        if not user:
            role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
            org = Organization(
                name="Ministry of Railways (Testing Division B)",
                organization_type="Government Ministry",
                is_active=True,
            )
            db.add(org)
            db.flush()

            profile = Profile(
                full_name="Railways Procurement Officer B",
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

        return get_token_for_user(email, password)
    finally:
        db.close()


def test_01_create_tender_success_and_rbac():
    """Verify Tender creation, ownership auto-binding, and role enforcement."""
    proc_token = get_token_for_user("procurement@test.local")
    bidder_token = get_token_for_user("bidder@test.local")

    suffix = uuid.uuid4().hex[:6].upper()
    tender_number = f"GEM/2026/TEST/{suffix}"

    now = datetime.now(timezone.utc)
    payload = {
        "tender_number": tender_number,
        "title": "Supply of Enterprise Workstations",
        "description": "High-end computing systems for R&D lab.",
        "department": "Department of Electronics",
        "category": "IT Equipment",
        "procurement_type": "GOODS",
        "estimated_value": "4500000.50",
        "currency": "INR",
        "publish_date": now.isoformat(),
        "submission_start_date": (now + timedelta(days=1)).isoformat(),
        "submission_end_date": (now + timedelta(days=15)).isoformat(),
        "evaluation_start_date": (now + timedelta(days=16)).isoformat(),
    }

    # 1. Bidder attempts to create tender -> 403 Forbidden
    res_bidder = client.post(
        "/api/v1/tenders",
        json=payload,
        headers={"Authorization": f"Bearer {bidder_token}"},
    )
    assert res_bidder.status_code == 403, f"Expected 403 for bidder, got {res_bidder.status_code}"

    # 2. Unauthenticated attempts to create tender -> 401 Unauthorized
    res_unauth = client.post("/api/v1/tenders", json=payload)
    assert res_unauth.status_code == 401

    # 3. Procurement Officer creates tender -> 201 Created
    res_create = client.post(
        "/api/v1/tenders",
        json=payload,
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_create.status_code == 201, f"Create tender failed: {res_create.text}"
    created_data = res_create.json()
    assert created_data["tender_number"] == tender_number
    assert created_data["title"] == payload["title"]
    assert created_data["status"] == "DRAFT"
    assert created_data["is_active"] is True
    assert "id" in created_data
    assert "organization_id" in created_data
    assert "created_by_profile_id" in created_data
    assert float(created_data["estimated_value"]) == 4500000.50

    # 4. Duplicate tender number -> 409 Conflict
    res_dup = client.post(
        "/api/v1/tenders",
        json=payload,
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_dup.status_code == 409
    assert "already exists" in res_dup.json()["detail"].lower()

    # 5. Invalid date validation (end < start) -> 422 Unprocessable Entity
    invalid_dates_payload = dict(payload)
    invalid_dates_payload["tender_number"] = f"GEM/INVALID/{uuid.uuid4().hex[:6].upper()}"
    invalid_dates_payload["submission_start_date"] = (now + timedelta(days=10)).isoformat()
    invalid_dates_payload["submission_end_date"] = (now + timedelta(days=2)).isoformat()
    res_invalid_dates = client.post(
        "/api/v1/tenders",
        json=invalid_dates_payload,
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_invalid_dates.status_code == 422

    print("PASS: test_01_create_tender_success_and_rbac")
    return created_data["id"]


def test_02_list_and_search_tenders(tender_id: str):
    """Verify paginated listing, status filtering, and search."""
    proc_token = get_token_for_user("procurement@test.local")

    # List all
    res_list = client.get(
        "/api/v1/tenders?page=1&page_size=10",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert "items" in list_data
    assert "total" in list_data
    assert list_data["total"] >= 1
    assert any(t["id"] == tender_id for t in list_data["items"])

    # Search filter
    res_search = client.get(
        "/api/v1/tenders?search=Enterprise",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert any(t["id"] == tender_id for t in search_data["items"])

    # Status filter
    res_status = client.get(
        "/api/v1/tenders?status=DRAFT",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_status.status_code == 200
    assert all(t["status"] == "DRAFT" for t in res_status.json()["items"])

    print("PASS: test_02_list_and_search_tenders")


def test_03_get_and_organization_isolation(tender_id: str):
    """Verify get by ID and strict cross-organization access isolation."""
    proc_token_a = get_token_for_user("procurement@test.local")
    proc_token_b = ensure_second_procurement_officer()

    # Officer A can view their own tender
    res_a = client.get(
        f"/api/v1/tenders/{tender_id}",
        headers={"Authorization": f"Bearer {proc_token_a}"},
    )
    assert res_a.status_code == 200
    assert res_a.json()["id"] == tender_id

    # Officer B from another organization attempting to access Officer A's tender -> 404 Not Found
    res_b = client.get(
        f"/api/v1/tenders/{tender_id}",
        headers={"Authorization": f"Bearer {proc_token_b}"},
    )
    assert res_b.status_code == 404, f"Expected 404 for cross-org access, got {res_b.status_code}"

    # Non-existent tender ID -> 404
    res_none = client.get(
        f"/api/v1/tenders/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {proc_token_a}"},
    )
    assert res_none.status_code == 404

    print("PASS: test_03_get_and_organization_isolation")


def test_04_update_tender(tender_id: str):
    """Verify partial updates (PATCH) on DRAFT tenders."""
    proc_token_a = get_token_for_user("procurement@test.local")
    proc_token_b = ensure_second_procurement_officer()
    bidder_token = get_token_for_user("bidder@test.local")

    update_payload = {
        "title": "Supply of Enterprise Workstations (Updated Scope)",
        "estimated_value": "4800000.00",
        "description": "Updated hardware specifications and testing requirements.",
    }

    # Bidder attempt -> 403
    res_bidder = client.patch(
        f"/api/v1/tenders/{tender_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {bidder_token}"},
    )
    assert res_bidder.status_code == 403

    # Officer B attempt on Officer A's tender -> 404
    res_b = client.patch(
        f"/api/v1/tenders/{tender_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {proc_token_b}"},
    )
    assert res_b.status_code == 404

    # Officer A updates their tender -> 200 OK
    res_update = client.patch(
        f"/api/v1/tenders/{tender_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {proc_token_a}"},
    )
    assert res_update.status_code == 200
    updated_data = res_update.json()
    assert updated_data["title"] == update_payload["title"]
    assert float(updated_data["estimated_value"]) == 4800000.00
    assert updated_data["description"] == update_payload["description"]

    print("PASS: test_04_update_tender")


def test_05_archive_tender(tender_id: str):
    """Verify soft-delete / archiving and active list filtering."""
    proc_token_a = get_token_for_user("procurement@test.local")
    proc_token_b = ensure_second_procurement_officer()
    bidder_token = get_token_for_user("bidder@test.local")

    # Bidder attempt -> 403
    res_bidder = client.delete(
        f"/api/v1/tenders/{tender_id}",
        headers={"Authorization": f"Bearer {bidder_token}"},
    )
    assert res_bidder.status_code == 403

    # Officer B attempt -> 404
    res_b = client.delete(
        f"/api/v1/tenders/{tender_id}",
        headers={"Authorization": f"Bearer {proc_token_b}"},
    )
    assert res_b.status_code == 404

    # Officer A archives their tender -> 200 OK
    res_archive = client.delete(
        f"/api/v1/tenders/{tender_id}",
        headers={"Authorization": f"Bearer {proc_token_a}"},
    )
    assert res_archive.status_code == 200
    archived_data = res_archive.json()
    assert archived_data["is_active"] is False
    assert archived_data["status"] == "ARCHIVED"

    # Verify normal list does NOT include archived tender
    res_active_list = client.get(
        "/api/v1/tenders",
        headers={"Authorization": f"Bearer {proc_token_a}"},
    )
    assert res_active_list.status_code == 200
    assert not any(t["id"] == tender_id for t in res_active_list.json()["items"])

    # Verify include_archived=true DOES include it
    res_all_list = client.get(
        "/api/v1/tenders?include_archived=true",
        headers={"Authorization": f"Bearer {proc_token_a}"},
    )
    assert res_all_list.status_code == 200
    assert any(t["id"] == tender_id for t in res_all_list.json()["items"])

    print("PASS: test_05_archive_tender")


if __name__ == "__main__":
    print("Running Part 2B Tender CRUD API Verification Suite...")
    tid = test_01_create_tender_success_and_rbac()
    test_02_list_and_search_tenders(tid)
    test_03_get_and_organization_isolation(tid)
    test_04_update_tender(tid)
    test_05_archive_tender(tid)
    print("\nALL PART 2B TENDER CRUD TESTS PASSED SUCCESSFULLY!")
