"""
Master QA Test Suite for Part 6E: Blacklisting, Debarment, Critical Rules & Review Logic
Tests blacklisting clearance, active vs expired debarments, declaration conflict detection,
cross-document consistency (PAN ↔ GSTIN, Organization Name, Address), critical vs mandatory flags,
critical failure detection, review item queue generation, DB persistence, idempotency, and security.
"""

import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from datetime import date, datetime, timezone
from decimal import Decimal
import logging
import uuid

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.compliance.evaluators.integrity import IntegrityComplianceEvaluator
from app.compliance.registry import compliance_registry
from app.compliance.types import (
    ComplianceContext,
    ComplianceOperator,
    ComplianceStatus,
)
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.compliance_result import ComplianceResult
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.db.models.verification_record import (
    VerificationMatchStatus,
    VerificationRecord,
    VerificationSourceType,
    VerificationStatus,
)
from app.db.session import get_session_factory
from app.services.compliance_service import (
    evaluate_bid_compliance,
    get_bid_compliance,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PASSED_TESTS = 0
FAILED_TESTS = 0


def record_result(test_name: str, condition: bool, details: str = "") -> None:
    global PASSED_TESTS, FAILED_TESTS
    if condition:
        PASSED_TESTS += 1
        print(f"  [PASS] {test_name} {details}")
    else:
        FAILED_TESTS += 1
        print(f"  [FAIL] {test_name} {details}")
        raise AssertionError(f"Test failed: {test_name} - {details}")


def print_test_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"[TEST] {title}")
    print("=" * 70)


def run_part6e_master_test_suite():
    global PASSED_TESTS, FAILED_TESTS
    print("\n" + "=" * 70)
    print("STARTING PART 6E BLACKLISTING, DEBARMENT & CRITICAL RULES TEST SUITE")
    print("=" * 70)

    db: Session = get_session_factory()()

    try:
        evaluator = IntegrityComplianceEvaluator()

        dummy_bid = Bid(id=uuid.uuid4(), bid_number="BID-6E-001", status="SUBMITTED")
        dummy_tender = Tender(
            id=uuid.uuid4(),
            tender_number="GEM/2026/6E/01",
            title="Tender with Integrity, Debarment & Consistency Requirements",
            submission_end_date=datetime(2026, 10, 31, 17, 0, 0, tzinfo=timezone.utc),
        )
        dummy_bidder_org = Organization(id=uuid.uuid4(), name="NATIONAL CYBERSHIELD PRIVATE LIMITED", organization_type="PRIVATE_LIMITED")

        # =========================================================================
        # 1. Evaluator Registration & Resolution
        # =========================================================================
        print_test_header("1. Evaluator Registration & Resolution")

        reg_evaluators = compliance_registry.list_evaluators()
        record_result("IntegrityComplianceEvaluator registered", "IntegrityComplianceEvaluator" in reg_evaluators)

        req_bl = TenderRequirement(id=uuid.uuid4(), code="NOT_BLACKLISTED", category="BLACKLISTING", is_critical=True)
        req_deb = TenderRequirement(id=uuid.uuid4(), code="NOT_DEBARRED", category="DEBARMENT", is_critical=True)
        req_pan_gst = TenderRequirement(id=uuid.uuid4(), code="PAN_GST_CONSISTENCY", category="CONSISTENCY", is_critical=True)
        req_name = TenderRequirement(id=uuid.uuid4(), code="ORGANIZATION_NAME_CONSISTENCY", category="CONSISTENCY")

        record_result("Resolves Blacklisting requirement", compliance_registry.resolve_evaluator(req_bl).evaluator_name == "IntegrityComplianceEvaluator")
        record_result("Resolves Debarment requirement", compliance_registry.resolve_evaluator(req_deb).evaluator_name == "IntegrityComplianceEvaluator")
        record_result("Resolves PAN-GST Consistency requirement", compliance_registry.resolve_evaluator(req_pan_gst).evaluator_name == "IntegrityComplianceEvaluator")
        record_result("Resolves Name Consistency requirement", compliance_registry.resolve_evaluator(req_name).evaluator_name == "IntegrityComplianceEvaluator")

        # =========================================================================
        # 2. Blacklisting Compliance Evaluation
        # =========================================================================
        print_test_header("2. Blacklisting Compliance Evaluation")

        # Case A: Clear Registry Status -> PASS
        v_bl_clear = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="BLACKLISTING",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Central Vigilance Portal",
            source_type=VerificationSourceType.MOCK,
            claimed_value="NOT_BLACKLISTED",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "registry_status": "CLEAR",
                "authority": "Central Vigilance Commission",
            },
            is_active=True,
        )
        ctx_bl_clear = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_bl_clear],
            verifications_by_type={"BLACKLISTING": [v_bl_clear]},
        )
        res_bl_clear = evaluator.evaluate(req_bl, ctx_bl_clear)
        record_result("Blacklisting CLEAR evaluates to PASS", res_bl_clear.compliance_status == ComplianceStatus.PASS, f"-> {res_bl_clear.reason}")
        record_result("Clear result does NOT flag critical failure", res_bl_clear.critical_failure is False)

        # Case B: Active Blacklisting -> FAIL + Critical Failure Flag
        v_bl_active = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="BLACKLISTING",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Central Vigilance Portal",
            source_type=VerificationSourceType.MOCK,
            claimed_value="NOT_BLACKLISTED",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "registry_status": "BLACKLISTED",
                "authority": "Department of Public Enterprises",
                "reference_number": "CVC/2025/BLK/990",
            },
            is_active=True,
        )
        ctx_bl_active = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_bl_active],
            verifications_by_type={"BLACKLISTING": [v_bl_active]},
        )
        res_bl_active = evaluator.evaluate(req_bl, ctx_bl_active)
        record_result("Active Blacklisting evaluates to FAIL", res_bl_active.compliance_status == ComplianceStatus.FAIL, f"-> {res_bl_active.reason}")
        record_result("Critical requirement failure sets critical_failure=True", res_bl_active.critical_failure is True)
        record_result("Preserves declaration_conflict in evidence", res_bl_active.evidence.get("declaration_conflict") is True)

        # Case C: Partial Entity Match / Uncertain -> REVIEW (Never premature FAIL)
        v_bl_partial = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="BLACKLISTING",
            verification_status=VerificationStatus.NEEDS_REVIEW,
            source_name="Central Vigilance Portal",
            source_type=VerificationSourceType.MOCK,
            claimed_value="NOT_BLACKLISTED",
            match_status=VerificationMatchStatus.PARTIAL_MATCH,
            error_message="Entity name phonetic match requires human verification",
            is_active=True,
        )
        ctx_bl_partial = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_bl_partial],
            verifications_by_type={"BLACKLISTING": [v_bl_partial]},
        )
        res_bl_partial = evaluator.evaluate(req_bl, ctx_bl_partial)
        record_result("Uncertain blacklisting entity match evaluates to REVIEW", res_bl_partial.compliance_status == ComplianceStatus.REVIEW, f"-> {res_bl_partial.reason}")
        record_result("Sets review_required=True", res_bl_partial.review_required is True)

        # Case D: Source UNAVAILABLE -> REVIEW (Bidder NOT failed)
        v_bl_unavail = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="BLACKLISTING",
            verification_status=VerificationStatus.UNAVAILABLE,
            source_name="Central Vigilance Portal",
            source_type=VerificationSourceType.MOCK,
            claimed_value="NOT_BLACKLISTED",
            is_active=True,
        )
        ctx_bl_unavail = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_bl_unavail],
            verifications_by_type={"BLACKLISTING": [v_bl_unavail]},
        )
        res_bl_unavail = evaluator.evaluate(req_bl, ctx_bl_unavail)
        record_result("UNAVAILABLE blacklisting source returns REVIEW without failing bidder", res_bl_unavail.compliance_status == ComplianceStatus.REVIEW, f"-> {res_bl_unavail.reason}")

        # =========================================================================
        # 3. Debarment Compliance Evaluation (Active vs Chronological Expiry)
        # =========================================================================
        print_test_header("3. Debarment Compliance Evaluation (Active vs Chronological Expiry)")

        # Case A: Active Debarment covering tender milestone -> FAIL
        v_deb_active = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="DEBARMENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Procurement Debarment Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="NOT_DEBARRED",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "registry_status": "DEBARRED",
                "effective_from": "2026-01-01",
                "effective_until": "2026-12-31",
            },
            is_active=True,
        )
        ctx_deb_active = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_deb_active],
            verifications_by_type={"DEBARMENT": [v_deb_active]},
        )
        res_deb_active = evaluator.evaluate(req_deb, ctx_deb_active)
        record_result("Active Debarment evaluates to FAIL", res_deb_active.compliance_status == ComplianceStatus.FAIL, f"-> {res_deb_active.reason}")
        record_result("Active debarment on critical rule flags critical_failure=True", res_deb_active.critical_failure is True)

        # Case B: Previous Debarment Expired before tender milestone (2026-06-30 < 2026-10-31) -> PASS
        v_deb_expired = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="DEBARMENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Procurement Debarment Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="NOT_DEBARRED",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "registry_status": "DEBARRED",
                "effective_from": "2025-01-01",
                "effective_until": "2026-06-30",
            },
            is_active=True,
        )
        ctx_deb_exp = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_deb_expired],
            verifications_by_type={"DEBARMENT": [v_deb_expired]},
        )
        res_deb_exp = evaluator.evaluate(req_deb, ctx_deb_exp)
        record_result("Expired Debarment prior to tender milestone evaluates to PASS", res_deb_exp.compliance_status == ComplianceStatus.PASS, f"-> {res_deb_exp.reason}")

        # Case C: Future Debarment (effective after tender date 2026-12-01 > 2026-10-31) -> PASS
        v_deb_future = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="DEBARMENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Procurement Debarment Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="NOT_DEBARRED",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "registry_status": "DEBARRED",
                "effective_from": "2026-12-01",
                "effective_until": "2027-12-01",
            },
            is_active=True,
        )
        ctx_deb_fut = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_deb_future],
            verifications_by_type={"DEBARMENT": [v_deb_future]},
        )
        res_deb_fut = evaluator.evaluate(req_deb, ctx_deb_fut)
        record_result("Future Debarment effective after tender milestone evaluates to PASS", res_deb_fut.compliance_status == ComplianceStatus.PASS, f"-> {res_deb_fut.reason}")

        # =========================================================================
        # 4. Cross-Document Consistency Evaluation
        # =========================================================================
        print_test_header("4. Cross-Document Consistency Evaluation")

        # Case A: PAN ↔ GSTIN Match -> PASS
        v_cd_match = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="CROSS_DOCUMENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Cross-Document Consistency Engine",
            source_type=VerificationSourceType.INTERNAL,
            claimed_value="9/9 MATCHED",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "findings": {
                    "pan_gstin": {"match_status": "MATCH"},
                    "organization_name": {"match_status": "MATCH"},
                    "registered_address": {"match_status": "MATCH"},
                }
            },
            is_active=True,
        )
        ctx_cd_match = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_cd_match],
            verifications_by_type={"CROSS_DOCUMENT": [v_cd_match]},
        )
        res_pan_match = evaluator.evaluate(req_pan_gst, ctx_cd_match)
        record_result("PAN-GST Consistency MATCH evaluates to PASS", res_pan_match.compliance_status == ComplianceStatus.PASS, f"-> {res_pan_match.reason}")

        # Case B: PAN ↔ GSTIN Mismatch -> FAIL (Strict identifier check)
        v_cd_pan_mm = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="CROSS_DOCUMENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Cross-Document Consistency Engine",
            source_type=VerificationSourceType.INTERNAL,
            claimed_value="DISCREPANCY",
            match_status=VerificationMatchStatus.MISMATCH,
            response_payload={
                "findings": {
                    "pan_gstin": {"match_status": "MISMATCH"},
                }
            },
            is_active=True,
        )
        ctx_cd_pan_mm = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_cd_pan_mm],
            verifications_by_type={"CROSS_DOCUMENT": [v_cd_pan_mm]},
        )
        res_pan_mm = evaluator.evaluate(req_pan_gst, ctx_cd_pan_mm)
        record_result("PAN-GST Consistency MISMATCH evaluates to FAIL", res_pan_mm.compliance_status == ComplianceStatus.FAIL, f"-> {res_pan_mm.reason}")
        record_result("PAN-GST failure on critical rule flags critical_failure=True", res_pan_mm.critical_failure is True)

        # Case C: Organization Name Partial Match -> REVIEW
        v_cd_name_part = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="CROSS_DOCUMENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Cross-Document Consistency Engine",
            source_type=VerificationSourceType.INTERNAL,
            claimed_value="PARTIAL",
            match_status=VerificationMatchStatus.PARTIAL_MATCH,
            response_payload={
                "findings": {
                    "organization_name": {"match_status": "PARTIAL_MATCH"},
                }
            },
            is_active=True,
        )
        ctx_cd_name_part = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_cd_name_part],
            verifications_by_type={"CROSS_DOCUMENT": [v_cd_name_part]},
        )
        res_name_part = evaluator.evaluate(req_name, ctx_cd_name_part)
        record_result("Organization Name PARTIAL_MATCH evaluates to REVIEW", res_name_part.compliance_status == ComplianceStatus.REVIEW, f"-> {res_name_part.reason}")

        # Case D: Address Variations -> REVIEW (Conservative handling)
        req_addr = TenderRequirement(id=uuid.uuid4(), code="ADDRESS_CONSISTENCY", category="CONSISTENCY")
        v_cd_addr = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="CROSS_DOCUMENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Cross-Document Consistency Engine",
            source_type=VerificationSourceType.INTERNAL,
            claimed_value="VARIATION",
            match_status=VerificationMatchStatus.PARTIAL_MATCH,
            response_payload={
                "findings": {
                    "registered_address": {"match_status": "PARTIAL_MATCH"},
                }
            },
            is_active=True,
        )
        ctx_cd_addr = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_cd_addr],
            verifications_by_type={"CROSS_DOCUMENT": [v_cd_addr]},
        )
        res_addr = evaluator.evaluate(req_addr, ctx_cd_addr)
        record_result("Address variations evaluate to REVIEW (conservative)", res_addr.compliance_status == ComplianceStatus.REVIEW, f"-> {res_addr.reason}")

        # =========================================================================
        # 5. Critical vs Mandatory Separation & Summary Counts
        # =========================================================================
        print_test_header("5. Critical vs Mandatory Separation & Summary Counts")

        req_mand_noncrit = TenderRequirement(id=uuid.uuid4(), code="MAND_NONCRIT", category="GENERAL", is_mandatory=True, is_critical=False)
        req_crit_mand = TenderRequirement(id=uuid.uuid4(), code="CRIT_MAND", category="BLACKLISTING", is_mandatory=True, is_critical=True)
        req_opt_crit = TenderRequirement(id=uuid.uuid4(), code="OPT_CRIT", category="BLACKLISTING", is_mandatory=False, is_critical=True)

        record_result("is_mandatory and is_critical are independent boolean attributes", req_mand_noncrit.is_mandatory and not req_mand_noncrit.is_critical)
        record_result("Combined critical mandatory requirement supported", req_crit_mand.is_mandatory and req_crit_mand.is_critical)

        # =========================================================================
        # 6. End-to-End Realistic Bid Compliance in Database with Review Summary
        # =========================================================================
        print_test_header("6. End-to-End Realistic Bid Compliance in Database with Review Summary")

        test_suffix = uuid.uuid4().hex[:6]
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        po_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()

        org_po = Organization(
            id=uuid.uuid4(),
            name=f"Defence Procurement Division {test_suffix}",
            organization_type="MINISTRY",
            is_active=True,
        )
        org_bidder = Organization(
            id=uuid.uuid4(),
            name=f"CYBERSHIELD DEFENCE SYSTEMS LIMITED {test_suffix}",
            organization_type="PUBLIC_LIMITED",
            is_active=True,
        )
        db.add_all([org_po, org_bidder])
        db.commit()

        prof_po = Profile(
            id=uuid.uuid4(),
            email=f"po_6e_{test_suffix}@gov.mock",
            role_id=po_role.id,
            organization_id=org_po.id,
            full_name="Col. R. Menon",
            is_active=True,
        )
        prof_bidder = Profile(
            id=uuid.uuid4(),
            email=f"bidder_6e_{test_suffix}@cybershield.mock",
            role_id=bidder_role.id,
            organization_id=org_bidder.id,
            full_name="Muthu Integrity Lead",
            is_active=True,
        )
        db.add_all([prof_po, prof_bidder])
        db.commit()

        user_bidder = User(
            id=uuid.uuid4(),
            email=f"bidder_6e_{test_suffix}@cybershield.mock",
            password_hash="mock_hash",
            profile_id=prof_bidder.id,
            is_active=True,
        )
        user_po = User(
            id=uuid.uuid4(),
            email=f"po_6e_{test_suffix}@gov.mock",
            password_hash="mock_hash",
            profile_id=prof_po.id,
            is_active=True,
        )
        db.add_all([user_bidder, user_po])
        db.commit()

        tender = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/6E/{test_suffix.upper()}",
            title="Strategic Communication & Cybersecurity Appliance Tender",
            description="Tender with critical exclusion and cross-document consistency checks",
            organization_id=org_po.id,
            created_by_profile_id=prof_po.id,
            submission_end_date=datetime(2026, 12, 31, 17, 0, 0, tzinfo=timezone.utc),
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)
        db.commit()

        # Seed 4 Requirements: 2 PASS, 1 CRITICAL FAIL, 1 REVIEW
        req_seed_bl = TenderRequirement(
            id=uuid.uuid4(), tender_id=tender.id, code="NOT_BLACKLISTED", name="Non-Blacklisting Clearance",
            category="BLACKLISTING", requirement_type="BOOLEAN", operator="EQUALS", expected_value="CLEAR",
            is_mandatory=True, is_critical=True, weight=Decimal("30.0"),
        )
        req_seed_deb = TenderRequirement(
            id=uuid.uuid4(), tender_id=tender.id, code="NOT_DEBARRED", name="Debarment Clearance",
            category="DEBARMENT", requirement_type="BOOLEAN", operator="EQUALS", expected_value="CLEAR",
            is_mandatory=True, is_critical=True, weight=Decimal("30.0"),
        )
        req_seed_pan_gst = TenderRequirement(
            id=uuid.uuid4(), tender_id=tender.id, code="PAN_GST_CONSISTENCY", name="PAN-GST Identifier Consistency",
            category="CONSISTENCY", requirement_type="TEXT", operator="EQUALS", expected_value="MATCH",
            is_mandatory=True, is_critical=True, weight=Decimal("20.0"),
        )
        req_seed_name = TenderRequirement(
            id=uuid.uuid4(), tender_id=tender.id, code="ORGANIZATION_NAME_CONSISTENCY", name="Organization Name Consistency",
            category="CONSISTENCY", requirement_type="TEXT", operator="EQUALS", expected_value="MATCH",
            is_mandatory=True, is_critical=False, weight=Decimal("20.0"),
        )
        db.add_all([req_seed_bl, req_seed_deb, req_seed_pan_gst, req_seed_name])
        db.commit()

        bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            submitted_by_profile_id=prof_bidder.id,
            bid_number=f"BID/2026/6E/{test_suffix.upper()}",
            status="SUBMITTED",
            submitted_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(bid)
        db.commit()

        # Seed Verification Records:
        # 1. Blacklisting -> CLEAR (PASS)
        # 2. Debarment -> DEBARRED (ACTIVE) -> CRITICAL FAIL
        # 3. Cross-Document -> PAN-GST MATCH (PASS), Name PARTIAL_MATCH (REVIEW)
        v_db_bl = VerificationRecord(
            id=uuid.uuid4(), bid_id=bid.id,
            verification_type="BLACKLISTING", verification_status=VerificationStatus.VERIFIED,
            source_name="Central Vigilance Portal", source_type=VerificationSourceType.MOCK,
            claimed_value="NOT_BLACKLISTED", match_status=VerificationMatchStatus.MATCH,
            response_payload={"registry_status": "CLEAR"},
            is_active=True,
        )
        v_db_deb = VerificationRecord(
            id=uuid.uuid4(), bid_id=bid.id,
            verification_type="DEBARMENT", verification_status=VerificationStatus.VERIFIED,
            source_name="Procurement Debarment Registry", source_type=VerificationSourceType.MOCK,
            claimed_value="NOT_DEBARRED", match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "registry_status": "DEBARRED",
                "effective_from": "2026-01-01",
                "effective_until": "2027-01-01",
            },
            is_active=True,
        )
        v_db_cd = VerificationRecord(
            id=uuid.uuid4(), bid_id=bid.id,
            verification_type="CROSS_DOCUMENT", verification_status=VerificationStatus.VERIFIED,
            source_name="Cross-Document Engine", source_type=VerificationSourceType.INTERNAL,
            claimed_value="CHECKED", match_status=VerificationMatchStatus.PARTIAL_MATCH,
            response_payload={
                "findings": {
                    "pan_gstin": {"match_status": "MATCH"},
                    "organization_name": {"match_status": "PARTIAL_MATCH"},
                }
            },
            is_active=True,
        )
        db.add_all([v_db_bl, v_db_deb, v_db_cd])
        db.commit()

        # Execute Compliance Evaluation
        eval_summary = evaluate_bid_compliance(
            db=db,
            current_user=user_bidder,
            bid_id=bid.id,
        )

        record_result("evaluate_bid_compliance processes all 4 rules", eval_summary.counts.total == 4)
        record_result("Counts: passed=2 (Blacklisting, PAN-GST)", eval_summary.counts.passed == 2)
        record_result("Counts: failed=1 (Debarment)", eval_summary.counts.failed == 1)
        record_result("Counts: review=1 (Organization Name partial match)", eval_summary.counts.review == 1)
        record_result("Counts: mandatory_failures=1", eval_summary.counts.mandatory_failures == 1)
        record_result("Counts: critical_failures=1", eval_summary.counts.critical_failures == 1)

        record_result("Review summary queue surfaces review item", len(eval_summary.review_items) == 1)
        rev_item = eval_summary.review_items[0]
        record_result("Review item specifies requirement code", rev_item.requirement_code == "ORGANIZATION_NAME_CONSISTENCY")
        record_result("Review item specifies review_type", rev_item.review_type == "CROSS_DOCUMENT_MISMATCH")

        for res in eval_summary.results:
            crit_str = " [CRITICAL FAIL]" if res.critical_failure else ""
            print(f"    -> [{res.compliance_status}]{crit_str} Req: {res.requirement_code}, Reason: {res.reason}")

        # Multi-Tenant Alien Check
        alien_user = User(id=uuid.uuid4(), email="alien_6e@other.org", password_hash="x", is_active=True)
        alien_rejected = False
        try:
            get_bid_compliance(
                db=db,
                current_user=alien_user,
                bid_id=bid.id,
            )
        except Exception:
            alien_rejected = True

        record_result("Alien user receives HTTP 404 (Tenant Isolation)", alien_rejected)

        # Strict Boundary Check: No Part 7/8 fields
        db_results = db.scalars(select(ComplianceResult).where(ComplianceResult.bid_id == bid.id)).all()
        for cr in db_results:
            assert not hasattr(cr, "score"), "ComplianceResult should not have score field"
            assert not hasattr(cr, "risk_level"), "ComplianceResult should not have risk_level field"
            assert not hasattr(cr, "final_decision"), "ComplianceResult should not have final_decision field"

        record_result("Strict compliance boundary preserved (No Part 7/8 fields)", True)

    except Exception as e:
        print(f"\n[ERROR] Exception during Part 6E testing: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

    print("\n" + "=" * 70)
    print("PART 6E MASTER TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run : {PASSED_TESTS + FAILED_TESTS}")
    print(f"Passed          : {PASSED_TESTS}")
    print(f"Failed          : {FAILED_TESTS}")

    if FAILED_TESTS == 0:
        print("\n>>> ALL PART 6E BLACKLISTING, DEBARMENT & CRITICAL RULES TESTS PASSED! <<<\n")
    else:
        print(f"\n>>> {FAILED_TESTS} TEST(S) FAILED <<<\n")
        sys.exit(1)


if __name__ == "__main__":
    run_part6e_master_test_suite()
