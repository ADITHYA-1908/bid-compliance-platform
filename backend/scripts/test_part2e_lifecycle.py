"""
Comprehensive Test Script for Part 2E: Tender Lifecycle & Status Management
Tests state machine transitions, readiness validation, status locking, timestamps, and RBAC.
"""

import sys
import os
import uuid
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException
from app.db.session import get_session_factory
from app.db.models.user import User
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.organization import Organization
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.schemas.tender import TenderCreate, TenderUpdate, TenderRequirementCreate, TenderRequirementUpdate
from app.services import tender_service, tender_requirement_service, tender_lifecycle_service


def run_lifecycle_tests():
    SessionLocal = get_session_factory()
    db = SessionLocal()
    print("=" * 70)
    print("STARTING PART 2E: TENDER LIFECYCLE & STATUS MANAGEMENT TEST SUITE")
    print("=" * 70)

    try:
        # 1. Setup Test Organizations, Roles, and Users
        po_role = db.query(Role).filter(Role.name == "PROCUREMENT_OFFICER").first()
        bidder_role = db.query(Role).filter(Role.name == "BIDDER").first()

        if not po_role or not bidder_role:
            print("ERROR: System roles not found. Run seed script first.")
            return False

        # Org A
        org_a = Organization(
            name=f"Test Ministry of Defense {uuid.uuid4().hex[:6]}",
            organization_type="BUYER",
            is_active=True,
        )
        # Org B
        org_b = Organization(
            name=f"Test Ministry of Railways {uuid.uuid4().hex[:6]}",
            organization_type="BUYER",
            is_active=True,
        )
        db.add_all([org_a, org_b])
        db.commit()

        # Officer A (Org A)
        email_a = f"officer_a_{uuid.uuid4().hex[:6]}@gem.gov.in"
        officer_a_prof = Profile(full_name="Officer Alpha", email=email_a, role_id=po_role.id, organization_id=org_a.id)
        db.add(officer_a_prof)
        db.commit()
        officer_a_user = User(email=email_a, password_hash="pw", profile_id=officer_a_prof.id, is_active=True)
        db.add(officer_a_user)

        # Officer B (Org B)
        email_b = f"officer_b_{uuid.uuid4().hex[:6]}@gem.gov.in"
        officer_b_prof = Profile(full_name="Officer Beta", email=email_b, role_id=po_role.id, organization_id=org_b.id)
        db.add(officer_b_prof)
        db.commit()
        officer_b_user = User(email=email_b, password_hash="pw", profile_id=officer_b_prof.id, is_active=True)
        db.add(officer_b_user)

        # Bidder User
        email_bidder = f"bidder_{uuid.uuid4().hex[:6]}@vendor.com"
        bidder_prof = Profile(full_name="Vendor Bidder", email=email_bidder, role_id=bidder_role.id)
        db.add(bidder_prof)
        db.commit()
        bidder_user = User(email=email_bidder, password_hash="pw", profile_id=bidder_prof.id, is_active=True)
        db.add(bidder_user)

        db.commit()
        db.refresh(officer_a_user)
        db.refresh(officer_b_user)
        db.refresh(bidder_user)

        print("[OK] Test users, profiles, and organizations successfully initialized.")

        # 2. Test Tender Creation in DRAFT
        now = datetime.now(timezone.utc)
        tender_number = f"GEM/2026/B/{uuid.uuid4().hex[:8].upper()}"
        tender_data = TenderCreate(
            tender_number=tender_number,
            title="Procurement of Secure AI Compute Servers",
            description="Supply and commissioning of HPC GPU clusters for GeM AI evaluation.",
            department="Ministry of Electronics and IT",
            category="Hardware",
            procurement_type="GOODS",
            estimated_value=7500000.0,
            currency="INR",
            submission_start_date=now + timedelta(days=1),
            submission_end_date=now + timedelta(days=15),
            evaluation_start_date=now + timedelta(days=16),
        )

        tender = tender_service.create_tender(db=db, data=tender_data, current_user=officer_a_user)
        assert tender.status == "DRAFT", "Tender initial status must be DRAFT"
        assert tender.is_active is True, "Tender must be active"
        assert "PUBLISHED" in tender.allowed_transitions, "DRAFT must allow transition to PUBLISHED"
        assert "ARCHIVED" in tender.allowed_transitions, "DRAFT must allow transition to ARCHIVED"
        print(f"[OK] Tender {tender.tender_number} created in DRAFT with allowed_transitions: {tender.allowed_transitions}")

        # 3. Test Pre-Publish Validation (Zero Requirements -> Must Fail)
        print("\n--- Test 3: Publish Validation with 0 Requirements ---")
        try:
            tender_lifecycle_service.transition_tender_status(
                db=db, tender_id=tender.id, target_status="PUBLISHED", current_user=officer_a_user
            )
            print("FAILED: Tender published without requirements!")
            return False
        except HTTPException as e:
            assert e.status_code == 409
            assert "at least one active eligibility/compliance requirement" in e.detail
            print(f"[OK] Correctly rejected publish without requirements (409 Conflict): {e.detail}")

        # 4. Add Dynamic Requirements in DRAFT state
        print("\n--- Test 4: Configure Requirements in DRAFT ---")
        req1_data = TenderRequirementCreate(
            code="ANNUAL_TURNOVER",
            name="Minimum Average Annual Turnover",
            description="Audited turnover of Rs 50 Lakhs in last 3 financial years.",
            category="FINANCIAL",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value=5000000.0,
            is_mandatory=True,
            weight=30.0,
            display_order=1,
        )
        req1 = tender_requirement_service.create_requirement(
            db=db, tender_id=tender.id, data=req1_data, current_user=officer_a_user
        )
        assert req1.code == "ANNUAL_TURNOVER"

        req2_data = TenderRequirementCreate(
            code="MAKE_IN_INDIA",
            name="Class 1 Local Supplier Undertaking",
            description="Minimum 50% local content requirement.",
            category="LOCAL_CONTENT",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value=50.0,
            is_mandatory=True,
            weight=20.0,
            display_order=2,
        )
        req2 = tender_requirement_service.create_requirement(
            db=db, tender_id=tender.id, data=req2_data, current_user=officer_a_user
        )
        print(f"[OK] Attached requirements: {req1.code}, {req2.code} to DRAFT tender.")

        # 5. Test Valid Publish Transition (DRAFT -> PUBLISHED)
        print("\n--- Test 5: Valid Transition DRAFT -> PUBLISHED ---")
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="PUBLISHED", current_user=officer_a_user
        )
        assert tender.status == "PUBLISHED"
        assert tender.published_at is not None
        assert tender.allowed_transitions == ["OPEN", "ARCHIVED"]
        print(f"[OK] Tender moved to PUBLISHED. Timestamp: {tender.published_at}, Next transitions: {tender.allowed_transitions}")

        # 6. Test Edit Lock on PUBLISHED Tender
        print("\n--- Test 6: Tender Edit Lock in Non-DRAFT Status ---")
        try:
            tender_service.update_tender(
                db=db, tender_id=tender.id, data=TenderUpdate(title="Attempted Title Change"), current_user=officer_a_user
            )
            print("FAILED: Updated tender outside DRAFT state!")
            return False
        except HTTPException as e:
            assert e.status_code == 400
            print(f"[OK] Correctly rejected tender update in PUBLISHED status: {e.detail}")

        # 7. Test Requirement Lock on PUBLISHED Tender
        print("\n--- Test 7: Requirement Modification Lock in Non-DRAFT Status ---")
        try:
            tender_requirement_service.create_requirement(
                db=db,
                tender_id=tender.id,
                data=TenderRequirementCreate(code="NEW_CRITERIA", name="New Criteria"),
                current_user=officer_a_user,
            )
            print("FAILED: Added requirement to PUBLISHED tender!")
            return False
        except HTTPException as e:
            assert e.status_code == 400
            print(f"[OK] Correctly rejected requirement addition in PUBLISHED status: {e.detail}")

        # 8. Test Invalid Transition Jump (PUBLISHED -> AWARDED)
        print("\n--- Test 8: Reject Illegal Transition Jump (PUBLISHED -> AWARDED) ---")
        try:
            tender_lifecycle_service.transition_tender_status(
                db=db, tender_id=tender.id, target_status="AWARDED", current_user=officer_a_user
            )
            print("FAILED: Invalid transition PUBLISHED -> AWARDED allowed!")
            return False
        except HTTPException as e:
            assert e.status_code == 409
            print(f"[OK] Correctly rejected illegal jump: {e.detail}")

        # 9. Test PUBLISHED -> OPEN
        print("\n--- Test 9: Transition PUBLISHED -> OPEN ---")
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="OPEN", current_user=officer_a_user
        )
        assert tender.status == "OPEN"
        assert tender.opened_at is not None
        assert tender.allowed_transitions == ["CLOSED"]
        print(f"[OK] Tender moved to OPEN. Timestamp: {tender.opened_at}, Allowed transitions: {tender.allowed_transitions}")

        # 10. Test Invalid Transition (OPEN -> DRAFT)
        print("\n--- Test 10: Reject Backward Transition (OPEN -> DRAFT) ---")
        try:
            tender_lifecycle_service.transition_tender_status(
                db=db, tender_id=tender.id, target_status="DRAFT", current_user=officer_a_user
            )
            print("FAILED: OPEN -> DRAFT transition allowed!")
            return False
        except HTTPException as e:
            assert e.status_code == 409
            print(f"[OK] Correctly rejected OPEN -> DRAFT: {e.detail}")

        # 11. Test OPEN -> CLOSED
        print("\n--- Test 11: Transition OPEN -> CLOSED ---")
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="CLOSED", current_user=officer_a_user
        )
        assert tender.status == "CLOSED"
        assert tender.closed_at is not None
        assert tender.allowed_transitions == ["UNDER_EVALUATION"]
        print(f"[OK] Tender moved to CLOSED. Timestamp: {tender.closed_at}, Allowed transitions: {tender.allowed_transitions}")

        # 12. Test CLOSED -> UNDER_EVALUATION
        print("\n--- Test 12: Transition CLOSED -> UNDER_EVALUATION ---")
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="UNDER_EVALUATION", current_user=officer_a_user
        )
        assert tender.status == "UNDER_EVALUATION"
        assert tender.evaluation_started_at is not None
        assert "AWARDED" in tender.allowed_transitions
        print(f"[OK] Tender moved to UNDER_EVALUATION. Timestamp: {tender.evaluation_started_at}, Allowed transitions: {tender.allowed_transitions}")

        # 13. Test UNDER_EVALUATION -> AWARDED
        print("\n--- Test 13: Transition UNDER_EVALUATION -> AWARDED ---")
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="AWARDED", current_user=officer_a_user
        )
        assert tender.status == "AWARDED"
        assert tender.awarded_at is not None
        assert tender.allowed_transitions == ["ARCHIVED"]
        print(f"[OK] Tender moved to AWARDED. Timestamp: {tender.awarded_at}, Allowed transitions: {tender.allowed_transitions}")

        # 14. Test AWARDED -> ARCHIVED (Terminal State)
        print("\n--- Test 14: Transition AWARDED -> ARCHIVED ---")
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="ARCHIVED", current_user=officer_a_user
        )
        assert tender.status == "ARCHIVED"
        assert tender.is_active is False
        assert tender.archived_at is not None
        assert tender.allowed_transitions == []
        print(f"[OK] Tender moved to ARCHIVED. Timestamp: {tender.archived_at}, is_active: {tender.is_active}, Allowed transitions: {tender.allowed_transitions}")

        # 15. Test ARCHIVED Immutable State
        print("\n--- Test 15: Reject Any Transition from ARCHIVED ---")
        try:
            tender_lifecycle_service.transition_tender_status(
                db=db, tender_id=tender.id, target_status="OPEN", current_user=officer_a_user
            )
            print("FAILED: Transitioned out of ARCHIVED!")
            return False
        except HTTPException as e:
            assert e.status_code == 409
            print(f"[OK] Correctly rejected transition from ARCHIVED: {e.detail}")

        # 16. Test Cross-Organization Security
        print("\n--- Test 16: Cross-Organization Protection ---")
        # Create fresh tender in Org A
        tender2 = tender_service.create_tender(
            db=db,
            data=TenderCreate(
                tender_number=f"GEM/2026/B/{uuid.uuid4().hex[:8].upper()}",
                title="Org A Private Tender",
                department="Department A",
                category="IT",
                procurement_type="GOODS",
                submission_start_date=now + timedelta(days=1),
                submission_end_date=now + timedelta(days=10),
            ),
            current_user=officer_a_user,
        )
        try:
            tender_lifecycle_service.transition_tender_status(
                db=db, tender_id=tender2.id, target_status="ARCHIVED", current_user=officer_b_user
            )
            print("FAILED: Officer B mutated Officer A's tender!")
            return False
        except HTTPException as e:
            assert e.status_code in [403, 404]
            print(f"[OK] Correctly blocked Officer B from mutating Officer A's tender: {e.status_code} {e.detail}")

        # 17. Test Bidder Security Protection
        print("\n--- Test 17: Bidder Access Rejection ---")
        try:
            tender_lifecycle_service.transition_tender_status(
                db=db, tender_id=tender2.id, target_status="ARCHIVED", current_user=bidder_user
            )
            print("FAILED: Bidder mutated tender status!")
            return False
        except HTTPException as e:
            assert e.status_code in [403, 404]
            print(f"[OK] Correctly blocked Bidder from lifecycle mutation: {e.status_code} {e.detail}")

        print("\n" + "=" * 70)
        print("ALL PART 2E BACKEND LIFECYCLE TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)
        return True

    except Exception as e:
        db.rollback()
        print(f"\nUNEXPECTED EXCEPTION DURING TESTS: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run_lifecycle_tests()
    sys.exit(0 if success else 1)
