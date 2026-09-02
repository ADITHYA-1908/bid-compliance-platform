"""
Part 6F Master Integration, Rule-by-Rule Results & QA Test Suite
BidVerify AI — Integrated Bid Compliance Verification Platform for GeM Procurement

Comprehensive Master Validation of Part 6 Compliance Engine:
1. Evaluator Registry Completeness (All 9 Specialized Evaluators + Generic Fallback)
2. Standard Operator Set Evaluation (EQUALS, NOT_EQUALS, GT, GTE, LT, LTE, CONTAINS, EXISTS, NOT_EXISTS, IN)
3. Standard Compliance Status Semantics (PASS, FAIL, REVIEW, NOT_APPLICABLE, PENDING, BLOCKED)
4. Prerequisite & Source Outage Resilience (UNAVAILABLE/FAILED -> REVIEW without penalizing bidder)
5. Critical vs Mandatory Rule Separation (critical_failure=True, critical_failures vs mandatory_failures)
6. Human Review Queue Aggregation (review_items with review_type, reason, and evidence)
7. Multi-Domain Realistic Synthetic Bid End-to-End Evaluation (Statutory, Financial, Experience, Technical, OEM, MII, BIS, Integrity)
8. Evaluation Versioning & Idempotent Audit Trail (is_current=False on supersede, version increment)
9. Partial Bid & Missing Document Handling (PENDING vs FAIL vs NOT_APPLICABLE)
10. Multi-Tenant Security & Strict RBAC Isolation (404 on cross-tenant access)
11. Post-Submission Procurement Officer Evaluation Flow
12. Strict Compliance Separation Guard (Zero Part 7/8 scoring or final qualification logic in Part 6)
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

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.compliance.evaluators.base import ComplianceRuleEvaluator
from app.compliance.evaluators.bis import BISComplianceEvaluator
from app.compliance.evaluators.document import SupportingDocumentEvaluator
from app.compliance.evaluators.experience import ExperienceComplianceEvaluator
from app.compliance.evaluators.financial import FinancialComplianceEvaluator
from app.compliance.evaluators.generic import GenericRuleEvaluator
from app.compliance.evaluators.integrity import IntegrityComplianceEvaluator
from app.compliance.evaluators.local_content import LocalContentComplianceEvaluator
from app.compliance.evaluators.oem import OEMComplianceEvaluator
from app.compliance.evaluators.statutory import StatutoryRuleEvaluator
from app.compliance.evaluators.technical import TechnicalComplianceEvaluator
from app.compliance.operators import (
    compare_numbers,
    compare_strings,
    evaluate_exists,
    evaluate_generic_operator,
)
from app.compliance.registry import compliance_registry
from app.compliance.types import (
    ComplianceContext,
    ComplianceOperator,
    ComplianceRuleResult,
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
from app.db.models.verification_record import VerificationRecord
from app.verification.types import (
    VerificationClaimSource,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationTriggerSource,
    VerificationType,
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


def run_part6f_master_test_suite():
    global PASSED_TESTS, FAILED_TESTS
    PASSED_TESTS = 0
    FAILED_TESTS = 0

    session_factory = get_session_factory()
    db = session_factory()

    print("\n" + "=" * 70)
    print("STARTING PART 6F MASTER COMPLIANCE INTEGRATION & QA TEST SUITE")
    print("=" * 70)

    try:
        # -----------------------------------------------------------------
        # TEST 1: Evaluator Registry Completeness
        # -----------------------------------------------------------------
        print_test_header("1. Evaluator Registry Completeness (All 9 Evaluators & Generic Fallback)")
        evaluator_names = compliance_registry.list_evaluators()
        record_result("Registry has registered evaluators", len(evaluator_names) >= 9, f"(Count: {len(evaluator_names)})")

        expected_evaluator_classes = [
            StatutoryRuleEvaluator,
            IntegrityComplianceEvaluator,
            FinancialComplianceEvaluator,
            ExperienceComplianceEvaluator,
            OEMComplianceEvaluator,
            LocalContentComplianceEvaluator,
            BISComplianceEvaluator,
            TechnicalComplianceEvaluator,
            SupportingDocumentEvaluator,
            GenericRuleEvaluator,
        ]
        for ec in expected_evaluator_classes:
            inst_name = ec.__name__
            record_result(f"Evaluator registered: {inst_name}", inst_name in evaluator_names)

        # Test resolution for standard requirement categories
        stat_req = TenderRequirement(
            id=uuid.uuid4(),
            code="GST_REGISTRATION",
            name="GST Registration",
            category="STATUTORY_LEGAL",
            requirement_type="REGISTRATION",
            is_active=True,
        )
        resolved = compliance_registry.resolve_evaluator(stat_req)
        record_result("Resolves StatutoryRuleEvaluator for GST requirement", isinstance(resolved, StatutoryRuleEvaluator))

        unsupported_req = TenderRequirement(
            id=uuid.uuid4(),
            code="QUANTUM_TELEPORTATION_CERT",
            name="Quantum Entanglement Certification",
            category="FICTIONAL_FUTURE_TECH",
            requirement_type="EXOTIC_CUSTOM",
            is_active=True,
        )
        # Even if not supported by domain evaluators, it safely resolves to Generic or Fallback without crash
        resolved_fallback = compliance_registry.resolve_evaluator(unsupported_req)
        record_result("Resolves safe fallback for unsupported requirement", resolved_fallback is not None)

        # -----------------------------------------------------------------
        # TEST 2: Operator Set Correctness
        # -----------------------------------------------------------------
        print_test_header("2. Operator Set Correctness (EQUALS, GT, GTE, LT, LTE, CONTAINS, EXISTS, IN)")
        # EQUALS
        eq_match, _ = evaluate_generic_operator("ACTIVE", "ACTIVE", "EQUALS", "TEXT")
        record_result("Operator EQUALS matching", eq_match)
        eq_mismatch, _ = evaluate_generic_operator("INACTIVE", "ACTIVE", "EQUALS", "TEXT")
        record_result("Operator EQUALS mismatching", not eq_mismatch)

        # Numeric GTE / LTE
        gte_match, _ = evaluate_generic_operator(Decimal("1500000"), 1000000, "GREATER_THAN_OR_EQUAL", "NUMBER")
        record_result("Operator GTE threshold", gte_match)
        lte_match, _ = evaluate_generic_operator(Decimal("800000"), 1000000, "LESS_THAN_OR_EQUAL", "NUMBER")
        record_result("Operator LTE threshold", lte_match)

        # CONTAINS
        contains_match, _ = evaluate_generic_operator("Heavy Duty Industrial Cable", "Industrial", "CONTAINS", "TEXT")
        record_result("Operator CONTAINS match", contains_match)

        # EXISTS & NOT_EXISTS
        exists_match, _ = evaluate_generic_operator("PresentValue", None, "EXISTS", "TEXT")
        record_result("Operator EXISTS with value", exists_match)
        exists_none, _ = evaluate_generic_operator(None, None, "EXISTS", "TEXT")
        record_result("Operator EXISTS with None", not exists_none)
        not_exists_none, _ = evaluate_generic_operator(None, None, "NOT_EXISTS", "TEXT")
        record_result("Operator NOT_EXISTS with None", not_exists_none)

        # IN list
        in_match, _ = evaluate_generic_operator("MICRO", ["MICRO", "SMALL"], "IN", "TEXT")
        record_result("Operator IN list match", in_match)
        in_miss, _ = evaluate_generic_operator("MEDIUM", ["MICRO", "SMALL"], "IN", "TEXT")
        record_result("Operator IN list miss", not in_miss)

        # -----------------------------------------------------------------
        # TEST 3: Standard Compliance Determinations
        # -----------------------------------------------------------------
        print_test_header("3. Standard Compliance Determinations (PASS, FAIL, REVIEW, NOT_APPLICABLE, PENDING, BLOCKED)")
        record_result("Status PASS defined", ComplianceStatus.PASS == "PASS")
        record_result("Status FAIL defined", ComplianceStatus.FAIL == "FAIL")
        record_result("Status REVIEW defined", ComplianceStatus.REVIEW == "REVIEW")
        record_result("Status NOT_APPLICABLE defined", ComplianceStatus.NOT_APPLICABLE == "NOT_APPLICABLE")
        record_result("Status PENDING defined", ComplianceStatus.PENDING == "PENDING")
        record_result("Status BLOCKED defined", ComplianceStatus.BLOCKED == "BLOCKED")

        # -----------------------------------------------------------------
        # TEST 4: Prerequisite & Source Outage Resilience
        # -----------------------------------------------------------------
        print_test_header("4. Prerequisite & Source Outage Resilience")
        stat_eval = StatutoryRuleEvaluator()
        outage_req = TenderRequirement(
            id=uuid.uuid4(),
            code="GST_REGISTRATION",
            name="GST Registration",
            category="STATUTORY_LEGAL",
            requirement_type="REGISTRATION",
            is_mandatory=True,
            is_active=True,
        )
        # Mock Context with UNAVAILABLE GST verification
        dummy_bid = Bid(id=uuid.uuid4(), bid_number="BID-DUMMY", status="DRAFT", bidder_organization_id=uuid.uuid4())
        dummy_tender = Tender(id=uuid.uuid4(), tender_number="TND-DUMMY", title="Dummy Tender", organization_id=uuid.uuid4())
        
        outage_rec = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="GST",
            verification_status=VerificationStatus.UNAVAILABLE,
            source_type=VerificationSourceType.OFFICIAL_API,
            source_name="GST Portal",
            response_payload={"error_message": "GST portal unavailable"},
            is_active=True,
        )
        outage_context = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[outage_rec],
            verifications_by_type={"GST": [outage_rec]},
            verifications_by_claim={},
        )
        res_outage = stat_eval.evaluate(outage_req, outage_context)
        record_result("External source outage returns REVIEW", res_outage.compliance_status == ComplianceStatus.REVIEW)
        record_result("External source outage sets review_required=True", res_outage.review_required is True)
        record_result("Reason explains source unavailability without penalizing bidder", "temporarily unavailable" in res_outage.reason.lower() or "unavailable" in res_outage.reason.lower())

        # -----------------------------------------------------------------
        # TEST 5: Critical vs Mandatory Rule Separation
        # -----------------------------------------------------------------
        print_test_header("5. Critical vs Mandatory Rule Separation")
        integ_eval = IntegrityComplianceEvaluator()
        crit_req = TenderRequirement(
            id=uuid.uuid4(),
            code="NOT_BLACKLISTED",
            name="Non-Blacklisting Undertaking",
            category="STATUTORY_LEGAL",
            requirement_type="COMPLIANCE",
            is_mandatory=True,
            is_critical=True,
            is_active=True,
        )
        blacklisted_rec = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="BLACKLISTING",
            verification_status=VerificationStatus.VERIFIED,
            match_status=VerificationMatchStatus.MATCH,
            source_type=VerificationSourceType.OFFICIAL_API,
            source_name="CVC Portal",
            response_payload={"is_blacklisted": True, "registry_status": "BLACKLISTED", "authority": "CVC", "reason": "Debarred for default"},
            is_active=True,
        )
        blacklisted_context = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[blacklisted_rec],
            verifications_by_type={"BLACKLISTING": [blacklisted_rec]},
            verifications_by_claim={},
        )
        res_crit = integ_eval.evaluate(crit_req, blacklisted_context)
        record_result("Active blacklisting evaluates to FAIL", res_crit.compliance_status == ComplianceStatus.FAIL)
        record_result("Critical requirement failure sets critical_failure=True", res_crit.critical_failure is True)

        # Standard mandatory (non-critical) failure
        std_req = TenderRequirement(
            id=uuid.uuid4(),
            code="MIN_ANNUAL_TURNOVER",
            name="Minimum Annual Turnover",
            category="FINANCIAL",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value="5 Crore",
            is_mandatory=True,
            is_critical=False,
            is_active=True,
        )
        fin_eval = FinancialComplianceEvaluator()
        from app.db.models.document_processing import DocumentProcessing
        doc_fin_fail = BidDocument(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            document_type="TURNOVER_CERTIFICATE",
            document_name="Turnover_Cert.pdf",
            is_active=True,
        )
        doc_fin_fail.processing = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_fin_fail.id,
            extracted_data={"annual_turnover": "3.8 Crore"},
            extraction_confidence=0.88,
        )
        low_turnover_context = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            bid_documents=[doc_fin_fail],
            verifications=[],
            verifications_by_type={},
            verifications_by_claim={},
        )
        res_std = fin_eval.evaluate(std_req, low_turnover_context)
        record_result("Low turnover evaluates to FAIL", res_std.compliance_status == ComplianceStatus.FAIL)
        record_result("Non-critical mandatory failure leaves critical_failure=False", res_std.critical_failure is False)

        # -----------------------------------------------------------------
        # TEST 6: Review Queue Aggregation & Telemetry
        # -----------------------------------------------------------------
        print_test_header("6. Review Queue Aggregation & Telemetry")
        review_pan_req = TenderRequirement(
            id=uuid.uuid4(),
            code="PAN_VERIFICATION",
            name="PAN Verification",
            category="STATUTORY_LEGAL",
            requirement_type="REGISTRATION",
            is_mandatory=True,
            is_critical=False,
            is_active=True,
        )
        pan_review_rec = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="PAN",
            verification_status=VerificationStatus.NEEDS_REVIEW,
            source_type=VerificationSourceType.OFFICIAL_API,
            source_name="ITD NSDL",
            response_payload={
                "name_match": False,
                "cardholder_name": "Adithya Enterprises Private Limited",
                "bidder_name": "Adithya Enterprises",
                "pan_number": "ABCDE1234F",
                "pan_status": "ACTIVE",
            },
            is_active=True,
        )
        pan_review_context = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[pan_review_rec],
            verifications_by_type={"PAN": [pan_review_rec]},
            verifications_by_claim={},
        )
        res_pan = stat_eval.evaluate(review_pan_req, pan_review_context)
        record_result("Name variation evaluates to REVIEW", res_pan.compliance_status == ComplianceStatus.REVIEW)
        record_result("Review record has review_type or review reason", res_pan.review_type is not None or "review" in res_pan.reason.lower())

        # -----------------------------------------------------------------
        # TEST 7: Multi-Domain Realistic Synthetic Bid End-to-End Evaluation
        # -----------------------------------------------------------------
        print_test_header("7. Multi-Domain Realistic Synthetic Bid End-to-End Evaluation (All 8 Domains)")
        
        # Setup test entities in database
        po_org = Organization(
            id=uuid.uuid4(),
            name="Department of Electronics & IT",
            organization_type="BUYER",
            is_active=True,
        )
        bidder_org = Organization(
            id=uuid.uuid4(),
            name="Zenith Core Infotech Private Limited",
            organization_type="SELLER",
            is_active=True,
        )
        db.add_all([po_org, bidder_org])
        db.flush()

        po_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()

        prof_po = Profile(
            id=uuid.uuid4(),
            email=f"po_qa_{uuid.uuid4().hex[:8]}@meity.gov.in",
            organization_id=po_org.id,
            role_id=po_role.id,
            full_name="Officer V. K. Sharma",
            is_active=True,
        )
        prof_bidder = Profile(
            id=uuid.uuid4(),
            email=f"bidder_qa_{uuid.uuid4().hex[:8]}@zenithcore.in",
            organization_id=bidder_org.id,
            role_id=bidder_role.id,
            full_name="Anil Kumar",
            is_active=True,
        )
        db.add_all([prof_po, prof_bidder])
        db.flush()

        po_user = User(
            id=uuid.uuid4(),
            email=prof_po.email,
            password_hash="mock_hash_part6f",
            profile_id=prof_po.id,
            is_active=True,
        )
        bidder_user = User(
            id=uuid.uuid4(),
            email=prof_bidder.email,
            password_hash="mock_hash_part6f",
            profile_id=prof_bidder.id,
            is_active=True,
        )
        db.add_all([po_user, bidder_user])
        db.flush()

        tender = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/B/{uuid.uuid4().hex[:6].upper()}",
            title="Supply, Installation & Maintenance of Cloud Infrastructure Hardware",
            description="Procurement of compute, high-speed networking, and enterprise storage arrays",
            organization_id=po_org.id,
            created_by_profile_id=prof_po.id,
            status="PUBLISHED",
            submission_end_date=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True,
        )
        db.add(tender)
        db.flush()

        # Create requirements covering all 8 domains
        reqs = [
            # 1. Statutory - GST
            TenderRequirement(
                id=uuid.uuid4(),
                tender_id=tender.id,
                code="GST_REGISTRATION",
                name="Active GSTIN Registration",
                category="STATUTORY",
                requirement_type="REGISTRATION",
                operator="EQUALS",
                expected_value="ACTIVE",
                is_mandatory=True,
                is_critical=True,
                is_active=True,
                display_order=1,
            ),
            # 2. Statutory - Udyam MSME
            TenderRequirement(
                id=uuid.uuid4(),
                tender_id=tender.id,
                code="UDYAM_REGISTRATION",
                name="MSME Enterprise Registration",
                category="STATUTORY",
                requirement_type="REGISTRATION",
                operator="EQUALS",
                expected_value="ACTIVE",
                is_mandatory=False,
                is_critical=False,
                is_active=True,
                display_order=2,
            ),
            # 3. Financial - Turnover
            TenderRequirement(
                id=uuid.uuid4(),
                tender_id=tender.id,
                code="MIN_ANNUAL_TURNOVER",
                name="Annual Turnover >= 5 Crore",
                category="FINANCIAL",
                requirement_type="NUMBER",
                operator="GREATER_THAN_OR_EQUAL",
                expected_value="5 Crore",
                is_mandatory=True,
                is_critical=False,
                is_active=True,
                display_order=3,
            ),
            # 4. Past Experience - Completed Projects
            TenderRequirement(
                id=uuid.uuid4(),
                tender_id=tender.id,
                code="MIN_COMPLETED_PROJECTS",
                name="Minimum 2 Completed Similar Projects",
                category="EXPERIENCE",
                requirement_type="NUMBER",
                expected_value=2,
                operator="GREATER_THAN_OR_EQUAL",
                is_mandatory=True,
                is_critical=False,
                is_active=True,
                display_order=4,
            ),
            # 5. Technical - Model & Spec
            TenderRequirement(
                id=uuid.uuid4(),
                tender_id=tender.id,
                code="MODEL_NUMBER",
                name="Server Model Specification",
                category="TECHNICAL",
                requirement_type="TEXT",
                expected_value="PowerEdge-R750",
                operator="EQUALS",
                is_mandatory=True,
                is_critical=False,
                is_active=True,
                display_order=5,
            ),
            # 6. OEM Authorization
            TenderRequirement(
                id=uuid.uuid4(),
                tender_id=tender.id,
                code="OEM_AUTHORIZATION",
                name="Manufacturer Authorization Form (MAF)",
                category="OEM",
                requirement_type="DOCUMENT",
                expected_value="ACTIVE",
                operator="EQUALS",
                is_mandatory=True,
                is_critical=False,
                is_active=True,
                display_order=6,
            ),
            # 7. Local Content / MII
            TenderRequirement(
                id=uuid.uuid4(),
                tender_id=tender.id,
                code="LOCAL_CONTENT",
                name="Minimum 50% Local Content",
                category="LOCAL_CONTENT",
                requirement_type="PERCENTAGE",
                expected_value=50.0,
                operator="GREATER_THAN_OR_EQUAL",
                is_mandatory=True,
                is_critical=False,
                is_active=True,
                display_order=7,
            ),
            # 8. BIS Certification
            TenderRequirement(
                id=uuid.uuid4(),
                tender_id=tender.id,
                code="BIS_CERTIFICATION",
                name="BIS Standard IS 13252 Conformance",
                category="BIS",
                requirement_type="CERTIFICATION",
                expected_value="IS 13252",
                operator="EQUALS",
                is_mandatory=True,
                is_critical=False,
                is_active=True,
                display_order=8,
            ),
            # 9. Integrity - Non-Blacklisting
            TenderRequirement(
                id=uuid.uuid4(),
                tender_id=tender.id,
                code="NOT_BLACKLISTED",
                name="Debarment & Blacklisting Clearance",
                category="INTEGRITY",
                requirement_type="COMPLIANCE",
                expected_value="CLEAR",
                operator="EQUALS",
                is_mandatory=True,
                is_critical=True,
                is_active=True,
                display_order=9,
            ),
            # 10. Cross-Document - PAN-GST Consistency
            TenderRequirement(
                id=uuid.uuid4(),
                tender_id=tender.id,
                code="PAN_GST_CONSISTENCY",
                name="PAN and GSTIN Identification Match",
                category="INTEGRITY",
                requirement_type="COMPLIANCE",
                expected_value="MATCH",
                operator="EQUALS",
                is_mandatory=True,
                is_critical=True,
                is_active=True,
                display_order=10,
            ),
        ]
        db.add_all(reqs)
        db.flush()

        bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=bidder_org.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-{uuid.uuid4().hex[:6].upper()}",
            status="SUBMITTED",
            submitted_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(bid)
        db.flush()

        # Seed Documents for Financial, Experience, Technical & OEM
        doc_turnover = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof_bidder.id,
            document_type="TURNOVER_CERTIFICATE",
            document_name="CA_Turnover.pdf",
            original_filename="CA_Turnover.pdf",
            storage_path="mock/turnover.pdf",
            mime_type="application/pdf",
            file_size=102400,
            is_active=True,
        )
        db.add(doc_turnover)
        db.flush()
        doc_proc_to = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_turnover.id,
            extracted_data={"annual_turnover": "8.5 Crore"},
            extraction_confidence=0.92,
        )
        db.add(doc_proc_to)

        doc_exp = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof_bidder.id,
            document_type="EXPERIENCE_CERTIFICATE",
            document_name="Work_Orders.pdf",
            original_filename="Work_Orders.pdf",
            storage_path="mock/exp.pdf",
            mime_type="application/pdf",
            file_size=102400,
            is_active=True,
        )
        db.add(doc_exp)
        db.flush()
        doc_proc_exp = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_exp.id,
            extracted_data={
                "projects": [
                    {"project_name": "Data Center Phase 1", "status": "COMPLETED", "contract_value": "1 Crore"},
                    {"project_name": "Cloud Migration", "status": "COMPLETED", "contract_value": "1.5 Crore"},
                    {"project_name": "SOC Setup", "status": "COMPLETED", "contract_value": "2 Crore"},
                ]
            },
            extraction_confidence=0.90,
        )
        db.add(doc_proc_exp)

        doc_tech = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof_bidder.id,
            document_type="TECHNICAL_DOCUMENT",
            document_name="Datasheet_R750.pdf",
            original_filename="Datasheet_R750.pdf",
            storage_path="mock/tech.pdf",
            mime_type="application/pdf",
            file_size=102400,
            is_active=True,
        )
        db.add(doc_tech)
        db.flush()
        doc_proc_tech = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_tech.id,
            extracted_data={"model_number": "PowerEdge-R750"},
            extraction_confidence=0.95,
        )
        db.add(doc_proc_tech)

        doc_oem = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof_bidder.id,
            document_type="OEM_AUTHORIZATION",
            document_name="Dell_MAF.pdf",
            original_filename="Dell_MAF.pdf",
            storage_path="mock/oem.pdf",
            mime_type="application/pdf",
            file_size=102400,
            is_active=True,
        )
        db.add(doc_oem)
        db.flush()
        doc_proc_oem = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc_oem.id,
            extracted_data={
                "oem_name": "Dell Technologies",
                "authorized_bidder": "Zenith Core Infotech Private Limited",
                "valid_until": "2027-12-31",
            },
            extraction_confidence=0.95,
        )
        db.add(doc_proc_oem)
        db.flush()

        # Seed realistic verification records for this bid
        records = [
            # GST Verified
            VerificationRecord(
                id=uuid.uuid4(),
                bid_id=bid.id,
                verification_type="GST",
                verification_status=VerificationStatus.VERIFIED,
                match_status=VerificationMatchStatus.MATCH,
                source_type=VerificationSourceType.OFFICIAL_API,
                source_name="GST Portal",
                claimed_value="29AAACA1234A1Z5",
                confidence=0.99,
                response_payload={"gstin": "29AAACA1234A1Z5", "registry_status": "ACTIVE", "legal_name": "Zenith Core Infotech Private Limited"},
                is_active=True,
            ),
            # MSME Verified
            VerificationRecord(
                id=uuid.uuid4(),
                bid_id=bid.id,
                verification_type="UDYAM",
                verification_status=VerificationStatus.VERIFIED,
                match_status=VerificationMatchStatus.MATCH,
                source_type=VerificationSourceType.OFFICIAL_API,
                source_name="Udyam Portal",
                claimed_value="UDYAM-KR-03-0012345",
                confidence=0.95,
                response_payload={"udyam_number": "UDYAM-KR-03-0012345", "enterprise_type": "MEDIUM", "registry_status": "ACTIVE"},
                is_active=True,
            ),
            # Financial Verified (Turnover = 85 Lakhs >= 50 Lakhs)
            VerificationRecord(
                id=uuid.uuid4(),
                bid_id=bid.id,
                verification_type="CA_CERTIFICATE",
                verification_status=VerificationStatus.VERIFIED,
                match_status=VerificationMatchStatus.MATCH,
                source_type=VerificationSourceType.INTERNAL,
                source_name="CA Audited Statement",
                claimed_value="8500000",
                confidence=0.90,
                response_payload={"annual_turnover": 8500000, "net_worth": 3000000},
                is_active=True,
            ),
            # Experience Verified (3 completed projects)
            VerificationRecord(
                id=uuid.uuid4(),
                bid_id=bid.id,
                verification_type="EXPERIENCE",
                verification_status=VerificationStatus.VERIFIED,
                match_status=VerificationMatchStatus.MATCH,
                source_type=VerificationSourceType.INTERNAL,
                source_name="Work Order Certificates",
                claimed_value="3",
                confidence=0.88,
                response_payload={"completed_projects_count": 3, "total_value": 15000000},
                is_active=True,
            ),
            # Technical Specification Verified
            VerificationRecord(
                id=uuid.uuid4(),
                bid_id=bid.id,
                verification_type="TECHNICAL_SPEC",
                verification_status=VerificationStatus.VERIFIED,
                match_status=VerificationMatchStatus.MATCH,
                source_type=VerificationSourceType.INTERNAL,
                source_name="Datasheet",
                claimed_value="PowerEdge-R750",
                confidence=0.92,
                response_payload={"model_number": "PowerEdge-R750", "specifications_compliant": True},
                is_active=True,
            ),
            # OEM Authorization Verified
            VerificationRecord(
                id=uuid.uuid4(),
                bid_id=bid.id,
                verification_type="OEM_AUTHORIZATION",
                verification_status=VerificationStatus.VERIFIED,
                match_status=VerificationMatchStatus.MATCH,
                source_type=VerificationSourceType.OFFICIAL_API,
                source_name="Dell Technologies",
                claimed_value="Authorized",
                confidence=0.95,
                response_payload={"oem_name": "Dell Technologies", "authorized_bidder": "Zenith Core Infotech Private Limited", "is_authorized": True, "valid_until": "2027-12-31"},
                is_active=True,
            ),
            # Local Content MII Verified (60% >= 50%)
            VerificationRecord(
                id=uuid.uuid4(),
                bid_id=bid.id,
                verification_type="LOCAL_CONTENT",
                verification_status=VerificationStatus.VERIFIED,
                match_status=VerificationMatchStatus.MATCH,
                source_type=VerificationSourceType.INTERNAL,
                source_name="Self Declaration",
                claimed_value="60.0",
                confidence=0.90,
                response_payload={"local_content_percentage": 60.0, "supplier_class": "CLASS_I"},
                is_active=True,
            ),
            # BIS Certification Verified
            VerificationRecord(
                id=uuid.uuid4(),
                bid_id=bid.id,
                verification_type="BIS",
                verification_status=VerificationStatus.VERIFIED,
                match_status=VerificationMatchStatus.MATCH,
                source_type=VerificationSourceType.OFFICIAL_API,
                source_name="BIS Registry",
                claimed_value="R-41001234",
                confidence=0.95,
                response_payload={"standard_number": "IS 13252", "registry_status": "VALID", "valid_until": "2027-06-30"},
                is_active=True,
            ),
            # Non-Blacklisted Verified Clear
            VerificationRecord(
                id=uuid.uuid4(),
                bid_id=bid.id,
                verification_type="BLACKLISTING",
                verification_status=VerificationStatus.VERIFIED,
                match_status=VerificationMatchStatus.MATCH,
                source_type=VerificationSourceType.OFFICIAL_API,
                source_name="CVC Portal",
                claimed_value="Clear",
                confidence=0.99,
                response_payload={"is_blacklisted": False, "registry_status": "CLEAR"},
                is_active=True,
            ),
            # PAN-GST Consistency Verified Match
            VerificationRecord(
                id=uuid.uuid4(),
                bid_id=bid.id,
                verification_type="CROSS_DOCUMENT",
                verification_status=VerificationStatus.VERIFIED,
                match_status=VerificationMatchStatus.MATCH,
                source_type=VerificationSourceType.INTERNAL,
                source_name="Cross Document Consistency Engine",
                claimed_value="PAN_GST_MATCH",
                confidence=1.00,
                response_payload={"pan_gst_match": True, "pan": "AAACA1234A", "gstin": "29AAACA1234A1Z5"},
                is_active=True,
            ),
        ]
        db.add_all(records)
        db.flush()

        # Run compliance evaluation
        summary = evaluate_bid_compliance(db, po_user, bid.id)

        for res_item in summary.results:
            print(f"    -> [{res_item.compliance_status}] Req: {res_item.requirement_code}, Reason: {res_item.reason}")

        record_result("All 10 multi-domain requirements evaluated", summary.counts.total == 10, f"(Total={summary.counts.total})")
        record_result("All 10 evaluated to PASS", summary.counts.passed == 10, f"(Passed={summary.counts.passed})")
        record_result("Zero failed requirements", summary.counts.failed == 0)
        record_result("Zero mandatory failures", summary.counts.mandatory_failures == 0)
        record_result("Zero critical failures", summary.counts.critical_failures == 0)
        record_result("Evaluation complete flag is True", summary.compliance_evaluation_complete is True)

        # -----------------------------------------------------------------
        # TEST 8: Evaluation Versioning & Idempotent Audit Trail
        # -----------------------------------------------------------------
        print_test_header("8. Evaluation Versioning & Idempotent Audit Trail")
        # Run second evaluation
        summary_v2 = evaluate_bid_compliance(db, po_user, bid.id)
        
        # Check database records for version 1 and version 2
        v1_records = db.scalars(
            select(ComplianceResult).where(
                and_(
                    ComplianceResult.bid_id == bid.id,
                    ComplianceResult.evaluation_version == 1,
                )
            )
        ).all()
        v2_records = db.scalars(
            select(ComplianceResult).where(
                and_(
                    ComplianceResult.bid_id == bid.id,
                    ComplianceResult.evaluation_version == 2,
                )
            )
        ).all()

        record_result("Version 1 records preserved in audit trail", len(v1_records) == 10)
        record_result("Version 1 records marked is_current=False", all(not r.is_current for r in v1_records))
        record_result("Version 2 records created", len(v2_records) == 10)
        record_result("Version 2 records marked is_current=True", all(r.is_current for r in v2_records))

        # -----------------------------------------------------------------
        # TEST 9: Partial Bid & Missing Document Handling
        # -----------------------------------------------------------------
        print_test_header("9. Partial Bid & Missing Document Handling")
        partial_bidder_org = Organization(
            id=uuid.uuid4(),
            name=f"Incomplete Solutions LLP {uuid.uuid4().hex[:6]}",
            organization_type="SELLER",
            is_active=True,
        )
        db.add(partial_bidder_org)
        db.flush()

        prof_partial = Profile(
            id=uuid.uuid4(),
            email=f"partial_{uuid.uuid4().hex[:8]}@incomplete.in",
            organization_id=partial_bidder_org.id,
            role_id=bidder_role.id,
            full_name="Partial Bidder",
            is_active=True,
        )
        db.add(prof_partial)
        db.flush()

        user_partial = User(
            id=uuid.uuid4(),
            email=prof_partial.email,
            password_hash="mock_hash_part6f",
            profile_id=prof_partial.id,
            is_active=True,
        )
        db.add(user_partial)
        db.flush()

        partial_bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=partial_bidder_org.id,
            created_by_profile_id=prof_partial.id,
            bid_number=f"BID-DRAFT-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            is_active=True,
        )
        db.add(partial_bid)
        db.flush()

        # Evaluate partial bid with ZERO verifications attached
        summary_partial = evaluate_bid_compliance(db, user_partial, partial_bid.id)
        record_result("Partial bid processes all active requirements", summary_partial.counts.total == 10)
        record_result("Missing verifications result in PENDING / REVIEW status", summary_partial.counts.pending + summary_partial.counts.review > 0)
        record_result("Summary properly reflects non-passing counts", summary_partial.counts.passed < 10)

        # -----------------------------------------------------------------
        # TEST 10: Multi-Tenant Security & Strict RBAC Isolation
        # -----------------------------------------------------------------
        print_test_header("10. Multi-Tenant Security & Strict RBAC Isolation")
        alien_org = Organization(
            id=uuid.uuid4(),
            name="Unauthorized Competitor Ltd",
            organization_type="SELLER",
            is_active=True,
        )
        db.add(alien_org)
        db.flush()

        alien_profile = Profile(
            id=uuid.uuid4(),
            email=f"alien_{uuid.uuid4().hex[:8]}@competitor.com",
            organization_id=alien_org.id,
            role_id=bidder_role.id,
            full_name="Alien Bidder",
            is_active=True,
        )
        db.add(alien_profile)
        db.flush()

        alien_user = User(
            id=uuid.uuid4(),
            email=alien_profile.email,
            password_hash="mock_hash_part6f",
            profile_id=alien_profile.id,
            is_active=True,
        )
        db.add(alien_user)
        db.flush()

        # Alien user trying to access bid compliance
        try:
            get_bid_compliance(db, alien_user, bid.id)
            record_result("Alien user cross-tenant access blocked", False, "Should raise 404")
        except HTTPException as he:
            record_result("Alien user receives HTTP 404 (Tenant Isolation)", he.status_code == 404, f"(Got {he.status_code})")

        # -----------------------------------------------------------------
        # TEST 11: Post-Submission Procurement Officer Evaluation Flow
        # -----------------------------------------------------------------
        print_test_header("11. Post-Submission Procurement Officer Evaluation Flow")
        po_get_summary = get_bid_compliance(db, po_user, bid.id)
        record_result("Procurement Officer successfully fetches submitted bid compliance", po_get_summary.bid_id == bid.id)
        record_result("Procurement Officer receives current version results", len(po_get_summary.results) == 10)

        # -----------------------------------------------------------------
        # TEST 12: Strict Compliance Separation Guard
        # -----------------------------------------------------------------
        print_test_header("12. Strict Compliance Separation Guard (No Part 7/8 scoring or final qualification logic)")
        summary_dict = summary.model_dump()
        forbidden_keys = [
            "compliance_score",
            "composite_score",
            "risk_level",
            "risk_score",
            "overall_score",
            "qualification_status",
            "award_decision",
            "ai_recommendation",
        ]
        has_forbidden_keys = any(k in summary_dict for k in forbidden_keys)
        record_result("Zero Part 7/8 scoring or final decision fields in summary", not has_forbidden_keys)

        results_dicts = [r.model_dump() for r in summary.results]
        results_have_forbidden = any(
            any(k in r for k in forbidden_keys)
            for r in results_dicts
        )
        record_result("Zero Part 7/8 scoring fields in individual rule results", not results_have_forbidden)

    except Exception as e:
        import traceback
        logger.error(f"Unhandled exception during master test suite: {e}")
        traceback.print_exc()
        FAILED_TESTS += 1
    finally:
        db.rollback()
        db.close()

    print("\n" + "=" * 70)
    print("PART 6F MASTER COMPLIANCE INTEGRATION QA SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run : {PASSED_TESTS + FAILED_TESTS}")
    print(f"Passed          : {PASSED_TESTS}")
    print(f"Failed          : {FAILED_TESTS}")

    if FAILED_TESTS == 0:
        print("\n>>> ALL PART 6F MASTER COMPLIANCE INTEGRATION & QA TESTS PASSED! <<<\n")
        return 0
    else:
        print(f"\n>>> MASTER QA COMPLIANCE SUITE FAILED WITH {FAILED_TESTS} ERRORS <<<\n")
        return 1


if __name__ == "__main__":
    exit_code = run_part6f_master_test_suite()
    sys.exit(exit_code)
