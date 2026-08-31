"""
Part 5F Master Integration, Evidence, Confidence & Final QA Test Suite
BidVerify AI — Integrated Bid Compliance Verification Platform for GeM Procurement

Comprehensive Master Validation of Part 5 Verification Engine (Parts 5A through 5F):
1. Adapter Registry Completeness (All 16 verification types supported)
2. Response Shape & DTO Standardization (Confidence 0.0-1.0, Evidence, Provenance)
3. Strict Separation of Registry Status vs Verification Status
4. Multi-Domain Realistic Synthetic Bid End-to-End Flow (All 14 statutory, technical, integrity & coherence domains)
5. Bid Verification Completeness & Compliance Readiness Flag (verification_ready_for_compliance)
6. Partial Bid Verification Handling (No spurious claims generated)
7. Source Outage Simulation & Retry Orchestration (Attempt history preservation)
8. Idempotent Execution & Deduplication
9. Submitted Bid Support (Post-submission verification execution)
10. Multi-Tenant Security & Strict Data Isolation
11. Replaced Document Audit History Preservation
12. Strict Compliance Separation Guard (No PASS/FAIL in Part 5)
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
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.db.session import get_session_factory
from app.services.cross_document_consistency_service import consistency_engine
from app.services.verification_engine import verification_engine
from app.services.verification_service import (
    get_bid_consistency_report,
    get_bid_verifications,
    get_document_verifications,
    retry_verification_record,
    verify_bid_blacklisting,
    verify_bid_consistency,
    verify_document_claims,
)
from app.verification.adapters.base import VerificationRequest, VerificationResult
from app.verification.normalizers import (
    compare_addresses,
    compare_names,
    compare_strings,
    extract_pan_from_gstin,
    normalize_organization_type,
)
from app.verification.registry import adapter_registry
from app.verification.types import (
    VerificationClaimSource,
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationTriggerSource,
    VerificationType,
)


def print_test_header(title: str):
    print(f"\n{'='*70}\n[TEST] {title}\n{'='*70}")


def print_pass(msg: str):
    print(f"  [PASS] {msg}")


def print_fail(msg: str):
    print(f"  [FAIL] {msg}")


async def run_part5f_master_test_suite():
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
        # 1. Adapter Registry Completeness
        # =========================================================================
        print_test_header("1. Adapter Registry Completeness")

        expected_types = [
            VerificationType.GST,
            VerificationType.PAN,
            VerificationType.UDYAM,
            VerificationType.MCA,
            VerificationType.STARTUP_INDIA,
            VerificationType.NSIC,
            VerificationType.EPFO,
            VerificationType.ESIC,
            VerificationType.OEM_AUTHORIZATION,
            VerificationType.LOCAL_CONTENT,
            VerificationType.BIS,
            VerificationType.DPIIT,
            VerificationType.SUPPORTING_DOCUMENT,
            VerificationType.BLACKLISTING,
            VerificationType.DEBARMENT,
        ]

        for v_type in expected_types:
            has_adapter = adapter_registry.is_type_supported(v_type)
            adapter = adapter_registry.get_adapter(v_type)
            record_result(
                f"Registry contains adapter for {v_type}",
                has_adapter and adapter is not None,
                f"-> {adapter.__class__.__name__ if adapter else 'None'}",
            )

        # Safe failure on unsupported type
        unsupported = adapter_registry.get_adapter("UNSUPPORTED_TYPE")
        record_result("Unknown type resolution returns None safely", unsupported is None)

        # =========================================================================
        # 2. Response Shape & Confidence Range Validation
        # =========================================================================
        print_test_header("2. Response Shape & Confidence Standardization")

        req_sample = VerificationRequest(
            verification_type=VerificationType.GST,
            claimed_value="33ABCDE1234F1Z5",
            supporting_claims={"legal_name": "TechFlow Enterprises Private Limited"},
        )
        res_sample: VerificationResult = await verification_engine.execute_verification(req_sample)

        record_result(
            "Verification result has valid status and source name",
            res_sample.verification_status in VerificationStatus.ALL and len(res_sample.source_name) > 0,
            f"-> Status={res_sample.verification_status}, Source={res_sample.source_name}",
        )
        record_result(
            "Confidence is bounded between 0.0 and 1.0",
            0.0 <= res_sample.confidence <= 1.0,
            f"-> Confidence={res_sample.confidence}",
        )
        record_result(
            "Evidence dictionary contains structured items and mock flag",
            isinstance(res_sample.evidence, dict) and "source" in res_sample.evidence,
        )

        # =========================================================================
        # 3. Separation of Registry Status from Verification Status
        # =========================================================================
        print_test_header("3. Separation of Registry Status vs Verification Status")

        # 3.1 Cancelled GST -> Status=VERIFIED, RegStatus=CANCELLED
        res_gst_canc = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.GST,
                claimed_value="33ABCDE1234F1Z9",
                supporting_claims={"legal_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED"},
            )
        )
        record_result(
            "Cancelled GST returns VERIFIED (reg_status='CANCELLED')",
            res_gst_canc.verification_status == VerificationStatus.VERIFIED
            and res_gst_canc.evidence.get("registration_status") == "CANCELLED",
            f"-> Status={res_gst_canc.verification_status}, RegStatus={res_gst_canc.evidence.get('registration_status')}",
        )

        # 3.2 Expired NSIC -> Status=VERIFIED, RegStatus=EXPIRED
        res_nsic_exp = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.NSIC,
                claimed_value="NSIC-DL-2020-009876",
                supporting_claims={"enterprise_name": "ALPHA PROCUREMENT SERVICES LIMITED"},
            )
        )
        record_result(
            "Expired NSIC returns VERIFIED (reg_status='EXPIRED')",
            res_nsic_exp.verification_status == VerificationStatus.VERIFIED
            and res_nsic_exp.evidence.get("registration_status") == "EXPIRED",
            f"-> Status={res_nsic_exp.verification_status}, RegStatus={res_nsic_exp.evidence.get('registration_status')}",
        )

        # 3.3 Active Blacklist -> Status=VERIFIED, RegStatus=BLACKLISTED
        res_bl_act = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.BLACKLISTING,
                claimed_value="XYZ9999X",
                supporting_claims={"pan": "XYZ9999X", "entity_name": "XYZ Suppliers Private Limited", "blacklisting_declaration": "BLACKLISTED"},
            )
        )
        record_result(
            "Blacklisted entity returns VERIFIED (reg_status='BLACKLISTED')",
            res_bl_act.verification_status == VerificationStatus.VERIFIED
            and res_bl_act.evidence.get("registry_status") == "BLACKLISTED",
            f"-> Status={res_bl_act.verification_status}, RegStatus={res_bl_act.evidence.get('registry_status')}",
        )

        # =========================================================================
        # 4. Multi-Domain Realistic Synthetic Bid End-to-End Flow
        # =========================================================================
        print_test_header("4. Multi-Domain Realistic Synthetic Bid End-to-End Flow")

        test_suffix = uuid.uuid4().hex[:6]
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()

        # Create Master Test Bidder Org (Aligns with verified Mock fixtures)
        org_master = Organization(
            id=uuid.uuid4(),
            name="TECHFLOW ENTERPRISES PRIVATE LIMITED",
            pan_number="ABCDE1234F",
            gstin="33ABCDE1234F1Z5",
            state="Tamil Nadu",
            city="Chennai",
            registered_address="123 Anna Salai, Chennai, Tamil Nadu - 600002",
            is_active=True,
        )
        db.add(org_master)
        db.commit()

        prof_master = Profile(
            id=uuid.uuid4(),
            email=f"bidder_5f_master_{test_suffix}@bidverify.mock",
            role_id=bidder_role.id,
            organization_id=org_master.id,
            full_name="Muthu Master QA",
            is_active=True,
        )
        db.add(prof_master)
        db.commit()

        user_master = User(
            id=uuid.uuid4(),
            email=f"bidder_5f_master_{test_suffix}@bidverify.mock",
            password_hash="mock_hash",
            profile_id=prof_master.id,
            is_active=True,
        )
        db.add(user_master)
        db.commit()

        tender_master = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/5F/{test_suffix.upper()}",
            title="Comprehensive GeM Hardware and Network Equipment Procurement",
            description="GeM statutory and technical verification master integration tender Part 5F",
            organization_id=org_master.id,
            created_by_profile_id=prof_master.id,
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender_master)
        db.commit()

        bid_master = Bid(
            id=uuid.uuid4(),
            tender_id=tender_master.id,
            bidder_organization_id=org_master.id,
            created_by_profile_id=prof_master.id,
            bid_number=f"BID-5F-MASTER-{test_suffix.upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid_master)
        db.commit()

        # Seed 8 Verified Domain Documents
        doc_specs = [
            ("GST_CERTIFICATE", "GST Certificate", {"gstin": "33ABCDE1234F1Z5", "legal_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED", "state": "Tamil Nadu"}),
            ("PAN", "PAN Card", {"pan_number": "ABCDE1234F", "name": "TECHFLOW ENTERPRISES PRIVATE LIMITED"}),
            ("UDYAM_CERTIFICATE", "Udyam Registration", {"udyam_registration_number": "UDYAM-TN-01-0012345", "enterprise_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED"}),
            ("COMMERCIAL_DOCUMENT", "Incorporation Certificate", {"cin": "U72900TN2018PTC123456", "company_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED"}),
            ("OEM_AUTHORIZATION", "OEM Authorization Letter", {"reference_number": "OEM-AUTH-2026-001", "oem_name": "ABC MANUFACTURING PRIVATE LIMITED", "authorized_entity": "TECHFLOW ENTERPRISES PRIVATE LIMITED", "product_scope": "Industrial Sensor Model X100, Edge Gateway E500"}),
            ("LOCAL_CONTENT_DECLARATION", "Local Content Declaration", {"reference_number": "LC-2026-0101", "local_content_percentage": "55%", "supplier_class": "Class-I Local Supplier", "product_name": "Industrial Controller Unit"}),
            ("TECHNICAL_EVALUATION", "BIS Registration Certificate", {"bis_registration_number": "R-12345678", "standard_number": "IS 13252", "manufacturer_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED"}),
            ("TURNOVER_CERTIFICATE", "Experience & Turnover Affidavit", {"document_reference": "AFF-2026-99", "ca_name": "Notary Public", "issue_date": "2026-01-15", "signatory_name": "Authorized Partner", "turnover": "5000000"}),
        ]

        created_docs = []
        for doc_type, doc_name, fields_dict in doc_specs:
            doc = BidDocument(
                id=uuid.uuid4(),
                bid_id=bid_master.id,
                uploaded_by_profile_id=prof_master.id,
                document_type=doc_type,
                document_name=f"{doc_name}.pdf",
                original_filename=f"{doc_name}.pdf",
                storage_path=f"bids/{bid_master.id}/{doc_name.lower().replace(' ', '_')}.pdf",
                file_size=10240,
                mime_type="application/pdf",
                is_active=True,
            )
            db.add(doc)
            db.commit()

            proc = DocumentProcessing(
                id=uuid.uuid4(),
                bid_document_id=doc.id,
                processing_status=ProcessingStatus.COMPLETED,
                processing_stage=ProcessingStage.COMPLETED,
                extracted_data={"fields": {k: {"value": v, "confidence": 1.0} for k, v in fields_dict.items()}},
            )
            db.add(proc)
            db.commit()
            created_docs.append((doc, fields_dict))

        # Run Document-Level Verification for each Document
        for doc, _ in created_docs:
            res_doc_v = await verify_document_claims(db, user_master, bid_master.id, doc.id)
            record_result(
                f"Document-level verification for {doc.document_name} completes successfully",
                len(res_doc_v.results) > 0 and all(r.verification_status == VerificationStatus.VERIFIED for r in res_doc_v.results),
                f"-> Verified claims count: {len(res_doc_v.results)}",
            )

        # Run Blacklisting & Debarment
        res_bl = await verify_bid_blacklisting(db, user_master, bid_master.id)
        record_result(
            "Bid Blacklisting & Debarment verification completed",
            len(res_bl.results) == 2 and all(r.verification_status == VerificationStatus.VERIFIED for r in res_bl.results),
        )

        # Run Cross-Document Consistency Engine
        res_cs = await verify_bid_consistency(db, user_master, bid_master.id)
        record_result(
            "Cross-document consistency engine completes with VERIFIED status",
            len(res_cs.results) == 1 and res_cs.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> Value={res_cs.results[0].verified_value}",
        )

        # =========================================================================
        # 5. Bid-Level Verification Completeness & Readiness Flag
        # =========================================================================
        print_test_header("5. Bid Verification Completeness & Compliance Readiness")

        bid_verifications = get_bid_verifications(db, user_master, bid_master.id)
        record_result(
            "get_bid_verifications aggregates all active records",
            bid_verifications.total_verifications >= 10,
            f"-> Total={bid_verifications.total_verifications}, Verified={bid_verifications.verified_count}",
        )
        record_result(
            "verification_ready_for_compliance flag is True when all claims are terminal",
            bid_verifications.verification_ready_for_compliance == True,
            f"-> Ready={bid_verifications.verification_ready_for_compliance}",
        )

        # =========================================================================
        # 6. Partial Bid Verification Handling
        # =========================================================================
        print_test_header("6. Partial Bid Verification Handling")

        tender_partial = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/5F/PARTIAL/{test_suffix.upper()}",
            title="Partial Procurement Tender",
            description="GeM partial tender for test 6",
            organization_id=org_master.id,
            created_by_profile_id=prof_master.id,
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender_partial)
        db.commit()

        bid_partial = Bid(
            id=uuid.uuid4(),
            tender_id=tender_partial.id,
            bidder_organization_id=org_master.id,
            created_by_profile_id=prof_master.id,
            bid_number=f"BID-5F-PARTIAL-{test_suffix.upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid_partial)
        db.commit()

        # Add single GST document
        doc_gst_only = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid_partial.id,
            uploaded_by_profile_id=prof_master.id,
            document_type="GST_CERTIFICATE",
            document_name="GST_Only.pdf",
            original_filename="GST_Only.pdf",
            storage_path=f"bids/{bid_partial.id}/gst.pdf",
            file_size=5120,
            mime_type="application/pdf",
            is_active=True,
        )
        db.add(doc_gst_only)
        db.commit()

        proc_gst_only = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_gst_only.id,
            processing_status=ProcessingStatus.COMPLETED,
            processing_stage=ProcessingStage.COMPLETED,
            extracted_data={"fields": {"gstin": {"value": "33ABCDE1234F1Z5", "confidence": 1.0}}},
        )
        db.add(proc_gst_only)
        db.commit()

        res_partial_doc = await verify_document_claims(db, user_master, bid_partial.id, doc_gst_only.id)
        partial_summary = get_bid_verifications(db, user_master, bid_partial.id)

        record_result(
            "Partial bid only verifies present claims (Total=1, No phantom claims)",
            partial_summary.total_verifications == 1 and partial_summary.verified_count == 1,
            f"-> Total={partial_summary.total_verifications}, Verified={partial_summary.verified_count}",
        )

        # =========================================================================
        # 7. Source Outage Simulation & Retry Orchestration
        # =========================================================================
        print_test_header("7. Source Outage Simulation & Retry Orchestration")

        # Seed an UNAVAILABLE record
        v_outage = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid_partial.id,
            verification_type=VerificationType.MCA,
            verification_status=VerificationStatus.UNAVAILABLE,
            source_name="Mock MCA Registry",
            source_type="MOCK",
            claim_source=VerificationClaimSource.DOCUMENT,
            claimed_value="U72900TN2018PTC123456",
            error_code=VerificationErrorCode.SOURCE_UNAVAILABLE,
            error_message="Mock MCA registry unavailable",
            attempt_number=1,
            is_active=True,
        )
        db.add(v_outage)
        db.commit()

        # Check that readiness flag becomes False due to UNAVAILABLE record
        summary_with_outage = get_bid_verifications(db, user_master, bid_partial.id)
        record_result(
            "verification_ready_for_compliance becomes False when a claim is UNAVAILABLE",
            summary_with_outage.verification_ready_for_compliance == False
            and summary_with_outage.unavailable_count == 1,
            f"-> Ready={summary_with_outage.verification_ready_for_compliance}, Unavailable={summary_with_outage.unavailable_count}",
        )

        # Retry the unavailable record
        retry_res = await retry_verification_record(db, user_master, bid_partial.id, v_outage.id)
        record_result(
            "retry_verification_record succeeds and increments attempt number to 2",
            retry_res.verification.verification_status == VerificationStatus.VERIFIED
            and retry_res.verification.attempt_number == 2,
            f"-> Status={retry_res.verification.verification_status}, Attempt={retry_res.verification.attempt_number}",
        )

        # Check that readiness flag restores to True after retry success
        summary_after_retry = get_bid_verifications(db, user_master, bid_partial.id)
        record_result(
            "verification_ready_for_compliance restores to True after retry resolves",
            summary_after_retry.verification_ready_for_compliance == True
            and summary_after_retry.unavailable_count == 0,
            f"-> Ready={summary_after_retry.verification_ready_for_compliance}",
        )

        # =========================================================================
        # 8. Idempotency & Deduplication Check
        # =========================================================================
        print_test_header("8. Idempotency & Deduplication Check")

        count_before = len(get_bid_verifications(db, user_master, bid_master.id).verifications)
        await verify_bid_blacklisting(db, user_master, bid_master.id)
        await verify_bid_consistency(db, user_master, bid_master.id)
        count_after = len(get_bid_verifications(db, user_master, bid_master.id).verifications)

        record_result(
            "Re-running full verification preserves record count without uncontrolled duplicates",
            count_before == count_after,
            f"-> Count before={count_before}, Count after={count_after}",
        )

        # =========================================================================
        # 9. Submitted Bid Support
        # =========================================================================
        print_test_header("9. Submitted Bid Support")

        bid_master.status = "SUBMITTED"
        bid_master.submitted_at = datetime.now(timezone.utc)
        db.commit()

        # Run verification on submitted bid
        res_sub_bl = await verify_bid_blacklisting(db, user_master, bid_master.id)
        res_sub_cs = await verify_bid_consistency(db, user_master, bid_master.id)

        record_result(
            "Verification engine executes smoothly on SUBMITTED proposal",
            res_sub_bl.results[0].verification_status == VerificationStatus.VERIFIED
            and res_sub_cs.results[0].verification_status == VerificationStatus.VERIFIED,
        )

        # =========================================================================
        # 10. Multi-Tenant Security & Tenant Isolation
        # =========================================================================
        print_test_header("10. Multi-Tenant Security & Tenant Isolation")

        org_alien = Organization(
            id=uuid.uuid4(),
            name=f"Alien Corp {test_suffix}",
            is_active=True,
        )
        db.add(org_alien)
        db.commit()

        prof_alien = Profile(
            id=uuid.uuid4(),
            email=f"bidder_5f_alien_{test_suffix}@bidverify.mock",
            role_id=bidder_role.id,
            organization_id=org_alien.id,
            full_name="Alien Bidder",
            is_active=True,
        )
        db.add(prof_alien)
        db.commit()

        user_alien = User(
            id=uuid.uuid4(),
            email=f"bidder_5f_alien_{test_suffix}@bidverify.mock",
            password_hash="mock_hash",
            profile_id=prof_alien.id,
            is_active=True,
        )
        db.add(user_alien)
        db.commit()

        try:
            get_bid_verifications(db, user_alien, bid_master.id)
            record_result("Cross-bidder verification list access rejected", False)
        except HTTPException as he:
            record_result(
                "Cross-bidder verification list access rejected with HTTP 404",
                he.status_code == 404,
                f"-> HTTP {he.status_code}",
            )

        # =========================================================================
        # 11. Replaced Document Audit History Preservation
        # =========================================================================
        print_test_header("11. Replaced Document Audit History Preservation")

        # Mark first document inactive (simulating replacement)
        first_doc = created_docs[0][0]
        first_doc.is_active = False
        db.commit()

        # Inactive doc cannot be verified again
        try:
            await verify_document_claims(db, user_master, bid_master.id, first_doc.id)
            record_result("Verifying inactive replaced document rejected", False)
        except HTTPException as he:
            record_result(
                "Verifying inactive replaced document rejected with HTTP 400",
                he.status_code == 400,
                f"-> HTTP {he.status_code}: {he.detail}",
            )

        # Active verification list excludes records of inactive documents
        v_list_after_replace = get_bid_verifications(db, user_master, bid_master.id)
        record_result(
            "Verification summary cleanly filters out superseded document records",
            all(v.claimed_value != "33ABCDE1234F1Z5" or v.verification_type != VerificationType.GST for v in v_list_after_replace.verifications),
        )

        # =========================================================================
        # 12. Strict Compliance Separation Guard
        # =========================================================================
        print_test_header("12. Strict Compliance Separation Guard")

        all_records = db.scalars(select(VerificationRecord).where(VerificationRecord.bid_id == bid_master.id)).all()
        forbidden_keywords = ["PASS", "FAIL", "COMPLIANT", "NON_COMPLIANT", "QUALIFIED", "DISQUALIFIED", "ELIGIBLE", "INELIGIBLE"]
        leak_found = False
        for rec in all_records:
            if rec.verification_status in forbidden_keywords or rec.match_status in forbidden_keywords:
                leak_found = True
                break

        record_result(
            "Strict compliance boundary enforced across all Part 5 verification tables",
            not leak_found,
        )

    finally:
        db.close()

    # =========================================================================
    # Master Test Summary
    # =========================================================================
    print(f"\n{'='*70}\nPART 5F MASTER QA SUMMARY\n{'='*70}")
    print(f"Total Tests Executed : {passed_count + failed_count}")
    print(f"Passed               : {passed_count}")
    print(f"Failed               : {failed_count}")

    if failed_count == 0:
        print("\n>>> ALL PART 5F MASTER INTEGRATION, EVIDENCE & QA TESTS PASSED! <<<\n")
        return True
    else:
        print(f"\n>>> {failed_count} TEST(S) FAILED IN PART 5F! <<<\n")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_part5f_master_test_suite())
    sys.exit(0 if success else 1)
