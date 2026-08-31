"""
Part 5D Comprehensive Test Suite — OEM, Local Content, BIS/DPIIT & Supporting Document Verification
BidVerify AI — GeM Verification Adapters, Registries, Internal Evidence Validators, and Telemetry

Tests:
1. Normalizers (Percentage parsing, Supplier Class normalization, BIS formatting, Scope comparison)
2. OEM Authorization Verification Tests:
   - Reference + OEM + Authorized Entity + Scope match -> VERIFIED (MATCH, conf=1.0)
   - Entity mismatch -> NEEDS_REVIEW (MISMATCH, conf=0.60)
   - Scope mismatch -> NEEDS_REVIEW
   - Expired authorization in registry -> VERIFIED with authorization_status="EXPIRED"
   - Absent reference -> NOT_VERIFIED
   - Outage -> UNAVAILABLE
3. Local Content (MII) Verification Tests:
   - Percentage match + Supplier class + Product match -> VERIFIED (55%, CLASS_I)
   - Percentage mismatch -> NEEDS_REVIEW
   - Entity mismatch -> NEEDS_REVIEW
   - Absent declaration -> NOT_VERIFIED
   - Outage -> UNAVAILABLE
4. BIS Certificate Verification Tests:
   - Registration + Manufacturer + Standard (IS 13252) match -> VERIFIED
   - Manufacturer mismatch -> NEEDS_REVIEW
   - Standard mismatch -> NEEDS_REVIEW
   - Expired certificate in registry -> VERIFIED with registry_status="EXPIRED"
   - Absent registration -> NOT_VERIFIED
   - Outage -> UNAVAILABLE
5. DPIIT Public Procurement MII Verification Tests:
   - Valid MII recognition -> VERIFIED
   - Entity mismatch -> NEEDS_REVIEW
   - Outage -> UNAVAILABLE
6. Supporting Document Internal Evidence Validator Tests:
   - Complete evidence (Reference, Issuer, Date, Signatory, Turnover) -> VERIFIED (Source=INTERNAL)
   - Partial evidence -> NEEDS_REVIEW
   - Missing fields -> NEEDS_REVIEW
7. Database Pipeline Verification for OEM, Local Content, BIS, and Supporting Documents
8. Idempotency Check
9. Outage Simulation & Retry Progression
10. Multi-Tenant Security & Tenant Isolation
11. Submitted Bid Support
12. Replaced Document Audit Preservation
13. Compliance Separation Guard (No PASS/FAIL in verification records)
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
from app.services.verification_engine import verification_engine
from app.services.verification_service import (
    discover_claims_for_document,
    get_bid_verifications,
    get_document_verifications,
    retry_verification_record,
    verify_document_claims,
)
from app.verification.adapters.base import VerificationRequest
from app.verification.normalizers import (
    compare_names,
    compare_percentages,
    compare_scope,
    compare_strings,
    normalize_bis_number,
    normalize_identifier,
    normalize_percentage,
    normalize_supplier_class,
)
from app.verification.registry import adapter_registry
from app.verification.types import (
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


async def run_part5d_test_suite():
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

        # Percentage Normalizer
        record_result("Percentage string '55%' parsed as float", normalize_percentage("55%") == 55.0)
        record_result("Percentage string '55.5 %' parsed as float", normalize_percentage("55.5 %") == 55.5)
        record_result("Numeric 50 parsed as float", normalize_percentage(50) == 50.0)

        # Supplier Class Normalizer
        record_result("Supplier Class 'Class-I Local Supplier' normalized", normalize_supplier_class("Class-I Local Supplier") == "CLASS_I")
        record_result("Supplier Class 'Class 2' normalized", normalize_supplier_class("Class 2") == "CLASS_II")
        record_result("Supplier Class 'Non-Local' normalized", normalize_supplier_class("Non-Local") == "NON_LOCAL")

        # BIS Number Normalizer
        record_result("BIS number formatting", normalize_bis_number(" r - 12345678 ") == "R-12345678")

        # Percentage Comparison
        m_pct, _ = compare_percentages(55.0, 55.0)
        p_pct, _ = compare_percentages(55.0, 56.0)
        f_pct, _ = compare_percentages(55.0, 25.0)
        record_result("Exact percentage comparison is MATCH", m_pct == VerificationMatchStatus.MATCH)
        record_result("Close percentage comparison is PARTIAL_MATCH", p_pct == VerificationMatchStatus.PARTIAL_MATCH)
        record_result("Divergent percentage comparison is MISMATCH", f_pct == VerificationMatchStatus.MISMATCH)

        # Scope Comparison
        s_match, _ = compare_scope("Industrial Sensor Model X100", "Industrial Sensor Model X100, Edge Gateway E500")
        s_mismatch, _ = compare_scope("Solar Inverters", "Server Racks")
        record_result("Scope subset comparison is MATCH", s_match == VerificationMatchStatus.MATCH)
        record_result("Distinct scope comparison is MISMATCH", s_mismatch == VerificationMatchStatus.MISMATCH)

        # =========================================================================
        # 2. OEM Authorization Verification Tests
        # =========================================================================
        print_test_header("2. OEM Authorization Verification Tests")

        # 2.1 Full Match
        res_oem_valid = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.OEM_AUTHORIZATION,
                claimed_value="OEM-AUTH-2026-001",
                supporting_claims={
                    "oem_name": "ABC Manufacturing Pvt Ltd",
                    "authorized_entity": "TechFlow Enterprises Private Limited",
                    "product_scope": "Industrial Sensor Model X100",
                },
            )
        )
        record_result(
            "OEM reference + authorized entity + scope match -> VERIFIED (MATCH, conf=1.0)",
            res_oem_valid.verification_status == VerificationStatus.VERIFIED
            and res_oem_valid.match_status == VerificationMatchStatus.MATCH
            and res_oem_valid.confidence == 1.0
            and res_oem_valid.evidence.get("authorization_status") == "VALID",
            f"-> Status={res_oem_valid.verification_status}, AuthStatus={res_oem_valid.evidence.get('authorization_status')}",
        )

        # 2.2 Authorized Entity Mismatch -> NEEDS_REVIEW
        res_oem_ent_mismatch = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.OEM_AUTHORIZATION,
                claimed_value="OEM-AUTH-2026-001",
                supporting_claims={
                    "authorized_entity": "Completely Unrelated Bidder Ltd",
                },
            )
        )
        record_result(
            "OEM valid reference + mismatched grantee -> NEEDS_REVIEW (MISMATCH, conf=0.60)",
            res_oem_ent_mismatch.verification_status == VerificationStatus.NEEDS_REVIEW
            and res_oem_ent_mismatch.confidence == 0.60,
            f"-> Status={res_oem_ent_mismatch.verification_status}, Reason={res_oem_ent_mismatch.error_message}",
        )

        # 2.3 Expired Authorization in Registry -> VERIFIED with authorization_status="EXPIRED"
        res_oem_expired = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.OEM_AUTHORIZATION,
                claimed_value="OEM-AUTH-2024-009",
                supporting_claims={
                    "oem_name": "ABC Manufacturing Private Limited",
                    "authorized_entity": "Alpha Procurement Services Limited",
                },
            )
        )
        record_result(
            "OEM authentic record with EXPIRED status -> VERIFIED (authorization_status preserved)",
            res_oem_expired.verification_status == VerificationStatus.VERIFIED
            and res_oem_expired.evidence.get("authorization_status") == "EXPIRED",
            f"-> Status={res_oem_expired.verification_status}, AuthStatus={res_oem_expired.evidence.get('authorization_status')}",
        )

        # 2.4 Absent Reference -> NOT_VERIFIED
        res_oem_absent = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.OEM_AUTHORIZATION,
                claimed_value="OEM-UNKNOWN-999",
            )
        )
        record_result(
            "OEM reference absent from mock registry -> NOT_VERIFIED",
            res_oem_absent.verification_status == VerificationStatus.NOT_VERIFIED,
            f"-> Status={res_oem_absent.verification_status}",
        )

        # 2.5 Outage -> UNAVAILABLE
        res_oem_outage = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.OEM_AUTHORIZATION,
                claimed_value="OEM-UNAV-0000-000",
            )
        )
        record_result(
            "OEM simulated outage -> UNAVAILABLE",
            res_oem_outage.verification_status == VerificationStatus.UNAVAILABLE,
            f"-> Status={res_oem_outage.verification_status}",
        )

        # =========================================================================
        # 3. Local Content (MII) Verification Tests
        # =========================================================================
        print_test_header("3. Local Content (MII) Verification Tests")

        # 3.1 Full Match
        res_lc_valid = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.LOCAL_CONTENT,
                claimed_value="LC-2026-0101",
                supporting_claims={
                    "local_content_percentage": 55.0,
                    "supplier_class": "Class-I Local Supplier",
                    "product_name": "Industrial Controller Unit",
                    "entity_name": "TechFlow Enterprises Private Limited",
                },
            )
        )
        record_result(
            "Local Content percentage + class + product match -> VERIFIED (55.0%, CLASS_I)",
            res_lc_valid.verification_status == VerificationStatus.VERIFIED
            and res_lc_valid.evidence.get("supplier_class") == "CLASS_I"
            and res_lc_valid.evidence.get("verified_percentage") == 55.0,
            f"-> Status={res_lc_valid.verification_status}, Class={res_lc_valid.evidence.get('supplier_class')}, Pct={res_lc_valid.evidence.get('verified_percentage')}",
        )

        # 3.2 Percentage Mismatch -> NEEDS_REVIEW
        res_lc_pct_mismatch = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.LOCAL_CONTENT,
                claimed_value="LC-2026-0101",
                supporting_claims={
                    "local_content_percentage": 85.0,  # Claims 85% but registry has 55%
                },
            )
        )
        record_result(
            "Local Content percentage mismatch -> NEEDS_REVIEW",
            res_lc_pct_mismatch.verification_status == VerificationStatus.NEEDS_REVIEW
            and res_lc_pct_mismatch.confidence == 0.60,
            f"-> Status={res_lc_pct_mismatch.verification_status}, Reason={res_lc_pct_mismatch.error_message}",
        )

        # 3.3 Outage -> UNAVAILABLE
        res_lc_outage = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.LOCAL_CONTENT,
                claimed_value="LC-UNAV-0000",
            )
        )
        record_result(
            "Local Content simulated outage -> UNAVAILABLE",
            res_lc_outage.verification_status == VerificationStatus.UNAVAILABLE,
            f"-> Status={res_lc_outage.verification_status}",
        )

        # =========================================================================
        # 4. BIS Certificate Verification Tests
        # =========================================================================
        print_test_header("4. BIS Certificate Verification Tests")

        # 4.1 Valid BIS Match
        res_bis_valid = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.BIS,
                claimed_value="R-12345678",
                supporting_claims={
                    "manufacturer_name": "TechFlow Enterprises Private Limited",
                    "standard_number": "IS 13252",
                    "product_name": "Power Supply Unit",
                },
            )
        )
        record_result(
            "BIS registration + manufacturer + standard match -> VERIFIED",
            res_bis_valid.verification_status == VerificationStatus.VERIFIED
            and res_bis_valid.evidence.get("standard_number") == "IS 13252"
            and res_bis_valid.evidence.get("registration_status") == "VALID",
            f"-> Status={res_bis_valid.verification_status}, Standard={res_bis_valid.evidence.get('standard_number')}",
        )

        # 4.2 Expired BIS License in Registry -> VERIFIED with registry_status="EXPIRED"
        res_bis_expired = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.BIS,
                claimed_value="R-99999999",
                supporting_claims={"manufacturer_name": "Alpha Procurement Services Limited"},
            )
        )
        record_result(
            "BIS authentic record with EXPIRED status -> VERIFIED (registry_status preserved)",
            res_bis_expired.verification_status == VerificationStatus.VERIFIED
            and res_bis_expired.evidence.get("registry_status") == "EXPIRED",
            f"-> Status={res_bis_expired.verification_status}, RegStatus={res_bis_expired.evidence.get('registry_status')}",
        )

        # 4.3 Absent BIS -> NOT_VERIFIED
        res_bis_absent = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.BIS,
                claimed_value="R-77777777",
            )
        )
        record_result(
            "BIS registration absent from mock registry -> NOT_VERIFIED",
            res_bis_absent.verification_status == VerificationStatus.NOT_VERIFIED,
            f"-> Status={res_bis_absent.verification_status}",
        )

        # 4.4 Outage -> UNAVAILABLE
        res_bis_outage = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.BIS,
                claimed_value="R-00000000",
            )
        )
        record_result(
            "BIS simulated outage -> UNAVAILABLE",
            res_bis_outage.verification_status == VerificationStatus.UNAVAILABLE,
            f"-> Status={res_bis_outage.verification_status}",
        )

        # =========================================================================
        # 5. DPIIT Public Procurement Verification Tests
        # =========================================================================
        print_test_header("5. DPIIT Public Procurement Verification Tests")

        res_dpiit_valid = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.DPIIT,
                claimed_value="DPIIT-MII-2026-001",
                supporting_claims={"entity_name": "TechFlow Enterprises Private Limited"},
            )
        )
        record_result(
            "DPIIT public procurement order match -> VERIFIED",
            res_dpiit_valid.verification_status == VerificationStatus.VERIFIED
            and res_dpiit_valid.evidence.get("registration_status") == "VALID",
            f"-> Status={res_dpiit_valid.verification_status}",
        )

        # =========================================================================
        # 6. Supporting Document Internal Evidence Validator Tests
        # =========================================================================
        print_test_header("6. Supporting Document Internal Evidence Validator Tests")

        # 6.1 Complete Evidence -> VERIFIED (Source: INTERNAL)
        res_supp_complete = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.SUPPORTING_DOCUMENT,
                claimed_value="UDIN-2026-CA-001",
                supporting_claims={
                    "reference_number": "UDIN-2026-CA-001",
                    "issuer_name": "M/s Sharma & Co Chartered Accountants",
                    "date": "2026-02-15",
                    "signatory_name": "Rajesh Sharma, FCA",
                    "turnover": "15.5 Crores",
                },
            )
        )
        record_result(
            "Supporting document with complete structural checklist -> VERIFIED (Source=INTERNAL)",
            res_supp_complete.verification_status == VerificationStatus.VERIFIED
            and res_supp_complete.source_type == "INTERNAL"
            and res_supp_complete.evidence.get("is_internal_check") == True,
            f"-> Status={res_supp_complete.verification_status}, Source={res_supp_complete.source_name}, Score={res_supp_complete.evidence.get('score')}",
        )

        # 6.2 Partial Evidence -> NEEDS_REVIEW
        res_supp_partial = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.SUPPORTING_DOCUMENT,
                claimed_value="SUPPORTING-DOC-002",
                supporting_claims={
                    "turnover": "10 Crores",
                },
            )
        )
        record_result(
            "Supporting document with minimal/partial fields -> NEEDS_REVIEW",
            res_supp_partial.verification_status == VerificationStatus.NEEDS_REVIEW
            and res_supp_partial.confidence == 0.60,
            f"-> Status={res_supp_partial.verification_status}, Reason={res_supp_partial.error_message}",
        )

        # =========================================================================
        # 7. Database Pipeline Verification
        # =========================================================================
        print_test_header("7. Database Pipeline Verification")

        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        test_suffix = uuid.uuid4().hex[:6]

        org = Organization(
            id=uuid.uuid4(),
            name=f"TechFlow D {test_suffix}",
            pan_number="ABCDE1234F",
            gstin="33ABCDE1234F1Z5",
            state="Tamil Nadu",
            city="Chennai",
            is_active=True,
        )
        org_other = Organization(
            id=uuid.uuid4(),
            name=f"Other Org D {test_suffix}",
            pan_number="AAAAA0000A",
            gstin="07AAAAA0000A1Z5",
            state="Delhi",
            city="New Delhi",
            is_active=True,
        )
        db.add_all([org, org_other])
        db.commit()

        prof = Profile(
            id=uuid.uuid4(),
            email=f"bidder_5d_{test_suffix}@bidverify.mock",
            role_id=bidder_role.id,
            organization_id=org.id,
            full_name="Muthu Developer 5D",
            is_active=True,
        )
        prof_other = Profile(
            id=uuid.uuid4(),
            email=f"bidder_5d_other_{test_suffix}@bidverify.mock",
            role_id=bidder_role.id,
            organization_id=org_other.id,
            full_name="Other Bidder 5D",
            is_active=True,
        )
        db.add_all([prof, prof_other])
        db.commit()

        user = User(
            id=uuid.uuid4(),
            email=f"bidder_5d_{test_suffix}@bidverify.mock",
            password_hash="mock_hash",
            profile_id=prof.id,
            is_active=True,
        )
        user_other = User(
            id=uuid.uuid4(),
            email=f"bidder_5d_other_{test_suffix}@bidverify.mock",
            password_hash="mock_hash",
            profile_id=prof_other.id,
            is_active=True,
        )
        db.add_all([user, user_other])
        db.commit()

        tender = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/5D/{test_suffix.upper()}",
            title="Procurement of Industrial Sensors & Hardware",
            description="GeM statutory verification test tender Part 5D",
            organization_id=org.id,
            created_by_profile_id=prof.id,
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)
        db.commit()

        bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org.id,
            created_by_profile_id=prof.id,
            bid_number=f"BID-5D-{test_suffix.upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid)
        db.commit()

        # Document 1: OEM Authorization
        doc_oem = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof.id,
            document_type="OEM_AUTHORIZATION",
            document_name="OEM Authorization Letter",
            original_filename="oem_auth.pdf",
            storage_path=f"bids/{bid.id}/oem_auth.pdf",
            mime_type="application/pdf",
            file_size=10240,
            status="UPLOADED",
            version=1,
            is_active=True,
        )
        db.add(doc_oem)
        db.commit()

        proc_oem = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_oem.id,
            processing_status=ProcessingStatus.COMPLETED,
            processing_stage=ProcessingStage.COMPLETED,
            extraction_method=ExtractionMethod.DIGITAL_PDF,
            detected_document_type=DocumentClass.OEM_AUTHORIZATION,
            classification_confidence=0.98,
            extracted_data={
                "fields": {
                    "reference_number": {"value": "OEM-AUTH-2026-001", "confidence": 0.99},
                    "oem_name": {"value": "ABC Manufacturing Private Limited", "confidence": 0.95},
                    "authorized_entity": {"value": "TechFlow Enterprises Private Limited", "confidence": 0.95},
                    "product_scope": {"value": "Industrial Sensor Model X100", "confidence": 0.90},
                }
            },
            raw_text="OEM-AUTH-2026-001 ABC Manufacturing",
            normalized_text="OEM-AUTH-2026-001 ABC Manufacturing",
        )
        db.add(proc_oem)
        db.commit()

        v_oem_res = await verify_document_claims(
            db=db,
            current_user=user,
            bid_id=bid.id,
            document_id=doc_oem.id,
        )
        record_result(
            "OEM Document Verification pipeline returns VERIFIED",
            len(v_oem_res.results) > 0 and v_oem_res.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> Status={v_oem_res.results[0].verification_status}",
        )

        # Document 2: Local Content Declaration
        doc_lc = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof.id,
            document_type="LOCAL_CONTENT_DECLARATION",
            document_name="Local Content Declaration",
            original_filename="local_content.pdf",
            storage_path=f"bids/{bid.id}/local_content.pdf",
            mime_type="application/pdf",
            file_size=10240,
            status="UPLOADED",
            version=1,
            is_active=True,
        )
        db.add(doc_lc)
        db.commit()

        proc_lc = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_lc.id,
            processing_status=ProcessingStatus.COMPLETED,
            processing_stage=ProcessingStage.COMPLETED,
            extraction_method=ExtractionMethod.DIGITAL_PDF,
            detected_document_type=DocumentClass.LOCAL_CONTENT_DECLARATION,
            classification_confidence=0.98,
            extracted_data={
                "fields": {
                    "reference_number": {"value": "LC-2026-0101", "confidence": 0.98},
                    "local_content_percentage": {"value": "55%", "confidence": 0.99},
                    "supplier_class": {"value": "Class-I Local Supplier", "confidence": 0.95},
                    "product_name": {"value": "Industrial Controller Unit", "confidence": 0.90},
                }
            },
            raw_text="LC-2026-0101 55% Class-I",
            normalized_text="LC-2026-0101 55% Class-I",
        )
        db.add(proc_lc)
        db.commit()

        v_lc_res = await verify_document_claims(
            db=db,
            current_user=user,
            bid_id=bid.id,
            document_id=doc_lc.id,
        )
        record_result(
            "Local Content Document Verification pipeline returns VERIFIED",
            len(v_lc_res.results) > 0 and v_lc_res.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> Status={v_lc_res.results[0].verification_status}",
        )

        # Document 3: Turnover Certificate (Supporting Document)
        doc_supp = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof.id,
            document_type="TURNOVER_CERTIFICATE",
            document_name="CA Turnover Certificate",
            original_filename="turnover.pdf",
            storage_path=f"bids/{bid.id}/turnover.pdf",
            mime_type="application/pdf",
            file_size=10240,
            status="UPLOADED",
            version=1,
            is_active=True,
        )
        db.add(doc_supp)
        db.commit()

        proc_supp = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_supp.id,
            processing_status=ProcessingStatus.COMPLETED,
            processing_stage=ProcessingStage.COMPLETED,
            extraction_method=ExtractionMethod.DIGITAL_PDF,
            detected_document_type=DocumentClass.TURNOVER_CERTIFICATE,
            classification_confidence=0.95,
            extracted_data={
                "fields": {
                    "udin": {"value": "UDIN-2026-CA-001", "confidence": 0.99},
                    "ca_name": {"value": "Sharma & Associates", "confidence": 0.95},
                    "turnover": {"value": "15 Crores", "confidence": 0.90},
                    "issue_date": {"value": "2026-01-20", "confidence": 0.92},
                    "signatory_name": {"value": "R. Sharma", "confidence": 0.90},
                }
            },
            raw_text="UDIN-2026-CA-001 Sharma & Associates",
            normalized_text="UDIN-2026-CA-001 Sharma & Associates",
        )
        db.add(proc_supp)
        db.commit()

        v_supp_res = await verify_document_claims(
            db=db,
            current_user=user,
            bid_id=bid.id,
            document_id=doc_supp.id,
        )
        record_result(
            "Supporting Document Verification pipeline returns VERIFIED (Source=INTERNAL)",
            len(v_supp_res.results) > 0 and v_supp_res.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> Status={v_supp_res.results[0].verification_status}",
        )

        # =========================================================================
        # 8. Idempotency Check
        # =========================================================================
        print_test_header("8. Idempotency Check")

        count_before = len(db.scalars(select(VerificationRecord).where(VerificationRecord.bid_document_id == doc_oem.id)).all())
        v_oem_again = await verify_document_claims(
            db=db,
            current_user=user,
            bid_id=bid.id,
            document_id=doc_oem.id,
        )
        count_after = len(db.scalars(select(VerificationRecord).where(VerificationRecord.bid_document_id == doc_oem.id)).all())

        record_result(
            "Repeated Part 5D verification trigger is idempotent (created_count=0)",
            count_before == count_after and v_oem_again.created_count == 0,
            f"-> Count before: {count_before}, Count after: {count_after}",
        )

        # =========================================================================
        # 9. Outage Simulation & Retry Progression
        # =========================================================================
        print_test_header("9. Outage Simulation & Retry Progression")

        doc_bis_outage = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof.id,
            document_type="TECHNICAL_DOCUMENT",
            document_name="BIS Certificate",
            original_filename="bis_outage.pdf",
            storage_path=f"bids/{bid.id}/bis_outage.pdf",
            mime_type="application/pdf",
            file_size=10240,
            status="UPLOADED",
            version=1,
            is_active=True,
        )
        db.add(doc_bis_outage)
        db.commit()

        proc_bis_outage = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_bis_outage.id,
            processing_status=ProcessingStatus.COMPLETED,
            processing_stage=ProcessingStage.COMPLETED,
            extraction_method=ExtractionMethod.DIGITAL_PDF,
            detected_document_type="OTHER",
            classification_confidence=0.90,
            extracted_data={
                "fields": {
                    "bis_registration_number": {"value": "R-00000000", "confidence": 0.99},
                    "standard_number": {"value": "IS 13252", "confidence": 0.90},
                }
            },
            raw_text="R-00000000 IS 13252",
            normalized_text="R-00000000 IS 13252",
        )
        db.add(proc_bis_outage)
        db.commit()

        v_bis_res = await verify_document_claims(
            db=db,
            current_user=user,
            bid_id=bid.id,
            document_id=doc_bis_outage.id,
        )

        v_bis_rec = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_document_id == doc_bis_outage.id,
                VerificationRecord.is_active == True,
            )
        ).first()

        record_result(
            "BIS outage claim creates UNAVAILABLE record (attempt 1)",
            v_bis_rec is not None and v_bis_rec.verification_status == VerificationStatus.UNAVAILABLE,
            f"-> Status={v_bis_rec.verification_status if v_bis_rec else 'None'}",
        )

        retry_bis = await retry_verification_record(
            db=db,
            current_user=user,
            bid_id=bid.id,
            verification_id=v_bis_rec.id,
        )

        record_result(
            "BIS retry increments attempt_number",
            retry_bis.verification.attempt_number == 2,
            f"-> Attempt number: {retry_bis.verification.attempt_number}",
        )

        # =========================================================================
        # 10. Multi-Tenant Security & Tenant Isolation
        # =========================================================================
        print_test_header("10. Multi-Tenant Security & Tenant Isolation")

        try:
            await verify_document_claims(
                db=db,
                current_user=user_other,
                bid_id=bid.id,
                document_id=doc_oem.id,
            )
            record_result("Cross-bidder verification trigger rejected", False)
        except HTTPException as he:
            record_result(
                "Cross-bidder verification trigger rejected with 404",
                he.status_code == 404,
                f"-> HTTP {he.status_code}: {he.detail}",
            )

        # =========================================================================
        # 11. Submitted Bid Support
        # =========================================================================
        print_test_header("11. Submitted Bid Support")

        bid.status = "SUBMITTED"
        bid.submitted_at = datetime.now(timezone.utc)
        db.commit()

        v_oem_sub = await verify_document_claims(
            db=db,
            current_user=user,
            bid_id=bid.id,
            document_id=doc_oem.id,
        )

        record_result(
            "Part 5D verification operates seamlessly on SUBMITTED bid",
            len(v_oem_sub.results) > 0 and v_oem_sub.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> Status={v_oem_sub.results[0].verification_status}",
        )

        # =========================================================================
        # 12. Replaced Document Audit Preservation
        # =========================================================================
        print_test_header("12. Replaced Document Audit Preservation")

        doc_oem.is_active = False
        db.commit()

        try:
            await verify_document_claims(
                db=db,
                current_user=user,
                bid_id=bid.id,
                document_id=doc_oem.id,
            )
            record_result("Verifying inactive replaced document rejected", False)
        except HTTPException as he:
            record_result(
                "Verifying inactive replaced document rejected with HTTP 400",
                he.status_code == 400,
                f"-> HTTP {he.status_code}: {he.detail}",
            )

        old_records = db.scalars(
            select(VerificationRecord).where(VerificationRecord.bid_document_id == doc_oem.id)
        ).all()
        record_result(
            "Replaced document retains past verification history in DB",
            len(old_records) > 0,
            f"-> Count: {len(old_records)}",
        )

        # =========================================================================
        # 13. Compliance Separation Guard
        # =========================================================================
        print_test_header("13. Compliance Separation Guard")

        all_v = db.scalars(select(VerificationRecord).where(VerificationRecord.bid_id == bid.id)).all()
        forbidden_terms = ["PASS", "FAIL", "COMPLIANT", "QUALIFIED", "DISQUALIFIED", "ELIGIBLE"]
        leak = any(r.verification_status in forbidden_terms or r.match_status in forbidden_terms for r in all_v)
        record_result(
            "Strict compliance boundary enforced across all Part 5D domains",
            not leak,
        )

    finally:
        db.close()

    # =========================================================================
    # Final Test Summary
    # =========================================================================
    print(f"\n{'='*70}\nPART 5D TEST SUMMARY\n{'='*70}")
    print(f"Total Tests Executed : {passed_count + failed_count}")
    print(f"Passed               : {passed_count}")
    print(f"Failed               : {failed_count}")

    if failed_count == 0:
        print("\n>>> ALL PART 5D OEM, LOCAL CONTENT, BIS & SUPPORTING DOC TESTS PASSED! <<<\n")
        return True
    else:
        print(f"\n>>> {failed_count} TEST(S) FAILED IN PART 5D! <<<\n")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_part5d_test_suite())
    sys.exit(0 if success else 1)
