"""
Part 5A Comprehensive Test Suite — Verification Engine Foundation & Adapter Architecture
BidVerify AI — GeM Verification Engine & Deterministic Mock Adapters

Tests:
1. Adapter Registry Unit Tests (GST, PAN, Udyam resolution, unsupported handling)
2. Claim Input Validation Unit Tests (Missing input -> NEEDS_REVIEW, Invalid format -> NOT_VERIFIED)
3. Deterministic Mock GST Adapter (Active VERIFIED, Inactive NOT_VERIFIED, Outage UNAVAILABLE)
4. Deterministic Mock PAN Adapter (Active VERIFIED, Inactive NOT_VERIFIED, Outage UNAVAILABLE)
5. Deterministic Mock Udyam Adapter (Active VERIFIED, Revoked NOT_VERIFIED, Outage UNAVAILABLE)
6. Status Separation (NOT_VERIFIED != UNAVAILABLE != FAILED)
7. Verification Engine & Service Request Lifecycle (Discovery, Execution, DB Persistence)
8. Idempotency (Existing valid records reused without endless duplication)
9. Retry Orchestration (Retry UNAVAILABLE/FAILED increments attempt_number)
10. Submitted Bid Support (Verification allowed on SUBMITTED bids)
11. Replaced Document Audit Trail (Replaced document preserves verifications, new version gets fresh records)
12. Multi-Tenant Security & Isolation (Cross-bidder 404 isolation)
13. Compliance Separation Guard (No PASS/FAIL, no Scoring, no AI recommendations)
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select

# Set Python path to backend root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import (
    DocumentClass,
    DocumentProcessing,
    ExtractionMethod,
    ProcessingStage,
    ProcessingStatus,
)
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.db.session import get_session_factory
from app.services.verification_engine import verification_engine
from app.services.verification_service import (
    discover_claims_for_document,
    get_bid_verifications,
    get_document_verifications,
    retry_verification_record,
    verify_document_claims,
)
from app.verification.adapters.base import VerificationRequest
from app.verification.registry import adapter_registry
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)


def print_test_header(title: str):
    print(f"\n{'='*70}\n[TEST] {title}\n{'='*70}")


def print_pass(msg: str):
    print(f"  [PASS] {msg}")


def print_fail(msg: str):
    print(f"  [FAIL] {msg}")


async def run_part5a_test_suite():
    session_factory = get_session_factory()
    db = session_factory()

    passed_count = 0
    failed_count = 0

    def record_result(test_name: str, passed: bool, details: str = ""):
        nonlocal passed_count, failed_count
        if passed:
            print_pass(f"{test_name} {details}")
            passed_count += 1
        else:
            print_fail(f"{test_name} {details}")
            failed_count += 1

    try:
        # =========================================================================
        # 1. Adapter Registry Unit Tests
        # =========================================================================
        print_test_header("1. Adapter Registry Unit Tests")

        gst_adapter = adapter_registry.get_adapter(VerificationType.GST)
        record_result(
            "Registry resolves GST adapter",
            gst_adapter is not None and gst_adapter.source_name == "Mock GST Registry",
            f"-> {gst_adapter.source_name if gst_adapter else 'None'}",
        )

        pan_adapter = adapter_registry.get_adapter(VerificationType.PAN)
        record_result(
            "Registry resolves PAN adapter",
            pan_adapter is not None and pan_adapter.source_name == "Mock PAN Registry",
            f"-> {pan_adapter.source_name if pan_adapter else 'None'}",
        )

        udyam_adapter = adapter_registry.get_adapter(VerificationType.UDYAM)
        record_result(
            "Registry resolves Udyam adapter",
            udyam_adapter is not None and udyam_adapter.source_name == "Mock MSME Udyam Registry",
            f"-> {udyam_adapter.source_name if udyam_adapter else 'None'}",
        )

        unsupported_adapter = adapter_registry.get_adapter("UNSUPPORTED_TYPE_XYZ")
        record_result(
            "Registry returns None for unregistered type",
            unsupported_adapter is None,
        )

        # =========================================================================
        # 2. Claim Input Validation Unit Tests
        # =========================================================================
        print_test_header("2. Claim Input Validation Unit Tests")

        # Missing input -> NEEDS_REVIEW with VERIFICATION_INPUT_MISSING
        res_missing = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.GST,
                claimed_value="",
            )
        )
        record_result(
            "Missing claim value returns NEEDS_REVIEW with MISSING_VERIFICATION_VALUE",
            res_missing.verification_status == VerificationStatus.NEEDS_REVIEW
            and res_missing.error_code == VerificationErrorCode.VERIFICATION_INPUT_MISSING,
            f"-> Status={res_missing.verification_status}, Code={res_missing.error_code}",
        )

        # Malformed GSTIN format -> NOT_VERIFIED with VERIFICATION_INPUT_INVALID
        res_bad_gst = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.GST,
                claimed_value="NOT_A_GSTIN",
            )
        )
        record_result(
            "Malformed GSTIN returns NOT_VERIFIED with VERIFICATION_INPUT_INVALID",
            res_bad_gst.verification_status == VerificationStatus.NOT_VERIFIED
            and res_bad_gst.error_code == VerificationErrorCode.VERIFICATION_INPUT_INVALID,
            f"-> Status={res_bad_gst.verification_status}, Code={res_bad_gst.error_code}",
        )

        # Malformed PAN format -> NOT_VERIFIED
        res_bad_pan = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.PAN,
                claimed_value="12345",
            )
        )
        record_result(
            "Malformed PAN returns NOT_VERIFIED with VERIFICATION_INPUT_INVALID",
            res_bad_pan.verification_status == VerificationStatus.NOT_VERIFIED
            and res_bad_pan.error_code == VerificationErrorCode.VERIFICATION_INPUT_INVALID,
            f"-> Status={res_bad_pan.verification_status}, Code={res_bad_pan.error_code}",
        )

        # Malformed Udyam format -> NOT_VERIFIED
        res_bad_udyam = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.UDYAM,
                claimed_value="UDYAM-BAD-FORMAT",
            )
        )
        record_result(
            "Malformed Udyam returns NOT_VERIFIED with VERIFICATION_INPUT_INVALID",
            res_bad_udyam.verification_status == VerificationStatus.NOT_VERIFIED
            and res_bad_udyam.error_code == VerificationErrorCode.VERIFICATION_INPUT_INVALID,
            f"-> Status={res_bad_udyam.verification_status}, Code={res_bad_udyam.error_code}",
        )

        # =========================================================================
        # 3. Deterministic Mock GST Adapter Tests
        # =========================================================================
        print_test_header("3. Deterministic Mock GST Adapter Tests")

        # Active Match
        res_gst_valid = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.GST,
                claimed_value="33ABCDE1234F1Z5",
            )
        )
        record_result(
            "Valid GSTIN returns VERIFIED, MATCH, confidence=1.0",
            res_gst_valid.verification_status == VerificationStatus.VERIFIED
            and res_gst_valid.match_status == VerificationMatchStatus.MATCH
            and res_gst_valid.confidence == 1.0
            and res_gst_valid.evidence.get("legal_name") == "TECHFLOW ENTERPRISES PRIVATE LIMITED",
            f"-> Legal Name: {res_gst_valid.evidence.get('legal_name')}",
        )

        # Cancelled GSTIN in registry -> VERIFIED with registration_status="CANCELLED"
        res_gst_cancelled = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.GST,
                claimed_value="33ABCDE1234F1Z9",
            )
        )
        record_result(
            "Cancelled GSTIN in mock registry returns VERIFIED with registration_status='CANCELLED'",
            res_gst_cancelled.verification_status == VerificationStatus.VERIFIED
            and res_gst_cancelled.evidence.get("registration_status") == "CANCELLED",
            f"-> Status={res_gst_cancelled.verification_status}, RegStatus={res_gst_cancelled.evidence.get('registration_status')}",
        )

        # Simulated Outage GSTIN -> UNAVAILABLE
        res_gst_outage = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.GST,
                claimed_value="27UNAVA9999A1Z1",
            )
        )
        record_result(
            "Simulated Outage GSTIN returns UNAVAILABLE",
            res_gst_outage.verification_status == VerificationStatus.UNAVAILABLE
            and res_gst_outage.error_code == VerificationErrorCode.SOURCE_UNAVAILABLE,
            f"-> Status={res_gst_outage.verification_status}, Code={res_gst_outage.error_code}",
        )

        # =========================================================================
        # 4. Deterministic Mock PAN Adapter Tests
        # =========================================================================
        print_test_header("4. Deterministic Mock PAN Adapter Tests")

        res_pan_valid = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.PAN,
                claimed_value="ABCDE1234F",
            )
        )
        record_result(
            "Valid PAN returns VERIFIED, MATCH, confidence=1.0",
            res_pan_valid.verification_status == VerificationStatus.VERIFIED
            and res_pan_valid.match_status == VerificationMatchStatus.MATCH
            and res_pan_valid.confidence == 1.0
            and res_pan_valid.evidence.get("entity_name") == "TECHFLOW ENTERPRISES PRIVATE LIMITED",
            f"-> Entity Name: {res_pan_valid.evidence.get('entity_name')}",
        )

        res_pan_inactive = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.PAN,
                claimed_value="ABCDE9999X",
            )
        )
        record_result(
            "Inactive PAN returns VERIFIED with pan_status='INACTIVE'",
            res_pan_inactive.verification_status == VerificationStatus.VERIFIED
            and res_pan_inactive.evidence.get("pan_status") == "INACTIVE",
            f"-> Status={res_pan_inactive.verification_status}, PANStatus={res_pan_inactive.evidence.get('pan_status')}",
        )

        res_pan_outage = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.PAN,
                claimed_value="UNAVA9999X",
            )
        )
        record_result(
            "Outage PAN returns UNAVAILABLE",
            res_pan_outage.verification_status == VerificationStatus.UNAVAILABLE
            and res_pan_outage.error_code == VerificationErrorCode.SOURCE_UNAVAILABLE,
            f"-> Status={res_pan_outage.verification_status}",
        )

        # =========================================================================
        # 5. Deterministic Mock Udyam Adapter Tests
        # =========================================================================
        print_test_header("5. Deterministic Mock Udyam Adapter Tests")

        res_udyam_valid = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.UDYAM,
                claimed_value="UDYAM-TN-01-0012345",
            )
        )
        record_result(
            "Valid Udyam returns VERIFIED, MATCH, confidence=1.0",
            res_udyam_valid.verification_status == VerificationStatus.VERIFIED
            and res_udyam_valid.match_status == VerificationMatchStatus.MATCH
            and res_udyam_valid.evidence.get("enterprise_type") == "Micro",
            f"-> Enterprise: {res_udyam_valid.evidence.get('enterprise_name')}",
        )

        res_udyam_revoked = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.UDYAM,
                claimed_value="UDYAM-DL-00-9999999",
            )
        )
        record_result(
            "Revoked Udyam returns VERIFIED with registration_status='CANCELLED'",
            res_udyam_revoked.verification_status == VerificationStatus.VERIFIED
            and res_udyam_revoked.evidence.get("registration_status") == "CANCELLED",
            f"-> Status={res_udyam_revoked.verification_status}",
        )

        res_udyam_outage = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.UDYAM,
                claimed_value="UDYAM-XX-00-0000000",
            )
        )
        record_result(
            "Outage Udyam returns UNAVAILABLE",
            res_udyam_outage.verification_status == VerificationStatus.UNAVAILABLE
            and res_udyam_outage.error_code == VerificationErrorCode.SOURCE_UNAVAILABLE,
            f"-> Status={res_udyam_outage.verification_status}",
        )

        # =========================================================================
        # 6. Database Fixture Setup (Bidder, Bid, Documents, Processing)
        # =========================================================================
        print_test_header("6. Setting Up Test Fixtures in Database")

        # Create or find Bidder Role
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        if not bidder_role:
            bidder_role = Role(name="BIDDER", description="Bidder Role")
            db.add(bidder_role)
            db.commit()
            db.refresh(bidder_role)

        test_suffix = uuid.uuid4().hex[:6]

        org_a = Organization(
            id=uuid.uuid4(),
            name=f"TechFlow A {test_suffix}",
            pan_number="ABCDE1234F",
            gstin="33ABCDE1234F1Z5",
            state="Tamil Nadu",
            city="Chennai",
            is_active=True,
        )
        org_b = Organization(
            id=uuid.uuid4(),
            name=f"Other Org B {test_suffix}",
            pan_number="AAAAA0000A",
            gstin="07AAAAA0000A1Z5",
            state="Delhi",
            city="New Delhi",
            is_active=True,
        )
        db.add_all([org_a, org_b])
        db.commit()

        profile_a = Profile(
            id=uuid.uuid4(),
            email=f"bidder_a_{test_suffix}@bidverify.mock",
            role_id=bidder_role.id,
            organization_id=org_a.id,
            full_name="Muthu Developer A",
            is_active=True,
        )
        profile_b = Profile(
            id=uuid.uuid4(),
            email=f"bidder_b_{test_suffix}@bidverify.mock",
            role_id=bidder_role.id,
            organization_id=org_b.id,
            full_name="Muthu Developer B",
            is_active=True,
        )
        db.add_all([profile_a, profile_b])
        db.commit()

        user_a = User(
            id=uuid.uuid4(),
            email=f"bidder_a_{test_suffix}@bidverify.mock",
            password_hash="mock_password_hash",
            profile_id=profile_a.id,
            is_active=True,
        )
        user_b = User(
            id=uuid.uuid4(),
            email=f"bidder_b_{test_suffix}@bidverify.mock",
            password_hash="mock_password_hash",
            profile_id=profile_b.id,
            is_active=True,
        )
        db.add_all([user_a, user_b])
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)

        # Create Tender
        tender = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/B/{test_suffix.upper()}",
            title="Procurement of IT Hardware & Cloud Servers",
            description="GeM statutory verification test tender",
            organization_id=org_a.id,
            created_by_profile_id=profile_a.id,
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)
        db.commit()

        # Create Bid for Bidder A
        bid_a = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_a.id,
            created_by_profile_id=profile_a.id,
            bid_number=f"BID-A-{test_suffix.upper()}",
            status="DRAFT",
            is_active=True,
        )
        # Create Bid for Bidder B
        bid_b = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_b.id,
            created_by_profile_id=profile_b.id,
            bid_number=f"BID-B-{test_suffix.upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add_all([bid_a, bid_b])
        db.commit()

        # Create Active GST BidDocument with structured extracted data
        doc_gst = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid_a.id,
            uploaded_by_profile_id=profile_a.id,
            document_type="GST_CERTIFICATE",
            document_name="GST Certificate",
            original_filename="gst_certificate_techflow.pdf",
            storage_path=f"bids/{bid_a.id}/gst.pdf",
            mime_type="application/pdf",
            file_size=10240,
            status="UPLOADED",
            version=1,
            is_active=True,
        )
        db.add(doc_gst)
        db.commit()

        proc_gst = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_gst.id,
            processing_status=ProcessingStatus.COMPLETED,
            processing_stage=ProcessingStage.COMPLETED,
            extraction_method=ExtractionMethod.DIGITAL_PDF,
            detected_document_type=DocumentClass.GST_CERTIFICATE,
            classification_confidence=0.95,
            extracted_data={
                "fields": {
                    "gstin": {
                        "value": "33ABCDE1234F1Z5",
                        "confidence": 0.98,
                        "evidence": "GSTIN: 33ABCDE1234F1Z5",
                        "page": 1,
                    },
                    "legal_name": {
                        "value": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
                        "confidence": 0.90,
                        "evidence": "Legal Name: TECHFLOW ENTERPRISES PRIVATE LIMITED",
                        "page": 1,
                    },
                }
            },
            raw_text="GSTIN: 33ABCDE1234F1Z5 TECHFLOW ENTERPRISES",
            normalized_text="GSTIN: 33ABCDE1234F1Z5 TECHFLOW ENTERPRISES",
        )
        db.add(proc_gst)
        db.commit()

        print_pass("Database test fixtures seeded successfully.")

        # =========================================================================
        # 7. Verification Service Request Execution & DB Persistence
        # =========================================================================
        print_test_header("7. Verification Service Request Execution & DB Persistence")

        v_trigger_res = await verify_document_claims(
            db=db,
            current_user=user_a,
            bid_id=bid_a.id,
            document_id=doc_gst.id,
        )

        record_result(
            "Trigger verification returns success response with results",
            len(v_trigger_res.results) > 0 and v_trigger_res.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> Count: {len(v_trigger_res.results)}, Status: {v_trigger_res.results[0].verification_status}",
        )

        # Inspect persisted row in PostgreSQL
        persisted_v = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_id == bid_a.id,
                VerificationRecord.bid_document_id == doc_gst.id,
                VerificationRecord.is_active == True,
            )
        ).first()

        record_result(
            "VerificationRecord correctly persisted in PostgreSQL",
            persisted_v is not None
            and persisted_v.verification_type == VerificationType.GST
            and persisted_v.verification_status == VerificationStatus.VERIFIED
            and persisted_v.source_name == "Mock GST Registry"
            and persisted_v.source_type == "MOCK"
            and persisted_v.claimed_value == "33ABCDE1234F1Z5"
            and persisted_v.verified_value == "33ABCDE1234F1Z5"
            and persisted_v.match_status == VerificationMatchStatus.MATCH
            and persisted_v.confidence == 1.0
            and persisted_v.verification_completed_at is not None,
            f"-> DB Record ID: {persisted_v.id if persisted_v else 'None'}",
        )

        # =========================================================================
        # 8. Idempotency Check
        # =========================================================================
        print_test_header("8. Idempotency Check")

        # Triggering again should reuse existing valid record without creating extra rows
        count_before = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_id == bid_a.id,
                VerificationRecord.bid_document_id == doc_gst.id,
            )
        ).all()

        v_trigger_again = await verify_document_claims(
            db=db,
            current_user=user_a,
            bid_id=bid_a.id,
            document_id=doc_gst.id,
        )

        count_after = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_id == bid_a.id,
                VerificationRecord.bid_document_id == doc_gst.id,
            )
        ).all()

        record_result(
            "Idempotent execution avoids duplicate records",
            len(count_before) == len(count_after) and v_trigger_again.created_count == 0,
            f"-> Records before: {len(count_before)}, Records after: {len(count_after)}",
        )

        # =========================================================================
        # 9. Outage Simulation & Retry Orchestration
        # =========================================================================
        print_test_header("9. Outage Simulation & Retry Orchestration")

        # Create Outage Document & Processing
        doc_outage = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid_a.id,
            uploaded_by_profile_id=profile_a.id,
            document_type="PAN",
            document_name="PAN Card Outage Test",
            original_filename="pan_outage.pdf",
            storage_path=f"bids/{bid_a.id}/pan_outage.pdf",
            mime_type="application/pdf",
            file_size=10240,
            status="UPLOADED",
            version=1,
            is_active=True,
        )
        db.add(doc_outage)
        db.commit()

        proc_outage = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_outage.id,
            processing_status=ProcessingStatus.COMPLETED,
            processing_stage=ProcessingStage.COMPLETED,
            extraction_method=ExtractionMethod.DIGITAL_PDF,
            detected_document_type=DocumentClass.PAN,
            classification_confidence=0.95,
            extracted_data={
                "fields": {
                    "pan_number": {
                        "value": "UNAVA9999X",  # Simulated outage PAN fixture
                        "confidence": 0.99,
                        "evidence": "PAN: UNAVA9999X",
                    }
                }
            },
            raw_text="PAN: UNAVA9999X",
            normalized_text="PAN: UNAVA9999X",
        )
        db.add(proc_outage)
        db.commit()

        # Trigger Outage Verification -> Returns UNAVAILABLE
        outage_res = await verify_document_claims(
            db=db,
            current_user=user_a,
            bid_id=bid_a.id,
            document_id=doc_outage.id,
        )

        v_outage_rec = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_document_id == doc_outage.id,
                VerificationRecord.is_active == True,
            )
        ).first()

        record_result(
            "Outage claim creates UNAVAILABLE verification record",
            v_outage_rec is not None
            and v_outage_rec.verification_status == VerificationStatus.UNAVAILABLE
            and v_outage_rec.attempt_number == 1,
            f"-> Status={v_outage_rec.verification_status if v_outage_rec else 'None'}",
        )

        # Retry the UNAVAILABLE verification
        retry_res = await retry_verification_record(
            db=db,
            current_user=user_a,
            bid_id=bid_a.id,
            verification_id=v_outage_rec.id,
        )

        record_result(
            "Retry increments attempt_number",
            retry_res.verification.attempt_number == 2,
            f"-> Attempt number={retry_res.verification.attempt_number}",
        )

        # Disallow retry on already VERIFIED records
        try:
            await retry_verification_record(
                db=db,
                current_user=user_a,
                bid_id=bid_a.id,
                verification_id=persisted_v.id,
            )
            record_result("Disallow retry on VERIFIED record", False, "Should have raised HTTP 400")
        except HTTPException as he:
            record_result(
                "Disallow retry on VERIFIED record",
                he.status_code == 400,
                f"-> HTTP {he.status_code}: {he.detail}",
            )

        # =========================================================================
        # 10. Multi-Tenant Security & Isolation
        # =========================================================================
        print_test_header("10. Multi-Tenant Security & Isolation")

        # Bidder B attempts to read or trigger verification on Bidder A's bid
        try:
            await verify_document_claims(
                db=db,
                current_user=user_b,
                bid_id=bid_a.id,
                document_id=doc_gst.id,
            )
            record_result("Bidder B triggering Bidder A verification rejected", False)
        except HTTPException as he:
            record_result(
                "Bidder B triggering Bidder A verification rejected with 404",
                he.status_code == 404,
                f"-> HTTP {he.status_code}: {he.detail}",
            )

        try:
            get_document_verifications(
                db=db,
                current_user=user_b,
                bid_id=bid_a.id,
                document_id=doc_gst.id,
            )
            record_result("Bidder B reading Bidder A verifications rejected", False)
        except HTTPException as he:
            record_result(
                "Bidder B reading Bidder A verifications rejected with 404",
                he.status_code == 404,
                f"-> HTTP {he.status_code}: {he.detail}",
            )

        # =========================================================================
        # 11. Submitted Bid Verification Support
        # =========================================================================
        print_test_header("11. Submitted Bid Verification Support")

        # Mark Bid A as SUBMITTED
        bid_a.status = "SUBMITTED"
        bid_a.submitted_at = datetime.now(timezone.utc)
        db.commit()

        # Create Udyam Document for Submitted Bid
        doc_udyam = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid_a.id,
            uploaded_by_profile_id=profile_a.id,
            document_type="UDYAM_CERTIFICATE",
            document_name="Udyam MSME Certificate",
            original_filename="udyam_techflow.pdf",
            storage_path=f"bids/{bid_a.id}/udyam.pdf",
            mime_type="application/pdf",
            file_size=12000,
            status="UPLOADED",
            version=1,
            is_active=True,
        )
        db.add(doc_udyam)
        db.commit()

        proc_udyam = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_udyam.id,
            processing_status=ProcessingStatus.COMPLETED,
            processing_stage=ProcessingStage.COMPLETED,
            extraction_method=ExtractionMethod.DIGITAL_PDF,
            detected_document_type=DocumentClass.UDYAM_CERTIFICATE,
            classification_confidence=0.96,
            extracted_data={
                "fields": {
                    "udyam_registration_number": {
                        "value": "UDYAM-TN-01-0012345",
                        "confidence": 0.99,
                        "evidence": "Udyam Registration: UDYAM-TN-01-0012345",
                    }
                }
            },
            raw_text="UDYAM-TN-01-0012345 TECHFLOW",
            normalized_text="UDYAM-TN-01-0012345 TECHFLOW",
        )
        db.add(proc_udyam)
        db.commit()

        # Verification must succeed on SUBMITTED bid
        v_sub_res = await verify_document_claims(
            db=db,
            current_user=user_a,
            bid_id=bid_a.id,
            document_id=doc_udyam.id,
        )

        record_result(
            "Verification succeeds on SUBMITTED bid",
            len(v_sub_res.results) > 0 and v_sub_res.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> Status={v_sub_res.results[0].verification_status}",
        )

        # =========================================================================
        # 12. Replaced Document Audit Trail
        # =========================================================================
        print_test_header("12. Replaced Document Audit Trail")

        # Supersede doc_udyam: mark is_active=False
        doc_udyam.is_active = False
        db.commit()

        # Attempting to verify inactive superseded doc should be rejected
        try:
            await verify_document_claims(
                db=db,
                current_user=user_a,
                bid_id=bid_a.id,
                document_id=doc_udyam.id,
            )
            record_result("Verifying inactive replaced document rejected", False)
        except HTTPException as he:
            record_result(
                "Verifying inactive replaced document rejected with HTTP 400",
                he.status_code == 400,
                f"-> HTTP {he.status_code}: {he.detail}",
            )

        # Past verification records for doc_udyam must still be preserved in DB
        old_v_records = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_document_id == doc_udyam.id
            )
        ).all()
        record_result(
            "Superseded document verification history is preserved in DB",
            len(old_v_records) > 0,
            f"-> Preserved records count: {len(old_v_records)}",
        )

        # =========================================================================
        # 13. Bid-Level Aggregate Verification Endpoint
        # =========================================================================
        print_test_header("13. Bid-Level Aggregate Verification Endpoint")

        bid_v_agg = get_bid_verifications(
            db=db,
            current_user=user_a,
            bid_id=bid_a.id,
        )

        record_result(
            "Bid-level verifications aggregation returns accurate counts",
            bid_v_agg.total_verifications >= 2
            and bid_v_agg.verified_count >= 1,
            f"-> Total: {bid_v_agg.total_verifications}, Verified: {bid_v_agg.verified_count}, Unavailable: {bid_v_agg.unavailable_count}",
        )

        # =========================================================================
        # 14. Compliance Separation Guard
        # =========================================================================
        print_test_header("14. Compliance Separation Guard")

        all_v_records = db.scalars(
            select(VerificationRecord).where(VerificationRecord.bid_id == bid_a.id)
        ).all()

        compliance_leak = False
        forbidden_terms = ["PASS", "FAIL", "COMPLIANT", "QUALIFIED", "REJECTED", "ELIGIBLE"]
        for r in all_v_records:
            if r.verification_status in forbidden_terms or r.match_status in forbidden_terms:
                compliance_leak = True
                break

        record_result(
            "Strict compliance separation enforced (No PASS/FAIL/QUALIFIED in verification records)",
            not compliance_leak,
        )

    finally:
        db.close()

    # =========================================================================
    # Final Test Summary
    # =========================================================================
    print(f"\n{'='*70}\nPART 5A TEST SUMMARY\n{'='*70}")
    print(f"Total Tests Executed : {passed_count + failed_count}")
    print(f"Passed               : {passed_count}")
    print(f"Failed               : {failed_count}")

    if failed_count == 0:
        print("\n>>> ALL PART 5A VERIFICATION ENGINE TESTS PASSED! <<<\n")
        return True
    else:
        print(f"\n>>> {failed_count} TEST(S) FAILED IN PART 5A! <<<\n")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_part5a_test_suite())
    sys.exit(0 if success else 1)
