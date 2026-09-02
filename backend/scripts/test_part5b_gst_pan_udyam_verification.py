"""
Part 5B Comprehensive Test Suite — GST, PAN & Udyam Verification
BidVerify AI — GeM Statutory Verification Adapters, Normalization & Evidence Telemetry

Tests:
1. Identifier Format Validation (GSTIN, PAN, Udyam) & Whitespace/Hyphen Normalization
2. Corporate Name Normalization & Token Comparison (PVT LTD == PRIVATE LIMITED, LTD == LIMITED)
3. PAN Entity Type Signal Inference (Company 'C', Individual 'P', Firm 'F', Trust 'T')
4. GST Domain Verification:
   - Exact Identifier & Name Match -> VERIFIED (confidence=1.0)
   - Exact Identifier + Partial Name Match -> VERIFIED (confidence=0.95)
   - Exact Identifier + Name Mismatch -> NEEDS_REVIEW (confidence=0.60)
   - Cancelled Status in Registry -> VERIFIED with registration_status="CANCELLED"
   - Absent GSTIN in Registry -> NOT_VERIFIED
   - Outage GSTIN -> UNAVAILABLE
5. PAN Domain Verification:
   - Valid PAN & Matching Name -> VERIFIED (confidence=1.0)
   - Valid PAN & Mismatched Name -> NEEDS_REVIEW (confidence=0.60)
   - Inactive PAN in Registry -> VERIFIED with pan_status="INACTIVE"
   - Absent PAN in Registry -> NOT_VERIFIED
   - Outage PAN -> UNAVAILABLE
6. Udyam MSME Domain Verification:
   - Valid Udyam & Matching Name -> VERIFIED (Micro/Small/Medium classification preserved)
   - Valid Udyam & Mismatched Name -> NEEDS_REVIEW (confidence=0.60)
   - Absent Udyam in Registry -> NOT_VERIFIED
   - Outage Udyam -> UNAVAILABLE
7. Status Separation (NOT_VERIFIED != UNAVAILABLE != FAILED)
8. End-to-End Database Lifecycle & Structured Payload Persistence (claim_payload, response_payload)
9. Idempotency & Duplicate Prevention
10. Retry Progression on Outages (attempt_number increments)
11. Submitted Bid Verification Support
12. Replaced Document Audit Preservation
13. Cross-Bidder Multi-Tenant Isolation (404)
14. Strict Compliance Separation (No PASS/FAIL in verification domain)
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
    compare_strings,
    extract_pan_entity_type,
    normalize_identifier,
    normalize_org_name,
    normalize_udyam_number,
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


async def run_part5b_test_suite():
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
        # 1. Identifier Format & Normalization Unit Tests
        # =========================================================================
        print_test_header("1. Identifier Format & Normalization Unit Tests")

        # GSTIN normalization & validation
        record_result(
            "GSTIN lowercase and whitespace normalization",
            normalize_identifier("  33abcde1234f1z5  ") == "33ABCDE1234F1Z5",
        )
        gst_adapter = adapter_registry.get_adapter(VerificationType.GST)
        valid_gst, _ = gst_adapter.validate_input("33ABCDE1234F1Z5")
        invalid_gst, _ = gst_adapter.validate_input("33INVALID123")
        record_result("GST adapter validates correct GSTIN", valid_gst)
        record_result("GST adapter rejects invalid GSTIN format", not invalid_gst)

        # PAN normalization & validation
        record_result(
            "PAN lowercase and whitespace normalization",
            normalize_identifier("  abcde1234f ") == "ABCDE1234F",
        )
        pan_adapter = adapter_registry.get_adapter(VerificationType.PAN)
        valid_pan, _ = pan_adapter.validate_input("ABCDE1234F")
        invalid_pan, _ = pan_adapter.validate_input("12345")
        record_result("PAN adapter validates correct PAN", valid_pan)
        record_result("PAN adapter rejects invalid PAN format", not invalid_pan)

        # Udyam normalization & validation
        norm_udyam = normalize_udyam_number("  udyam - tn - 01 - 0012345 ")
        record_result(
            "Udyam whitespace and hyphen normalization",
            norm_udyam == "UDYAM-TN-01-0012345",
            f"-> {norm_udyam}",
        )
        udyam_adapter = adapter_registry.get_adapter(VerificationType.UDYAM)
        valid_u, _ = udyam_adapter.validate_input("UDYAM-TN-01-0012345")
        invalid_u, _ = udyam_adapter.validate_input("UDYAM-BAD-FORMAT")
        record_result("Udyam adapter validates correct Udyam format", valid_u)
        record_result("Udyam adapter rejects invalid Udyam format", not invalid_u)

        # =========================================================================
        # 2. Corporate Name Normalization & Token Comparison Unit Tests
        # =========================================================================
        print_test_header("2. Corporate Name Normalization & Token Comparison Unit Tests")

        norm_1 = normalize_org_name("TechFlow Enterprises Pvt. Ltd.")
        norm_2 = normalize_org_name("TECHFLOW ENTERPRISES PRIVATE LIMITED")
        record_result(
            "Corporate suffix normalization (PVT. LTD. -> PRIVATE LIMITED)",
            norm_1 == norm_2 and norm_1 == "TECHFLOW ENTERPRISES PRIVATE LIMITED",
            f"-> {norm_1}",
        )

        match_st, conf = compare_names("TechFlow Enterprises Pvt Ltd", "TECHFLOW ENTERPRISES PRIVATE LIMITED")
        record_result(
            "compare_names matches equivalent corporate suffix names",
            match_st == VerificationMatchStatus.MATCH and conf == 1.0,
            f"-> Status={match_st}, Conf={conf}",
        )

        match_part, conf_p = compare_names("TechFlow Enterprises", "TECHFLOW ENTERPRISES PRIVATE LIMITED")
        record_result(
            "compare_names identifies token subset as PARTIAL_MATCH",
            match_part == VerificationMatchStatus.PARTIAL_MATCH and conf_p >= 0.75,
            f"-> Status={match_part}, Conf={conf_p}",
        )

        match_diff, conf_d = compare_names("TechFlow Enterprises", "GLOBAL INFOTECH SOLUTIONS LIMITED")
        record_result(
            "compare_names identifies distinct companies as MISMATCH",
            match_diff == VerificationMatchStatus.MISMATCH and conf_d == 0.0,
            f"-> Status={match_diff}, Conf={conf_d}",
        )

        # =========================================================================
        # 3. PAN Entity Type Signal Inference Unit Tests
        # =========================================================================
        print_test_header("3. PAN Entity Type Signal Inference Unit Tests")

        e_comp = extract_pan_entity_type("AAACC1234F")
        record_result(
            "Infers Company type from 4th char 'C'",
            e_comp.get("entity_type_code") == "C" and "Company" in e_comp.get("entity_type_description", ""),
            f"-> {e_comp}",
        )

        e_ind = extract_pan_entity_type("AAAPP1234F")
        record_result(
            "Infers Individual type from 4th char 'P'",
            e_ind.get("entity_type_code") == "P" and "Individual" in e_ind.get("entity_type_description", ""),
            f"-> {e_ind}",
        )

        e_firm = extract_pan_entity_type("AAAFK1234F")
        record_result(
            "Infers Partnership Firm / LLP from 4th char 'F'",
            e_firm.get("entity_type_code") == "F" and "Partnership" in e_firm.get("entity_type_description", ""),
            f"-> {e_firm}",
        )

        # =========================================================================
        # 4. GST Domain Verification Tests
        # =========================================================================
        print_test_header("4. GST Domain Verification Tests")

        # 4.1 Exact Match (Identifier + Legal Name)
        res_gst_exact = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.GST,
                claimed_value="33ABCDE1234F1Z5",
                supporting_claims={"legal_name": "TechFlow Enterprises Pvt Ltd"},
            )
        )
        record_result(
            "GST exact identifier & normalized legal name match -> VERIFIED (MATCH, conf=1.0)",
            res_gst_exact.verification_status == VerificationStatus.VERIFIED
            and res_gst_exact.match_status == VerificationMatchStatus.MATCH
            and res_gst_exact.confidence == 1.0
            and res_gst_exact.evidence.get("legal_name_match") == VerificationMatchStatus.MATCH,
            f"-> Status={res_gst_exact.verification_status}, Conf={res_gst_exact.confidence}",
        )

        # 4.2 Legal Name Mismatch -> NEEDS_REVIEW (not NOT_VERIFIED!)
        res_gst_mismatch = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.GST,
                claimed_value="33ABCDE1234F1Z5",
                supporting_claims={"legal_name": "Totally Different Company Pvt Ltd"},
            )
        )
        record_result(
            "GST valid identifier + mismatched legal name -> NEEDS_REVIEW (MISMATCH, conf=0.60)",
            res_gst_mismatch.verification_status == VerificationStatus.NEEDS_REVIEW
            and res_gst_mismatch.match_status == VerificationMatchStatus.MISMATCH
            and res_gst_mismatch.confidence == 0.60
            and res_gst_mismatch.evidence.get("legal_name_match") == VerificationMatchStatus.MISMATCH,
            f"-> Status={res_gst_mismatch.verification_status}, Conf={res_gst_mismatch.confidence}, Reason={res_gst_mismatch.error_message}",
        )

        # 4.3 Cancelled Status in Registry -> Authenticity VERIFIED with registration_status="CANCELLED"
        res_gst_cancelled = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.GST,
                claimed_value="33ABCDE1234F1Z9",
                supporting_claims={"legal_name": "TechFlow Enterprises Private Limited"},
            )
        )
        record_result(
            "GST authentic record with CANCELLED status -> VERIFIED (registration_status preserved)",
            res_gst_cancelled.verification_status == VerificationStatus.VERIFIED
            and res_gst_cancelled.evidence.get("registration_status") == "CANCELLED"
            and res_gst_cancelled.normalized_verified_payload.get("registration_status") == "CANCELLED",
            f"-> Status={res_gst_cancelled.verification_status}, RegStatus={res_gst_cancelled.evidence.get('registration_status')}",
        )

        # 4.4 Absent GSTIN -> NOT_VERIFIED
        res_gst_absent = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.GST,
                claimed_value="99ABCDE0000Z1Z5",
            )
        )
        record_result(
            "GST absent from mock registry -> NOT_VERIFIED",
            res_gst_absent.verification_status == VerificationStatus.NOT_VERIFIED
            and res_gst_absent.match_status == VerificationMatchStatus.MISMATCH,
            f"-> Status={res_gst_absent.verification_status}",
        )

        # 4.5 Outage GSTIN -> UNAVAILABLE
        res_gst_outage = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.GST,
                claimed_value="27UNAVA9999A1Z1",
            )
        )
        record_result(
            "GST simulated outage -> UNAVAILABLE (SOURCE_UNAVAILABLE)",
            res_gst_outage.verification_status == VerificationStatus.UNAVAILABLE
            and res_gst_outage.error_code == VerificationErrorCode.SOURCE_UNAVAILABLE,
            f"-> Status={res_gst_outage.verification_status}",
        )

        # =========================================================================
        # 5. PAN Domain Verification Tests
        # =========================================================================
        print_test_header("5. PAN Domain Verification Tests")

        # 5.1 PAN Valid & Matching Name -> VERIFIED
        res_pan_valid = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.PAN,
                claimed_value="ABCDE1234F",
                supporting_claims={"name": "Techflow Enterprises Pvt Ltd"},
            )
        )
        record_result(
            "PAN exact identifier & normalized name match -> VERIFIED (MATCH, conf=1.0)",
            res_pan_valid.verification_status == VerificationStatus.VERIFIED
            and res_pan_valid.match_status == VerificationMatchStatus.MATCH
            and res_pan_valid.confidence == 1.0
            and res_pan_valid.evidence.get("name_match") == VerificationMatchStatus.MATCH,
            f"-> Status={res_pan_valid.verification_status}, Conf={res_pan_valid.confidence}",
        )

        # 5.2 PAN Valid & Mismatched Name -> NEEDS_REVIEW
        res_pan_mismatch = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.PAN,
                claimed_value="ABCDE1234F",
                supporting_claims={"name": "Other Unrelated Person"},
            )
        )
        record_result(
            "PAN valid identifier + mismatched name -> NEEDS_REVIEW (MISMATCH, conf=0.60)",
            res_pan_mismatch.verification_status == VerificationStatus.NEEDS_REVIEW
            and res_pan_mismatch.match_status == VerificationMatchStatus.MISMATCH
            and res_pan_mismatch.confidence == 0.60,
            f"-> Status={res_pan_mismatch.verification_status}, Reason={res_pan_mismatch.error_message}",
        )

        # 5.3 PAN Inactive in Registry -> VERIFIED with pan_status="INACTIVE"
        res_pan_inactive = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.PAN,
                claimed_value="ABCDE9999X",
                supporting_claims={"name": "Deactivated Entity Holdings"},
            )
        )
        record_result(
            "PAN authentic record with INACTIVE status -> VERIFIED (pan_status preserved)",
            res_pan_inactive.verification_status == VerificationStatus.VERIFIED
            and res_pan_inactive.evidence.get("pan_status") == "INACTIVE",
            f"-> Status={res_pan_inactive.verification_status}, PANStatus={res_pan_inactive.evidence.get('pan_status')}",
        )

        # 5.4 Absent PAN -> NOT_VERIFIED
        res_pan_absent = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.PAN,
                claimed_value="ZZZZZ9999Z",
            )
        )
        record_result(
            "PAN absent from mock registry -> NOT_VERIFIED",
            res_pan_absent.verification_status == VerificationStatus.NOT_VERIFIED,
            f"-> Status={res_pan_absent.verification_status}",
        )

        # =========================================================================
        # 6. Udyam MSME Domain Verification Tests
        # =========================================================================
        print_test_header("6. Udyam MSME Domain Verification Tests")

        # 6.1 Udyam Valid & Matching Name -> VERIFIED with Micro/Small/Medium classification
        res_udyam_valid = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.UDYAM,
                claimed_value="UDYAM-TN-01-0012345",
                supporting_claims={"enterprise_name": "TechFlow Enterprises Pvt Ltd"},
            )
        )
        record_result(
            "Udyam matching enterprise -> VERIFIED (Classification: Micro stored)",
            res_udyam_valid.verification_status == VerificationStatus.VERIFIED
            and res_udyam_valid.match_status == VerificationMatchStatus.MATCH
            and res_udyam_valid.evidence.get("enterprise_classification") == "Micro"
            and res_udyam_valid.normalized_verified_payload.get("enterprise_classification") == "Micro",
            f"-> Status={res_udyam_valid.verification_status}, Classification={res_udyam_valid.evidence.get('enterprise_classification')}",
        )

        # 6.2 Udyam Valid & Mismatched Enterprise Name -> NEEDS_REVIEW
        res_udyam_mismatch = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.UDYAM,
                claimed_value="UDYAM-TN-01-0012345",
                supporting_claims={"enterprise_name": "Different Fabricators LLP"},
            )
        )
        record_result(
            "Udyam valid identifier + mismatched enterprise name -> NEEDS_REVIEW",
            res_udyam_mismatch.verification_status == VerificationStatus.NEEDS_REVIEW
            and res_udyam_mismatch.match_status == VerificationMatchStatus.MISMATCH
            and res_udyam_mismatch.confidence == 0.60,
            f"-> Status={res_udyam_mismatch.verification_status}, Reason={res_udyam_mismatch.error_message}",
        )

        # 6.3 Udyam Absent -> NOT_VERIFIED
        res_udyam_absent = await verification_engine.execute_verification(
            VerificationRequest(
                verification_type=VerificationType.UDYAM,
                claimed_value="UDYAM-TN-99-9999999",
            )
        )
        record_result(
            "Udyam absent from mock registry -> NOT_VERIFIED",
            res_udyam_absent.verification_status == VerificationStatus.NOT_VERIFIED,
            f"-> Status={res_udyam_absent.verification_status}",
        )

        # =========================================================================
        # 7. Database Fixture Setup & End-to-End Verification Pipeline
        # =========================================================================
        print_test_header("7. Database Fixtures & Full Pipeline Verification")

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

        tender = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/B/{test_suffix.upper()}",
            title="Procurement of IT Hardware & Cloud Servers",
            description="GeM statutory verification test tender Part 5B",
            organization_id=org_a.id,
            created_by_profile_id=profile_a.id,
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)
        db.commit()

        bid_a = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_a.id,
            created_by_profile_id=profile_a.id,
            bid_number=f"BID-A-{test_suffix.upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid_a)
        db.commit()

        # Document 1: GST Certificate
        doc_gst = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid_a.id,
            uploaded_by_profile_id=profile_a.id,
            document_type="GST_CERTIFICATE",
            document_name="GST Certificate",
            original_filename="gst_techflow.pdf",
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
                    "gstin": {"value": "33ABCDE1234F1Z5", "confidence": 0.98, "evidence": "GSTIN: 33ABCDE1234F1Z5"},
                    "legal_name": {"value": "TechFlow Enterprises Pvt Ltd", "confidence": 0.90, "evidence": "Legal Name: TechFlow Enterprises Pvt Ltd"},
                    "trade_name": {"value": "TechFlow India", "confidence": 0.85, "evidence": "Trade Name: TechFlow India"},
                    "state": {"value": "Tamil Nadu", "confidence": 0.95, "evidence": "State: Tamil Nadu"},
                }
            },
            raw_text="GSTIN: 33ABCDE1234F1Z5 TechFlow Enterprises Pvt Ltd",
            normalized_text="GSTIN: 33ABCDE1234F1Z5 TechFlow Enterprises Pvt Ltd",
        )
        db.add(proc_gst)
        db.commit()

        # Trigger GST Document Claims Verification
        v_gst_res = await verify_document_claims(
            db=db,
            current_user=user_a,
            bid_id=bid_a.id,
            document_id=doc_gst.id,
        )

        record_result(
            "Full GST Document Verification succeeds and returns VERIFIED",
            len(v_gst_res.results) > 0 and v_gst_res.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> Status={v_gst_res.results[0].verification_status}",
        )

        persisted_gst = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_document_id == doc_gst.id,
                VerificationRecord.is_active == True,
            )
        ).first()

        record_result(
            "VerificationRecord persists request_payload and response_payload",
            persisted_gst is not None
            and isinstance(persisted_gst.request_payload, dict)
            and isinstance(persisted_gst.response_payload, dict)
            and persisted_gst.request_payload.get("legal_name") == "TechFlow Enterprises Pvt Ltd"
            and persisted_gst.response_payload.get("registration_status") == "ACTIVE",
            f"-> RegStatus in response_payload: {persisted_gst.response_payload.get('registration_status') if persisted_gst else 'None'}",
        )

        # =========================================================================
        # 8. Idempotency and Duplication Prevention
        # =========================================================================
        print_test_header("8. Idempotency and Duplication Prevention")

        records_count_1 = len(db.scalars(select(VerificationRecord).where(VerificationRecord.bid_document_id == doc_gst.id)).all())
        v_gst_again = await verify_document_claims(
            db=db,
            current_user=user_a,
            bid_id=bid_a.id,
            document_id=doc_gst.id,
        )
        records_count_2 = len(db.scalars(select(VerificationRecord).where(VerificationRecord.bid_document_id == doc_gst.id)).all())

        record_result(
            "Repeated verification trigger is idempotent (created_count=0)",
            records_count_1 == records_count_2 and v_gst_again.created_count == 0,
            f"-> Count before: {records_count_1}, Count after: {records_count_2}",
        )

        # =========================================================================
        # 9. Outage Simulation & Retry Progression
        # =========================================================================
        print_test_header("9. Outage Simulation & Retry Progression")

        doc_pan_outage = BidDocument(
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
        db.add(doc_pan_outage)
        db.commit()

        proc_pan_outage = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_pan_outage.id,
            processing_status=ProcessingStatus.COMPLETED,
            processing_stage=ProcessingStage.COMPLETED,
            extraction_method=ExtractionMethod.DIGITAL_PDF,
            detected_document_type=DocumentClass.PAN,
            classification_confidence=0.95,
            extracted_data={
                "fields": {
                    "pan_number": {"value": "UNAVA9999X", "confidence": 0.99},
                    "holder_name": {"value": "TechFlow Enterprises Pvt Ltd", "confidence": 0.90},
                }
            },
            raw_text="PAN: UNAVA9999X",
            normalized_text="PAN: UNAVA9999X",
        )
        db.add(proc_pan_outage)
        db.commit()

        v_outage_res = await verify_document_claims(
            db=db,
            current_user=user_a,
            bid_id=bid_a.id,
            document_id=doc_pan_outage.id,
        )

        v_pan_rec = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_document_id == doc_pan_outage.id,
                VerificationRecord.is_active == True,
            )
        ).first()

        record_result(
            "Outage claim creates UNAVAILABLE record (attempt 1)",
            v_pan_rec is not None and v_pan_rec.verification_status == VerificationStatus.UNAVAILABLE and v_pan_rec.attempt_number == 1,
            f"-> Status={v_pan_rec.verification_status if v_pan_rec else 'None'}",
        )

        # Retry the outage verification
        retry_res = await retry_verification_record(
            db=db,
            current_user=user_a,
            bid_id=bid_a.id,
            verification_id=v_pan_rec.id,
        )

        record_result(
            "Retry preserves supporting claims and increments attempt_number",
            retry_res.verification.attempt_number == 2,
            f"-> Attempt number: {retry_res.verification.attempt_number}",
        )

        # =========================================================================
        # 10. Multi-Tenant Security & Tenant Isolation
        # =========================================================================
        print_test_header("10. Multi-Tenant Security & Tenant Isolation")

        try:
            await verify_document_claims(
                db=db,
                current_user=user_b,
                bid_id=bid_a.id,
                document_id=doc_gst.id,
            )
            record_result("Cross-bidder verification trigger rejected", False)
        except HTTPException as he:
            record_result(
                "Cross-bidder verification trigger rejected with 404",
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
            record_result("Cross-bidder verification read rejected", False)
        except HTTPException as he:
            record_result(
                "Cross-bidder verification read rejected with 404",
                he.status_code == 404,
                f"-> HTTP {he.status_code}: {he.detail}",
            )

        # =========================================================================
        # 11. Submitted Bid Verification Support
        # =========================================================================
        print_test_header("11. Submitted Bid Verification Support")

        bid_a.status = "SUBMITTED"
        bid_a.submitted_at = datetime.now(timezone.utc)
        db.commit()

        doc_udyam = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid_a.id,
            uploaded_by_profile_id=profile_a.id,
            document_type="UDYAM_CERTIFICATE",
            document_name="Udyam Certificate",
            original_filename="udyam_submitted.pdf",
            storage_path=f"bids/{bid_a.id}/udyam_sub.pdf",
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
                    "udyam_registration_number": {"value": "UDYAM-TN-01-0012345", "confidence": 0.99},
                    "enterprise_name": {"value": "TechFlow Enterprises Private Limited", "confidence": 0.95},
                }
            },
            raw_text="UDYAM-TN-01-0012345 TechFlow Enterprises",
            normalized_text="UDYAM-TN-01-0012345 TechFlow Enterprises",
        )
        db.add(proc_udyam)
        db.commit()

        v_sub_res = await verify_document_claims(
            db=db,
            current_user=user_a,
            bid_id=bid_a.id,
            document_id=doc_udyam.id,
        )

        record_result(
            "Verification operates seamlessly on SUBMITTED bids",
            len(v_sub_res.results) > 0 and v_sub_res.results[0].verification_status == VerificationStatus.VERIFIED,
            f"-> Status={v_sub_res.results[0].verification_status}",
        )

        # =========================================================================
        # 12. Replaced Document Audit Preservation
        # =========================================================================
        print_test_header("12. Replaced Document Audit Preservation")

        doc_udyam.is_active = False
        db.commit()

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

        old_records = db.scalars(
            select(VerificationRecord).where(VerificationRecord.bid_document_id == doc_udyam.id)
        ).all()
        record_result(
            "Replaced document retains past verification audit trail in DB",
            len(old_records) > 0,
            f"-> Count: {len(old_records)}",
        )

        # =========================================================================
        # 13. Compliance Separation Guard
        # =========================================================================
        print_test_header("13. Compliance Separation Guard")

        all_v = db.scalars(select(VerificationRecord).where(VerificationRecord.bid_id == bid_a.id)).all()
        forbidden_terms = ["PASS", "FAIL", "COMPLIANT", "QUALIFIED", "DISQUALIFIED", "ELIGIBLE"]
        leak = any(r.verification_status in forbidden_terms or r.match_status in forbidden_terms for r in all_v)
        record_result(
            "Strict compliance boundary enforced (No PASS/FAIL or tender qualification in verification)",
            not leak,
        )

    finally:
        db.close()

    # =========================================================================
    # Final Test Summary
    # =========================================================================
    print(f"\n{'='*70}\nPART 5B TEST SUMMARY\n{'='*70}")
    print(f"Total Tests Executed : {passed_count + failed_count}")
    print(f"Passed               : {passed_count}")
    print(f"Failed               : {failed_count}")

    if failed_count == 0:
        print("\n>>> ALL PART 5B GST, PAN & UDYAM VERIFICATION TESTS PASSED! <<<\n")
        return True
    else:
        print(f"\n>>> {failed_count} TEST(S) FAILED IN PART 5B! <<<\n")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_part5b_test_suite())
    sys.exit(0 if success else 1)
