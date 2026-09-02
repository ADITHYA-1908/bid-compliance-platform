"""
High-Volume 200-Bidder Seed & Benchmark Script
Provisions a large-scale GeM Tender with 200 submitted bids and configures
the exact target breakdown: 128 PASS, 47 REVIEW, 20 FAIL, and 5 CRITICAL findings.
"""

import sys
import os
import logging
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.db.session import get_session_factory
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.user import User
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.bulk_evaluation_job import (
    BulkEvaluationJob,
    BulkEvaluationJobItem,
    BulkJobStatus,
    BulkItemStatus,
    BulkStage,
)
from app.db.models.document_processing import DocumentProcessing, ProcessingStage, ProcessingStatus
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.core.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BENCHMARK_TENDER_NUMBER = "GEM/2026/B/200000"


def seed_200_bidders_tender(run_bulk_job_immediately: bool = True) -> str:
    """
    Idempotently provisions a 200-bidder tender and optionally pre-executes
    or seeds the bulk evaluation job with exact target distribution:
    128 PASS, 47 REVIEW, 20 FAIL, 5 CRITICAL findings.
    """
    from app.db.base import Base
    from app.db.session import get_engine
    Base.metadata.create_all(bind=get_engine())

    session_factory = get_session_factory()
    db = session_factory()

    try:
        logger.info("Initializing 200-Bidder Benchmark Tender Seed...")

        # 1. Fetch or create Procurement Officer Profile
        proc_user = db.scalars(
            select(User)
            .where(User.email == "procurement@test.local")
            .options(selectinload(User.profile).selectinload(Profile.organization))
        ).first()

        if not proc_user:
            # Check for alternative email
            proc_user = db.scalars(
                select(User)
                .where(User.email == "procurement.officer@railways.gov.in")
                .options(selectinload(User.profile).selectinload(Profile.organization))
            ).first()

        if not proc_user:
            logger.info("Creating default Procurement Officer account (procurement@test.local)...")
            role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
            if not role:
                role = Role(name="PROCUREMENT_OFFICER", description="Procurement Officer")
                db.add(role)
                db.flush()

            org = Organization(
                name="Ministry of Railways (GeM Procurement Cell)",
                organization_type="Government Ministry",
                is_active=True,
            )
            db.add(org)
            db.flush()

            profile = Profile(
                full_name="Chief Procurement Officer",
                email="procurement@test.local",
                role_id=role.id,
                organization_id=org.id,
                is_active=True,
            )
            db.add(profile)
            db.flush()

            proc_user = User(
                email="procurement@test.local",
                password_hash=hash_password("TestPassword123!"),
                profile_id=profile.id,
                is_active=True,
            )
            db.add(proc_user)
            db.commit()

        proc_profile = proc_user.profile
        org_id = proc_profile.organization_id

        # 2. Check if benchmark tender already exists
        tender = db.scalars(
            select(Tender)
            .where(Tender.tender_number == BENCHMARK_TENDER_NUMBER)
            .options(selectinload(Tender.requirements))
        ).first()

        now = datetime.now(timezone.utc)

        if not tender:
            logger.info(f"Creating Benchmark Tender '{BENCHMARK_TENDER_NUMBER}'...")
            tender = Tender(
                tender_number=BENCHMARK_TENDER_NUMBER,
                title="GeM High-Volume Enterprise IT Procurement (200 Bidders Benchmark)",
                description="High-volume national tender for supplying enterprise IT networking hardware, cloud servers, and statutory compliance verification for 200 participating vendors across India.",
                department="Directorate of Signal & Telecommunications",
                category="IT Infrastructure",
                procurement_type="GOODS",
                estimated_value=Decimal("125000000.00"),  # 12.5 Crore INR
                currency="INR",
                publish_date=now - timedelta(days=10),
                submission_start_date=now - timedelta(days=9),
                submission_end_date=now - timedelta(days=1),
                evaluation_start_date=now,
                organization_id=org_id,
                created_by_profile_id=proc_profile.id,
                status="UNDER_EVALUATION",
                is_active=True,
            )
            db.add(tender)
            db.flush()

            # Add Standard Tender Requirements
            requirements = [
                TenderRequirement(
                    tender_id=tender.id,
                    code="GST_REGISTRATION",
                    name="Active GST Registration",
                    description="Bidder must possess a valid, active GSTIN registration without default flag.",
                    category="STATUTORY",
                    requirement_type="BOOLEAN",
                    is_mandatory=True,
                    display_order=1,
                ),
                TenderRequirement(
                    tender_id=tender.id,
                    code="MIN_TURNOVER",
                    name="Minimum Annual Financial Turnover",
                    description="Average annual turnover over last 3 financial years must be at least ₹5.0 Crore.",
                    category="FINANCIAL",
                    requirement_type="MINIMUM_NUMERIC",
                    operator="GREATER_THAN_OR_EQUAL",
                    expected_value=50000000.00,
                    is_mandatory=True,
                    display_order=2,
                ),
                TenderRequirement(
                    tender_id=tender.id,
                    code="OEM_AUTHORIZATION",
                    name="Valid OEM Authorization Letter",
                    description="Manufacturer Authorization Form (MAF) from OEM for server equipment.",
                    category="TECHNICAL",
                    requirement_type="DOCUMENT_EXISTS",
                    is_mandatory=True,
                    display_order=3,
                ),
                TenderRequirement(
                    tender_id=tender.id,
                    code="NO_DEBARMENT",
                    name="Non-Blacklisting & Integrity Declaration",
                    description="Declaration confirming no debarment by GeM, CVC, or Ministry of Finance.",
                    category="CRITICAL",
                    requirement_type="BOOLEAN",
                    is_mandatory=True,
                    display_order=4,
                ),
            ]
            db.add_all(requirements)
            db.commit()

        logger.info(f"Tender ID: {tender.id}")

        # 3. Check existing bids for this tender
        existing_bids = db.scalars(select(Bid).where(Bid.tender_id == tender.id)).all()
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        if not bidder_role:
            bidder_role = Role(name="BIDDER", description="Vendor / Bidder")
            db.add(bidder_role)
            db.flush()

        if len(existing_bids) < 200:
            needed = 200 - len(existing_bids)
            logger.info(f"Seeding {needed} additional submitted bids to reach 200 bidders...")

            start_idx = len(existing_bids) + 1
            for i in range(start_idx, 201):
                org_name = f"Vendor {i:03d} Solutions Pvt Ltd"
                b_org = db.scalars(select(Organization).where(Organization.name == org_name)).first()
                if not b_org:
                    b_org = Organization(name=org_name, organization_type="Private Vendor", is_active=True)
                    db.add(b_org)
                    db.flush()

                b_email = f"bidder_{i:03d}@vendor.gem.in"
                b_user = db.scalars(select(User).where(User.email == b_email)).first()
                if not b_user:
                    b_prof = Profile(
                        full_name=f"Director Vendor {i:03d}",
                        email=b_email,
                        role_id=bidder_role.id,
                        organization_id=b_org.id,
                        is_active=True,
                    )
                    db.add(b_prof)
                    db.flush()

                    b_user = User(
                        email=b_email,
                        password_hash=hash_password("VendorPass123!"),
                        profile_id=b_prof.id,
                        is_active=True,
                    )
                    db.add(b_user)
                    db.flush()

                bid = Bid(
                    tender_id=tender.id,
                    bidder_organization_id=b_org.id,
                    created_by_profile_id=b_user.profile_id,
                    bid_number=f"BID-2026-{tender.id.hex[:4].upper()}-{i:03d}",
                    status="SUBMITTED",
                    submitted_at=now - timedelta(hours=i),
                    is_active=True,
                )
                db.add(bid)
                db.flush()

                # Add sample document
                doc = BidDocument(
                    bid_id=bid.id,
                    uploaded_by_profile_id=b_user.profile_id,
                    document_name=f"Vendor_{i:03d}_Statutory_Dossier.pdf",
                    original_filename=f"Vendor_{i:03d}_Statutory_Dossier.pdf",
                    storage_path=f"uploads/bids/{bid.id}/dossier.pdf",
                    file_size=245000,
                    mime_type="application/pdf",
                    document_type="STATUTORY_CERTIFICATE",
                    is_active=True,
                )
                db.add(doc)

            db.commit()
            logger.info("Successfully seeded 200 submitted bids!")

        # 4. Fetch all 200 bids ordered by creation
        all_bids = db.scalars(
            select(Bid).where(Bid.tender_id == tender.id).order_by(Bid.created_at.asc())
        ).all()

        # Clean existing bulk jobs for this tender to start fresh
        db.execute(delete(BulkEvaluationJobItem).where(
            BulkEvaluationJobItem.job_id.in_(
                select(BulkEvaluationJob.id).where(BulkEvaluationJob.tender_id == tender.id)
            )
        ))
        db.execute(delete(BulkEvaluationJob).where(BulkEvaluationJob.tender_id == tender.id))
        db.commit()

        if run_bulk_job_immediately:
            logger.info("Creating and population Bulk Evaluation Job with target breakdown:")
            logger.info("  🟢 128 PASS")
            logger.info("  🟡 47 REVIEW")
            logger.info("  🔴 20 FAIL")
            logger.info("  🚨 5 CRITICAL")

            # Create Bulk Job record
            job = BulkEvaluationJob(
                organization_id=org_id,
                tender_id=tender.id,
                status=BulkJobStatus.PARTIALLY_COMPLETED,
                total_bids=200,
                processed_bids=200,
                successful_bids=128,
                review_required_bids=47,
                failed_bids=20,
                critical_findings_bids=5,
                started_by_profile_id=proc_profile.id,
                started_at=now - timedelta(minutes=15),
                completed_at=now - timedelta(minutes=2),
            )
            db.add(job)
            db.flush()

            job_items = []
            for idx, bid in enumerate(all_bids):
                # Target indexing logic:
                # Bids 0..127 (128 items): PASS
                # Bids 128..174 (47 items): REVIEW REQUIRED
                # Bids 175..194 (20 items): FAILED
                # Bids 195..199 (5 items): CRITICAL
                
                if idx < 128:
                    # PASS
                    status = BulkItemStatus.SUCCESS
                    doc_status = "SUCCESS"
                    ver_status = "SUCCESS"
                    comp_status = "SUCCESS"
                    score_status = "SUCCESS"
                    risk_status = "SUCCESS"
                    final_score = round(82.5 + (idx % 15) * 1.1, 2)
                    risk_lvl = "LOW"
                    rev_req = False
                    crit_count = 0
                    err_code = None
                    err_msg = None
                elif idx < 175:
                    # REVIEW REQUIRED
                    status = BulkItemStatus.REVIEW_REQUIRED
                    doc_status = "NEEDS_REVIEW"
                    ver_status = "SUCCESS"
                    comp_status = "REVIEW_REQUIRED"
                    score_status = "SUCCESS"
                    risk_status = "SUCCESS"
                    final_score = round(68.0 + (idx % 10) * 1.2, 2)
                    risk_lvl = "MEDIUM"
                    rev_req = True
                    crit_count = 0
                    err_code = None
                    err_msg = None
                elif idx < 195:
                    # FAIL
                    status = BulkItemStatus.FAILED
                    doc_status = "SUCCESS"
                    ver_status = "FAILED"
                    comp_status = "FAILED"
                    score_status = "SUCCESS"
                    risk_status = "SUCCESS"
                    final_score = round(35.0 + (idx % 10) * 1.5, 2)
                    risk_lvl = "HIGH"
                    rev_req = False
                    crit_count = 0
                    err_code = "TURNOVER_RULE_FAILED"
                    err_msg = "Annual turnover INR 3.2 Cr is below mandatory requirement of INR 5.0 Cr."
                else:
                    # CRITICAL
                    status = BulkItemStatus.REVIEW_REQUIRED
                    doc_status = "NEEDS_REVIEW"
                    ver_status = "FAILED"
                    comp_status = "FAILED"
                    score_status = "SUCCESS"
                    risk_status = "SUCCESS"
                    final_score = 15.0
                    risk_lvl = "CRITICAL"
                    rev_req = True
                    crit_count = 1
                    err_code = "CVC_DEBARMENT_FLAG"
                    err_msg = "CRITICAL: Vendor matches active CVC Debarment Registry & GeM Blacklist Ledger."

                item = BulkEvaluationJobItem(
                    job_id=job.id,
                    bid_id=bid.id,
                    status=status,
                    current_stage=BulkStage.COMPLETED,
                    document_processing_status=doc_status,
                    verification_status=ver_status,
                    compliance_status=comp_status,
                    score_status=score_status,
                    risk_status=risk_status,
                    final_score=final_score,
                    risk_level=risk_lvl,
                    review_required=rev_req,
                    critical_findings_count=crit_count,
                    error_code=err_code,
                    error_message=err_msg,
                    started_at=now - timedelta(minutes=14),
                    completed_at=now - timedelta(minutes=3),
                )
                job_items.append(item)

            db.add_all(job_items)
            db.commit()

            logger.info("Bulk job pre-execution seeded successfully!")
            logger.info(f"Job ID: {job.id}")
            logger.info(f"Summary telemetry: {job.total_bids} Bids -> {job.successful_bids} PASS, {job.review_required_bids} REVIEW, {job.failed_bids} FAIL, {job.critical_findings_bids} CRITICAL")

        return str(tender.id)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed 200-bidder benchmark tender: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    tender_id = seed_200_bidders_tender(run_bulk_job_immediately=True)
    print("\n" + "=" * 80)
    print("SUCCESS: 200-Bidder Bulk Verification Benchmark Tender Ready!")
    print(f"Tender ID: {tender_id}")
    print("Run Guide: Log in as 'procurement@test.local' / 'TestPassword123!' on Frontend")
    print("=" * 80)
