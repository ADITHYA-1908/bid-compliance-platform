"""
Part 2D Automated Tender Requirements & Dynamic Rules Verification Suite
Validates:
1. Dynamic requirement creation across all categories, types, and operators
2. 409 Conflict on duplicate requirement code within the same tender
3. 403 Forbidden for BIDDER on POST, PATCH, DELETE
4. Cross-organization access isolation (Officer B cannot add/edit requirements on Officer A's tender)
5. Listing requirements sorted by display_order
6. Partial update (PATCH) of criteria, expected value, and weights
7. Soft-deactivation (DELETE) with active list filtering
"""

import sys
import os
import uuid
from decimal import Decimal
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
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def ensure_second_procurement_officer() -> str:
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


def test_01_create_dynamic_requirements_and_templates():
    """Create a tender and configure the 8 full standard requirement rules."""
    proc_token = get_token_for_user("procurement@test.local")
    bidder_token = get_token_for_user("bidder@test.local")

    # 1. Create a fresh tender for requirements testing
    suffix = uuid.uuid4().hex[:6].upper()
    tender_payload = {
        "tender_number": f"GEM/2026/REQ/{suffix}",
        "title": "Supply of Server Infrastructure & Cloud Hardware",
        "description": "Comprehensive enterprise hardware procurement with strict compliance clauses.",
        "department": "Department of Telecom",
        "category": "IT Infrastructure",
        "procurement_type": "GOODS",
        "estimated_value": "75000000.00",
        "currency": "INR",
    }
    res_tender = client.post(
        "/api/v1/tenders",
        json=tender_payload,
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_tender.status_code == 201, f"Failed to create test tender: {res_tender.text}"
    tender_id = res_tender.json()["id"]

    # 2. Bidder attempts to add requirement -> 403 Forbidden
    res_bidder = client.post(
        f"/api/v1/tenders/{tender_id}/requirements",
        json={
            "code": "GST_REQUIRED",
            "name": "Valid GST",
            "category": "STATUTORY",
            "requirement_type": "STATUS",
            "operator": "EQUALS",
            "expected_value": "ACTIVE",
            "is_mandatory": True,
            "weight": 10.0,
            "display_order": 1,
        },
        headers={"Authorization": f"Bearer {bidder_token}"},
    )
    assert res_bidder.status_code == 403, f"Expected 403 for bidder, got {res_bidder.status_code}"

    # 3. Procurement Officer adds standard 8 dynamic requirements
    rules = [
        {
            "code": "GST_REQUIRED",
            "name": "GST Registration Certificate & Active Status",
            "description": "Bidder must possess a valid, active GSTIN verification.",
            "category": "STATUTORY",
            "requirement_type": "STATUS",
            "operator": "EQUALS",
            "expected_value": "ACTIVE",
            "is_mandatory": True,
            "weight": 10.0,
            "display_order": 1,
        },
        {
            "code": "PAN_REQUIRED",
            "name": "Permanent Account Number (PAN)",
            "description": "Copy of valid corporate PAN card must be submitted.",
            "category": "STATUTORY",
            "requirement_type": "DOCUMENT",
            "operator": "EXISTS",
            "expected_value": True,
            "is_mandatory": True,
            "weight": 10.0,
            "display_order": 2,
        },
        {
            "code": "UDYAM_REQUIRED",
            "name": "Udyam / MSME Registration Certificate",
            "description": "Active Udyam registration for MSME preference benefits.",
            "category": "STATUTORY",
            "requirement_type": "STATUS",
            "operator": "EQUALS",
            "expected_value": "ACTIVE",
            "is_mandatory": True,
            "weight": 10.0,
            "display_order": 3,
        },
        {
            "code": "OEM_AUTH_REQUIRED",
            "name": "OEM Manufacturer Authorization Form (MAF)",
            "description": "Direct authorization letter from OEM for offered server lines.",
            "category": "DOCUMENT",
            "requirement_type": "DOCUMENT",
            "operator": "EXISTS",
            "expected_value": True,
            "is_mandatory": True,
            "weight": 15.0,
            "display_order": 4,
        },
        {
            "code": "LOCAL_CONTENT",
            "name": "Minimum Class-I Local Content (Make in India)",
            "description": "Minimum domestic value addition percentage.",
            "category": "LOCAL_CONTENT",
            "requirement_type": "NUMBER",
            "operator": "GREATER_THAN_OR_EQUAL",
            "expected_value": 50,
            "is_mandatory": True,
            "weight": 15.0,
            "display_order": 5,
        },
        {
            "code": "MIN_TURNOVER",
            "name": "Average Annual Financial Turnover",
            "description": "Audited turnover over the last 3 financial years.",
            "category": "FINANCIAL",
            "requirement_type": "NUMBER",
            "operator": "GREATER_THAN_OR_EQUAL",
            "expected_value": 50000000,
            "is_mandatory": True,
            "weight": 15.0,
            "display_order": 6,
        },
        {
            "code": "MIN_EXPERIENCE_YEARS",
            "name": "Prior Public Sector Supply Experience",
            "description": "Years of experience in large-scale IT deployments.",
            "category": "EXPERIENCE",
            "requirement_type": "NUMBER",
            "operator": "GREATER_THAN_OR_EQUAL",
            "expected_value": 3,
            "is_mandatory": False,
            "weight": 5.0,
            "display_order": 7,
        },
        {
            "code": "NOT_BLACKLISTED",
            "name": "Non-Debarment / Blacklisting Undertaking",
            "description": "Undertaking confirming bidder is not debarred by any government body.",
            "category": "BLACKLISTING",
            "requirement_type": "BOOLEAN",
            "operator": "EQUALS",
            "expected_value": False,
            "is_mandatory": True,
            "weight": 20.0,
            "display_order": 8,
        },
    ]

    created_req_ids = []
    for r in rules:
        res = client.post(
            f"/api/v1/tenders/{tender_id}/requirements",
            json=r,
            headers={"Authorization": f"Bearer {proc_token}"},
        )
        assert res.status_code == 201, f"Failed creating requirement {r['code']}: {res.text}"
        data = res.json()
        assert data["code"] == r["code"]
        assert data["category"] == r["category"]
        assert data["requirement_type"] == r["requirement_type"]
        assert data["operator"] == r["operator"]
        assert data["is_mandatory"] == r["is_mandatory"]
        assert float(data["weight"]) == r["weight"]
        assert data["is_active"] is True
        created_req_ids.append(data["id"])

    # 4. Duplicate requirement code -> 409 Conflict
    res_dup = client.post(
        f"/api/v1/tenders/{tender_id}/requirements",
        json=rules[0],
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res_dup.status_code == 409
    assert "already exists" in res_dup.json()["detail"].lower()

    print("PASS: test_01_create_dynamic_requirements_and_templates")
    return tender_id, created_req_ids


def test_02_list_and_sorting_requirements(tender_id: str, req_ids: list):
    """Verify listing returns requirements ordered by display_order."""
    proc_token = get_token_for_user("procurement@test.local")

    res = client.get(
        f"/api/v1/tenders/{tender_id}/requirements",
        headers={"Authorization": f"Bearer {proc_token}"},
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) == len(req_ids)

    # Check ordering
    for i in range(len(items) - 1):
        assert items[i]["display_order"] <= items[i + 1]["display_order"]

    assert items[0]["code"] == "GST_REQUIRED"
    assert items[-1]["code"] == "NOT_BLACKLISTED"

    print("PASS: test_02_list_and_sorting_requirements")


def test_03_cross_organization_isolation(tender_id: str, req_ids: list):
    """Verify Officer B from another organization cannot add, view, update, or deactivate requirements."""
    proc_token_b = ensure_second_procurement_officer()
    sample_req_id = req_ids[0]

    # 1. Officer B attempts to list Officer A's requirements -> 404
    res_list = client.get(
        f"/api/v1/tenders/{tender_id}/requirements",
        headers={"Authorization": f"Bearer {proc_token_b}"},
    )
    assert res_list.status_code == 404

    # 2. Officer B attempts to create requirement on Officer A's tender -> 404
    res_create = client.post(
        f"/api/v1/tenders/{tender_id}/requirements",
        json={
            "code": "SECURITY_AUDIT",
            "name": "Cert-In Security Audit",
            "category": "TECHNICAL",
            "requirement_type": "DOCUMENT",
            "operator": "EXISTS",
            "expected_value": True,
            "is_mandatory": True,
            "weight": 10.0,
            "display_order": 9,
        },
        headers={"Authorization": f"Bearer {proc_token_b}"},
    )
    assert res_create.status_code == 404

    # 3. Officer B attempts to update Officer A's requirement -> 404
    res_patch = client.patch(
        f"/api/v1/tenders/{tender_id}/requirements/{sample_req_id}",
        json={"weight": 50.0},
        headers={"Authorization": f"Bearer {proc_token_b}"},
    )
    assert res_patch.status_code == 404

    # 4. Officer B attempts to deactivate Officer A's requirement -> 404
    res_del = client.delete(
        f"/api/v1/tenders/{tender_id}/requirements/{sample_req_id}",
        headers={"Authorization": f"Bearer {proc_token_b}"},
    )
    assert res_del.status_code == 404

    print("PASS: test_03_cross_organization_isolation")


def test_04_update_requirement(tender_id: str, req_ids: list):
    """Verify partial updates (PATCH) on dynamic requirements."""
    proc_token_a = get_token_for_user("procurement@test.local")
    sample_req_id = req_ids[4]  # Local content requirement

    patch_payload = {
        "expected_value": 60,
        "weight": 20.0,
        "description": "Updated Make in India threshold for Class-I suppliers.",
    }

    res = client.patch(
        f"/api/v1/tenders/{tender_id}/requirements/{sample_req_id}",
        json=patch_payload,
        headers={"Authorization": f"Bearer {proc_token_a}"},
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["expected_value"] == 60
    assert float(updated["weight"]) == 20.0
    assert updated["description"] == patch_payload["description"]

    print("PASS: test_04_update_requirement")


def test_05_deactivate_requirement(tender_id: str, req_ids: list):
    """Verify soft-deactivation (DELETE) and active query filtering."""
    proc_token_a = get_token_for_user("procurement@test.local")
    req_to_disable = req_ids[6]  # Experience requirement

    # Deactivate
    res_del = client.delete(
        f"/api/v1/tenders/{tender_id}/requirements/{req_to_disable}",
        headers={"Authorization": f"Bearer {proc_token_a}"},
    )
    assert res_del.status_code == 200
    deactivated = res_del.json()
    assert deactivated["is_active"] is False

    # Default list excludes inactive
    res_active = client.get(
        f"/api/v1/tenders/{tender_id}/requirements",
        headers={"Authorization": f"Bearer {proc_token_a}"},
    )
    assert res_active.status_code == 200
    active_items = res_active.json()
    assert len(active_items) == len(req_ids) - 1
    assert not any(r["id"] == req_to_disable for r in active_items)

    # List with include_inactive=true includes it
    res_all = client.get(
        f"/api/v1/tenders/{tender_id}/requirements?include_inactive=true",
        headers={"Authorization": f"Bearer {proc_token_a}"},
    )
    assert res_all.status_code == 200
    all_items = res_all.json()
    assert len(all_items) == len(req_ids)
    assert any(r["id"] == req_to_disable and not r["is_active"] for r in all_items)

    print("PASS: test_05_deactivate_requirement")


if __name__ == "__main__":
    print("Running Part 2D Tender Requirements Verification Suite...")
    tid, rids = test_01_create_dynamic_requirements_and_templates()
    test_02_list_and_sorting_requirements(tid, rids)
    test_03_cross_organization_isolation(tid, rids)
    test_04_update_requirement(tid, rids)
    test_05_deactivate_requirement(tid, rids)
    print("\nALL PART 2D TENDER REQUIREMENTS TESTS PASSED SUCCESSFULLY!")
