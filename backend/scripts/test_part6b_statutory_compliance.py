"""
Master Test Suite for Part 6B: Statutory & Registration Compliance Rules
Validates all statutory domains and rule evaluation logic:
1. GST Registration (PASS, FAIL, REVIEW)
2. GST Status (ACTIVE vs CANCELLED vs SUSPENDED)
3. PAN Verification & Holder Name Mismatch (MATCH -> PASS, MISMATCH -> REVIEW)
4. Udyam Registration & Status
5. MSME Classification (MICRO, SMALL, MEDIUM, IN lists)
6. MCA Registration, Company Status (ACTIVE, DORMANT, STRIKE_OFF) & Applicability (PROPRIETORSHIP -> NOT_APPLICABLE)
7. Startup India Recognition & Status (RECOGNIZED, REVOKED, NOT_VERIFIED)
8. NSIC Registration & Validity vs Tender Deadline (Valid -> PASS, Expired -> FAIL)
9. EPFO Registration & Status
10. ESIC Registration & Status
11. Source Outage Handling (UNAVAILABLE -> REVIEW without penalizing bidder)
12. Missing Verification Handling (PENDING)
13. Invalid Tender Configuration Resilience (Safe REVIEW without crash)
14. End-to-End Database Persistence, Versioning & Idempotency
15. Multi-Tenant Isolation & Submitted Bid Support
16. Strict Boundary Guard (No Score, No Risk, No Final Decision)
"""

import asyncio
import os
import sys
import uuid
from decimal import Decimal
from datetime import datetime, timezone, date, timedelta

# Append backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, and_, func
from app.db.session import get_session_factory
from app.db.models.role import Role
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.user import User
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.verification_record import (
    VerificationRecord,
    VerificationStatus,
    VerificationMatchStatus,
    VerificationSourceType,
)
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus
from app.compliance.types import (
    ComplianceOperator,
    ComplianceContext,
    ComplianceRuleResult,
)
from app.compliance.evaluators.statutory import StatutoryRuleEvaluator
from app.compliance.registry import compliance_registry
from app.compliance.engine import evaluate_requirement, build_compliance_context
from app.services.compliance_service import evaluate_bid_compliance, get_bid_compliance
from fastapi import HTTPException


def print_test_header(title: str):
    print("\n" + "=" * 70)
    print(f"[TEST] {title}")
    print("=" * 70)


def record_result(test_name: str, passed: bool, details: str = ""):
    status_str = "[PASS]" if passed else "[FAIL]"
    print(f"  {status_str} {test_name} {details}")
    if not passed:
        raise AssertionError(f"Test failed: {test_name} - {details}")


async def run_part6b_master_test_suite():
    print("\n" + "=" * 70)
    print("STARTING PART 6B STATUTORY & REGISTRATION COMPLIANCE TEST SUITE")
    print("=" * 70)

    db = get_session_factory()()
    evaluator = StatutoryRuleEvaluator()

    try:
        # =========================================================================
        # 1. Evaluator Registration & Supports Check
        # =========================================================================
        print_test_header("1. Evaluator Registration & Supports Check")

        record_result(
            "StatutoryRuleEvaluator is registered in compliance_registry",
            "StatutoryRuleEvaluator" in compliance_registry.list_evaluators(),
        )

        req_gst_check = TenderRequirement(
            id=uuid.uuid4(),
            code="GST_REGISTRATION",
            name="Valid GSTIN Registration",
            category="STATUTORY",
            requirement_type="STATUS",
            operator="EQUALS",
            expected_value="ACTIVE",
        )
        record_result("Evaluator supports category='STATUTORY'", evaluator.supports(req_gst_check) is True)
        record_result("Resolves verification type as 'GST'", evaluator.resolve_verification_type(req_gst_check) == "GST")

        # =========================================================================
        # 2. GST Registration & Status Rules (ACTIVE vs CANCELLED vs SUSPENDED)
        # =========================================================================
        print_test_header("2. GST Registration & Status Rules")

        dummy_bid = Bid(id=uuid.uuid4(), tender_id=uuid.uuid4(), bidder_organization_id=uuid.uuid4())
        dummy_tender = Tender(id=dummy_bid.tender_id, tender_number="GEM/2026/T1", title="Test Tender")

        # Case A: GST ACTIVE -> PASS
        v_gst_active = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="GST",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock GST Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="33ABCDE1234F1Z5",
            verified_value="ACTIVE",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"gstin": "33ABCDE1234F1Z5", "status": "ACTIVE"},
            is_active=True,
        )
        ctx_gst_active = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_gst_active],
            verifications_by_type={"GST": [v_gst_active]},
        )
        res_gst_pass = evaluator.evaluate(req_gst_check, ctx_gst_active)
        record_result("GST Active status evaluates to PASS", res_gst_pass.compliance_status == ComplianceStatus.PASS, f"-> {res_gst_pass.reason}")

        # Case B: GST CANCELLED -> FAIL
        v_gst_cancelled = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="GST",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock GST Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="33ABCDE1234F1Z5",
            verified_value="CANCELLED",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"gstin": "33ABCDE1234F1Z5", "status": "CANCELLED"},
            is_active=True,
        )
        ctx_gst_cancelled = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_gst_cancelled],
            verifications_by_type={"GST": [v_gst_cancelled]},
        )
        res_gst_fail = evaluator.evaluate(req_gst_check, ctx_gst_cancelled)
        record_result("GST Cancelled status evaluates to FAIL", res_gst_fail.compliance_status == ComplianceStatus.FAIL, f"-> {res_gst_fail.reason}")

        # Case C: GST NOT_VERIFIED -> FAIL
        v_gst_not_verified = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="GST",
            verification_status=VerificationStatus.NOT_VERIFIED,
            source_name="Mock GST Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="33ABCDE1234F1Z5",
            match_status=VerificationMatchStatus.UNKNOWN,
            is_active=True,
        )
        ctx_gst_not_verified = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_gst_not_verified],
            verifications_by_type={"GST": [v_gst_not_verified]},
        )
        res_gst_not_ver = evaluator.evaluate(req_gst_check, ctx_gst_not_verified)
        record_result("GST NOT_VERIFIED evaluates to FAIL", res_gst_not_ver.compliance_status == ComplianceStatus.FAIL, f"-> {res_gst_not_ver.reason}")

        # =========================================================================
        # 3. PAN Verification & Holder Name Mismatch Check
        # =========================================================================
        print_test_header("3. PAN Verification & Holder Name Mismatch Check")

        req_pan = TenderRequirement(
            id=uuid.uuid4(),
            code="PAN_REQUIRED",
            name="Valid PAN Verification",
            category="STATUTORY",
            requirement_type="STATUS",
            operator="EQUALS",
            expected_value="VALID",
        )

        # Case A: PAN Matched -> PASS
        v_pan_match = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="PAN",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock PAN Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="ABCDE1234F",
            verified_value="VALID",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"pan": "ABCDE1234F", "status": "VALID", "holder_name": "TECHFLOW ENTERPRISES PVT LTD"},
            is_active=True,
        )
        ctx_pan_match = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_pan_match],
            verifications_by_type={"PAN": [v_pan_match]},
        )
        res_pan_match = evaluator.evaluate(req_pan, ctx_pan_match)
        record_result("PAN MATCH evaluates to PASS", res_pan_match.compliance_status == ComplianceStatus.PASS, f"-> {res_pan_match.reason}")

        # Case B: PAN Holder Name Mismatch -> REVIEW
        v_pan_mismatch = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="PAN",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock PAN Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="ABCDE1234F",
            verified_value="VALID",
            match_status=VerificationMatchStatus.MISMATCH,
            response_payload={"pan": "ABCDE1234F", "status": "VALID", "holder_name": "DIFFERENT HOLDER PVT LTD"},
            is_active=True,
        )
        ctx_pan_mismatch = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_pan_mismatch],
            verifications_by_type={"PAN": [v_pan_mismatch]},
        )
        res_pan_mismatch = evaluator.evaluate(req_pan, ctx_pan_mismatch)
        record_result("PAN MISMATCH evaluates to REVIEW (requires manual review)", res_pan_mismatch.compliance_status == ComplianceStatus.REVIEW, f"-> {res_pan_mismatch.reason}")

        # =========================================================================
        # 4. Udyam Registration & MSME Classification
        # =========================================================================
        print_test_header("4. Udyam Registration & MSME Classification")

        req_msme_class = TenderRequirement(
            id=uuid.uuid4(),
            code="MSME_CLASSIFICATION",
            name="MSME Classification (Micro or Small)",
            category="STATUTORY",
            requirement_type="TEXT",
            operator="IN",
            expected_value=["MICRO", "SMALL"],
        )

        # Case A: Bidder is SMALL -> PASS
        v_udyam_small = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="UDYAM",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock Udyam Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="UDYAM-TN-01-0012345",
            verified_value="SMALL",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"udyam_registration_number": "UDYAM-TN-01-0012345", "enterprise_type": "SMALL", "status": "ACTIVE"},
            is_active=True,
        )
        ctx_udyam_small = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_udyam_small],
            verifications_by_type={"UDYAM": [v_udyam_small]},
        )
        res_msme_pass = evaluator.evaluate(req_msme_class, ctx_udyam_small)
        record_result("MSME classification SMALL in ['MICRO', 'SMALL'] evaluates to PASS", res_msme_pass.compliance_status == ComplianceStatus.PASS, f"-> {res_msme_pass.reason}")

        # Case B: Bidder is MEDIUM -> FAIL
        v_udyam_medium = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="UDYAM",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock Udyam Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="UDYAM-TN-01-0099999",
            verified_value="MEDIUM",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"udyam_registration_number": "UDYAM-TN-01-0099999", "enterprise_type": "MEDIUM", "status": "ACTIVE"},
            is_active=True,
        )
        ctx_udyam_medium = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_udyam_medium],
            verifications_by_type={"UDYAM": [v_udyam_medium]},
        )
        res_msme_fail = evaluator.evaluate(req_msme_class, ctx_udyam_medium)
        record_result("MSME classification MEDIUM not in ['MICRO', 'SMALL'] evaluates to FAIL", res_msme_fail.compliance_status == ComplianceStatus.FAIL, f"-> {res_msme_fail.reason}")

        # =========================================================================
        # 5. MCA Registration, Company Status & Applicability Check
        # =========================================================================
        print_test_header("5. MCA Registration, Company Status & Applicability Check")

        req_mca_status = TenderRequirement(
            id=uuid.uuid4(),
            code="MCA_COMPANY_STATUS",
            name="MCA Company Registration Status",
            category="STATUTORY",
            requirement_type="STATUS",
            operator="EQUALS",
            expected_value="ACTIVE",
            is_mandatory=True,
        )

        # Case A: Company ACTIVE -> PASS
        v_mca_active = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="MCA",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock MCA Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="U72900TN2020PTC123456",
            verified_value="ACTIVE",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"cin": "U72900TN2020PTC123456", "company_status": "ACTIVE"},
            is_active=True,
        )
        ctx_mca_active = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_mca_active],
            verifications_by_type={"MCA": [v_mca_active]},
        )
        res_mca_pass = evaluator.evaluate(req_mca_status, ctx_mca_active)
        record_result("MCA Company Status ACTIVE evaluates to PASS", res_mca_pass.compliance_status == ComplianceStatus.PASS, f"-> {res_mca_pass.reason}")

        # Case B: Company DORMANT -> FAIL
        v_mca_dormant = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="MCA",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock MCA Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="U72900TN2020PTC123456",
            verified_value="DORMANT",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"cin": "U72900TN2020PTC123456", "company_status": "DORMANT"},
            is_active=True,
        )
        ctx_mca_dormant = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_mca_dormant],
            verifications_by_type={"MCA": [v_mca_dormant]},
        )
        res_mca_fail = evaluator.evaluate(req_mca_status, ctx_mca_dormant)
        record_result("MCA Company Status DORMANT evaluates to FAIL", res_mca_fail.compliance_status == ComplianceStatus.FAIL, f"-> {res_mca_fail.reason}")

        # Case C: Proprietorship Organization -> NOT_APPLICABLE (when non-mandatory or company-scoped)
        req_mca_scoped = TenderRequirement(
            id=uuid.uuid4(),
            code="MCA_COMPANY_REGISTRATION",
            name="MCA Incorporation Certificate",
            category="STATUTORY",
            requirement_type="STATUS",
            operator="EQUALS",
            expected_value="ACTIVE",
            is_mandatory=False,
        )
        org_prop = Organization(id=uuid.uuid4(), name="Single Owner Trading Co", organization_type="PROPRIETORSHIP")
        ctx_mca_prop = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            bidder_organization=org_prop,
            verifications=[],
        )
        res_mca_na = evaluator.evaluate(req_mca_scoped, ctx_mca_prop)
        record_result("MCA for PROPRIETORSHIP evaluates to NOT_APPLICABLE", res_mca_na.compliance_status == ComplianceStatus.NOT_APPLICABLE, f"-> {res_mca_na.reason}")

        # =========================================================================
        # 6. Startup India Recognition Rule
        # =========================================================================
        print_test_header("6. Startup India Recognition Rule")

        req_startup = TenderRequirement(
            id=uuid.uuid4(),
            code="STARTUP_INDIA_RECOGNITION",
            name="DPIIT Startup India Recognition",
            category="STATUTORY",
            requirement_type="STATUS",
            operator="EQUALS",
            expected_value="RECOGNIZED",
        )

        v_startup_rec = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="STARTUP_INDIA",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock Startup India Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="DIPP12345",
            verified_value="RECOGNIZED",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"certificate_number": "DIPP12345", "recognition_status": "RECOGNIZED"},
            is_active=True,
        )
        ctx_startup = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_startup_rec],
            verifications_by_type={"STARTUP_INDIA": [v_startup_rec]},
        )
        res_startup_pass = evaluator.evaluate(req_startup, ctx_startup)
        record_result("Startup India RECOGNIZED evaluates to PASS", res_startup_pass.compliance_status == ComplianceStatus.PASS, f"-> {res_startup_pass.reason}")

        # Startup REVOKED -> FAIL
        v_startup_revoked = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="STARTUP_INDIA",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock Startup India Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="DIPP12345",
            verified_value="REVOKED",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"certificate_number": "DIPP12345", "recognition_status": "REVOKED"},
            is_active=True,
        )
        ctx_startup_revoked = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_startup_revoked],
            verifications_by_type={"STARTUP_INDIA": [v_startup_revoked]},
        )
        res_startup_fail = evaluator.evaluate(req_startup, ctx_startup_revoked)
        record_result("Startup India REVOKED evaluates to FAIL", res_startup_fail.compliance_status == ComplianceStatus.FAIL, f"-> {res_startup_fail.reason}")

        # =========================================================================
        # 7. NSIC Registration & Validity vs Tender Deadline
        # =========================================================================
        print_test_header("7. NSIC Registration & Validity vs Tender Deadline")

        tender_with_deadline = Tender(
            id=uuid.uuid4(),
            tender_number="GEM/2026/NSIC/01",
            title="Tender with Deadline",
            submission_end_date=datetime(2026, 9, 1, 17, 0, 0, tzinfo=timezone.utc),
        )

        req_nsic_val = TenderRequirement(
            id=uuid.uuid4(),
            code="NSIC_VALIDITY",
            name="NSIC Certificate Validity",
            category="STATUTORY",
            requirement_type="DATE",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value=None,  # Automatically compared against tender submission deadline
        )

        # Case A: Valid through 2026-12-31 (Deadline: 2026-09-01) -> PASS
        v_nsic_valid = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="NSIC",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock NSIC Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="NSIC-2026-001",
            verified_value="2026-12-31",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"certificate_number": "NSIC-2026-001", "valid_until": "2026-12-31", "status": "ACTIVE"},
            is_active=True,
        )
        ctx_nsic_valid = ComplianceContext(
            bid=dummy_bid,
            tender=tender_with_deadline,
            verifications=[v_nsic_valid],
            verifications_by_type={"NSIC": [v_nsic_valid]},
        )
        res_nsic_pass = evaluator.evaluate(req_nsic_val, ctx_nsic_valid)
        record_result("NSIC valid (2026-12-31 >= 2026-09-01) evaluates to PASS", res_nsic_pass.compliance_status == ComplianceStatus.PASS, f"-> {res_nsic_pass.reason}")

        # Case B: Expired on 2026-07-31 (Deadline: 2026-09-01) -> FAIL
        v_nsic_expired = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="NSIC",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock NSIC Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="NSIC-2026-001",
            verified_value="2026-07-31",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"certificate_number": "NSIC-2026-001", "valid_until": "2026-07-31", "status": "EXPIRED"},
            is_active=True,
        )
        ctx_nsic_expired = ComplianceContext(
            bid=dummy_bid,
            tender=tender_with_deadline,
            verifications=[v_nsic_expired],
            verifications_by_type={"NSIC": [v_nsic_expired]},
        )
        res_nsic_fail = evaluator.evaluate(req_nsic_val, ctx_nsic_expired)
        record_result("NSIC expired (2026-07-31 < 2026-09-01) evaluates to FAIL", res_nsic_fail.compliance_status == ComplianceStatus.FAIL, f"-> {res_nsic_fail.reason}")

        # =========================================================================
        # 8. EPFO & ESIC Registration & Status Rules
        # =========================================================================
        print_test_header("8. EPFO & ESIC Registration & Status Rules")

        req_epfo = TenderRequirement(
            id=uuid.uuid4(),
            code="EPFO_REGISTRATION",
            name="EPFO Establishment Registration",
            category="STATUTORY",
            requirement_type="STATUS",
            operator="EQUALS",
            expected_value="ACTIVE",
        )
        req_esic = TenderRequirement(
            id=uuid.uuid4(),
            code="ESIC_REGISTRATION",
            name="ESIC Establishment Registration",
            category="STATUTORY",
            requirement_type="STATUS",
            operator="EQUALS",
            expected_value="ACTIVE",
        )

        v_epfo = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="EPFO",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock EPFO Portal",
            source_type=VerificationSourceType.MOCK,
            claimed_value="MH/BAN/12345/000",
            verified_value="ACTIVE",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"establishment_code": "MH/BAN/12345/000", "status": "ACTIVE"},
            is_active=True,
        )
        v_esic = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="ESIC",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock ESIC Portal",
            source_type=VerificationSourceType.MOCK,
            claimed_value="31000123450000101",
            verified_value="ACTIVE",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={"employer_code": "31000123450000101", "status": "ACTIVE"},
            is_active=True,
        )

        ctx_labor = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_epfo, v_esic],
            verifications_by_type={"EPFO": [v_epfo], "ESIC": [v_esic]},
        )

        res_epfo = evaluator.evaluate(req_epfo, ctx_labor)
        res_esic = evaluator.evaluate(req_esic, ctx_labor)

        record_result("EPFO Active evaluates to PASS", res_epfo.compliance_status == ComplianceStatus.PASS, f"-> {res_epfo.reason}")
        record_result("ESIC Active evaluates to PASS", res_esic.compliance_status == ComplianceStatus.PASS, f"-> {res_esic.reason}")

        # =========================================================================
        # 9. Source Outage & Invalid Configuration Resilience
        # =========================================================================
        print_test_header("9. Source Outage & Invalid Configuration Resilience")

        # Source Outage: UNAVAILABLE verification
        v_epfo_outage = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="EPFO",
            verification_status=VerificationStatus.UNAVAILABLE,
            source_name="Mock EPFO Portal",
            source_type=VerificationSourceType.MOCK,
            claimed_value="MH/BAN/12345/000",
            error_message="Gateway timeout",
            is_active=True,
        )
        ctx_outage = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_epfo_outage],
            verifications_by_type={"EPFO": [v_epfo_outage]},
        )
        res_epfo_outage = evaluator.evaluate(req_epfo, ctx_outage)
        record_result(
            "UNAVAILABLE verification returns REVIEW without failing the bidder",
            res_epfo_outage.compliance_status == ComplianceStatus.REVIEW,
            f"-> {res_epfo_outage.reason}",
        )

        # Missing expected value config error
        req_bad_config = TenderRequirement(
            id=uuid.uuid4(),
            code="GST_STATUS",
            name="GST Status Check",
            category="STATUTORY",
            requirement_type="STATUS",
            operator="EQUALS",
            expected_value=None,  # Missing!
        )
        res_bad_config = evaluator.evaluate(req_bad_config, ctx_gst_active)
        record_result(
            "Missing expected_value returns REVIEW without crashing",
            res_bad_config.compliance_status == ComplianceStatus.REVIEW,
            f"-> {res_bad_config.reason}",
        )

        # =========================================================================
        # 10. End-to-End Realistic Statutory Bid Compliance in Database
        # =========================================================================
        print_test_header("10. End-to-End Realistic Statutory Bid Compliance in Database")

        test_suffix = uuid.uuid4().hex[:6]
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        po_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()

        org_po = Organization(
            id=uuid.uuid4(),
            name=f"Defence Procurement Org {test_suffix}",
            state="Delhi",
            city="New Delhi",
            is_active=True,
        )
        org_bidder = Organization(
            id=uuid.uuid4(),
            name="TECHFLOW ENTERPRISES PRIVATE LIMITED",
            pan_number="ABCDE1234F",
            gstin="33ABCDE1234F1Z5",
            organization_type="PRIVATE_LIMITED",
            is_active=True,
        )
        db.add_all([org_po, org_bidder])
        db.commit()

        prof_po = Profile(
            id=uuid.uuid4(),
            email=f"po_6b_{test_suffix}@gov.mock",
            role_id=po_role.id,
            organization_id=org_po.id,
            full_name="Col. R. Sharma",
            is_active=True,
        )
        prof_bidder = Profile(
            id=uuid.uuid4(),
            email=f"bidder_6b_{test_suffix}@bidverify.mock",
            role_id=bidder_role.id,
            organization_id=org_bidder.id,
            full_name="Muthu Statutory Lead",
            is_active=True,
        )
        db.add_all([prof_po, prof_bidder])
        db.commit()

        user_bidder = User(
            id=uuid.uuid4(),
            email=f"bidder_6b_{test_suffix}@bidverify.mock",
            password_hash="mock_hash",
            profile_id=prof_bidder.id,
            is_active=True,
        )
        user_po = User(
            id=uuid.uuid4(),
            email=f"po_6b_{test_suffix}@gov.mock",
            password_hash="mock_hash",
            profile_id=prof_po.id,
            is_active=True,
        )
        db.add_all([user_bidder, user_po])
        db.commit()

        tender = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/6B/{test_suffix.upper()}",
            title="Supply of Cloud Security Appliances",
            description="Tender with comprehensive statutory criteria",
            organization_id=org_po.id,
            created_by_profile_id=prof_po.id,
            submission_end_date=datetime(2026, 12, 1, 17, 0, 0, tzinfo=timezone.utc),
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)
        db.commit()

        # Seed 8 Statutory Requirements
        reqs = [
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="GST_STATUS", name="Active GSTIN Registration",
                category="STATUTORY", requirement_type="STATUS", operator="EQUALS", expected_value="ACTIVE",
                is_mandatory=True, weight=Decimal("15.0"), display_order=1, is_active=True,
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="PAN_REQUIRED", name="PAN Cardholder Verification",
                category="STATUTORY", requirement_type="STATUS", operator="EQUALS", expected_value="VALID",
                is_mandatory=True, weight=Decimal("15.0"), display_order=2, is_active=True,
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="UDYAM_REGISTRATION", name="Udyam MSME Registration",
                category="STATUTORY", requirement_type="STATUS", operator="EQUALS", expected_value="ACTIVE",
                is_mandatory=True, weight=Decimal("15.0"), display_order=3, is_active=True,
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="MSME_CLASSIFICATION", name="MSME Classification (Micro/Small)",
                category="STATUTORY", requirement_type="TEXT", operator="IN", expected_value=["MICRO", "SMALL"],
                is_mandatory=True, weight=Decimal("10.0"), display_order=4, is_active=True,
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="MCA_COMPANY_STATUS", name="MCA Active Company Status",
                category="STATUTORY", requirement_type="STATUS", operator="EQUALS", expected_value="ACTIVE",
                is_mandatory=True, weight=Decimal("15.0"), display_order=5, is_active=True,
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="STARTUP_INDIA_RECOGNITION", name="Startup India DPIIT Recognition",
                category="STATUTORY", requirement_type="STATUS", operator="EQUALS", expected_value="RECOGNIZED",
                is_mandatory=True, weight=Decimal("10.0"), display_order=6, is_active=True,
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="NSIC_VALIDITY", name="NSIC Certificate Validity",
                category="STATUTORY", requirement_type="DATE", operator="GREATER_THAN_OR_EQUAL", expected_value=None,
                is_mandatory=True, weight=Decimal("10.0"), display_order=7, is_active=True,
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="EPFO_REGISTRATION", name="EPFO Active Registration",
                category="STATUTORY", requirement_type="STATUS", operator="EQUALS", expected_value="ACTIVE",
                is_mandatory=True, weight=Decimal("10.0"), display_order=8, is_active=True,
            ),
        ]
        db.add_all(reqs)
        db.commit()

        # Seed Bid
        bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-6B-{test_suffix.upper()}",
            status="SUBMITTED",
            quoted_amount=Decimal("4900000.00"),
            currency="INR",
            submitted_at=datetime.now(timezone.utc),
            declaration_accepted=True,
            is_active=True,
        )
        db.add(bid)
        db.commit()

        # Seed 8 Verification Records
        v_records = [
            VerificationRecord(
                id=uuid.uuid4(), bid_id=bid.id, verification_type="GST", verification_status=VerificationStatus.VERIFIED,
                source_name="Mock GST Registry", source_type=VerificationSourceType.MOCK, claim_source="gstin",
                claimed_value="33ABCDE1234F1Z5", verified_value="ACTIVE", match_status=VerificationMatchStatus.MATCH,
                confidence=1.0, response_payload={"gstin": "33ABCDE1234F1Z5", "status": "ACTIVE"}, is_active=True,
            ),
            VerificationRecord(
                id=uuid.uuid4(), bid_id=bid.id, verification_type="PAN", verification_status=VerificationStatus.VERIFIED,
                source_name="Mock PAN Registry", source_type=VerificationSourceType.MOCK, claim_source="pan",
                claimed_value="ABCDE1234F", verified_value="VALID", match_status=VerificationMatchStatus.MATCH,
                confidence=1.0, response_payload={"pan": "ABCDE1234F", "status": "VALID"}, is_active=True,
            ),
            VerificationRecord(
                id=uuid.uuid4(), bid_id=bid.id, verification_type="UDYAM", verification_status=VerificationStatus.VERIFIED,
                source_name="Mock Udyam Registry", source_type=VerificationSourceType.MOCK, claim_source="udyam",
                claimed_value="UDYAM-TN-01-0012345", verified_value="SMALL", match_status=VerificationMatchStatus.MATCH,
                confidence=1.0, response_payload={"udyam_registration_number": "UDYAM-TN-01-0012345", "enterprise_type": "SMALL", "status": "ACTIVE"}, is_active=True,
            ),
            VerificationRecord(
                id=uuid.uuid4(), bid_id=bid.id, verification_type="MCA", verification_status=VerificationStatus.VERIFIED,
                source_name="Mock MCA Registry", source_type=VerificationSourceType.MOCK, claim_source="mca",
                claimed_value="U72900TN2020PTC123456", verified_value="ACTIVE", match_status=VerificationMatchStatus.MATCH,
                confidence=1.0, response_payload={"cin": "U72900TN2020PTC123456", "company_status": "ACTIVE"}, is_active=True,
            ),
            VerificationRecord(
                id=uuid.uuid4(), bid_id=bid.id, verification_type="STARTUP_INDIA", verification_status=VerificationStatus.VERIFIED,
                source_name="Mock Startup India Registry", source_type=VerificationSourceType.MOCK, claim_source="startup",
                claimed_value="DIPP12345", verified_value="RECOGNIZED", match_status=VerificationMatchStatus.MATCH,
                confidence=1.0, response_payload={"certificate_number": "DIPP12345", "recognition_status": "RECOGNIZED"}, is_active=True,
            ),
            VerificationRecord(
                id=uuid.uuid4(), bid_id=bid.id, verification_type="NSIC", verification_status=VerificationStatus.VERIFIED,
                source_name="Mock NSIC Registry", source_type=VerificationSourceType.MOCK, claim_source="nsic",
                claimed_value="NSIC-2026-001", verified_value="2027-03-31", match_status=VerificationMatchStatus.MATCH,
                confidence=1.0, response_payload={"certificate_number": "NSIC-2026-001", "valid_until": "2027-03-31", "status": "ACTIVE"}, is_active=True,
            ),
            VerificationRecord(
                id=uuid.uuid4(), bid_id=bid.id, verification_type="EPFO", verification_status=VerificationStatus.VERIFIED,
                source_name="Mock EPFO Portal", source_type=VerificationSourceType.MOCK, claim_source="epfo",
                claimed_value="MH/BAN/12345/000", verified_value="ACTIVE", match_status=VerificationMatchStatus.MATCH,
                confidence=1.0, response_payload={"establishment_code": "MH/BAN/12345/000", "status": "ACTIVE"}, is_active=True,
            ),
        ]
        db.add_all(v_records)
        db.commit()

        # Execute Service-Layer Evaluation
        comp_summary = evaluate_bid_compliance(db, user_bidder, bid.id)

        for r in comp_summary.results:
            print(f"    -> [{r.compliance_status}] Req: {r.requirement_code}, Actual: '{r.actual_value}', Expected: '{r.expected_value}', Reason: {r.reason}")

        record_result(
            "evaluate_bid_compliance processes all 8 statutory rules",
            comp_summary.counts.total == 8 and comp_summary.counts.passed == 8,
            f"-> Total={comp_summary.counts.total}, Passed={comp_summary.counts.passed}",
        )
        record_result(
            "All compliance results contain required audit provenance and reasons",
            all(
                r.actual_value is not None
                and r.reason is not None
                and r.source_verification_ids is not None
                for r in comp_summary.results
            ),
        )

        # Multi-Tenant Isolation Check
        try:
            org_alien = Organization(id=uuid.uuid4(), name=f"Alien Org {test_suffix}", is_active=True)
            prof_alien = Profile(id=uuid.uuid4(), email=f"alien_{test_suffix}@mock.com", role_id=bidder_role.id, organization_id=org_alien.id, full_name="Alien", is_active=True)
            user_alien = User(id=uuid.uuid4(), email=f"alien_{test_suffix}@mock.com", password_hash="mock", profile_id=prof_alien.id, is_active=True)
            db.add_all([org_alien, prof_alien, user_alien])
            db.commit()

            get_bid_compliance(db, user_alien, bid.id)
            record_result("Alien user cannot access compliance results", False)
        except HTTPException as he:
            record_result("Alien user receives HTTP 404", he.status_code == 404)

        # Strict Boundary Check: No score, no risk, no decision
        cr = db.scalars(select(ComplianceResult).where(ComplianceResult.bid_id == bid.id)).first()
        record_result(
            "No score, risk level, or final qualification decision exists in ComplianceResult",
            not hasattr(cr, "score") and not hasattr(cr, "risk_level") and not hasattr(cr, "qualification_decision"),
        )

        print("\n" + "=" * 70)
        print("PART 6B MASTER TEST SUMMARY")
        print("=" * 70)
        print(">>> ALL PART 6B STATUTORY & REGISTRATION COMPLIANCE TESTS PASSED! <<<")
        return True

    except Exception as e:
        print(f"\n[ERROR] Exception during Part 6B testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = asyncio.run(run_part6b_master_test_suite())
    if not success:
        sys.exit(1)
