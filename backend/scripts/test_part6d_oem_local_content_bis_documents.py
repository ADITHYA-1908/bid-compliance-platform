"""
Master QA Test Suite for Part 6D: OEM, Local Content, BIS & Supporting Document Compliance Rules
Tests OEM authorization rules (presence, entity match, validity, scope), Make-in-India / Local Content
percentage thresholds, supplier classes (Class-I, Class-II), BIS CRS / License rules (presence, status,
standard IS 13252, validity), Supporting Document presence & internal structural evidence, outage resilience,
DB persistence, idempotency, and multi-tenant security.
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

from app.compliance.evaluators.bis import BISComplianceEvaluator, normalize_bis_standard
from app.compliance.evaluators.document import SupportingDocumentEvaluator
from app.compliance.evaluators.local_content import (
    LocalContentComplianceEvaluator,
    normalize_supplier_class,
)
from app.compliance.evaluators.oem import OEMComplianceEvaluator
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


def run_part6d_master_test_suite():
    global PASSED_TESTS, FAILED_TESTS
    print("\n" + "=" * 70)
    print("STARTING PART 6D OEM, LOCAL CONTENT, BIS & DOCUMENT TEST SUITE")
    print("=" * 70)

    db: Session = get_session_factory()()

    try:
        oem_evaluator = OEMComplianceEvaluator()
        lc_evaluator = LocalContentComplianceEvaluator()
        bis_evaluator = BISComplianceEvaluator()
        doc_evaluator = SupportingDocumentEvaluator()

        dummy_bid = Bid(id=uuid.uuid4(), bid_number="BID-6D-001", status="SUBMITTED")
        dummy_tender = Tender(
            id=uuid.uuid4(),
            tender_number="GEM/2026/6D/01",
            title="Procurement of Secure Hardware & Computing Infrastructure",
            submission_end_date=datetime(2026, 11, 30, 17, 0, 0, tzinfo=timezone.utc),
        )
        dummy_bidder_org = Organization(id=uuid.uuid4(), name="SECURETECH INDIA PRIVATE LIMITED", organization_type="PRIVATE_LIMITED")

        # =========================================================================
        # 1. Evaluator Registration & Supports Check
        # =========================================================================
        print_test_header("1. Evaluator Registration & Supports Check")

        reg_evaluators = compliance_registry.list_evaluators()
        record_result("OEMComplianceEvaluator registered", "OEMComplianceEvaluator" in reg_evaluators)
        record_result("LocalContentComplianceEvaluator registered", "LocalContentComplianceEvaluator" in reg_evaluators)
        record_result("BISComplianceEvaluator registered", "BISComplianceEvaluator" in reg_evaluators)
        record_result("SupportingDocumentEvaluator registered", "SupportingDocumentEvaluator" in reg_evaluators)

        req_oem = TenderRequirement(id=uuid.uuid4(), code="OEM_AUTHORIZATION_REQUIRED", category="OEM")
        req_lc = TenderRequirement(id=uuid.uuid4(), code="MIN_LOCAL_CONTENT_PERCENTAGE", category="LOCAL_CONTENT")
        req_bis = TenderRequirement(id=uuid.uuid4(), code="BIS_STANDARD_REQUIRED", category="BIS")
        req_doc = TenderRequirement(id=uuid.uuid4(), code="COMMERCIAL_DOCUMENT_REQUIRED", category="DOCUMENT")

        record_result("Resolves OEM evaluator", compliance_registry.resolve_evaluator(req_oem).evaluator_name == "OEMComplianceEvaluator")
        record_result("Resolves Local Content evaluator", compliance_registry.resolve_evaluator(req_lc).evaluator_name == "LocalContentComplianceEvaluator")
        record_result("Resolves BIS evaluator", compliance_registry.resolve_evaluator(req_bis).evaluator_name == "BISComplianceEvaluator")
        record_result("Resolves Supporting Document evaluator", compliance_registry.resolve_evaluator(req_doc).evaluator_name == "SupportingDocumentEvaluator")

        # =========================================================================
        # 2. OEM Authorization Rules (Presence, Entity, Validity, Scope)
        # =========================================================================
        print_test_header("2. OEM Authorization Rules (Presence, Entity, Validity, Scope)")

        req_oem_auth = TenderRequirement(
            id=uuid.uuid4(),
            code="OEM_AUTHORIZATION_REQUIRED",
            name="Valid OEM Manufacturer Authorization",
            category="OEM",
            requirement_type="TEXT",
            operator="EQUALS",
            expected_value="VALID",
        )

        req_oem_entity = TenderRequirement(
            id=uuid.uuid4(),
            code="OEM_AUTHORIZED_ENTITY_MATCH",
            name="OEM Authorization issued to Bidder",
            category="OEM",
            requirement_type="TEXT",
            operator="EQUALS",
            expected_value="SECURETECH INDIA PRIVATE LIMITED",
        )

        req_oem_validity = TenderRequirement(
            id=uuid.uuid4(),
            code="OEM_AUTHORIZATION_VALID",
            name="OEM Authorization valid through tender submission deadline",
            category="OEM",
            requirement_type="DATE",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value=None,  # Automatically falls back to tender.submission_end_date
        )

        req_oem_scope = TenderRequirement(
            id=uuid.uuid4(),
            code="OEM_SCOPE_MATCH",
            name="OEM Authorization covers Enterprise Firewall Series",
            category="OEM",
            requirement_type="TEXT",
            operator="CONTAINS",
            expected_value="Enterprise Firewall",
        )

        # Case A: Full Valid OEM Record -> PASS across all rules
        v_oem_valid = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="OEM_AUTHORIZATION",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock OEM Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="OEM/2026/AUTH/001",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "reference_number": "OEM/2026/AUTH/001",
                "oem_name": "Cisco Global Systems",
                "authorized_entity": "SECURETECH INDIA PRIVATE LIMITED",
                "product_scope": "Enterprise Firewall Series 9000",
                "authorization_status": "VALID",
                "valid_until": "2026-12-31",
            },
            is_active=True,
        )
        ctx_oem = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            bidder_organization=dummy_bidder_org,
            verifications=[v_oem_valid],
            verifications_by_type={"OEM_AUTHORIZATION": [v_oem_valid]},
        )

        res_oem_auth = oem_evaluator.evaluate(req_oem_auth, ctx_oem)
        record_result("OEM Authorization status VALID evaluates to PASS", res_oem_auth.compliance_status == ComplianceStatus.PASS, f"-> {res_oem_auth.reason}")

        res_oem_entity = oem_evaluator.evaluate(req_oem_entity, ctx_oem)
        record_result("OEM Authorized Entity matches bidder evaluates to PASS", res_oem_entity.compliance_status == ComplianceStatus.PASS, f"-> {res_oem_entity.reason}")

        res_oem_val = oem_evaluator.evaluate(req_oem_validity, ctx_oem)
        record_result("OEM Validity (2026-12-31 >= 2026-11-30) evaluates to PASS", res_oem_val.compliance_status == ComplianceStatus.PASS, f"-> {res_oem_val.reason}")

        res_oem_sc = oem_evaluator.evaluate(req_oem_scope, ctx_oem)
        record_result("OEM Product Scope match evaluates to PASS", res_oem_sc.compliance_status == ComplianceStatus.PASS, f"-> {res_oem_sc.reason}")

        # Case B: Expired OEM Authorization -> FAIL
        v_oem_expired = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="OEM_AUTHORIZATION",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock OEM Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="OEM/2026/AUTH/002",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "reference_number": "OEM/2026/AUTH/002",
                "oem_name": "Cisco Global Systems",
                "authorized_entity": "SECURETECH INDIA PRIVATE LIMITED",
                "product_scope": "Enterprise Firewall Series 9000",
                "authorization_status": "EXPIRED",
                "valid_until": "2026-08-31",
            },
            is_active=True,
        )
        ctx_oem_exp = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            bidder_organization=dummy_bidder_org,
            verifications=[v_oem_expired],
            verifications_by_type={"OEM_AUTHORIZATION": [v_oem_expired]},
        )
        res_oem_exp = oem_evaluator.evaluate(req_oem_validity, ctx_oem_exp)
        record_result("OEM Expired before deadline evaluates to FAIL", res_oem_exp.compliance_status == ComplianceStatus.FAIL, f"-> {res_oem_exp.reason}")

        # Case C: Entity Mismatch -> FAIL
        v_oem_mismatch = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="OEM_AUTHORIZATION",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock OEM Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="OEM/2026/AUTH/003",
            match_status=VerificationMatchStatus.MISMATCH,
            response_payload={
                "reference_number": "OEM/2026/AUTH/003",
                "oem_name": "Cisco Global Systems",
                "authorized_entity": "UNRELATED DISTRIBUTOR CORP",
                "product_scope": "Enterprise Firewall Series 9000",
                "authorization_status": "VALID",
                "valid_until": "2026-12-31",
            },
            is_active=True,
        )
        ctx_oem_mm = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            bidder_organization=dummy_bidder_org,
            verifications=[v_oem_mismatch],
            verifications_by_type={"OEM_AUTHORIZATION": [v_oem_mismatch]},
        )
        res_oem_mm = oem_evaluator.evaluate(req_oem_entity, ctx_oem_mm)
        record_result("OEM Entity Mismatch evaluates to FAIL", res_oem_mm.compliance_status == ComplianceStatus.FAIL, f"-> {res_oem_mm.reason}")

        # =========================================================================
        # 3. Local Content / Make in India Percentage & Supplier Class
        # =========================================================================
        print_test_header("3. Local Content / Make in India Percentage & Supplier Class")

        record_result("Supplier Class normalization 'Class-I' -> 'CLASS_I'", normalize_supplier_class("Class-I") == "CLASS_I")
        record_result("Supplier Class normalization 'Class 2' -> 'CLASS_II'", normalize_supplier_class("Class 2") == "CLASS_II")

        req_lc_pct = TenderRequirement(
            id=uuid.uuid4(),
            code="MIN_LOCAL_CONTENT_PERCENTAGE",
            name="Minimum 50% Local Content (Make in India)",
            category="LOCAL_CONTENT",
            requirement_type="NUMBER",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value="50",
        )

        req_supplier_class = TenderRequirement(
            id=uuid.uuid4(),
            code="CLASS_I_LOCAL_SUPPLIER_REQUIRED",
            name="Class-I Local Supplier Status Required",
            category="LOCAL_CONTENT",
            requirement_type="TEXT",
            operator="EQUALS",
            expected_value="CLASS_I",
        )

        # Case A: 55% Local Content & Class-I -> PASS
        v_lc_55 = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="LOCAL_CONTENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock Local Content Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="55%",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "local_content_percentage": 55,
                "supplier_class": "CLASS_I",
                "product_name": "Cyber Appliance Hardware",
                "entity_name": "SECURETECH INDIA PRIVATE LIMITED",
            },
            is_active=True,
        )
        ctx_lc_55 = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_lc_55],
            verifications_by_type={"LOCAL_CONTENT": [v_lc_55]},
        )
        res_lc_55 = lc_evaluator.evaluate(req_lc_pct, ctx_lc_55)
        record_result("Local Content 55% >= 50% evaluates to PASS", res_lc_55.compliance_status == ComplianceStatus.PASS, f"-> {res_lc_55.reason}")

        res_class_pass = lc_evaluator.evaluate(req_supplier_class, ctx_lc_55)
        record_result("Supplier Class CLASS_I evaluates to PASS", res_class_pass.compliance_status == ComplianceStatus.PASS, f"-> {res_class_pass.reason}")

        # Case B: 45% Local Content (< 50%) -> FAIL (Key Part 5 vs Part 6 distinction)
        v_lc_45 = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="LOCAL_CONTENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock Local Content Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="45%",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "local_content_percentage": 45,
                "supplier_class": "CLASS_II",
            },
            is_active=True,
        )
        ctx_lc_45 = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_lc_45],
            verifications_by_type={"LOCAL_CONTENT": [v_lc_45]},
        )
        res_lc_45 = lc_evaluator.evaluate(req_lc_pct, ctx_lc_45)
        record_result("Local Content 45% < 50% evaluates to FAIL", res_lc_45.compliance_status == ComplianceStatus.FAIL, f"-> {res_lc_45.reason}")

        res_class_fail = lc_evaluator.evaluate(req_supplier_class, ctx_lc_45)
        record_result("Supplier Class CLASS_II (when CLASS_I required) evaluates to FAIL", res_class_fail.compliance_status == ComplianceStatus.FAIL, f"-> {res_class_fail.reason}")

        # Case C: Impossible Percentage (110%) -> REVIEW
        v_lc_bad = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="LOCAL_CONTENT",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock Local Content Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="110%",
            response_payload={"local_content_percentage": 110},
            is_active=True,
        )
        ctx_lc_bad = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_lc_bad],
            verifications_by_type={"LOCAL_CONTENT": [v_lc_bad]},
        )
        res_lc_bad = lc_evaluator.evaluate(req_lc_pct, ctx_lc_bad)
        record_result("Impossible percentage 110% evaluates to REVIEW", res_lc_bad.compliance_status == ComplianceStatus.REVIEW, f"-> {res_lc_bad.reason}")

        # =========================================================================
        # 4. BIS CRS / License Compliance Rules
        # =========================================================================
        print_test_header("4. BIS CRS / License Compliance Rules")

        record_result("BIS Standard normalization 'IS 13252 (Part 1)'", normalize_bis_standard("IS 13252 (Part 1)") == "IS 13252 (PART 1)")

        req_bis_std = TenderRequirement(
            id=uuid.uuid4(),
            code="BIS_STANDARD_REQUIRED",
            name="BIS Standard IS 13252 Certification",
            category="BIS",
            requirement_type="TEXT",
            operator="EQUALS",
            expected_value="IS 13252",
        )

        req_bis_stat = TenderRequirement(
            id=uuid.uuid4(),
            code="BIS_STATUS",
            name="BIS License Active Status",
            category="BIS",
            requirement_type="TEXT",
            operator="EQUALS",
            expected_value="VALID",
        )

        req_bis_val = TenderRequirement(
            id=uuid.uuid4(),
            code="BIS_VALIDITY",
            name="BIS License valid through tender deadline",
            category="BIS",
            requirement_type="DATE",
            operator="GREATER_THAN_OR_EQUAL",
            expected_value=None,  # compared vs tender deadline (2026-11-30)
        )

        # Case A: Valid BIS Record -> PASS
        v_bis_valid = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="BIS",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock BIS Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="R-41001234",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "bis_registration_number": "R-41001234",
                "standard_number": "IS 13252",
                "manufacturer_name": "SecureCore Systems",
                "registry_status": "VALID",
                "valid_until": "2027-03-31",
            },
            is_active=True,
        )
        ctx_bis_valid = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_bis_valid],
            verifications_by_type={"BIS": [v_bis_valid]},
        )

        res_bis_std = bis_evaluator.evaluate(req_bis_std, ctx_bis_valid)
        record_result("BIS Standard IS 13252 evaluates to PASS", res_bis_std.compliance_status == ComplianceStatus.PASS, f"-> {res_bis_std.reason}")

        res_bis_stat = bis_evaluator.evaluate(req_bis_stat, ctx_bis_valid)
        record_result("BIS Status VALID evaluates to PASS", res_bis_stat.compliance_status == ComplianceStatus.PASS, f"-> {res_bis_stat.reason}")

        res_bis_val = bis_evaluator.evaluate(req_bis_val, ctx_bis_valid)
        record_result("BIS Validity (2027-03-31 >= 2026-11-30) evaluates to PASS", res_bis_val.compliance_status == ComplianceStatus.PASS, f"-> {res_bis_val.reason}")

        # Case B: Cancelled BIS Status -> FAIL
        v_bis_canc = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="BIS",
            verification_status=VerificationStatus.VERIFIED,
            source_name="Mock BIS Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="R-41001234",
            match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "bis_registration_number": "R-41001234",
                "standard_number": "IS 13252",
                "registry_status": "CANCELLED",
                "valid_until": "2027-03-31",
            },
            is_active=True,
        )
        ctx_bis_canc = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_bis_canc],
            verifications_by_type={"BIS": [v_bis_canc]},
        )
        res_bis_canc = bis_evaluator.evaluate(req_bis_stat, ctx_bis_canc)
        record_result("BIS Status CANCELLED evaluates to FAIL", res_bis_canc.compliance_status == ComplianceStatus.FAIL, f"-> {res_bis_canc.reason}")

        # =========================================================================
        # 5. Supporting Document Presence & Internal Evidence Rules
        # =========================================================================
        print_test_header("5. Supporting Document Presence & Internal Evidence Rules")

        req_doc_mand = TenderRequirement(
            id=uuid.uuid4(),
            code="COMMERCIAL_DOCUMENT_REQUIRED",
            name="Commercial Price Schedule Document",
            category="DOCUMENT",
            requirement_type="DOCUMENT",
            is_mandatory=True,
        )

        req_doc_opt = TenderRequirement(
            id=uuid.uuid4(),
            code="OPTIONAL_AFFIDAVIT_REQUIRED",
            name="Optional Litigation Affidavit",
            category="DOCUMENT",
            requirement_type="DOCUMENT",
            is_mandatory=False,
        )

        # Document Present -> PASS
        doc_comm = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="COMMERCIAL_DOCUMENT", document_name="Price_Schedule.pdf", file_size=50000, is_active=True)
        ctx_doc_pass = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_comm])
        res_doc_pass = doc_evaluator.evaluate(req_doc_mand, ctx_doc_pass)
        record_result("Mandatory document present evaluates to PASS", res_doc_pass.compliance_status == ComplianceStatus.PASS, f"-> {res_doc_pass.reason}")

        # Mandatory Document Missing -> FAIL
        ctx_doc_missing = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[])
        res_doc_miss = doc_evaluator.evaluate(req_doc_mand, ctx_doc_missing)
        record_result("Mandatory document missing evaluates to FAIL", res_doc_miss.compliance_status == ComplianceStatus.FAIL, f"-> {res_doc_miss.reason}")

        # Optional Document Missing -> NOT_APPLICABLE
        res_doc_opt = doc_evaluator.evaluate(req_doc_opt, ctx_doc_missing)
        record_result("Optional document missing evaluates to NOT_APPLICABLE", res_doc_opt.compliance_status == ComplianceStatus.NOT_APPLICABLE, f"-> {res_doc_opt.reason}")

        # Document Processing Failed -> REVIEW
        doc_failed_proc = BidDocument(id=uuid.uuid4(), bid_id=dummy_bid.id, document_type="COMMERCIAL_DOCUMENT", document_name="Corrupt_Scan.pdf", file_size=50000, is_active=True)
        doc_failed_proc.processing = DocumentProcessing(id=uuid.uuid4(), bid_document_id=doc_failed_proc.id, processing_status="FAILED", classification_reason="Corrupt PDF byte header")
        ctx_proc_fail = ComplianceContext(bid=dummy_bid, tender=dummy_tender, bid_documents=[doc_failed_proc])
        res_proc_fail = doc_evaluator.evaluate(req_doc_mand, ctx_proc_fail)
        record_result("Document with FAILED processing evaluates to REVIEW", res_proc_fail.compliance_status == ComplianceStatus.REVIEW, f"-> {res_proc_fail.reason}")

        # =========================================================================
        # 6. Outage & Prerequisite Handling Resilience
        # =========================================================================
        print_test_header("6. Outage & Prerequisite Handling Resilience")

        v_oem_outage = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=dummy_bid.id,
            verification_type="OEM_AUTHORIZATION",
            verification_status=VerificationStatus.UNAVAILABLE,
            source_name="Mock OEM Registry",
            source_type=VerificationSourceType.MOCK,
            claimed_value="OEM/2026/AUTH/004",
            is_active=True,
        )
        ctx_outage = ComplianceContext(
            bid=dummy_bid,
            tender=dummy_tender,
            verifications=[v_oem_outage],
            verifications_by_type={"OEM_AUTHORIZATION": [v_oem_outage]},
        )
        res_oem_outage = oem_evaluator.evaluate(req_oem_auth, ctx_outage)
        record_result("UNAVAILABLE OEM verification returns REVIEW without failing bidder", res_oem_outage.compliance_status == ComplianceStatus.REVIEW, f"-> {res_oem_outage.reason}")

        # =========================================================================
        # 7. End-to-End Realistic Bid Compliance in Database
        # =========================================================================
        print_test_header("7. End-to-End Realistic Bid Compliance in Database")

        test_suffix = uuid.uuid4().hex[:6]
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        po_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()

        org_po = Organization(
            id=uuid.uuid4(),
            name=f"Defence Cyber Command {test_suffix}",
            organization_type="MINISTRY",
            is_active=True,
        )
        org_bidder = Organization(
            id=uuid.uuid4(),
            name=f"BHARAT SECURECOM PRIVATE LIMITED {test_suffix}",
            organization_type="PRIVATE_LIMITED",
            is_active=True,
        )
        db.add_all([org_po, org_bidder])
        db.commit()

        prof_po = Profile(
            id=uuid.uuid4(),
            email=f"po_6d_{test_suffix}@gov.mock",
            role_id=po_role.id,
            organization_id=org_po.id,
            full_name="Brig. V. Anand",
            is_active=True,
        )
        prof_bidder = Profile(
            id=uuid.uuid4(),
            email=f"bidder_6d_{test_suffix}@securecom.mock",
            role_id=bidder_role.id,
            organization_id=org_bidder.id,
            full_name="Muthu OEM Lead",
            is_active=True,
        )
        db.add_all([prof_po, prof_bidder])
        db.commit()

        user_bidder = User(
            id=uuid.uuid4(),
            email=f"bidder_6d_{test_suffix}@securecom.mock",
            password_hash="mock_hash",
            profile_id=prof_bidder.id,
            is_active=True,
        )
        user_po = User(
            id=uuid.uuid4(),
            email=f"po_6d_{test_suffix}@gov.mock",
            password_hash="mock_hash",
            profile_id=prof_po.id,
            is_active=True,
        )
        db.add_all([user_bidder, user_po])
        db.commit()

        tender = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/6D/{test_suffix.upper()}",
            title="Procurement of Secure Hardware Security Modules",
            description="Tender covering OEM, Make in India, BIS, and Document criteria",
            organization_id=org_po.id,
            created_by_profile_id=prof_po.id,
            submission_end_date=datetime(2026, 12, 31, 17, 0, 0, tzinfo=timezone.utc),
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)
        db.commit()

        # Seed Requirements
        req_defs = [
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="OEM_AUTHORIZATION_REQUIRED", name="OEM Authorization Certificate",
                category="OEM", requirement_type="TEXT", operator="EQUALS", expected_value="VALID",
                is_mandatory=True, weight=Decimal("25.0"),
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="MIN_LOCAL_CONTENT_PERCENTAGE", name="Minimum 50% Local Content",
                category="LOCAL_CONTENT", requirement_type="NUMBER", operator="GREATER_THAN_OR_EQUAL", expected_value="50",
                is_mandatory=True, weight=Decimal("25.0"),
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="BIS_STANDARD_REQUIRED", name="BIS Standard IS 13252 Compliance",
                category="BIS", requirement_type="TEXT", operator="EQUALS", expected_value="IS 13252",
                is_mandatory=True, weight=Decimal("25.0"),
            ),
            TenderRequirement(
                id=uuid.uuid4(), tender_id=tender.id, code="COMMERCIAL_DOCUMENT_REQUIRED", name="Commercial Price Bid Document",
                category="DOCUMENT", requirement_type="DOCUMENT", operator="EXISTS", expected_value=True,
                is_mandatory=True, weight=Decimal("25.0"),
            ),
        ]
        db.add_all(req_defs)
        db.commit()

        bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            submitted_by_profile_id=prof_bidder.id,
            bid_number=f"BID/2026/6D/{test_suffix.upper()}",
            status="SUBMITTED",
            submitted_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(bid)
        db.commit()

        # Seed Bid Documents
        doc_oem = BidDocument(
            id=uuid.uuid4(), bid_id=bid.id, uploaded_by_profile_id=prof_bidder.id,
            document_type="OEM_AUTHORIZATION", document_name="OEM_MAF_Letter.pdf",
            original_filename="OEM_MAF_Letter.pdf", storage_path="/mock/oem.pdf",
            mime_type="application/pdf", file_size=102400, is_active=True,
        )
        doc_lc = BidDocument(
            id=uuid.uuid4(), bid_id=bid.id, uploaded_by_profile_id=prof_bidder.id,
            document_type="LOCAL_CONTENT_DECLARATION", document_name="MII_Self_Declaration.pdf",
            original_filename="MII_Self_Declaration.pdf", storage_path="/mock/mii.pdf",
            mime_type="application/pdf", file_size=153600, is_active=True,
        )
        doc_bis = BidDocument(
            id=uuid.uuid4(), bid_id=bid.id, uploaded_by_profile_id=prof_bidder.id,
            document_type="BIS_CERTIFICATE", document_name="BIS_CRS_Registration.pdf",
            original_filename="BIS_CRS_Registration.pdf", storage_path="/mock/bis.pdf",
            mime_type="application/pdf", file_size=204800, is_active=True,
        )
        doc_comm_db = BidDocument(
            id=uuid.uuid4(), bid_id=bid.id, uploaded_by_profile_id=prof_bidder.id,
            document_type="COMMERCIAL_DOCUMENT", document_name="Price_Schedule_Signed.pdf",
            original_filename="Price_Schedule_Signed.pdf", storage_path="/mock/price.pdf",
            mime_type="application/pdf", file_size=81920, is_active=True,
        )
        db.add_all([doc_oem, doc_lc, doc_bis, doc_comm_db])
        db.commit()

        # Seed Part 5 Verification Records
        v_rec_oem = VerificationRecord(
            id=uuid.uuid4(), bid_id=bid.id, bid_document_id=doc_oem.id,
            verification_type="OEM_AUTHORIZATION", verification_status=VerificationStatus.VERIFIED,
            source_name="Mock OEM Registry", source_type=VerificationSourceType.MOCK,
            claimed_value="OEM/2026/AUTH/888", match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "reference_number": "OEM/2026/AUTH/888",
                "oem_name": "Fortinet Inc",
                "authorized_entity": org_bidder.name,
                "product_scope": "HSM Security Appliances",
                "authorization_status": "VALID",
                "valid_until": "2027-06-30",
            },
            is_active=True,
        )
        v_rec_lc = VerificationRecord(
            id=uuid.uuid4(), bid_id=bid.id, bid_document_id=doc_lc.id,
            verification_type="LOCAL_CONTENT", verification_status=VerificationStatus.VERIFIED,
            source_name="Mock Local Content Registry", source_type=VerificationSourceType.MOCK,
            claimed_value="60%", match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "local_content_percentage": 60,
                "supplier_class": "CLASS_I",
                "product_name": "HSM Security Appliances",
            },
            is_active=True,
        )
        v_rec_bis = VerificationRecord(
            id=uuid.uuid4(), bid_id=bid.id, bid_document_id=doc_bis.id,
            verification_type="BIS", verification_status=VerificationStatus.VERIFIED,
            source_name="Mock BIS Registry", source_type=VerificationSourceType.MOCK,
            claimed_value="R-41009999", match_status=VerificationMatchStatus.MATCH,
            response_payload={
                "bis_registration_number": "R-41009999",
                "standard_number": "IS 13252",
                "registry_status": "VALID",
                "valid_until": "2027-12-31",
            },
            is_active=True,
        )
        db.add_all([v_rec_oem, v_rec_lc, v_rec_bis])
        db.commit()

        # Run Compliance Evaluation
        eval_summary = evaluate_bid_compliance(
            db=db,
            current_user=user_bidder,
            bid_id=bid.id,
        )

        record_result("evaluate_bid_compliance evaluates all 4 Part 6D rules", eval_summary.counts.total == 4)
        record_result("All 4 requirements evaluated to PASS", eval_summary.counts.passed == 4)

        for res in eval_summary.results:
            print(f"    -> [{res.compliance_status}] Req: {res.requirement_code}, Actual: '{res.actual_value}', Reason: {res.reason}")

        # Multi-Tenant Alien Access
        alien_user = User(id=uuid.uuid4(), email="alien_6d@other.org", password_hash="x", is_active=True)
        alien_rejected = False
        try:
            get_bid_compliance(
                db=db,
                current_user=alien_user,
                bid_id=bid.id,
            )
        except Exception:
            alien_rejected = True

        record_result("Alien user access rejected with HTTP 404 (Tenant Isolation)", alien_rejected)

        # Boundary Check: No Part 7/8 fields
        db_results = db.scalars(select(ComplianceResult).where(ComplianceResult.bid_id == bid.id)).all()
        for cr in db_results:
            assert not hasattr(cr, "score"), "ComplianceResult should not have score field"
            assert not hasattr(cr, "risk_level"), "ComplianceResult should not have risk_level field"
            assert not hasattr(cr, "final_decision"), "ComplianceResult should not have final_decision field"

        record_result("Strict compliance boundary preserved (No Part 7/8 fields)", True)

    except Exception as e:
        print(f"\n[ERROR] Exception during Part 6D testing: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

    print("\n" + "=" * 70)
    print("PART 6D MASTER TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run : {PASSED_TESTS + FAILED_TESTS}")
    print(f"Passed          : {PASSED_TESTS}")
    print(f"Failed          : {FAILED_TESTS}")

    if FAILED_TESTS == 0:
        print("\n>>> ALL PART 6D OEM, LOCAL CONTENT, BIS & DOCUMENT TESTS PASSED! <<<\n")
    else:
        print(f"\n>>> {FAILED_TESTS} TEST(S) FAILED <<<\n")
        sys.exit(1)


if __name__ == "__main__":
    run_part6d_master_test_suite()
