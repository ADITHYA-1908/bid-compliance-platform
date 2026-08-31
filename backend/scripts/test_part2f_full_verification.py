"""
Comprehensive End-to-End QA & Hardening Verification Suite for Part 2 (Tender Management)
Tests: Part 2A (DB & Models), 2B (CRUD API), 2C (Frontend APIs), 2D (Dynamic Requirements),
2E (Lifecycle State Machine), and 2F (Security, Cross-Org Isolation, & Persistence).
"""

import sys
import os
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException
from app.db.session import get_session_factory
from app.db.models.user import User
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.organization import Organization
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.schemas.tender import (
    TenderCreate,
    TenderUpdate,
    TenderRequirementCreate,
    TenderRequirementUpdate,
)
from app.services import (
    tender_service,
    tender_requirement_service,
    tender_lifecycle_service,
)


def run_full_verification():
    SessionLocal = get_session_factory()
    db = SessionLocal()

    print("=" * 80)
    print("STARTING PART 2F: TENDER MODULE FINAL INTEGRATION & QA VERIFICATION SUITE")
    print("=" * 80)

    try:
        # =========================================================================
        # 1. Provision Test Roles, Organizations, and Users
        # =========================================================================
        print("\n--- Step 1: Provision Test Security Contexts ---")
        po_role = db.query(Role).filter(Role.name == "PROCUREMENT_OFFICER").first()
        bidder_role = db.query(Role).filter(Role.name == "BIDDER").first()
        admin_role = db.query(Role).filter(Role.name == "ADMIN").first()

        assert po_role and bidder_role and admin_role, "Required system roles must exist in DB."

        # Ministry A (Procuring Entity A)
        org_a = Organization(
            name=f"Ministry of Power & Renewable Energy {uuid.uuid4().hex[:6]}",
            organization_type="BUYER",
            registration_number=f"MOP-{uuid.uuid4().hex[:6].upper()}",
            is_active=True,
        )
        # Ministry B (Procuring Entity B - for cross-org testing)
        org_b = Organization(
            name=f"Ministry of Heavy Industries {uuid.uuid4().hex[:6]}",
            organization_type="BUYER",
            registration_number=f"MHI-{uuid.uuid4().hex[:6].upper()}",
            is_active=True,
        )
        db.add_all([org_a, org_b])
        db.commit()

        # Procurement Officer Alpha (Org A)
        email_po_a = f"officer_alpha_{uuid.uuid4().hex[:6]}@gem.gov.in"
        prof_po_a = Profile(full_name="Officer Alpha", email=email_po_a, role_id=po_role.id, organization_id=org_a.id)
        db.add(prof_po_a)
        db.commit()
        user_po_a = User(email=email_po_a, password_hash="hash", profile_id=prof_po_a.id, is_active=True)
        db.add(user_po_a)

        # Procurement Officer Beta (Org B)
        email_po_b = f"officer_beta_{uuid.uuid4().hex[:6]}@gem.gov.in"
        prof_po_b = Profile(full_name="Officer Beta", email=email_po_b, role_id=po_role.id, organization_id=org_b.id)
        db.add(prof_po_b)
        db.commit()
        user_po_b = User(email=email_po_b, password_hash="hash", profile_id=prof_po_b.id, is_active=True)
        db.add(user_po_b)

        # Bidder User
        email_bidder = f"vendor_{uuid.uuid4().hex[:6]}@techcorp.in"
        prof_bidder = Profile(full_name="TechCorp Bidder", email=email_bidder, role_id=bidder_role.id)
        db.add(prof_bidder)
        db.commit()
        user_bidder = User(email=email_bidder, password_hash="hash", profile_id=prof_bidder.id, is_active=True)
        db.add(user_bidder)

        db.commit()
        db.refresh(user_po_a)
        db.refresh(user_po_b)
        db.refresh(user_bidder)
        print("[PASS] Security identities and multi-organization buyers successfully provisioned.")

        # =========================================================================
        # 2. Tender Creation & Metadata Validation (Part 2A/2B)
        # =========================================================================
        print("\n--- Step 2: Tender Opportunity Creation & CRUD in DRAFT ---")
        now = datetime.now(timezone.utc)
        tender_number = f"GEM/2026/B/{uuid.uuid4().hex[:8].upper()}"
        
        tender_in = TenderCreate(
            tender_number=tender_number,
            title="Design, Supply & Commissioning of High-Efficiency Solar Inverter Systems",
            description="Turnkey procurement of 50MW grid-connected solar power conditioning units.",
            department="Solar Energy Division",
            category="Renewable Energy Equipment",
            procurement_type="GOODS",
            estimated_value=125000000.00,
            currency="INR",
            publish_date=now,
            submission_start_date=now + timedelta(days=2),
            submission_end_date=now + timedelta(days=20),
            evaluation_start_date=now + timedelta(days=21),
        )

        tender = tender_service.create_tender(db=db, data=tender_in, current_user=user_po_a)
        assert tender.id is not None
        assert tender.tender_number == tender_number
        assert tender.status == "DRAFT"
        assert tender.is_active is True
        assert tender.organization_id == org_a.id
        assert tender.created_by_profile_id == prof_po_a.id
        assert "PUBLISHED" in tender.allowed_transitions
        assert "ARCHIVED" in tender.allowed_transitions
        print(f"[PASS] Tender created: {tender.tender_number} in status '{tender.status}'.")

        # Update tender details in DRAFT
        updated = tender_service.update_tender(
            db=db,
            tender_id=tender.id,
            data=TenderUpdate(title="Design, Supply & Commissioning of High-Efficiency Solar Inverter Systems (Rev 1)"),
            current_user=user_po_a,
        )
        assert updated.title == "Design, Supply & Commissioning of High-Efficiency Solar Inverter Systems (Rev 1)"
        print("[PASS] Tender details updated successfully in DRAFT state.")

        # =========================================================================
        # 3. Search, Pagination, & Organization Filtering
        # =========================================================================
        print("\n--- Step 3: Search, Pagination & Org Filtering ---")
        items, total, total_pages = tender_service.list_tenders(
            db=db,
            current_user=user_po_a,
            search="Solar Inverter",
            page=1,
            page_size=10,
        )
        assert total >= 1
        assert any(t.id == tender.id for t in items)
        print(f"[PASS] Search by keyword succeeded (found {total} tenders).")

        # =========================================================================
        # 4. Configure Full Standard GeM Requirement Rules (Part 2D)
        # =========================================================================
        print("\n--- Step 4: Configure 7 Dynamic GeM Compliance Requirements ---")
        standard_requirements = [
            TenderRequirementCreate(
                code="GST_ACTIVE_STATUS",
                name="Valid & Active GST Registration",
                description="Bidder must possess active Goods and Services Tax identification number.",
                category="STATUTORY",
                requirement_type="STATUS",
                operator="EQUALS",
                expected_value="ACTIVE",
                is_mandatory=True,
                weight=15.0,
                display_order=1,
            ),
            TenderRequirementCreate(
                code="PAN_CARD_VERIFICATION",
                name="Permanent Account Number (PAN)",
                description="Valid income tax entity PAN card certificate.",
                category="DOCUMENT",
                requirement_type="DOCUMENT",
                operator="EXISTS",
                expected_value=True,
                is_mandatory=True,
                weight=10.0,
                display_order=2,
            ),
            TenderRequirementCreate(
                code="UDYAM_MSME_REGISTRATION",
                name="Udyam MSME Registration Certificate",
                description="Valid Udyam certificate for preferential procurement benefits.",
                category="STATUTORY",
                requirement_type="STATUS",
                operator="EQUALS",
                expected_value="ACTIVE",
                is_mandatory=False,
                weight=10.0,
                display_order=3,
            ),
            TenderRequirementCreate(
                code="OEM_AUTHORIZATION",
                name="Manufacturer Authorization Form (MAF)",
                description="Direct OEM authorization for supplying inverter hardware.",
                category="TECHNICAL",
                requirement_type="DOCUMENT",
                operator="EXISTS",
                expected_value=True,
                is_mandatory=True,
                weight=20.0,
                display_order=4,
            ),
            TenderRequirementCreate(
                code="MAKE_IN_INDIA_LOCAL_CONTENT",
                name="Class 1 Local Content (MII Compliance)",
                description="Minimum local value addition under PPP-MII policy.",
                category="LOCAL_CONTENT",
                requirement_type="NUMBER",
                operator="GREATER_THAN_OR_EQUAL",
                expected_value=50.0,
                is_mandatory=True,
                weight=20.0,
                display_order=5,
            ),
            TenderRequirementCreate(
                code="ANNUAL_FINANCIAL_TURNOVER",
                name="Minimum Average Annual Financial Turnover",
                description="Audited turnover of >= INR 40,00,00,000 over last 3 fiscal years.",
                category="FINANCIAL",
                requirement_type="NUMBER",
                operator="GREATER_THAN_OR_EQUAL",
                expected_value=400000000.00,
                is_mandatory=True,
                weight=15.0,
                display_order=6,
            ),
            TenderRequirementCreate(
                code="NON_DEBARMENT_UNDERTAKING",
                name="Non-Blacklisting / Debarment Undertaking",
                description="Self-declaration of non-debarment by any CPSE/Govt ministry.",
                category="BLACKLISTING",
                requirement_type="BOOLEAN",
                operator="EQUALS",
                expected_value=False,
                is_mandatory=True,
                weight=10.0,
                display_order=7,
            ),
        ]

        created_reqs = []
        for req_data in standard_requirements:
            r = tender_requirement_service.create_requirement(
                db=db, tender_id=tender.id, data=req_data, current_user=user_po_a
            )
            created_reqs.append(r)

        assert len(created_reqs) == 7
        print(f"[PASS] Successfully configured all 7 standard compliance rules. Total weight: {sum(r.weight for r in created_reqs)} Pts.")

        # Update one requirement
        updated_req = tender_requirement_service.update_requirement(
            db=db,
            tender_id=tender.id,
            requirement_id=created_reqs[0].id,
            data=TenderRequirementUpdate(name="Valid & Active GSTIN Registration (Verified)"),
            current_user=user_po_a,
        )
        assert updated_req.name == "Valid & Active GSTIN Registration (Verified)"
        print("[PASS] Requirement update verified.")

        # =========================================================================
        # 5. Lifecycle State Machine Progression (Part 2E)
        # =========================================================================
        print("\n--- Step 5: Lifecycle State Machine Transitions ---")

        # DRAFT -> PUBLISHED
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="PUBLISHED", current_user=user_po_a
        )
        assert tender.status == "PUBLISHED"
        assert tender.published_at is not None
        assert tender.allowed_transitions == ["OPEN", "ARCHIVED"]
        print(f"[PASS] DRAFT -> PUBLISHED (published_at={tender.published_at})")

        # Verify Tender & Requirement Edit Lock in PUBLISHED state
        try:
            tender_service.update_tender(
                db=db, tender_id=tender.id, data=TenderUpdate(title="Illegal Edit"), current_user=user_po_a
            )
            assert False, "Should block edit in PUBLISHED status."
        except HTTPException as e:
            assert e.status_code == 400
            print("[PASS] Blocked tender modification in PUBLISHED status.")

        try:
            tender_requirement_service.create_requirement(
                db=db, tender_id=tender.id, data=standard_requirements[0], current_user=user_po_a
            )
            assert False, "Should block adding requirements in PUBLISHED status."
        except HTTPException as e:
            assert e.status_code == 400
            print("[PASS] Blocked requirement modification in PUBLISHED status.")

        # PUBLISHED -> OPEN
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="OPEN", current_user=user_po_a
        )
        assert tender.status == "OPEN"
        assert tender.opened_at is not None
        assert tender.allowed_transitions == ["CLOSED"]
        print(f"[PASS] PUBLISHED -> OPEN (opened_at={tender.opened_at})")

        # Test Illegal Backward Transition: OPEN -> DRAFT (Must Fail 409)
        try:
            tender_lifecycle_service.transition_tender_status(
                db=db, tender_id=tender.id, target_status="DRAFT", current_user=user_po_a
            )
            assert False, "Should block OPEN -> DRAFT transition."
        except HTTPException as e:
            assert e.status_code == 409
            print("[PASS] Blocked illegal backward transition OPEN -> DRAFT (409 Conflict).")

        # OPEN -> CLOSED
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="CLOSED", current_user=user_po_a
        )
        assert tender.status == "CLOSED"
        assert tender.closed_at is not None
        assert tender.allowed_transitions == ["UNDER_EVALUATION"]
        print(f"[PASS] OPEN -> CLOSED (closed_at={tender.closed_at})")

        # CLOSED -> UNDER_EVALUATION
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="UNDER_EVALUATION", current_user=user_po_a
        )
        assert tender.status == "UNDER_EVALUATION"
        assert tender.evaluation_started_at is not None
        assert "AWARDED" in tender.allowed_transitions
        print(f"[PASS] CLOSED -> UNDER_EVALUATION (evaluation_started_at={tender.evaluation_started_at})")

        # UNDER_EVALUATION -> AWARDED
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="AWARDED", current_user=user_po_a
        )
        assert tender.status == "AWARDED"
        assert tender.awarded_at is not None
        assert tender.allowed_transitions == ["ARCHIVED"]
        print(f"[PASS] UNDER_EVALUATION -> AWARDED (awarded_at={tender.awarded_at})")

        # AWARDED -> ARCHIVED
        tender = tender_lifecycle_service.transition_tender_status(
            db=db, tender_id=tender.id, target_status="ARCHIVED", current_user=user_po_a
        )
        assert tender.status == "ARCHIVED"
        assert tender.is_active is False
        assert tender.archived_at is not None
        assert tender.allowed_transitions == []
        print(f"[PASS] AWARDED -> ARCHIVED (archived_at={tender.archived_at}, is_active=False, terminal state)")

        # ARCHIVED -> Cannot transition further
        try:
            tender_lifecycle_service.transition_tender_status(
                db=db, tender_id=tender.id, target_status="DRAFT", current_user=user_po_a
            )
            assert False, "Should block transition from ARCHIVED."
        except HTTPException as e:
            assert e.status_code == 409
            print("[PASS] Blocked transition out of terminal ARCHIVED state.")

        # =========================================================================
        # 6. Security: Cross-Organization Isolation & Bidder Role Lockdown
        # =========================================================================
        print("\n--- Step 6: Multi-Tenant Isolation & Role Authorization ---")
        # Create Tender in Org A
        fresh_tender = tender_service.create_tender(
            db=db,
            data=TenderCreate(
                tender_number=f"GEM/2026/B/{uuid.uuid4().hex[:8].upper()}",
                title="Defense Grid Security Hardware",
                department="Department A",
                category="Security",
                procurement_type="GOODS",
                submission_start_date=now + timedelta(days=1),
                submission_end_date=now + timedelta(days=10),
            ),
            current_user=user_po_a,
        )

        # Cross-Org Officer B attempts access -> 404 (not found / isolated)
        try:
            tender_service.get_tender_by_id(db=db, tender_id=fresh_tender.id, current_user=user_po_b)
            assert False, "Officer B should not access Org A's private tender."
        except HTTPException as e:
            assert e.status_code == 404
            print("[PASS] Cross-organization read isolation verified.")

        try:
            tender_service.update_tender(
                db=db,
                tender_id=fresh_tender.id,
                data=TenderUpdate(title="Hacked"),
                current_user=user_po_b,
            )
            assert False, "Officer B should not update Org A's tender."
        except HTTPException as e:
            assert e.status_code in [403, 404]
            print("[PASS] Cross-organization mutation blocked.")

        # Bidder attempts draft access -> 404 (draft hidden)
        try:
            tender_service.get_tender_by_id(db=db, tender_id=fresh_tender.id, current_user=user_bidder)
            assert False, "Bidder should not access DRAFT tender."
        except HTTPException as e:
            assert e.status_code == 404
            print("[PASS] Bidder DRAFT visibility isolation verified.")

        print("\n" + "=" * 80)
        print("ALL PART 2F TENDER MODULE VERIFICATION TESTS PASSED (100% SUCCESS)!")
        print("=" * 80)
        return True

    except Exception as e:
        db.rollback()
        print(f"\n[FAIL] EXCEPTION ENCOUNTERED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run_full_verification()
    sys.exit(0 if success else 1)
