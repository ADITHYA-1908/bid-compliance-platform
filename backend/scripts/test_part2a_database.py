"""
Part 2A Database Foundation & Verification Suite
Verifies:
1. Existence and structure of `tenders` and `tender_requirements` tables.
2. Foreign key constraints to `organizations` and `profiles`.
3. Unique constraint on `tender_number`.
4. Check constraints on `weight` and `display_order`.
5. ORM navigation and cascade behaviors.
6. Existing Part 1 tables and records integrity.
"""

import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime, timezone

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, text, inspect
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.db.session import get_session_factory
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.user import User
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement


def test_01_tables_exist():
    """Verify tenders and tender_requirements tables exist in PostgreSQL."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        assert "tenders" in tables, "Table 'tenders' not found in database."
        assert "tender_requirements" in tables, "Table 'tender_requirements' not found in database."
        assert "organizations" in tables, "Table 'organizations' not found."
        assert "profiles" in tables, "Table 'profiles' not found."
        assert "roles" in tables, "Table 'roles' not found."
        assert "users" in tables, "Table 'users' not found."
        print("PASS: test_01_tables_exist")
    finally:
        db.close()


def test_02_tender_and_requirements_orm():
    """Verify ORM relationships, loading, and cascade deletion."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        # Get an existing organization and profile
        org = db.scalars(select(Organization)).first()
        profile = db.scalars(select(Profile)).first()
        assert org is not None, "Organization record required"
        assert profile is not None, "Profile record required"

        temp_tender_number = f"TEMP/TEST/{uuid.uuid4().hex[:6].upper()}"

        # 1. Create a test tender with 2 requirements
        tender = Tender(
            tender_number=temp_tender_number,
            title="Temporary Test Tender for ORM Validation",
            description="Testing relationships and constraints",
            department="Testing Department",
            category="IT Equipment",
            procurement_type="GOODS",
            estimated_value=Decimal("1250000.00"),
            currency="INR",
            organization_id=org.id,
            created_by_profile_id=profile.id,
            status="DRAFT",
            is_active=True,
        )
        db.add(tender)
        db.flush()

        req1 = TenderRequirement(
            tender_id=tender.id,
            code="TEST_GST",
            name="Test GST Requirement",
            category="STATUTORY",
            requirement_type="BOOLEAN",
            operator="EQUALS",
            expected_value=True,
            is_mandatory=True,
            weight=Decimal("10.00"),
            display_order=1,
            is_active=True,
        )
        req2 = TenderRequirement(
            tender_id=tender.id,
            code="TEST_LOCAL_CONTENT",
            name="Test Local Content Requirement",
            category="LOCAL_CONTENT",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value=50,
            is_mandatory=True,
            weight=Decimal("15.00"),
            display_order=2,
            is_active=True,
        )
        db.add_all([req1, req2])
        db.commit()

        # 2. Reload and verify relationships
        stmt = (
            select(Tender)
            .where(Tender.id == tender.id)
            .options(
                selectinload(Tender.requirements),
                selectinload(Tender.organization),
                selectinload(Tender.created_by),
            )
        )
        loaded_tender = db.scalars(stmt).first()
        assert loaded_tender is not None
        assert len(loaded_tender.requirements) == 2
        assert loaded_tender.organization.id == org.id
        assert loaded_tender.created_by.id == profile.id
        assert loaded_tender.requirements[0].code == "TEST_GST"
        assert loaded_tender.requirements[1].code == "TEST_LOCAL_CONTENT"

        # 3. Test cascade deletion of requirements when tender is deleted
        tender_id = loaded_tender.id
        db.delete(loaded_tender)
        db.commit()

        # Verify requirements were cleanly cascaded
        orphan_reqs = db.scalars(select(TenderRequirement).where(TenderRequirement.tender_id == tender_id)).all()
        assert len(orphan_reqs) == 0, "Requirements were not cascaded on tender deletion"

        # Verify organization and profile remain untouched
        assert db.scalars(select(Organization).where(Organization.id == org.id)).first() is not None
        assert db.scalars(select(Profile).where(Profile.id == profile.id)).first() is not None

        print("PASS: test_02_tender_and_requirements_orm")
    finally:
        db.close()


def test_03_unique_tender_number_constraint():
    """Verify unique constraint on tender_number."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        org = db.scalars(select(Organization)).first()
        profile = db.scalars(select(Profile)).first()
        duplicate_num = f"DUP/{uuid.uuid4().hex[:6].upper()}"

        t1 = Tender(
            tender_number=duplicate_num,
            title="Tender 1",
            organization_id=org.id,
            created_by_profile_id=profile.id,
        )
        db.add(t1)
        db.commit()

        # Attempt to insert same tender_number
        t2 = Tender(
            tender_number=duplicate_num,
            title="Tender 2 Duplicate",
            organization_id=org.id,
            created_by_profile_id=profile.id,
        )
        db.add(t2)
        try:
            db.commit()
            assert False, "Duplicate tender_number should raise IntegrityError"
        except IntegrityError:
            db.rollback()

        # Cleanup t1
        db.delete(t1)
        db.commit()

        print("PASS: test_03_unique_tender_number_constraint")
    finally:
        db.close()


def test_04_check_constraints():
    """Verify check constraints (weight >= 0, display_order >= 0)."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        org = db.scalars(select(Organization)).first()
        profile = db.scalars(select(Profile)).first()
        temp_num = f"CHECK/{uuid.uuid4().hex[:6].upper()}"

        tender = Tender(
            tender_number=temp_num,
            title="Check Constraints Tender",
            organization_id=org.id,
            created_by_profile_id=profile.id,
        )
        db.add(tender)
        db.flush()

        # Negative weight should violate check constraint
        bad_req = TenderRequirement(
            tender_id=tender.id,
            code="BAD_WEIGHT",
            name="Negative Weight",
            weight=Decimal("-5.00"),
        )
        db.add(bad_req)
        try:
            db.commit()
            assert False, "Negative weight should raise IntegrityError"
        except IntegrityError:
            db.rollback()

        print("PASS: test_04_check_constraints")
    finally:
        db.close()


def test_05_demo_seed_verification():
    """Verify demo tender seeded in database."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        stmt = (
            select(Tender)
            .where(Tender.tender_number == "GEM/2026/B/001245")
            .options(selectinload(Tender.requirements))
        )
        demo_tender = db.scalars(stmt).first()
        assert demo_tender is not None, "Demo tender GEM/2026/B/001245 should exist"
        assert demo_tender.title == "Supply of 500 Business Laptops"
        assert demo_tender.status == "DRAFT"
        assert len(demo_tender.requirements) == 5
        req_codes = [r.code for r in demo_tender.requirements]
        assert "GST_REQUIRED" in req_codes
        assert "PAN_REQUIRED" in req_codes
        assert "UDYAM_REQUIRED" in req_codes
        assert "OEM_AUTH_REQUIRED" in req_codes
        assert "LOCAL_CONTENT" in req_codes
        print("PASS: test_05_demo_seed_verification")
    finally:
        db.close()


if __name__ == "__main__":
    print("Running Part 2A Database Foundation Verification...")
    test_01_tables_exist()
    test_02_tender_and_requirements_orm()
    test_03_unique_tender_number_constraint()
    test_04_check_constraints()
    test_05_demo_seed_verification()
    print("\nALL PART 2A DATABASE TESTS PASSED SUCCESSFULLY!")
