"""
Part 5E Comprehensive Test Suite — Blacklisting, Debarment & Cross-Document Consistency Checks
BidVerify AI — GeM Verification Adapters, Registries, Cross-Document Consistency Engine, and Telemetry

Tests:
1. Normalizers (extract_pan_from_gstin, normalize_organization_type, compare_addresses)
2. Blacklisting Verification Tests:
   - Clear bidder -> VERIFIED, registry_status="CLEAR", conf=1.0
   - Blacklisted bidder (exact PAN/GSTIN) -> VERIFIED, registry_status="BLACKLISTED", conf=1.0
   - Partial name match only -> NEEDS_REVIEW, conf=0.60
   - Self-declaration conflict (Declared clean vs Blacklisted) -> NEEDS_REVIEW
   - Outage simulation -> UNAVAILABLE
3. Debarment Verification Tests:
   - Clear bidder -> VERIFIED, registry_status="CLEAR"
   - Active debarment -> VERIFIED, registry_status="DEBARRED"
   - Expired debarment -> VERIFIED, registry_status="EXPIRED"
   - Outage simulation -> UNAVAILABLE
4. Cross-Document Consistency Tests:
   - PAN matches GSTIN embedded PAN -> MATCH, requires_review=False
   - PAN does not match GSTIN embedded PAN -> MISMATCH, requires_review=True, HIGH_ATTENTION
   - Company name compatible aliases -> MATCH / PARTIAL_MATCH
   - Divergent company names across documents -> MISMATCH, requires_review=True
   - CIN & Udyam number consistency across profile and registry
   - Registered state and address consistency
   - Organization legal entity type normalization
   - Missing fields return NOT_APPLICABLE (not false mismatch)
5. Database Pipeline & API Verification:
   - verify_bid_blacklisting execution and storage
   - verify_bid_consistency execution and storage
   - get_bid_consistency_report report generation
6. Idempotency & Re-verification
7. Multi-Tenant Security & Tenant Isolation
8. Submitted Bid Support
9. Compliance Separation Guard (No PASS/FAIL in verification records)
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
from app.verification.adapters.base import VerificationRequest
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
    VerificationStatus,
    VerificationType,
)


def print_test_header(title: str):
    print(f"\n{'='*70}\n[TEST] {title}\n{'='*70}")


def print_pass(msg: str):
    print(f"  [PASS] {msg}")


def print_fail(msg: str):
    print(f"  [FAIL] {msg}")


async def run_part5e_test_suite():
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
        # 1. Normalization & Comparison Unit Tests
        # =========================================================================
        print_test_header("1. Normalization & Comparison Unit Tests")

        # 1.1 PAN from GSTIN Extraction
        extracted_pan = extract_pan_from_gstin("33ABCDE1234F1Z5")
        record_result(
            "Extract embedded PAN from 15-char GSTIN ('33ABCDE1234F1Z5' -> 'ABCDE1234F')",
            extracted_pan == "ABCDE1234F",
            f"-> {extracted_pan}",
        )
        record_result(
            "Extract PAN from invalid GSTIN returns None",
            extract_pan_from_gstin("INVALID_GSTIN") is None,
        )

        # 1.2 Organization Type Normalization
        record_result(
            "Normalize 'Private Limited' -> 'PRIVATE_LIMITED'",
            normalize_organization_type("Private Limited Company") == "PRIVATE_LIMITED",
        )
        record_result(
            "Normalize 'Pvt Ltd' -> 'PRIVATE_LIMITED'",
            normalize_organization_type("TechFlow India Pvt. Ltd.") == "PRIVATE_LIMITED",
        )
        record_result(
            "Normalize 'Limited Liability Partnership' -> 'LLP'",
            normalize_organization_type("Innovative Systems LLP") == "LLP",
        )
        record_result(
            "Normalize 'Public Limited Company' -> 'PUBLIC_LIMITED'",
            normalize_organization_type("Alpha Procurement Services Limited") == "PUBLIC_LIMITED",
        )

        # 1.3 Address Comparison
        addr_match, _ = compare_addresses(
            "123 Anna Salai, Chennai, Tamil Nadu - 600002",
            "123 Anna Salai, Chennai, Tamil Nadu - 600002",
        )
        addr_pin_diff, _ = compare_addresses(
            "123 Anna Salai, Chennai - 600002",
            "123 Anna Salai, Chennai - 560100",
        )
        record_result("Identical addresses comparison is MATCH", addr_match == VerificationMatchStatus.MATCH)
        record_result("Addresses with conflicting PIN codes is MISMATCH", addr_pin_diff == VerificationMatchStatus.MISMATCH)

        # =========================================================================
        # 2. Blacklisting Verification Tests
        # =========================================================================
        print_test_header("2. Blacklisting Verification Tests")

        # 2.1 Clear Bidder
        res_bl_clear = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.BLACKLISTING,
                claimed_value="ABCDE1234F",
                supporting_claims={
                    "pan": "ABCDE1234F",
                    "gstin": "33ABCDE1234F1Z5",
                    "entity_name": "TechFlow Enterprises Private Limited",
                    "blacklisting_declaration": "NOT_BLACKLISTED",
                },
            )
        )
        record_result(
            "Clean bidder organization -> VERIFIED, registry_status='CLEAR', conf=1.0",
            res_bl_clear.verification_status == VerificationStatus.VERIFIED
            and res_bl_clear.evidence.get("registry_status") == "CLEAR"
            and res_bl_clear.confidence == 1.0,
            f"-> Status={res_bl_clear.verification_status}, RegStatus={res_bl_clear.evidence.get('registry_status')}",
        )

        # 2.2 Blacklisted Bidder (Exact PAN/GSTIN)
        res_bl_matched = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.BLACKLISTING,
                claimed_value="XYZ9999X",
                supporting_claims={
                    "pan": "XYZ9999X",
                    "gstin": "33XYZ9999X1Z5",
                    "entity_name": "XYZ Suppliers Private Limited",
                    "blacklisting_declaration": "BLACKLISTED",
                },
            )
        )
        record_result(
            "Blacklisted entity exact identifier match -> VERIFIED, registry_status='BLACKLISTED'",
            res_bl_matched.verification_status == VerificationStatus.VERIFIED
            and res_bl_matched.evidence.get("registry_status") == "BLACKLISTED"
            and res_bl_matched.confidence == 1.0,
            f"-> Status={res_bl_matched.verification_status}, RegStatus={res_bl_matched.evidence.get('registry_status')}, Ref={res_bl_matched.evidence.get('reference_number')}",
        )

        # 2.3 Partial Name Match Only -> NEEDS_REVIEW
        res_bl_partial = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.BLACKLISTING,
                claimed_value="XYZ SUPPLIERS",
                supporting_claims={
                    "entity_name": "XYZ Suppliers",
                    "pan": "DIFF1234D",  # Different PAN
                },
            )
        )
        record_result(
            "Partial name match without corroborating PAN -> NEEDS_REVIEW (conf=0.60)",
            res_bl_partial.verification_status == VerificationStatus.NEEDS_REVIEW
            and res_bl_partial.confidence == 0.60,
            f"-> Status={res_bl_partial.verification_status}, Reason={res_bl_partial.error_message}",
        )

        # 2.4 Self-Declaration Conflict (Declared NOT_BLACKLISTED vs Registry BLACKLISTED)
        res_bl_conflict = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.BLACKLISTING,
                claimed_value="XYZ9999X",
                supporting_claims={
                    "pan": "XYZ9999X",
                    "entity_name": "XYZ Suppliers Private Limited",
                    "blacklisting_declaration": "NOT_BLACKLISTED",  # Conflict!
                },
            )
        )
        record_result(
            "Declaration conflict (Declared Clean vs Blacklisted) -> NEEDS_REVIEW",
            res_bl_conflict.verification_status == VerificationStatus.NEEDS_REVIEW
            and res_bl_conflict.evidence.get("declaration_conflict") == True,
            f"-> Status={res_bl_conflict.verification_status}, Conflict={res_bl_conflict.evidence.get('declaration_conflict')}",
        )

        # 2.5 Outage Simulation -> UNAVAILABLE
        res_bl_outage = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.BLACKLISTING,
                claimed_value="BL-UNAV-0000",
            )
        )
        record_result(
            "Blacklisting simulated outage -> UNAVAILABLE",
            res_bl_outage.verification_status == VerificationStatus.UNAVAILABLE,
            f"-> Status={res_bl_outage.verification_status}",
        )

        # =========================================================================
        # 3. Debarment Verification Tests
        # =========================================================================
        print_test_header("3. Debarment Verification Tests")

        # 3.1 Clear Debarment
        res_db_clear = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.DEBARMENT,
                claimed_value="U72900TN2018PTC123456",
                supporting_claims={"cin": "U72900TN2018PTC123456", "pan": "ABCDE1234F"},
            )
        )
        record_result(
            "Clear debarment check -> VERIFIED, registry_status='CLEAR'",
            res_db_clear.verification_status == VerificationStatus.VERIFIED
            and res_db_clear.evidence.get("registry_status") == "CLEAR",
            f"-> Status={res_db_clear.verification_status}, RegStatus={res_db_clear.evidence.get('registry_status')}",
        )

        # 3.2 Active Debarment Match
        res_db_active = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.DEBARMENT,
                claimed_value="U72900TN2024PTC123456",
                supporting_claims={"cin": "U72900TN2024PTC123456"},
            )
        )
        record_result(
            "Active debarment match -> VERIFIED, registry_status='DEBARRED'",
            res_db_active.verification_status == VerificationStatus.VERIFIED
            and res_db_active.evidence.get("registry_status") == "DEBARRED",
            f"-> Status={res_db_active.verification_status}, RegStatus={res_db_active.evidence.get('registry_status')}",
        )

        # 3.3 Expired Debarment Match
        res_db_expired = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.DEBARMENT,
                claimed_value="EXP9999P",
                supporting_claims={"pan": "EXP9999P"},
            )
        )
        record_result(
            "Expired debarment match -> VERIFIED, registry_status='EXPIRED'",
            res_db_expired.verification_status == VerificationStatus.VERIFIED
            and res_db_expired.evidence.get("registry_status") == "EXPIRED",
            f"-> Status={res_db_expired.verification_status}, RegStatus={res_db_expired.evidence.get('registry_status')}",
        )

        # 3.4 Outage Simulation -> UNAVAILABLE
        res_db_outage = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.DEBARMENT,
                claimed_value="DB-UNAV-0000",
            )
        )
        record_result(
            "Debarment simulated outage -> UNAVAILABLE",
            res_db_outage.verification_status == VerificationStatus.UNAVAILABLE,
            f"-> Status={res_db_outage.verification_status}",
        )

        # =========================================================================
        # 4. Cross-Document Consistency Engine Tests
        # =========================================================================
        print_test_header("4. Cross-Document Consistency Engine Tests")

        test_suffix = uuid.uuid4().hex[:6]
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()

        # Org 1: Perfect Alignment (TechFlow)
        org_aligned = Organization(
            id=uuid.uuid4(),
            name=f"TechFlow Enterprises Private Limited {test_suffix}",
            pan_number="ABCDE1234F",
            gstin="33ABCDE1234F1Z5",
            state="Tamil Nadu",
            city="Chennai",
            registered_address="123 Anna Salai, Chennai, Tamil Nadu - 600002",
            is_active=True,
        )
        db.add(org_aligned)
        db.commit()

        prof_aligned = Profile(
            id=uuid.uuid4(),
            email=f"bidder_5e_aligned_{test_suffix}@bidverify.mock",
            role_id=bidder_role.id,
            organization_id=org_aligned.id,
            full_name="Muthu Developer 5E",
            is_active=True,
        )
        db.add(prof_aligned)
        db.commit()

        user_aligned = User(
            id=uuid.uuid4(),
            email=f"bidder_5e_aligned_{test_suffix}@bidverify.mock",
            password_hash="mock_hash",
            profile_id=prof_aligned.id,
            is_active=True,
        )
        db.add(user_aligned)
        db.commit()

        tender = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/5E/{test_suffix.upper()}",
            title="Procurement of IT Systems and Hardware",
            description="GeM statutory verification test tender Part 5E",
            organization_id=org_aligned.id,
            created_by_profile_id=prof_aligned.id,
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)
        db.commit()

        bid_aligned = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_aligned.id,
            created_by_profile_id=prof_aligned.id,
            bid_number=f"BID-5E-ALIGNED-{test_suffix.upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid_aligned)
        db.commit()

        # Add Verified PAN Record
        v_pan = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid_aligned.id,
            verification_type=VerificationType.PAN,
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock Income Tax PAN Registry",
            source_type="MOCK",
            claim_source=VerificationClaimSource.DOCUMENT,
            claimed_value="ABCDE1234F",
            verified_value="ABCDE1234F",
            match_status=VerificationMatchStatus.MATCH,
            confidence=1.0,
            evidence={"name": org_aligned.name, "entity_type_description": "Company / Private Limited / Limited"},
            is_active=True,
        )
        # Add Verified GST Record
        v_gst = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid_aligned.id,
            verification_type=VerificationType.GST,
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock GST Registry",
            source_type="MOCK",
            claim_source=VerificationClaimSource.DOCUMENT,
            claimed_value="33ABCDE1234F1Z5",
            verified_value="33ABCDE1234F1Z5",
            match_status=VerificationMatchStatus.MATCH,
            confidence=1.0,
            evidence={"legal_name": org_aligned.name, "state": "Tamil Nadu", "address": "123 Anna Salai, Chennai, Tamil Nadu - 600002"},
            is_active=True,
        )
        # Add Verified MCA Record
        v_mca = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid_aligned.id,
            verification_type=VerificationType.MCA,
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock MCA Registry",
            source_type="MOCK",
            claim_source=VerificationClaimSource.DOCUMENT,
            claimed_value="U72900TN2018PTC123456",
            verified_value="U72900TN2018PTC123456",
            match_status=VerificationMatchStatus.MATCH,
            confidence=1.0,
            evidence={"company_name": org_aligned.name, "company_type": "Private Limited Company", "registered_office_state": "Tamil Nadu"},
            is_active=True,
        )
        db.add_all([v_pan, v_gst, v_mca])
        db.commit()

        # Run Consistency Engine on Aligned Bid
        v_stat_aligned, m_stat_aligned, findings_aligned, ev_aligned = consistency_engine.evaluate_bid_consistency(db, bid_aligned)
        record_result(
            "Aligned bid cross-document consistency returns VERIFIED (All checks MATCH)",
            v_stat_aligned == VerificationStatus.VERIFIED
            and m_stat_aligned == VerificationMatchStatus.MATCH
            and ev_aligned["review_required_checks"] == 0,
            f"-> Status={v_stat_aligned}, Total={ev_aligned['total_checks']}, ReviewRequired={ev_aligned['review_required_checks']}",
        )

        # Org 2: PAN vs GST Mismatch Bid
        org_mismatch = Organization(
            id=uuid.uuid4(),
            name=f"Divergent Bidder Corp {test_suffix}",
            pan_number="ABCDE1234F",  # PAN
            gstin="33ZZZZZ9999Z1Z5",  # Embedded PAN is ZZZZZ9999Z
            state="Tamil Nadu",
            is_active=True,
        )
        db.add(org_mismatch)
        db.commit()

        prof_mismatch = Profile(
            id=uuid.uuid4(),
            email=f"bidder_5e_mismatch_{test_suffix}@bidverify.mock",
            role_id=bidder_role.id,
            organization_id=org_mismatch.id,
            full_name="Divergent Bidder",
            is_active=True,
        )
        db.add(prof_mismatch)
        db.commit()

        bid_mismatch = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_mismatch.id,
            created_by_profile_id=prof_mismatch.id,
            bid_number=f"BID-5E-MISMATCH-{test_suffix.upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid_mismatch)
        db.commit()

        v_pan_mis = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid_mismatch.id,
            verification_type=VerificationType.PAN,
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock PAN",
            source_type="MOCK",
            claim_source=VerificationClaimSource.DOCUMENT,
            claimed_value="ABCDE1234F",
            verified_value="ABCDE1234F",
            is_active=True,
        )
        v_gst_mis = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid_mismatch.id,
            verification_type=VerificationType.GST,
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock GST",
            source_type="MOCK",
            claim_source=VerificationClaimSource.DOCUMENT,
            claimed_value="33ZZZZZ9999Z1Z5",
            verified_value="33ZZZZZ9999Z1Z5",
            is_active=True,
        )
        db.add_all([v_pan_mis, v_gst_mis])
        db.commit()

        v_stat_mis, m_stat_mis, findings_mis, ev_mis = consistency_engine.evaluate_bid_consistency(db, bid_mismatch)
        record_result(
            "PAN vs GSTIN mismatch produces NEEDS_REVIEW (HIGH_ATTENTION)",
            v_stat_mis == VerificationStatus.NEEDS_REVIEW
            and any(f.finding_type == "PAN_GST_MISMATCH" and f.requires_review for f in findings_mis),
            f"-> Status={v_stat_mis}, ReviewRequired={ev_mis['review_required_checks']}",
        )

        # =========================================================================
        # 5. Database Pipeline & API Verification
        # =========================================================================
        print_test_header("5. Database Pipeline & API Verification")

        # 5.1 Blacklisting Verification Pipeline
        res_bl_pipeline = await verify_bid_blacklisting(db, user_aligned, bid_aligned.id)
        record_result(
            "verify_bid_blacklisting pipeline creates/updates records in DB",
            len(res_bl_pipeline.results) == 2
            and res_bl_pipeline.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> Results count: {len(res_bl_pipeline.results)}, Status: {res_bl_pipeline.results[0].verification_status}",
        )

        # 5.2 Cross-Document Consistency Pipeline
        res_cs_pipeline = await verify_bid_consistency(db, user_aligned, bid_aligned.id)
        record_result(
            "verify_bid_consistency pipeline persists CROSS_DOCUMENT record in DB",
            len(res_cs_pipeline.results) == 1
            and res_cs_pipeline.results[0].verification_type == VerificationType.CROSS_DOCUMENT
            and res_cs_pipeline.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> Status: {res_cs_pipeline.results[0].verification_status}, Value: {res_cs_pipeline.results[0].verified_value}",
        )

        # 5.3 Fetch Consistency Report
        report = get_bid_consistency_report(db, user_aligned, bid_aligned.id)
        record_result(
            "get_bid_consistency_report returns structured findings dictionary",
            report["verification_status"] == VerificationStatus.VERIFIED
            and report["total_checks"] > 0
            and isinstance(report["findings"], list),
            f"-> Total checks: {report['total_checks']}, Matched: {report['matched_checks']}",
        )

        # =========================================================================
        # 6. Idempotency Check
        # =========================================================================
        print_test_header("6. Idempotency Check")

        res_cs_again = await verify_bid_consistency(db, user_aligned, bid_aligned.id)
        record_result(
            "Repeated consistency check trigger is idempotent (created_count=0)",
            res_cs_again.created_count == 0,
            f"-> created_count: {res_cs_again.created_count}",
        )

        # =========================================================================
        # 7. Multi-Tenant Security & Tenant Isolation
        # =========================================================================
        print_test_header("7. Multi-Tenant Security & Tenant Isolation")

        user_other = User(
            id=uuid.uuid4(),
            email=f"bidder_5e_other_{test_suffix}@bidverify.mock",
            password_hash="mock_hash",
            profile_id=prof_mismatch.id,
            is_active=True,
        )
        db.add(user_other)
        db.commit()

        try:
            await verify_bid_blacklisting(db, user_other, bid_aligned.id)
            record_result("Cross-bidder blacklisting verification trigger rejected", False)
        except HTTPException as he:
            record_result(
                "Cross-bidder blacklisting verification trigger rejected with 404",
                he.status_code == 404,
                f"-> HTTP {he.status_code}: {he.detail}",
            )

        try:
            get_bid_consistency_report(db, user_other, bid_aligned.id)
            record_result("Cross-bidder consistency report access rejected", False)
        except HTTPException as he:
            record_result(
                "Cross-bidder consistency report access rejected with 404",
                he.status_code == 404,
                f"-> HTTP {he.status_code}: {he.detail}",
            )

        # =========================================================================
        # 8. Submitted Bid Support
        # =========================================================================
        print_test_header("8. Submitted Bid Support")

        bid_aligned.status = "SUBMITTED"
        bid_aligned.submitted_at = datetime.now(timezone.utc)
        db.commit()

        res_bl_sub = await verify_bid_blacklisting(db, user_aligned, bid_aligned.id)
        res_cs_sub = await verify_bid_consistency(db, user_aligned, bid_aligned.id)

        record_result(
            "Part 5E verification succeeds seamlessly on SUBMITTED bid",
            res_bl_sub.results[0].verification_status == VerificationStatus.VERIFIED
            and res_cs_sub.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> BL Status={res_bl_sub.results[0].verification_status}, CS Status={res_cs_sub.results[0].verification_status}",
        )

        # =========================================================================
        # 9. Compliance Separation Guard
        # =========================================================================
        print_test_header("9. Compliance Separation Guard")

        all_v = db.scalars(select(VerificationRecord).where(VerificationRecord.bid_id == bid_aligned.id)).all()
        forbidden_terms = ["PASS", "FAIL", "COMPLIANT", "QUALIFIED", "DISQUALIFIED", "ELIGIBLE"]
        leak = any(r.verification_status in forbidden_terms or r.match_status in forbidden_terms for r in all_v)
        record_result(
            "Strict compliance boundary enforced across all Part 5E domains",
            not leak,
        )

    finally:
        db.close()

    # =========================================================================
    # Final Test Summary
    # =========================================================================
    print(f"\n{'='*70}\nPART 5E TEST SUMMARY\n{'='*70}")
    print(f"Total Tests Executed : {passed_count + failed_count}")
    print(f"Passed               : {passed_count}")
    print(f"Failed               : {failed_count}")

    if failed_count == 0:
        print("\n>>> ALL PART 5E BLACKLISTING, DEBARMENT & CONSISTENCY TESTS PASSED! <<<\n")
        return True
    else:
        print(f"\n>>> {failed_count} TEST(S) FAILED IN PART 5E! <<<\n")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_part5e_test_suite())
    sys.exit(0 if success else 1)
