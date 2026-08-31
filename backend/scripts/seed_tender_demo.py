"""
Demo / Development Seed Script for Tender Management (Part 2A)
Provisions a sample DRAFT tender with standard compliance requirements
under the Ministry of Electronics & IT procurement officer account.
"""

import sys
import os
import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_session_factory
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEMO_TENDER_NUMBER = "GEM/2026/B/001245"


def seed_tender_demo() -> None:
    """Idempotently seeds a demo DRAFT tender with 5 sample requirements."""
    session_factory = get_session_factory()
    db = session_factory()

    try:
        logger.info("Checking for existing demo tender...")

        # 1. Fetch Procurement Officer Profile
        proc_profile = db.scalars(
            select(Profile)
            .where(Profile.email == "procurement@test.local")
            .options(selectinload(Profile.organization))
        ).first()

        if not proc_profile:
            logger.warning("Procurement test account 'procurement@test.local' not found. Run create_test_users.py first.")
            return

        org_id = proc_profile.organization_id
        if not org_id:
            # Fallback to first available organization
            org = db.scalars(select(Organization)).first()
            if not org:
                raise ValueError("No organization exists in database.")
            org_id = org.id

        # 2. Check if demo tender already exists
        existing_tender = db.scalars(
            select(Tender)
            .where(Tender.tender_number == DEMO_TENDER_NUMBER)
            .options(selectinload(Tender.requirements))
        ).first()

        now = datetime.now(timezone.utc)

        if existing_tender:
            logger.info(f"Demo tender '{DEMO_TENDER_NUMBER}' already exists (ID: {existing_tender.id}, {len(existing_tender.requirements)} requirements). Skipping.")
            return

        # 3. Create Demo Tender
        tender = Tender(
            tender_number=DEMO_TENDER_NUMBER,
            title="Supply of 500 Business Laptops",
            description="Procurement of high-performance business laptops for departmental computing and administrative operations under GeM procurement guidelines.",
            department="Department of Information Technology",
            category="IT Equipment",
            procurement_type="GOODS",
            estimated_value=Decimal("35000000.00"),  # 3.5 Crore INR
            currency="INR",
            publish_date=now,
            submission_start_date=now + timedelta(days=1),
            submission_end_date=now + timedelta(days=21),
            evaluation_start_date=now + timedelta(days=22),
            organization_id=org_id,
            created_by_profile_id=proc_profile.id,
            status="DRAFT",
            is_active=True,
        )
        db.add(tender)
        db.flush()

        # 4. Create Sample Requirements
        sample_requirements = [
            TenderRequirement(
                tender_id=tender.id,
                code="GST_REQUIRED",
                name="Valid GST Registration Certificate",
                description="Bidder must submit an active Goods and Services Tax (GSTIN) registration certificate.",
                category="STATUTORY",
                requirement_type="BOOLEAN",
                operator="EQUALS",
                expected_value=True,
                is_mandatory=True,
                weight=Decimal("10.00"),
                display_order=1,
                is_active=True,
            ),
            TenderRequirement(
                tender_id=tender.id,
                code="PAN_REQUIRED",
                name="Permanent Account Number (PAN) Card",
                description="Bidder entity or authorized proprietor must hold a valid Income Tax PAN card.",
                category="STATUTORY",
                requirement_type="BOOLEAN",
                operator="EQUALS",
                expected_value=True,
                is_mandatory=True,
                weight=Decimal("10.00"),
                display_order=2,
                is_active=True,
            ),
            TenderRequirement(
                tender_id=tender.id,
                code="UDYAM_REQUIRED",
                name="MSME / Udyam Registration Certificate",
                description="Proof of valid Udyam registration for MSME exemption and procurement preference eligibility.",
                category="STATUTORY",
                requirement_type="BOOLEAN",
                operator="EQUALS",
                expected_value=True,
                is_mandatory=True,
                weight=Decimal("10.00"),
                display_order=3,
                is_active=True,
            ),
            TenderRequirement(
                tender_id=tender.id,
                code="OEM_AUTH_REQUIRED",
                name="OEM Manufacturer Authorization Form (MAF)",
                description="Valid manufacturer authorization certifying genuine hardware and warranty commitment.",
                category="TECHNICAL",
                requirement_type="DOCUMENT",
                operator="EXISTS",
                expected_value=True,
                is_mandatory=True,
                weight=Decimal("15.00"),
                display_order=4,
                is_active=True,
            ),
            TenderRequirement(
                tender_id=tender.id,
                code="LOCAL_CONTENT",
                name="Minimum 50% Class-I Local Content Certificate",
                description="Self-certification or auditor certificate of local content under Make in India (DPIIT) guidelines.",
                category="LOCAL_CONTENT",
                requirement_type="NUMBER",
                operator="GREATER_THAN_OR_EQUAL",
                expected_value=50,
                is_mandatory=True,
                weight=Decimal("15.00"),
                display_order=5,
                is_active=True,
            ),
        ]

        db.add_all(sample_requirements)
        db.commit()
        logger.info(f"Successfully seeded demo tender '{DEMO_TENDER_NUMBER}' with {len(sample_requirements)} requirements (Tender ID: {tender.id}).")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed demo tender: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_tender_demo()
