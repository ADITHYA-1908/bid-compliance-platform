"""
Part 1F Automated End-to-End Integration & Foundation Verification Suite
Validates:
1. Health & Database Connectivity
2. CORS & Security Configuration
3. User Signup & Duplicate Account Handling
4. Authentication (BIDDER, PROCUREMENT_OFFICER, ADMIN)
5. Invalid Password & Corrupt Token Handling
6. Protected Identity Endpoint (/api/v1/auth/me)
7. RBAC Matrix & 403 Forbidden Enforcement across all 3 roles
8. Public Metadata & OpenAPI / Swagger
"""

import sys
import os
import uuid
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_01_root_and_health():
    """Verify root, health, and database health endpoints."""
    # Root
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "BidVerify AI" in res_root.json().get("message", "")

    # Basic Health
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json() == {"status": "healthy"}

    # Database Health
    res_db = client.get("/health/database")
    assert res_db.status_code == 200
    assert res_db.json() == {"database": "connected"}
    print("PASS: test_01_root_and_health")


def test_02_cors_and_docs():
    """Verify OpenAPI docs and CORS headers."""
    res_docs = client.get("/docs")
    assert res_docs.status_code == 200

    res_openapi = client.get("/openapi.json")
    assert res_openapi.status_code == 200
    schema = res_openapi.json()
    assert "/api/v1/auth/signup" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/auth/me" in schema["paths"]
    assert "/api/v1/bidder/test" in schema["paths"]
    assert "/api/v1/procurement/test" in schema["paths"]
    assert "/api/v1/admin/test" in schema["paths"]

    # CORS options preflight
    res_cors = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res_cors.status_code == 200
    assert res_cors.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert res_cors.headers.get("access-control-allow-credentials") == "true"
    print("PASS: test_02_cors_and_docs")


def test_03_signup_flow():
    """Verify Bidder self-registration flow with duplicate protection."""
    random_suffix = uuid.uuid4().hex[:8]
    test_email = f"bidder_{random_suffix}@testcompany.com"
    payload = {
        "full_name": "Integration Test Bidder",
        "email": test_email,
        "password": "SecurePassword123!",
        "organization_name": f"Test Enterprise {random_suffix}",
        "organization_type": "Vendor / Bidder",
    }

    # 1. Signup succeeds
    res_signup = client.post("/api/v1/auth/signup", json=payload)
    assert res_signup.status_code == 201, f"Signup failed: {res_signup.text}"
    data = res_signup.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == test_email
    assert data["user"]["role"] == "BIDDER"
    assert data["user"]["organization"] == payload["organization_name"]

    # 2. Duplicate signup fails with 400 Bad Request
    res_dup = client.post("/api/v1/auth/signup", json=payload)
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json().get("detail", "").lower()

    # 3. New account can immediately authenticate
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": "SecurePassword123!"},
    )
    assert res_login.status_code == 200
    assert "access_token" in res_login.json()
    print("PASS: test_03_signup_flow")


def test_04_auth_and_roles_matrix():
    """Verify login and RBAC across all 3 standard seed roles."""
    roles_credentials = {
        "BIDDER": ("bidder@test.local", "TestPassword123!"),
        "PROCUREMENT_OFFICER": ("procurement@test.local", "TestPassword123!"),
        "ADMIN": ("admin@test.local", "TestPassword123!"),
    }

    tokens = {}

    # Login each role
    for role_name, (email, pwd) in roles_credentials.items():
        res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": pwd},
        )
        assert res.status_code == 200, f"Login failed for {role_name}: {res.text}"
        body = res.json()
        assert body["user"]["role"] == role_name
        assert body["user"]["email"] == email
        tokens[role_name] = body["access_token"]

    # Test /api/v1/auth/me for each role
    for role_name, token in tokens.items():
        res_me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_me.status_code == 200
        user_data = res_me.json()
        assert user_data["role"] == role_name
        assert user_data["is_active"] is True
        assert "id" in user_data
        assert "full_name" in user_data

    # Test RBAC Permissions Matrix
    # BIDDER permissions
    bidder_token = tokens["BIDDER"]
    assert client.get("/api/v1/bidder/test", headers={"Authorization": f"Bearer {bidder_token}"}).status_code == 200
    assert client.get("/api/v1/procurement/test", headers={"Authorization": f"Bearer {bidder_token}"}).status_code == 403
    assert client.get("/api/v1/admin/test", headers={"Authorization": f"Bearer {bidder_token}"}).status_code == 403

    # PROCUREMENT_OFFICER permissions
    proc_token = tokens["PROCUREMENT_OFFICER"]
    assert client.get("/api/v1/procurement/test", headers={"Authorization": f"Bearer {proc_token}"}).status_code == 200
    assert client.get("/api/v1/bidder/test", headers={"Authorization": f"Bearer {proc_token}"}).status_code == 403
    assert client.get("/api/v1/admin/test", headers={"Authorization": f"Bearer {proc_token}"}).status_code == 403

    # ADMIN permissions
    admin_token = tokens["ADMIN"]
    assert client.get("/api/v1/admin/test", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 200
    assert client.get("/api/v1/bidder/test", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 403
    assert client.get("/api/v1/procurement/test", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 403

    print("PASS: test_04_auth_and_roles_matrix")


def test_05_auth_failure_handling():
    """Verify security handling for invalid credentials and expired/corrupted tokens."""
    # 1. Bad password
    res_bad_pw = client.post(
        "/api/v1/auth/login",
        json={"email": "bidder@test.local", "password": "WrongPassword999!"},
    )
    assert res_bad_pw.status_code == 401
    assert "Invalid email or password" in res_bad_pw.json().get("detail", "")

    # 2. Non-existent email
    res_no_user = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent_user_999@domain.xyz", "password": "AnyPassword123!"},
    )
    assert res_no_user.status_code == 401
    assert "Invalid email or password" in res_no_user.json().get("detail", "")

    # 3. Missing Authorization token
    res_no_token = client.get("/api/v1/auth/me")
    assert res_no_token.status_code == 401

    # 4. Malformed Bearer token
    res_bad_token = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.valid.jwt.token"},
    )
    assert res_bad_token.status_code == 401
    print("PASS: test_05_auth_failure_handling")


def test_06_roles_registry():
    """Verify public roles registry endpoint."""
    res_roles = client.get("/api/v1/roles")
    assert res_roles.status_code == 200
    roles = res_roles.json()
    role_names = [r["name"] for r in roles]
    for required_role in ["BIDDER", "PROCUREMENT_OFFICER", "ADMIN"]:
        assert required_role in role_names
    print("PASS: test_06_roles_registry")


if __name__ == "__main__":
    print("Running Part 1F Integration & Foundation Verification...")
    test_01_root_and_health()
    test_02_cors_and_docs()
    test_03_signup_flow()
    test_04_auth_and_roles_matrix()
    test_05_auth_failure_handling()
    test_06_roles_registry()
    print("\nALL PART 1F INTEGRATION TESTS PASSED SUCCESSFULLY!")
