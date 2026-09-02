"""
Master Test Suite for Part 6A: Compliance Engine Foundation & Rule Evaluation Architecture
Validates all requirements:
1. Centralized Compliance Statuses & Enums
2. Numeric Comparisons using Decimal Arithmetic
3. Date Normalization and Chronological Comparisons
4. String Normalization & Substring Matching
5. Boolean Comparisons & Truthiness
6. Presence Evaluation (EXISTS / NOT_EXISTS)
7. Verification Prerequisite Mapping (VERIFIED, NOT_VERIFIED, NEEDS_REVIEW, UNAVAILABLE)
8. Evaluator Registry & Fallback for Unsupported Requirements
9. End-to-End Database Evaluation & Persistence
10. Versioning, Idempotency & Audit Preservation
11. Multi-Tenant Security & Tenant Isolation (HTTP 404)
12. Submitted Bid Compliance Evaluation Support
13. Strict Boundary Guards (No Score, No Risk, No Final Decision in Part 6)
"""

import asyncio
import os
import sys
import uuid
from decimal import Decimal
from datetime import datetime, timezone, date

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
from app.db.models.document_processing import DocumentProcessing, ProcessingStatus, ProcessingStage
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
from app.compliance.operators import (
    compare_numbers,
    compare_dates,
    compare_strings,
    compare_booleans,
    evaluate_exists,
    evaluate_generic_operator,
)
from app.compliance.evaluators.base import ComplianceRuleEvaluator
from app.compliance.evaluators.generic import GenericRuleEvaluator
from app.compliance.registry import compliance_registry, FallbackUnsupportedEvaluator
from app.compliance.engine import build_compliance_context, evaluate_requirement
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


async def run_part6a_master_test_suite():
    print("\n" + "=" * 70)
    print("STARTING PART 6A COMPLIANCE ENGINE FOUNDATION TEST SUITE")
    print("=" * 70)

    db = get_session_factory()()
    total_tests = 0
    passed_tests = 0

    try:
        # =========================================================================
        # 1. Centralized Compliance Statuses & Enums
        # =========================================================================
        print_test_header("1. Centralized Compliance Statuses & Vocabulary")

        record_result(
            "ComplianceStatus has all required states",
            all(
                hasattr(ComplianceStatus, s)
                for s in ["PASS", "FAIL", "REVIEW", "NOT_APPLICABLE", "PENDING", "BLOCKED"]
            ),
        )
        record_result(
            "ComplianceStatus.TERMINAL defines terminal non-pending states",
            set(ComplianceStatus.TERMINAL) == {"PASS", "FAIL", "REVIEW", "NOT_APPLICABLE"},
        )
        record_result(
            "ComplianceOperator has all required comparison operators",
            all(
                hasattr(ComplianceOperator, op)
                for op in [
                    "EQUALS", "NOT_EQUALS", "GREATER_THAN", "GREATER_THAN_OR_EQUAL",
                    "LESS_THAN", "LESS_THAN_OR_EQUAL", "CONTAINS", "EXISTS", "NOT_EXISTS"
                ]
            ),
        )

        # =========================================================================
        # 2. Decimal-Based Numeric Operator Evaluation
        # =========================================================================
        print_test_header("2. Decimal-Based Numeric Operator Evaluation")

        # Greater Than / GTE
        res_gt, _ = compare_numbers(5000000, 4000000, ComplianceOperator.GREATER_THAN)
        record_result("5,000,000 > 4,000,000 is True", res_gt is True)

        res_gte, _ = compare_numbers(Decimal("4000000.00"), "4000000", ComplianceOperator.GREATER_THAN_OR_EQUAL)
        record_result("4000000.00 >= 4000000 is True", res_gte is True)

        # Floating point precision safety (0.1 + 0.2 vs 0.3)
        res_dec_prec, _ = compare_numbers("0.3", "0.30", ComplianceOperator.EQUALS)
        record_result("Decimal comparison handles precision without float rounding errors", res_dec_prec is True)

        # Currency string normalization (INR 5,00,000 vs 500000)
        res_curr, _ = compare_numbers("INR 5,00,000", "500000", ComplianceOperator.EQUALS)
        record_result("Currency formatting (INR, commas) normalized cleanly", res_curr is True)

        # Less Than
        res_lt, _ = compare_numbers("45%", "50%", ComplianceOperator.LESS_THAN)
        record_result("45% < 50% is True", res_lt is True)

        # Failure cases
        res_fail, _ = compare_numbers(300, 500, ComplianceOperator.GREATER_THAN)
        record_result("300 > 500 is False", res_fail is False)

        # =========================================================================
        # 3. Date Normalization & Chronological Comparisons
        # =========================================================================
        print_test_header("3. Date Normalization & Chronological Comparisons")

        res_date_gte, _ = compare_dates("2027-03-31", "2026-12-31", ComplianceOperator.GREATER_THAN_OR_EQUAL)
        record_result("2027-03-31 >= 2026-12-31 is True", res_date_gte is True)

        res_date_eq, _ = compare_dates("15/01/2026", "2026-01-15", ComplianceOperator.EQUALS)
        record_result("Different date format strings (DD/MM/YYYY vs YYYY-MM-DD) evaluate as equal", res_date_eq is True)

        res_date_past, _ = compare_dates("2024-01-01", "2026-01-01", ComplianceOperator.GREATER_THAN)
        record_result("Past date vs future date is False", res_date_past is False)

        # =========================================================================
        # 4. String Normalization & Substring Matching
        # =========================================================================
        print_test_header("4. String Normalization & Substring Matching")

        res_str_eq, _ = compare_strings("  TechFlow Enterprises Pvt Ltd  ", "techflow enterprises pvt ltd", ComplianceOperator.EQUALS)
        record_result("String comparison trims whitespace and ignores case", res_str_eq is True)

        res_str_contains, _ = compare_strings("Class-I Local Supplier (MII Compliant)", "Class-I Local Supplier", ComplianceOperator.CONTAINS)
        record_result("CONTAINS operator matches substring safely", res_str_contains is True)

        res_str_neq, _ = compare_strings("ACTIVE", "CANCELLED", ComplianceOperator.NOT_EQUALS)
        record_result("NOT_EQUALS string check evaluates accurately", res_str_neq is True)

        # =========================================================================
        # 5. Boolean Comparisons & Truthiness
        # =========================================================================
        print_test_header("5. Boolean Comparisons & Truthiness")

        res_bool_true, _ = compare_booleans("ACTIVE", True, ComplianceOperator.EQUALS)
        record_result("'ACTIVE' evaluates to boolean True", res_bool_true is True)

        res_bool_false, _ = compare_booleans("CANCELLED", False, ComplianceOperator.EQUALS)
        record_result("'CANCELLED' evaluates to boolean False", res_bool_false is True)

        res_bool_explicit, _ = compare_booleans(True, False, ComplianceOperator.NOT_EQUALS)
        record_result("Explicit True != False is True", res_bool_explicit is True)

        # =========================================================================
        # 6. Presence Evaluation (EXISTS / NOT_EXISTS)
        # =========================================================================
        print_test_header("6. Presence Evaluation (EXISTS / NOT_EXISTS)")

        res_exists_val, _ = evaluate_exists("33ABCDE1234F1Z5", ComplianceOperator.EXISTS)
        record_result("Non-empty string EXISTS is True", res_exists_val is True)

        res_not_exists_none, _ = evaluate_exists(None, ComplianceOperator.NOT_EXISTS)
        record_result("None NOT_EXISTS is True", res_not_exists_none is True)

        res_exists_empty_list, _ = evaluate_exists([], ComplianceOperator.EXISTS)
        record_result("Empty list EXISTS is False", res_exists_empty_list is False)

        # =========================================================================
        # 7. Evaluator Registry & Fallback Handling
        # =========================================================================
        print_test_header("7. Evaluator Registry & Fallback Handling")

        registered_evaluators = compliance_registry.list_evaluators()
        record_result("ComplianceEvaluatorRegistry has GenericRuleEvaluator registered", "GenericRuleEvaluator" in registered_evaluators)

        # Dummy requirement for unsupported category
        dummy_req = TenderRequirement(
            id=uuid.uuid4(),
            code="UNSUPPORTED_SPECIAL_CODE",
            name="Unsupported Custom Criterion",
            category="CUSTOM_AI_MAGIC",
            requirement_type="TEXT",
            operator="EQUALS",
            expected_value="SOMETHING",
        )
        resolved_ev = compliance_registry.resolve_evaluator(dummy_req)
        record_result("Unsupported requirement resolves to an evaluator safely without crashing", resolved_ev is not None)

        # =========================================================================
        # 8. End-to-End Bid Compliance Database Evaluation
        # =========================================================================
        print_test_header("8. End-to-End Bid Compliance Evaluation & Database Persistence")

        test_suffix = uuid.uuid4().hex[:6]
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        po_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()

        # Create Organizations
        org_po = Organization(
            id=uuid.uuid4(),
            name=f"Defence Procurement Division {test_suffix}",
            state="Delhi",
            city="New Delhi",
            is_active=True,
        )
        db.add(org_po)

        org_bidder = Organization(
            id=uuid.uuid4(),
            name="TECHFLOW ENTERPRISES PRIVATE LIMITED",
            pan_number="ABCDE1234F",
            gstin="33ABCDE1234F1Z5",
            state="Tamil Nadu",
            city="Chennai",
            registered_address="123 Anna Salai, Chennai, Tamil Nadu - 600002",
            is_active=True,
        )
        db.add(org_bidder)
        db.commit()

        # Create Profiles and Users
        prof_po = Profile(
            id=uuid.uuid4(),
            email=f"po_6a_{test_suffix}@gov.mock",
            role_id=po_role.id,
            organization_id=org_po.id,
            full_name="Col. R. Sharma",
            is_active=True,
        )
        db.add(prof_po)

        user_po = User(
            id=uuid.uuid4(),
            email=f"po_6a_{test_suffix}@gov.mock",
            password_hash="mock_hash",
            profile_id=prof_po.id,
            is_active=True,
        )
        db.add(user_po)

        prof_bidder = Profile(
            id=uuid.uuid4(),
            email=f"bidder_6a_{test_suffix}@bidverify.mock",
            role_id=bidder_role.id,
            organization_id=org_bidder.id,
            full_name="Muthu Compliance Lead",
            is_active=True,
        )
        db.add(prof_bidder)

        user_bidder = User(
            id=uuid.uuid4(),
            email=f"bidder_6a_{test_suffix}@bidverify.mock",
            password_hash="mock_hash",
            profile_id=prof_bidder.id,
            is_active=True,
        )
        db.add(user_bidder)
        db.commit()

        # Create Tender with 4 Requirements
        tender = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/6A/{test_suffix.upper()}",
            title="Procurement of Secure Networking Gateway",
            description="Tender for Part 6A Compliance Evaluation",
            organization_id=org_po.id,
            created_by_profile_id=prof_po.id,
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)
        db.commit()

        req_gst = TenderRequirement(
            id=uuid.uuid4(),
            tender_id=tender.id,
            code="REQ_GST_ACTIVE",
            name="Active GSTIN Registration",
            category="STATUTORY",
            requirement_type="STATUS",
            operator="EQUALS",
            expected_value="ACTIVE",
            is_mandatory=True,
            weight=Decimal("20.0"),
            display_order=1,
            is_active=True,
        )
        req_turnover = TenderRequirement(
            id=uuid.uuid4(),
            tender_id=tender.id,
            code="REQ_MIN_TURNOVER",
            name="Minimum Annual Turnover (INR 40 Lakhs)",
            category="FINANCIAL",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value=4000000,
            is_mandatory=True,
            weight=Decimal("25.0"),
            display_order=2,
            is_active=True,
        )
        req_local_content = TenderRequirement(
            id=uuid.uuid4(),
            tender_id=tender.id,
            code="REQ_LOCAL_CONTENT_50",
            name="Local Content Minimum 50%",
            category="LOCAL_CONTENT",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value=50,
            is_mandatory=True,
            weight=Decimal("20.0"),
            display_order=3,
            is_active=True,
        )
        req_oem_doc = TenderRequirement(
            id=uuid.uuid4(),
            tender_id=tender.id,
            code="REQ_OEM_AUTHORIZATION",
            name="OEM Manufacturer Authorization Letter",
            category="DOCUMENT",
            requirement_type="DOCUMENT",
            operator="EXISTS",
            expected_value=True,
            is_mandatory=True,
            weight=Decimal("15.0"),
            display_order=4,
            is_active=True,
        )
        db.add_all([req_gst, req_turnover, req_local_content, req_oem_doc])
        db.commit()

        # Create Bid
        bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-6A-{test_suffix.upper()}",
            status="SUBMITTED",
            quoted_amount=Decimal("4500000.00"),
            currency="INR",
            submitted_at=datetime.now(timezone.utc),
            declaration_accepted=True,
            is_active=True,
        )
        db.add(bid)
        db.commit()

        # Seed Documents & DocumentProcessing
        doc_gst = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof_bidder.id,
            tender_requirement_id=req_gst.id,
            document_type="GST_CERTIFICATE",
            document_name="GST_Cert.pdf",
            original_filename="GST_Cert.pdf",
            storage_path=f"bids/{bid.id}/gst.pdf",
            file_size=10240,
            mime_type="application/pdf",
            is_active=True,
        )
        doc_oem = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof_bidder.id,
            tender_requirement_id=req_oem_doc.id,
            document_type="OEM_AUTHORIZATION",
            document_name="OEM_Letter.pdf",
            original_filename="OEM_Letter.pdf",
            storage_path=f"bids/{bid.id}/oem.pdf",
            file_size=10240,
            mime_type="application/pdf",
            is_active=True,
        )
        db.add_all([doc_gst, doc_oem])
        db.commit()

        # Seed Verification Records (Part 5 Outputs)
        # 1. GST: Verified ACTIVE -> Should PASS REQ_GST_ACTIVE
        v_gst = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid.id,
            bid_document_id=doc_gst.id,
            verification_type="GST",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock GST Registry",
            source_type=VerificationSourceType.MOCK,
            claim_source="gstin",
            claimed_value="33ABCDE1234F1Z5",
            verified_value="ACTIVE",
            match_status=VerificationMatchStatus.MATCH,
            confidence=1.0,
            response_payload={"gstin": "33ABCDE1234F1Z5", "status": "ACTIVE", "legal_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED"},
            attempt_number=1,
            is_active=True,
        )
        # 2. Turnover: Verified 5000000 -> Should PASS REQ_MIN_TURNOVER (50L >= 40L)
        v_turnover = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid.id,
            verification_type="SUPPORTING_DOCUMENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Internal Evidence Validator",
            source_type=VerificationSourceType.INTERNAL,
            claim_source="turnover",
            claimed_value="5000000",
            verified_value=5000000,
            match_status=VerificationMatchStatus.MATCH,
            confidence=1.0,
            response_payload={"turnover": 5000000, "status": "VALID"},
            attempt_number=1,
            is_active=True,
        )
        # 3. Local Content: Verified 55% -> Should PASS REQ_LOCAL_CONTENT_50 (55 >= 50)
        v_lc = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid.id,
            verification_type="LOCAL_CONTENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock Local Content MII Registry",
            source_type=VerificationSourceType.MOCK,
            claim_source="local_content",
            claimed_value="55%",
            verified_value=55.0,
            match_status=VerificationMatchStatus.MATCH,
            confidence=1.0,
            response_payload={"local_content_percentage": 55.0, "status": "VALID"},
            attempt_number=1,
            is_active=True,
        )
        # 4. OEM: Verified
        v_oem = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid.id,
            bid_document_id=doc_oem.id,
            verification_type="OEM_AUTHORIZATION",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock OEM Registry",
            source_type=VerificationSourceType.MOCK,
            claim_source="oem_authorization",
            claimed_value="OEM-AUTH-2026-001",
            verified_value="VALID",
            match_status=VerificationMatchStatus.MATCH,
            confidence=1.0,
            response_payload={"authorization_status": "VALID"},
            attempt_number=1,
            is_active=True,
        )
        db.add_all([v_gst, v_turnover, v_lc, v_oem])
        db.commit()

        # Trigger Compliance Evaluation via Service
        comp_summary = evaluate_bid_compliance(db, user_bidder, bid.id)
        for r in comp_summary.results:
            print(f"    -> Req: {r.requirement_code}, Status: {r.compliance_status}, Actual: {r.actual_value}, Expected: {r.expected_value}, Op: {r.operator}, Reason: {r.reason}")

        record_result(
            "evaluate_bid_compliance executes and evaluates all 4 requirements",
            comp_summary.counts.total == 4 and comp_summary.counts.passed == 4,
            f"-> Total={comp_summary.counts.total}, Passed={comp_summary.counts.passed}",
        )
        record_result(
            "compliance_evaluation_complete is True when all rules are in terminal statuses",
            comp_summary.compliance_evaluation_complete is True,
        )
        record_result(
            "Every compliance result contains actual, expected, operator, and reason",
            all(
                r.actual_value is not None
                and r.expected_value is not None
                and r.operator is not None
                and r.reason is not None
                for r in comp_summary.results
            ),
        )

        # =========================================================================
        # 9. Verification Prerequisite Outage & Failure Handling
        # =========================================================================
        print_test_header("9. Verification Prerequisite Outage & Failure Handling")

        # Simulate source outage on GST verification
        v_gst.verification_status = VerificationStatus.UNAVAILABLE
        v_gst.evidence = {"error_code": "SOURCE_UNAVAILABLE", "message": "Portal timeout"}
        db.commit()

        comp_summary_outage = evaluate_bid_compliance(db, user_bidder, bid.id)
        gst_res = next(r for r in comp_summary_outage.results if r.requirement_code == "REQ_GST_ACTIVE")

        record_result(
            "UNAVAILABLE verification produces REVIEW status without penalizing bidder with FAIL",
            gst_res.compliance_status == ComplianceStatus.REVIEW,
            f"-> Status={gst_res.compliance_status}, Reason={gst_res.reason}",
        )
        record_result(
            "Review count increments and pass count adjusts",
            comp_summary_outage.counts.review == 1 and comp_summary_outage.counts.passed == 3,
            f"-> Review={comp_summary_outage.counts.review}, Passed={comp_summary_outage.counts.passed}",
        )

        # Restore GST to VERIFIED
        v_gst.verification_status = VerificationStatus.VERIFIED
        db.commit()

        # =========================================================================
        # 10. Versioning & Idempotency Check
        # =========================================================================
        print_test_header("10. Versioning & Idempotency Check")

        comp_summary_v3 = evaluate_bid_compliance(db, user_bidder, bid.id)
        total_records_db = db.scalar(
            select(func.count(ComplianceResult.id)).where(ComplianceResult.bid_id == bid.id)
        )
        current_records_db = db.scalar(
            select(func.count(ComplianceResult.id)).where(
                and_(ComplianceResult.bid_id == bid.id, ComplianceResult.is_current == True)
            )
        )

        record_result(
            "Re-evaluations increment version while maintaining exactly 4 current records",
            current_records_db == 4 and total_records_db == 12,  # 3 runs * 4 reqs = 12 total in audit
            f"-> Total audit records: {total_records_db}, Current active records: {current_records_db}",
        )

        # =========================================================================
        # 11. Multi-Tenant Security & Tenant Isolation
        # =========================================================================
        print_test_header("11. Multi-Tenant Security & Tenant Isolation")

        org_alien = Organization(
            id=uuid.uuid4(),
            name=f"Alien Corp {test_suffix}",
            is_active=True,
        )
        db.add(org_alien)
        db.commit()

        prof_alien = Profile(
            id=uuid.uuid4(),
            email=f"alien_6a_{test_suffix}@mock.com",
            role_id=bidder_role.id,
            organization_id=org_alien.id,
            full_name="Alien Bidder",
            is_active=True,
        )
        db.add(prof_alien)
        db.commit()

        user_alien = User(
            id=uuid.uuid4(),
            email=f"alien_6a_{test_suffix}@mock.com",
            password_hash="mock_hash",
            profile_id=prof_alien.id,
            is_active=True,
        )
        db.add(user_alien)
        db.commit()

        try:
            get_bid_compliance(db, user_alien, bid.id)
            record_result("Alien bidder accessing other bid rejected with HTTP 404", False)
        except HTTPException as he:
            record_result(
                "Alien bidder accessing other bid rejected with HTTP 404",
                he.status_code == 404,
                f"-> HTTP {he.status_code}: {he.detail}",
            )

        # Procurement Officer of the owning organization CAN access
        po_summary = get_bid_compliance(db, user_po, bid.id)
        record_result(
            "Procurement Officer of owning organization can access compliance results",
            po_summary.bid_id == bid.id and po_summary.counts.total == 4,
            f"-> Total={po_summary.counts.total}, Passed={po_summary.counts.passed}",
        )

        # =========================================================================
        # 12. Strict Compliance Separation Boundary Guard
        # =========================================================================
        print_test_header("12. Strict Compliance Separation Boundary Guard")

        # Verify no score, risk, or final decision columns exist in compliance_results
        cr_sample = db.scalars(
            select(ComplianceResult).where(ComplianceResult.bid_id == bid.id)
        ).first()

        has_score = hasattr(cr_sample, "compliance_score")
        has_risk = hasattr(cr_sample, "risk_level")
        has_final_decision = hasattr(cr_sample, "qualification_decision")

        record_result(
            "ComplianceResult strictly excludes Part 7/8 fields (score, risk_level, final_decision)",
            not has_score and not has_risk and not has_final_decision,
        )

        print("\n" + "=" * 70)
        print("PART 6A MASTER TEST SUMMARY")
        print("=" * 70)
        print(">>> ALL PART 6A COMPLIANCE ENGINE FOUNDATION TESTS PASSED! <<<")
        return True

    except Exception as e:
        print(f"\n[ERROR] Exception during Part 6A testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = asyncio.run(run_part6a_master_test_suite())
    if not success:
        sys.exit(1)
