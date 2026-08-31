"""
Master QA Test Suite for Part 6C: Financial, Experience & Technical Compliance Rules
Tests all financial rules, multi-year turnover averaging, Indian unit normalization,
profitability rules, experience duration (without double-counting overlapping periods),
completed project counts, single/total project values, deterministic technical and
specification evaluations, outage/review resilience, DB persistence, and multi-tenant security.
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

from app.compliance.evaluators.experience import (
    ExperienceComplianceEvaluator,
    merge_date_intervals,
)
from app.compliance.evaluators.financial import (
    FinancialComplianceEvaluator,
    normalize_indian_currency,
)
from app.compliance.evaluators.technical import (
    TechnicalComplianceEvaluator,
    normalize_model_number,
)
from app.compliance.registry import compliance_registry
from app.compliance.types import (
    ComplianceContext,
    ComplianceOperator,
    ComplianceStatus,
)
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.compliance_result import ComplianceResult
from app.db.models.document_processing import DocumentProcessing
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


def run_part6c_master_test_suite():
    global PASSED_TESTS, FAILED_TESTS
    print("\n" + "=" * 70)
    print("STARTING PART 6C FINANCIAL, EXPERIENCE & TECHNICAL TEST SUITE")
    print("=" * 70)

    db: Session = get_session_factory()()

    try:
        fin_evaluator = FinancialComplianceEvaluator()
        exp_evaluator = ExperienceComplianceEvaluator()
        tech_evaluator = TechnicalComplianceEvaluator()

        dummy_bid = Bid(id=uuid.uuid4(), bid_number="BID-6C-001", status="SUBMITTED")
        dummy_tender = Tender(
            id=uuid.uuid4(),
            tender_number="GEM/2026/6C/01",
            title="Supply & Integration of Cyber Defence Suite",
            submission_end_date=datetime(2026, 10, 1, 17, 0, 0, tzinfo=timezone.utc),
        )

        # =========================================================================
        # 1. Evaluator Registration & Supports Check
        # =========================================================================
        print_test_header("1. Evaluator Registration & Supports Check")

        reg_evaluators = compliance_registry.list_evaluators()
        record_result("FinancialComplianceEvaluator registered", "FinancialComplianceEvaluator" in reg_evaluators)
        record_result("ExperienceComplianceEvaluator registered", "ExperienceComplianceEvaluator" in reg_evaluators)
        record_result("TechnicalComplianceEvaluator registered", "TechnicalComplianceEvaluator" in reg_evaluators)

        req_fin = TenderRequirement(id=uuid.uuid4(), code="MIN_ANNUAL_TURNOVER", category="FINANCIAL")
        req_exp = TenderRequirement(id=uuid.uuid4(), code="MIN_YEARS_EXPERIENCE", category="EXPERIENCE")
        req_tech = TenderRequirement(id=uuid.uuid4(), code="MODEL_NUMBER", category="TECHNICAL")

        resolved_fin = compliance_registry.resolve_evaluator(req_fin)
        resolved_exp = compliance_registry.resolve_evaluator(req_exp)
        resolved_tech = compliance_registry.resolve_evaluator(req_tech)

        record_result("Resolves Financial evaluator", resolved_fin.evaluator_name == "FinancialComplianceEvaluator")
        record_result("Resolves Experience evaluator", resolved_exp.evaluator_name == "ExperienceComplianceEvaluator")
        record_result("Resolves Technical evaluator", resolved_tech.evaluator_name == "TechnicalComplianceEvaluator")

        # =========================================================================
        # 2. Indian Currency & Decimal Normalization
        # =========================================================================
        print_test_header("2. Indian Currency & Decimal Normalization")

        val_cr = normalize_indian_currency("5 Crore")
        val_cr_dot = normalize_indian_currency("5.4 Cr")
        val_lakh = normalize_indian_currency("50 Lakh")
        val_symbol = normalize_indian_currency("₹ 5,00,00,000")
        val_million = normalize_indian_currency("10 Million")

        record_result("'5 Crore' -> 50,000,000", val_cr == Decimal("50000000"))
        record_result("'5.4 Cr' -> 54,000,000", val_cr_dot == Decimal("54000000"))
        record_result("'50 Lakh' -> 5,000,000", val_lakh == Decimal("5000000"))
        record_result("'₹ 5,00,00,000' -> 50,000,000", val_symbol == Decimal("50000000"))
        record_result("'10 Million' -> 10,000,000", val_million == Decimal("10000000"))

        # =========================================================================
        # 3. Minimum Annual Turnover Rules
        # =========================================================================
        print_test_header("3. Minimum Annual Turnover Rules")

        req_turnover = TenderRequirement(
            id=uuid.uuid4(),
            code="MIN_ANNUAL_TURNOVER",
            name="Minimum Annual Turnover",
            category="FINANCIAL",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value="5 Crore",
        )

        # Case A: Actual ₹6.2 Crore >= ₹5 Crore -> PASS
        doc_fin_pass = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="TURNOVER_CERTIFICATE", document_name="Turnover_Cert.pdf", is_active=True)
        doc_fin_pass.processing = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_fin_pass.id,
            extracted_data={"annual_turnover": "6.2 Crore"},
            extraction_confidence=0.92,
        )
        ctx_to_pass = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_fin_pass])
        res_to_pass = fin_evaluator.evaluate(req_turnover, ctx_to_pass)
        record_result("Turnover ₹6.2 Cr >= ₹5 Cr evaluates to PASS", res_to_pass.compliance_status == ComplianceStatus.PASS, f"-> {res_to_pass.reason}")

        # Case B: Actual ₹3.8 Crore < ₹5 Crore -> FAIL
        doc_fin_fail = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="TURNOVER_CERTIFICATE", document_name="Turnover_Cert.pdf", is_active=True)
        doc_fin_fail.processing = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_fin_fail.id,
            extracted_data={"annual_turnover": "3.8 Crore"},
            extraction_confidence=0.88,
        )
        ctx_to_fail = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_fin_fail])
        res_to_fail = fin_evaluator.evaluate(req_turnover, ctx_to_fail)
        record_result("Turnover ₹3.8 Cr < ₹5 Cr evaluates to FAIL", res_to_fail.compliance_status == ComplianceStatus.FAIL, f"-> {res_to_fail.reason}")

        # =========================================================================
        # 4. Multi-Year Average Annual Turnover & Missing Year Handling
        # =========================================================================
        print_test_header("4. Multi-Year Average Annual Turnover & Missing Year Handling")

        req_avg_turnover = TenderRequirement(
            id=uuid.uuid4(),
            code="MIN_AVERAGE_ANNUAL_TURNOVER",
            name="Average Turnover for Last 3 Financial Years",
            category="FINANCIAL",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value="5 Crore",
        )

        # Case A: 3 Years: FY22-23=4Cr, FY23-24=5Cr, FY24-25=6Cr -> Avg = 5Cr -> PASS
        doc_3yr = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="FINANCIAL_STATEMENT", document_name="3yr_Audited_CA.pdf", is_active=True)
        doc_3yr.processing = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_3yr.id,
            extracted_data={
                "financial_years": {
                    "2022-23": "4 Crore",
                    "2023-24": "5 Crore",
                    "2024-25": "6 Crore",
                }
            },
            extraction_confidence=0.95,
        )
        ctx_3yr = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_3yr])
        res_3yr = fin_evaluator.evaluate(req_avg_turnover, ctx_3yr)
        record_result("3-Year Average (4+5+6)/3 = 5 Cr evaluates to PASS", res_3yr.compliance_status == ComplianceStatus.PASS, f"-> {res_3yr.reason}")

        # Case B: Missing 3rd Year: Only 2 Years provided (4Cr, 5Cr) -> REVIEW (No silent averaging)
        doc_2yr = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="FINANCIAL_STATEMENT", document_name="2yr_Statement.pdf", is_active=True)
        doc_2yr.processing = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_2yr.id,
            extracted_data={
                "financial_years": {
                    "2023-24": "4 Crore",
                    "2024-25": "5 Crore",
                }
            },
            extraction_confidence=0.90,
        )
        ctx_2yr = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_2yr])
        res_2yr = fin_evaluator.evaluate(req_avg_turnover, ctx_2yr)
        record_result("Only 2 of 3 required years provided evaluates to REVIEW", res_2yr.compliance_status == ComplianceStatus.REVIEW, f"-> {res_2yr.reason}")

        # =========================================================================
        # 5. Profitability / Net Profit After Tax Rules
        # =========================================================================
        print_test_header("5. Profitability / Net Profit After Tax Rules")

        req_pat = TenderRequirement(
            id=uuid.uuid4(),
            code="POSITIVE_NET_PROFIT_REQUIRED",
            name="Positive Net Profit After Tax",
            category="FINANCIAL",
            requirement_type="NUMBER",
            operator="GREATER_THAN",
            expected_value="0",
        )

        # Positive PAT -> PASS
        doc_pat_pos = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="FINANCIAL_STATEMENT", document_name="PL_Statement.pdf", is_active=True)
        doc_pat_pos.processing = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_pat_pos.id,
            extracted_data={"profit_after_tax": "45 Lakh"},
            extraction_confidence=0.94,
        )
        ctx_pat_pos = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_pat_pos])
        res_pat_pos = fin_evaluator.evaluate(req_pat, ctx_pat_pos)
        record_result("Profit After Tax (₹45 Lakh > 0) evaluates to PASS", res_pat_pos.compliance_status == ComplianceStatus.PASS, f"-> {res_pat_pos.reason}")

        # Negative PAT (Loss) -> FAIL
        doc_pat_neg = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="FINANCIAL_STATEMENT", document_name="PL_Statement.pdf", is_active=True)
        doc_pat_neg.processing = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_pat_neg.id,
            extracted_data={"profit_after_tax": "-15 Lakh"},
            extraction_confidence=0.91,
        )
        ctx_pat_neg = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_pat_neg])
        res_pat_neg = fin_evaluator.evaluate(req_pat, ctx_pat_neg)
        record_result("Loss (-₹15 Lakh <= 0) evaluates to FAIL", res_pat_neg.compliance_status == ComplianceStatus.FAIL, f"-> {res_pat_neg.reason}")

        # Missing PAT -> REVIEW
        doc_pat_miss = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="FINANCIAL_STATEMENT", document_name="Incomplete.pdf", is_active=True)
        doc_pat_miss.processing = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_pat_miss.id,
            extracted_data={"turnover": "5 Crore"},  # No profit field
            extraction_confidence=0.85,
        )
        ctx_pat_miss = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_pat_miss])
        res_pat_miss = fin_evaluator.evaluate(req_pat, ctx_pat_miss)
        record_result("Missing Profit data evaluates to REVIEW", res_pat_miss.compliance_status == ComplianceStatus.REVIEW, f"-> {res_pat_miss.reason}")

        # =========================================================================
        # 6. Experience Duration & Overlapping Interval Merging
        # =========================================================================
        print_test_header("6. Experience Duration & Overlapping Interval Merging")

        # Verify merge_date_intervals
        # Interval 1: 2021-01-01 to 2022-12-31 (2 years)
        # Interval 2: 2022-06-01 to 2023-12-31 (Overlaps with 1)
        # Merged should be 2021-01-01 to 2023-12-31 (3 years, NOT 3.5 years double-counted)
        int1 = (date(2021, 1, 1), date(2022, 12, 31))
        int2 = (date(2022, 6, 1), date(2023, 12, 31))
        merged = merge_date_intervals([int1, int2])
        record_result("Overlapping date intervals merged correctly", len(merged) == 1 and merged[0] == (date(2021, 1, 1), date(2023, 12, 31)))

        req_exp_years = TenderRequirement(
            id=uuid.uuid4(),
            code="MIN_YEARS_EXPERIENCE",
            name="At least 3 Years Relevant Experience",
            category="EXPERIENCE",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value="3",
        )

        doc_exp = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="EXPERIENCE_CERTIFICATE", document_name="Experience_Letters.pdf", is_active=True)
        doc_exp.processing = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_exp.id,
            extracted_data={
                "projects": [
                    {"project_name": "Project Alpha", "start_date": "2021-01-01", "completion_date": "2022-12-31"},
                    {"project_name": "Project Beta", "start_date": "2022-06-01", "completion_date": "2024-06-30"},
                ]
            },
            extraction_confidence=0.92,
        )
        ctx_exp_years = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_exp])
        res_exp_years = exp_evaluator.evaluate(req_exp_years, ctx_exp_years)
        record_result("Merged non-overlapping experience (3.5 yrs >= 3 yrs) evaluates to PASS", res_exp_years.compliance_status == ComplianceStatus.PASS, f"-> {res_exp_years.reason}")

        # =========================================================================
        # 7. Completed Projects Count & Project Value Rules
        # =========================================================================
        print_test_header("7. Completed Projects Count & Project Value Rules")

        req_proj_count = TenderRequirement(
            id=uuid.uuid4(),
            code="MIN_COMPLETED_PROJECTS",
            name="Minimum 3 Completed Projects",
            category="EXPERIENCE",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value="3",
        )

        req_single_val = TenderRequirement(
            id=uuid.uuid4(),
            code="MIN_SINGLE_PROJECT_VALUE",
            name="At least one project >= ₹1 Crore",
            category="EXPERIENCE",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value="1 Crore",
        )

        req_total_val = TenderRequirement(
            id=uuid.uuid4(),
            code="MIN_TOTAL_PROJECT_VALUE",
            name="Total completed project value >= ₹3 Crore",
            category="EXPERIENCE",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value="3 Crore",
        )

        doc_multi_proj = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="EXPERIENCE_CERTIFICATE", document_name="Past_Projects.pdf", is_active=True)
        doc_multi_proj.processing = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_multi_proj.id,
            extracted_data={
                "projects": [
                    {"project_name": "Naval Base Firewall", "contract_value": "1.2 Crore", "status": "COMPLETED", "completion_date": "2024-01-15"},
                    {"project_name": "Air Force LAN", "contract_value": "80 Lakh", "status": "COMPLETED", "completion_date": "2024-06-20"},
                    {"project_name": "Defence SOC Integration", "contract_value": "1.5 Crore", "status": "COMPLETED", "completion_date": "2025-02-10"},
                ]
            },
            extraction_confidence=0.96,
        )
        ctx_multi_proj = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_multi_proj])

        res_cnt = exp_evaluator.evaluate(req_proj_count, ctx_multi_proj)
        record_result("Project Count (3 >= 3) evaluates to PASS", res_cnt.compliance_status == ComplianceStatus.PASS, f"-> {res_cnt.reason}")

        res_single = exp_evaluator.evaluate(req_single_val, ctx_multi_proj)
        record_result("Single Project Value (Max ₹1.5 Cr >= ₹1 Cr) evaluates to PASS", res_single.compliance_status == ComplianceStatus.PASS, f"-> {res_single.reason}")

        res_total = exp_evaluator.evaluate(req_total_val, ctx_multi_proj)
        record_result("Total Project Value (1.2 + 0.8 + 1.5 = ₹3.5 Cr >= ₹3 Cr) evaluates to PASS", res_total.compliance_status == ComplianceStatus.PASS, f"-> {res_total.reason}")

        # =========================================================================
        # 8. Technical Rules (Product, Model Number & Specifications)
        # =========================================================================
        print_test_header("8. Technical Rules (Product, Model Number & Specifications)")

        record_result("Model Number normalization 'X-100' -> 'X100'", normalize_model_number("X-100") == "X100")
        record_result("Model Number normalization 'SEC-2026/A' -> 'SEC2026A'", normalize_model_number("SEC-2026/A") == "SEC2026A")

        req_model = TenderRequirement(
            id=uuid.uuid4(),
            code="MODEL_REQUIRED",
            name="Offered Model Specification",
            category="TECHNICAL",
            requirement_type="TEXT",
            operator="EQUALS",
            expected_value="NGFW-5000",
        )

        req_capacity = TenderRequirement(
            id=uuid.uuid4(),
            code="TECH_CAPACITY",
            name="Throughput Capacity in Gbps",
            category="TECHNICAL",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value="100",
        )

        # Technical Match -> PASS
        doc_tech = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="TECHNICAL_DOCUMENT", document_name="Appliance_Datasheet.pdf", is_active=True)
        doc_tech.processing = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_tech.id,
            extracted_data={
                "product_name": "NextGen Enterprise Firewall",
                "model_number": "NGFW-5000",
                "manufacturer": "SecureCore Systems",
                "capacity": 120,
            },
            extraction_confidence=0.95,
        )
        ctx_tech = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_tech])

        res_model = tech_evaluator.evaluate(req_model, ctx_tech)
        record_result("Model NGFW-5000 matches expected NGFW-5000 -> PASS", res_model.compliance_status == ComplianceStatus.PASS, f"-> {res_model.reason}")

        res_cap = tech_evaluator.evaluate(req_capacity, ctx_tech)
        record_result("Technical Capacity (120 >= 100 Gbps) evaluates to PASS", res_cap.compliance_status == ComplianceStatus.PASS, f"-> {res_cap.reason}")

        # Model Mismatch -> FAIL
        doc_tech_bad_model = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="TECHNICAL_DOCUMENT", document_name="Old_Datasheet.pdf", is_active=True)
        doc_tech_bad_model.processing = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_tech_bad_model.id,
            extracted_data={"model_number": "NGFW-2000"},
            extraction_confidence=0.90,
        )
        ctx_tech_bad = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_tech_bad_model])
        res_bad_model = tech_evaluator.evaluate(req_model, ctx_tech_bad)
        record_result("Model NGFF-2000 does not match NGFW-5000 -> FAIL", res_bad_model.compliance_status == ComplianceStatus.FAIL, f"-> {res_bad_model.reason}")

        # Missing Technical Spec -> REVIEW (No semantic guessing)
        req_missing_spec = TenderRequirement(
            id=uuid.uuid4(),
            code="TECH_ENCRYPTION_CHIP",
            name="Dedicated HSM Encryption Chipset",
            category="TECHNICAL",
            requirement_type="TEXT",
            operator="EQUALS",
            expected_value="FIPS-140-2 Level 3",
        )
        res_miss_spec = tech_evaluator.evaluate(req_missing_spec, ctx_tech)
        record_result("Unextracted technical spec evaluates to REVIEW", res_miss_spec.compliance_status == ComplianceStatus.REVIEW, f"-> {res_miss_spec.reason}")

        # =========================================================================
        # 9. Conflicting Values & Outage Resilience
        # =========================================================================
        print_test_header("9. Conflicting Values & Outage Resilience")

        # Conflict between two documents (Turnover cert says 5Cr, Balance sheet says 3Cr)
        doc_c1 = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="TURNOVER_CERTIFICATE", document_name="CA_Turnover.pdf", is_active=True)
        doc_c1.processing = DocumentProcessing(id=uuid.uuid4(), bid_document_id=doc_c1.id, extracted_data={"turnover": "5 Crore"})
        doc_c2 = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="FINANCIAL_STATEMENT", document_name="PL_Report.pdf", is_active=True)
        doc_c2.processing = DocumentProcessing(id=uuid.uuid4(), bid_document_id=doc_c2.id, extracted_data={"turnover": "3 Crore"})

        ctx_conflict = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_c1, doc_c2])
        res_conflict = fin_evaluator.evaluate(req_turnover, ctx_conflict)
        record_result("Conflicting turnover values across documents evaluates to REVIEW", res_conflict.compliance_status == ComplianceStatus.REVIEW, f"-> {res_conflict.reason}")

        # =========================================================================
        # 10. End-to-End Realistic Bid Compliance in Database
        # =========================================================================
        print_test_header("10. End-to-End Realistic Bid Compliance in Database")

        test_suffix = uuid.uuid4().hex[:6]
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        po_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()

        org_po = Organization(
            id=uuid.uuid4(),
            name=f"Ministry of Electronics {test_suffix}",
            organization_type="MINISTRY",
            is_active=True,
        )
        org_bidder = Organization(
            id=uuid.uuid4(),
            name="CYBERDEFENCE SOLUTIONS PRIVATE LIMITED",
            organization_type="PRIVATE_LIMITED",
            is_active=True,
        )
        db.add_all([org_po, org_bidder])
        db.commit()

        prof_po = Profile(
            id=uuid.uuid4(),
            email=f"po_6c_{test_suffix}@gov.mock",
            role_id=po_role.id,
            organization_id=org_po.id,
            full_name="Director S. K. Verma",
            is_active=True,
        )
        prof_bidder = Profile(
            id=uuid.uuid4(),
            email=f"bidder_6c_{test_suffix}@cybersec.mock",
            role_id=bidder_role.id,
            organization_id=org_bidder.id,
            full_name="Muthu Financial Lead",
            is_active=True,
        )
        db.add_all([prof_po, prof_bidder])
        db.commit()

        user_bidder = User(
            id=uuid.uuid4(),
            email=f"bidder_6c_{test_suffix}@cybersec.mock",
            password_hash="mock_hash",
            profile_id=prof_bidder.id,
            is_active=True,
        )
        user_po = User(
            id=uuid.uuid4(),
            email=f"po_6c_{test_suffix}@gov.mock",
            password_hash="mock_hash",
            profile_id=prof_po.id,
            is_active=True,
        )
        db.add_all([user_bidder, user_po])
        db.commit()

        tender = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/6C/{test_suffix.upper()}",
            title="Procurement of AI-Ready Cyber Security Hardware",
            description="Tender with combined financial, experience, and technical criteria",
            organization_id=org_po.id,
            created_by_profile_id=prof_po.id,
            submission_end_date=datetime(2026, 12, 1, 17, 0, 0, tzinfo=timezone.utc),
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)
        db.commit()

        # Requirements spanning Financial, Experience, and Technical
        req_defs = [
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="MIN_ANNUAL_TURNOVER", name="Minimum Annual Turnover >= ₹5 Cr",
                category="FINANCIAL", requirement_type="NUMBER", operator="GREATER_THAN_OR_EQUAL", expected_value="5 Crore",
                is_mandatory=True, weight=Decimal("25.0"),
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="MIN_YEARS_EXPERIENCE", name="At least 3 Years Relevant Experience",
                category="EXPERIENCE", requirement_type="NUMBER", operator="GREATER_THAN_OR_EQUAL", expected_value="3",
                is_mandatory=True, weight=Decimal("25.0"),
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="MIN_SINGLE_PROJECT_VALUE", name="Single Project Value >= ₹1 Cr",
                category="EXPERIENCE", requirement_type="NUMBER", operator="GREATER_THAN_OR_EQUAL", expected_value="1 Crore",
                is_mandatory=True, weight=Decimal("20.0"),
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="MODEL_NUMBER", name="Offered Model must be CYBER-9000",
                category="TECHNICAL", requirement_type="TEXT", operator="EQUALS", expected_value="CYBER-9000",
                is_mandatory=True, weight=Decimal("30.0"),
            ),
        ]
        db.add_all(req_defs)
        db.commit()

        # Bid
        bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            submitted_by_profile_id=prof_bidder.id,
            bid_number=f"BID/2026/6C/{test_suffix.upper()}",
            status="SUBMITTED",
            submitted_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(bid)
        db.commit()

        # Seed Documents with Processed Data
        doc_fin = BidDocument(
            id=uuid.uuid4(), bid_id=bid.id, uploaded_by_profile_id=prof_bidder.id,
            document_type="TURNOVER_CERTIFICATE", document_name="CA_Certified_Turnover.pdf",
            original_filename="CA_Certified_Turnover.pdf", storage_path="/mock/turnover.pdf",
            mime_type="application/pdf", file_size=102400, is_active=True,
        )
        doc_exp_db = BidDocument(
            id=uuid.uuid4(), bid_id=bid.id, uploaded_by_profile_id=prof_bidder.id,
            document_type="EXPERIENCE_CERTIFICATE", document_name="Completed_Projects.pdf",
            original_filename="Completed_Projects.pdf", storage_path="/mock/projects.pdf",
            mime_type="application/pdf", file_size=204800, is_active=True,
        )
        doc_tech_db = BidDocument(
            id=uuid.uuid4(), bid_id=bid.id, uploaded_by_profile_id=prof_bidder.id,
            document_type="TECHNICAL_DOCUMENT", document_name="Cyber_9000_Datasheet.pdf",
            original_filename="Cyber_9000_Datasheet.pdf", storage_path="/mock/datasheet.pdf",
            mime_type="application/pdf", file_size=307200, is_active=True,
        )
        db.add_all([doc_fin, doc_exp_db, doc_tech_db])
        db.commit()

        proc_fin = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_fin.id,
            processing_status="COMPLETED", processing_stage="COMPLETED",
            extracted_data={"annual_turnover": "7.5 Crore", "total_revenue": "8 Crore"},
            extraction_confidence=0.96,
        )
        proc_exp = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_exp_db.id,
            processing_status="COMPLETED", processing_stage="COMPLETED",
            extracted_data={
                "projects": [
                    {"project_name": "State WAN SOC", "start_date": "2020-01-01", "completion_date": "2022-12-31", "contract_value": "1.8 Crore", "status": "COMPLETED"},
                    {"project_name": "Airport Security LAN", "start_date": "2023-01-01", "completion_date": "2024-12-31", "contract_value": "90 Lakh", "status": "COMPLETED"},
                ]
            },
            extraction_confidence=0.94,
        )
        proc_tech = DocumentProcessing(
            id=uuid.uuid4(), bid_document_id=doc_tech_db.id,
            processing_status="COMPLETED", processing_stage="COMPLETED",
            extracted_data={
                "product_name": "CyberDefence Hardware Appliance",
                "model_number": "CYBER-9000",
                "manufacturer": "CyberDefence Corp",
            },
            extraction_confidence=0.98,
        )
        db.add_all([proc_fin, proc_exp, proc_tech])
        db.commit()

        # Execute Compliance Evaluation
        eval_summary = evaluate_bid_compliance(
            db=db,
            current_user=user_bidder,
            bid_id=bid.id,
        )

        record_result("evaluate_bid_compliance evaluates all 4 rules", eval_summary.counts.total == 4)
        record_result("All 4 requirements evaluated to PASS", eval_summary.counts.passed == 4)

        for res in eval_summary.results:
            print(f"    -> [{res.compliance_status}] Req: {res.requirement_code}, Actual: '{res.actual_value}', Reason: {res.reason}")

        # Multi-Tenant Alien Check
        alien_user = User(id=uuid.uuid4(), email="alien@other.org", password_hash="x", is_active=True)
        alien_rejected = False
        try:
            get_bid_compliance(
                db=db,
                current_user=alien_user,
                bid_id=bid.id,
            )
        except Exception:
            alien_rejected = True

        record_result("Alien user cannot access compliance records (Tenant Isolation)", alien_rejected)

        # Boundary Check: Verify no score or final qualification decision was computed
        db_results = db.scalars(select(ComplianceResult).where(ComplianceResult.bid_id == bid.id)).all()
        for cr in db_results:
            assert not hasattr(cr, "score"), "ComplianceResult should not have score field"
            assert not hasattr(cr, "risk_level"), "ComplianceResult should not have risk_level field"
            assert not hasattr(cr, "final_decision"), "ComplianceResult should not have final_decision field"

        record_result("Strict compliance boundary preserved (No Part 7/8 fields)", True)

    except Exception as e:
        print(f"\n[ERROR] Exception during Part 6C testing: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

    print("\n" + "=" * 70)
    print("PART 6C MASTER TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run : {PASSED_TESTS + FAILED_TESTS}")
    print(f"Passed          : {PASSED_TESTS}")
    print(f"Failed          : {FAILED_TESTS}")

    if FAILED_TESTS == 0:
        print("\n>>> ALL PART 6C FINANCIAL, EXPERIENCE & TECHNICAL TESTS PASSED! <<<\n")
    else:
        print(f"\n>>> {FAILED_TESTS} TEST(S) FAILED <<<\n")
        sys.exit(1)


if __name__ == "__main__":
    run_part6c_master_test_suite()
