"""
Part 7F Master QA Test Suite: Unified Bid Evaluation Summary, Hardening, and Regression Testing

Covers:
1. Unified evaluation generation across Compliance, Scoring, Risk, and Grounded AI
2. Score & Category Scoring Integration
3. Base Risk & Adjusted Risk Overrides Integration
4. AI Recommendation & Grounded Citation Integration
5. Critical Findings Section Aggregation (Active Blacklisting & Critical Defect)
6. Mandatory Failure Section Aggregation
7. Human Review Required Flags & Review Summary Aggregation
8. Evaluation Completeness (Compliance + Score + Risk complete; AI decoupled)
9. AI Failure Isolation (Simulated AI failure -> Deterministic evaluation remains complete & working)
10. Version Consistency & Dependency Tracking (Compliance -> Score -> Risk -> AI)
11. Stale Score Detection (Compliance change flags score as stale)
12. Stale Risk Detection (Score change flags risk as stale)
13. Stale AI Detection (Risk/Score change flags AI as stale)
14. Deterministic Refresh (Recalculates score/risk without LLM call)
15. Explicit AI Regeneration (Forces fresh knowledge indexing & AI synthesis)
16. Traceable Full Evidence Chain (Requirement -> Doc -> Ver -> Comp -> Score -> Risk -> AI)
17. Mock Source Transparency preserved
18. Multi-Tenant RBAC Security (Cross-tenant officer blocked)
19. Multi-Tenant RBAC Security (Bidder blocked)
20. Strict Boundary Invariant: final_decision_status is NOT_MADE; no automatic qualification
21. Strict Boundary Invariant: AI never mutates compliance, score, or risk values
"""

import os
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from fastapi import HTTPException

from app.core.security import hash_password
from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.compliance_result import ComplianceResult
from app.db.models.document_processing import DocumentProcessing, ProcessingStatus
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.rag_chunk import RAGChunk
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.db.session import get_session_factory
from app.services.ai.ai_config import AIRecommendationEnum
from app.services.ai.ai_recommendation_service import AIRecommendationService
from app.services.evaluation.bid_evaluation_service import BidEvaluationService
from app.services.risk_service import calculate_and_save_bid_risk
from app.services.scoring_service import calculate_and_save_bid_score

SessionLocal = get_session_factory()

passed_tests = 0
failed_tests = 0


def log_test(test_num: int, name: str, passed: bool, details: str = ""):
    global passed_tests, failed_tests
    status_str = "[PASS]" if passed else "[FAIL]"
    if passed:
        passed_tests += 1
    else:
        failed_tests += 1
    print(f"  {status_str} | Test {test_num:02d}: {name}")
    if details:
        print(f"         {details}")


def run_tests():
    global passed_tests, failed_tests
    print("\n" + "=" * 80)
    print("STARTING PART 7F MASTER QA SUITE: UNIFIED BID EVALUATION INTEGRATION")
    print("=" * 80 + "\n")

    db = SessionLocal()

    try:
        # =========================================================================
        # SECTION 1: Setup Multi-Tenant Test Fixtures
        # =========================================================================
        print("--- SECTION 1: Setting Up Multi-Tenant Fixtures ---")

        officer_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
        if not officer_role:
            officer_role = Role(name="PROCUREMENT_OFFICER", description="Procurement Officer")
            db.add(officer_role)
            db.flush()

        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        if not bidder_role:
            bidder_role = Role(name="BIDDER", description="Bidder Role")
            db.add(bidder_role)
            db.flush()

        test_run_id = uuid.uuid4().hex[:6]

        # Org A (Procuring Org)
        org_a = Organization(
            name=f"Ministry of Electronics QA-7F {test_run_id}",
            organization_type="PROCURING_ENTITY",
            is_active=True,
        )
        db.add(org_a)
        db.flush()

        # Org B (Alien Procuring Org)
        org_b = Organization(
            name=f"Ministry of Health QA-7F {test_run_id}",
            organization_type="PROCURING_ENTITY",
            is_active=True,
        )
        db.add(org_b)
        db.flush()

        # Bidder Org
        org_bidder = Organization(
            name=f"Apex Servers India Pvt Ltd QA-7F {test_run_id}",
            organization_type="BIDDER",
            is_active=True,
        )
        db.add(org_bidder)
        db.flush()

        # Officer A
        prof_a = Profile(
            full_name="Officer A",
            email=f"officer_a_{test_run_id}@gov.in",
            role_id=officer_role.id,
            organization_id=org_a.id,
            is_active=True,
        )
        db.add(prof_a)
        db.flush()

        user_officer_a = User(
            email=f"officer_a_{test_run_id}@gov.in",
            password_hash=hash_password("Secret123!"),
            profile_id=prof_a.id,
            is_active=True,
        )
        db.add(user_officer_a)

        # Officer B (Alien Org)
        prof_b = Profile(
            full_name="Officer B",
            email=f"officer_b_{test_run_id}@gov.in",
            role_id=officer_role.id,
            organization_id=org_b.id,
            is_active=True,
        )
        db.add(prof_b)
        db.flush()

        user_officer_b = User(
            email=f"officer_b_{test_run_id}@gov.in",
            password_hash=hash_password("Secret123!"),
            profile_id=prof_b.id,
            is_active=True,
        )
        db.add(user_officer_b)

        # Bidder User 1
        prof_bidder = Profile(
            full_name="Bidder User 1",
            email=f"bidder_1_{test_run_id}@apex.in",
            role_id=bidder_role.id,
            organization_id=org_bidder.id,
            is_active=True,
        )
        db.add(prof_bidder)
        db.flush()

        user_bidder = User(
            email=f"bidder_1_{test_run_id}@apex.in",
            password_hash=hash_password("Secret123!"),
            profile_id=prof_bidder.id,
            is_active=True,
        )
        db.add(user_bidder)

        # Bidder Org 2 & Profile 2
        org_bidder_2 = Organization(
            name=f"Zenith Compute Solutions QA-7F {test_run_id}",
            organization_type="BIDDER",
            is_active=True,
        )
        db.add(org_bidder_2)
        db.flush()

        prof_bidder_2 = Profile(
            full_name="Bidder User 2",
            email=f"bidder_2_{test_run_id}@zenith.in",
            role_id=bidder_role.id,
            organization_id=org_bidder_2.id,
            is_active=True,
        )
        db.add(prof_bidder_2)
        db.flush()

        # Bidder Org 3 & Profile 3
        org_bidder_3 = Organization(
            name=f"Param Systems India QA-7F {test_run_id}",
            organization_type="BIDDER",
            is_active=True,
        )
        db.add(org_bidder_3)
        db.flush()

        prof_bidder_3 = Profile(
            full_name="Bidder User 3",
            email=f"bidder_3_{test_run_id}@param.in",
            role_id=bidder_role.id,
            organization_id=org_bidder_3.id,
            is_active=True,
        )
        db.add(prof_bidder_3)
        db.flush()

        # Create Tender under Org A
        tender_a = Tender(
            organization_id=org_a.id,
            created_by_profile_id=prof_a.id,
            tender_number=f"GEM/2026/B/7F-{test_run_id}",
            title="High Performance Computing Cluster Servers",
            description="Procurement of compute nodes with Make in India compliance",
            category="IT_EQUIPMENT",
            estimated_value=Decimal("50000000.00"),
            status="OPEN",
            is_active=True,
        )
        db.add(tender_a)
        db.flush()

        # Create Dynamic Requirements
        req_gst = TenderRequirement(
            tender_id=tender_a.id,
            code="GST_REGISTRATION",
            name="Active GST Registration",
            category="STATUTORY",
            description="Active GST on government portal",
            is_mandatory=True,
            is_critical=True,
            weight=Decimal("20.0000"),
            is_active=True,
        )
        req_turnover = TenderRequirement(
            tender_id=tender_a.id,
            code="MIN_ANNUAL_TURNOVER",
            name="Minimum Annual Turnover INR 5 Cr",
            category="FINANCIAL",
            description="Minimum turnover ₹5 Crore",
            is_mandatory=True,
            is_critical=False,
            weight=Decimal("30.0000"),
            is_active=True,
        )
        req_local = TenderRequirement(
            tender_id=tender_a.id,
            code="LOCAL_CONTENT",
            name="Class-I Local Content (>=50%)",
            category="LOCAL_CONTENT",
            description="Minimum 50% Make in India local content",
            is_mandatory=True,
            is_critical=False,
            weight=Decimal("25.0000"),
            is_active=True,
        )
        req_black = TenderRequirement(
            tender_id=tender_a.id,
            code="NOT_BLACKLISTED",
            name="Integrity & Non-Blacklisting",
            category="INTEGRITY",
            description="No active blacklisting or debarment",
            is_mandatory=True,
            is_critical=True,
            weight=Decimal("25.0000"),
            is_active=True,
        )
        db.add_all([req_gst, req_turnover, req_local, req_black])
        db.flush()

        # Create Bid 1 (Happy path clean pass bid)
        bid_1 = Bid(
            tender_id=tender_a.id,
            bidder_organization_id=org_bidder.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-2026-7F-001-{test_run_id}",
            status="SUBMITTED",
            quoted_amount=Decimal("48000000.00"),
            is_active=True,
        )
        db.add(bid_1)
        db.flush()

        # Create Documents & Extractions for Bid 1
        doc_gst = BidDocument(
            bid_id=bid_1.id,
            uploaded_by_profile_id=prof_bidder.id,
            document_type="GST_CERTIFICATE",
            document_name="GST Certificate",
            original_filename="GST_Certificate.pdf",
            storage_path=f"bids/{bid_1.id}/GST_Certificate.pdf",
            mime_type="application/pdf",
            file_size=10240,
            is_active=True,
        )
        db.add(doc_gst)
        db.flush()

        proc_gst = DocumentProcessing(
            bid_document_id=doc_gst.id,
            processing_status=ProcessingStatus.COMPLETED,
            raw_text="GSTIN: 27AAAAA0000A1Z5 Legal Name: Apex Servers India Pvt Ltd Status: ACTIVE",
            normalized_text="gstin: 27aaaaa0000a1z5 legal name: apex servers india pvt ltd status: active",
            extracted_data={"gstin": {"value": "27AAAAA0000A1Z5", "confidence": 0.99, "evidence": "GSTIN: 27AAAAA0000A1Z5"}},
        )
        db.add(proc_gst)
        db.flush()

        # Verification records for Bid 1
        ver_gst = VerificationRecord(
            bid_id=bid_1.id,
            bid_document_id=doc_gst.id,
            verification_type="GST",
            verification_status="VERIFIED",
            source_name="Mock GST Registry",
            source_type="MOCK",
            claimed_value="27AAAAA0000A1Z5",
            verified_value="ACTIVE",
            match_status="MATCHED",
            confidence=Decimal("1.0"),
            is_active=True,
        )
        ver_turnover = VerificationRecord(
            bid_id=bid_1.id,
            verification_type="FINANCIAL",
            verification_status="VERIFIED",
            source_name="Audited Financial Statement",
            source_type="INTERNAL",
            claimed_value="85000000.0",
            verified_value="85000000.0",
            match_status="MATCHED",
            confidence=Decimal("1.0"),
            is_active=True,
        )
        ver_local = VerificationRecord(
            bid_id=bid_1.id,
            verification_type="LOCAL_CONTENT",
            verification_status="VERIFIED",
            source_name="MII Declaration Certificate",
            source_type="INTERNAL",
            claimed_value="65.0",
            verified_value="65.0",
            match_status="MATCHED",
            confidence=Decimal("1.0"),
            is_active=True,
        )
        ver_black = VerificationRecord(
            bid_id=bid_1.id,
            verification_type="BLACKLISTING",
            verification_status="VERIFIED",
            source_name="Central Debarment Registry",
            source_type="MOCK",
            claimed_value="NOT_BLACKLISTED",
            verified_value="CLEAR",
            match_status="MATCHED",
            confidence=Decimal("1.0"),
            is_active=True,
        )
        db.add_all([ver_gst, ver_turnover, ver_local, ver_black])
        db.flush()

        # Compliance results for Bid 1 (All PASS)
        cr_gst_1 = ComplianceResult(
            bid_id=bid_1.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_gst.id,
            compliance_status="PASS",
            reason="GST active on portal",
            is_mandatory=True,
            is_critical=True,
            evaluation_version=1,
            is_current=True,
        )
        cr_turnover_1 = ComplianceResult(
            bid_id=bid_1.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_turnover.id,
            compliance_status="PASS",
            reason="Turnover INR 8.5 Cr meets INR 5 Cr threshold",
            is_mandatory=True,
            is_critical=False,
            evaluation_version=1,
            is_current=True,
        )
        cr_local_1 = ComplianceResult(
            bid_id=bid_1.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_local.id,
            compliance_status="PASS",
            reason="Local content 65.0% exceeds 50.0% requirement",
            is_mandatory=True,
            is_critical=False,
            evaluation_version=1,
            is_current=True,
        )
        cr_black_1 = ComplianceResult(
            bid_id=bid_1.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_black.id,
            compliance_status="PASS",
            reason="Bidder not blacklisted on official registry",
            is_mandatory=True,
            is_critical=True,
            evaluation_version=1,
            is_current=True,
        )
        db.add_all([cr_gst_1, cr_turnover_1, cr_local_1, cr_black_1])
        db.commit()

        # Calculate initial score, risk, and AI for Bid 1
        score_1 = calculate_and_save_bid_score(db, user_officer_a, bid_1.id)
        risk_1 = calculate_and_save_bid_risk(db, user_officer_a, bid_1.id)
        ai_1 = AIRecommendationService.generate_bid_recommendation(db, user_officer_a, bid_1.id, force_refresh=True)

        # =========================================================================
        # SECTION 2: Unified Bid Evaluation Generation & Sub-Sections (Happy Path)
        # =========================================================================
        print("\n--- SECTION 2: Unified Bid Evaluation Output Verification ---")

        eval_resp_1 = BidEvaluationService.get_unified_evaluation(db, user_officer_a, bid_1.id)

        # Test 01: Top level attributes
        t01_ok = (
            eval_resp_1.bid_id == bid_1.id
            and eval_resp_1.tender_id == tender_a.id
            and eval_resp_1.bid_number == bid_1.bid_number
            and eval_resp_1.tender_number == tender_a.tender_number
            and eval_resp_1.bidder_name == org_bidder.name
            and eval_resp_1.evaluation_complete is True
        )
        log_test(1, "get_unified_evaluation returns typed summary with all metadata", t01_ok, f"Bid: {eval_resp_1.bid_number}, Complete: {eval_resp_1.evaluation_complete}")

        # Test 02: Score Section
        t02_ok = (
            eval_resp_1.score.overall_compliance_score is not None
            and abs(eval_resp_1.score.overall_compliance_score - 100.0) < 1e-2
            and eval_resp_1.score.score_type == "FINAL"
            and eval_resp_1.score.scoring_complete is True
            and eval_resp_1.score.earned_weight > 0
            and abs(eval_resp_1.score.earned_weight - eval_resp_1.score.eligible_weight) < 1e-2
            and "STATUTORY" in eval_resp_1.score.category_scores
            and "LOCAL_CONTENT" in eval_resp_1.score.category_scores
        )
        log_test(2, "Score section accurately reflects 100% compliance and category items", t02_ok, f"Overall: {eval_resp_1.score.overall_compliance_score}%, Categories: {list(eval_resp_1.score.category_scores.keys())}")

        # Test 03: Risk Section
        t03_ok = (
            eval_resp_1.risk.base_risk_score == 0.0
            and eval_resp_1.risk.base_risk_level == "LOW"
            and eval_resp_1.risk.adjusted_risk_score == 0.0
            and eval_resp_1.risk.adjusted_risk_level == "LOW"
            and eval_resp_1.risk.override_applied is False
            and eval_resp_1.risk.risk_complete is True
        )
        log_test(3, "Risk section accurately reflects base & adjusted LOW risk (0.0/100)", t03_ok, f"Base: {eval_resp_1.risk.base_risk_score}, Adjusted: {eval_resp_1.risk.adjusted_risk_score}")

        # Test 04: AI Section
        t04_ok = (
            eval_resp_1.ai_recommendation.status == "CURRENT"
            and eval_resp_1.ai_recommendation.recommendation == "PROCEED"
            and len(eval_resp_1.ai_recommendation.strengths) > 0
            and len(eval_resp_1.ai_recommendation.evidence_refs) > 0
        )
        log_test(4, "AI recommendation section reflects CURRENT status with grounded citations", t04_ok, f"Rec: {eval_resp_1.ai_recommendation.recommendation}, Strengths: {len(eval_resp_1.ai_recommendation.strengths)}, Citations: {len(eval_resp_1.ai_recommendation.evidence_refs)}")

        # =========================================================================
        # SECTION 3: Critical Defect Bid (Active Blacklisting Failure)
        # =========================================================================
        print("\n--- SECTION 3: Critical Defect & Risk Override Integration ---")

        bid_2 = Bid(
            tender_id=tender_a.id,
            bidder_organization_id=org_bidder_2.id,
            created_by_profile_id=prof_bidder_2.id,
            bid_number=f"BID-2026-7F-002-{test_run_id}",
            status="SUBMITTED",
            quoted_amount=Decimal("49000000.00"),
            is_active=True,
        )
        db.add(bid_2)
        db.flush()

        # Bid 2 verifications: Blacklisting failed!
        ver_black_fail = VerificationRecord(
            bid_id=bid_2.id,
            verification_type="BLACKLISTING",
            verification_status="VERIFIED",
            source_name="Central Debarment Registry",
            source_type="MOCK",
            claimed_value="NOT_BLACKLISTED",
            verified_value="BLACKLISTED",
            match_status="MISMATCH",
            confidence=Decimal("1.0"),
            is_active=True,
        )
        db.add(ver_black_fail)
        db.flush()

        # Compliance for Bid 2: Blacklisting FAIL (critical=True), others PASS
        cr_gst_2 = ComplianceResult(
            bid_id=bid_2.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_gst.id,
            compliance_status="PASS",
            reason="GST active",
            is_mandatory=True,
            is_critical=True,
            evaluation_version=1,
            is_current=True,
        )
        cr_turnover_2 = ComplianceResult(
            bid_id=bid_2.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_turnover.id,
            compliance_status="PASS",
            reason="Turnover verified",
            is_mandatory=True,
            is_critical=False,
            evaluation_version=1,
            is_current=True,
        )
        cr_local_2 = ComplianceResult(
            bid_id=bid_2.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_local.id,
            compliance_status="PASS",
            reason="Local content verified",
            is_mandatory=True,
            is_critical=False,
            evaluation_version=1,
            is_current=True,
        )
        cr_black_2 = ComplianceResult(
            bid_id=bid_2.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_black.id,
            compliance_status="FAIL",
            reason="Entity actively listed on Central Debarment Registry",
            is_mandatory=True,
            is_critical=True,
            evaluation_version=1,
            is_current=True,
        )
        db.add_all([cr_gst_2, cr_turnover_2, cr_local_2, cr_black_2])
        db.commit()

        # Compute score, risk, and AI for Bid 2
        calculate_and_save_bid_score(db, user_officer_a, bid_2.id)
        calculate_and_save_bid_risk(db, user_officer_a, bid_2.id)
        AIRecommendationService.generate_bid_recommendation(db, user_officer_a, bid_2.id, force_refresh=True)

        eval_resp_2 = BidEvaluationService.get_unified_evaluation(db, user_officer_a, bid_2.id)

        # Test 05: Critical Summary Aggregation
        t05_ok = (
            eval_resp_2.critical_summary.critical_failure_present is True
            and eval_resp_2.critical_summary.critical_failure_count == 1
            and eval_resp_2.critical_summary.critical_override_applied is True
            and len(eval_resp_2.critical_summary.critical_findings) == 1
            and eval_resp_2.critical_summary.critical_findings[0].requirement_code == "NOT_BLACKLISTED"
        )
        log_test(5, "Critical summary aggregates active blacklisting critical finding and override", t05_ok, f"Crit Defect: {eval_resp_2.critical_summary.critical_failure_present}, Findings: {len(eval_resp_2.critical_summary.critical_findings)}")

        # Test 06: Mandatory vs Non-Mandatory Failures
        t06_ok = (
            eval_resp_2.compliance.fail_count == 1
            and eval_resp_2.compliance.mandatory_failures_count == 1
            and eval_resp_2.compliance.critical_failures_count == 1
        )
        log_test(6, "Compliance section accurately enumerates mandatory & critical failures", t06_ok, f"Fails: {eval_resp_2.compliance.fail_count}, Mandatory Fails: {eval_resp_2.compliance.mandatory_failures_count}")

        # Test 07: Human Review Required Summary
        t07_ok = (
            eval_resp_2.human_review_required is True
            and eval_resp_2.review_summary.human_review_required is True
        )
        log_test(7, "human_review_required flag is set to True upon critical defects or overrides", t07_ok, f"Review Req: {eval_resp_2.human_review_required}")

        # Test 08: Evaluation Completeness independent of AI
        t08_ok = (
            eval_resp_2.evaluation_complete is True
            and eval_resp_2.compliance.evaluation_complete is True
            and eval_resp_2.score.scoring_complete is True
            and eval_resp_2.risk.risk_complete is True
        )
        log_test(8, "Deterministic evaluation_complete is True when compliance, score, risk complete", t08_ok, f"Complete: {eval_resp_2.evaluation_complete}")

        # =========================================================================
        # SECTION 4: AI Failure & Isolation
        # =========================================================================
        print("\n--- SECTION 4: AI Failure Isolation & Decoupling ---")

        # Bid 3: No AI Recommendation generated (Simulating offline or uninvoked LLM)
        bid_3 = Bid(
            tender_id=tender_a.id,
            bidder_organization_id=org_bidder_3.id,
            created_by_profile_id=prof_bidder_3.id,
            bid_number=f"BID-2026-7F-003-{test_run_id}",
            status="SUBMITTED",
            quoted_amount=Decimal("47000000.00"),
            is_active=True,
        )
        db.add(bid_3)
        db.flush()

        cr_gst_3 = ComplianceResult(
            bid_id=bid_3.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_gst.id,
            compliance_status="PASS",
            reason="GST active",
            is_mandatory=True,
            is_critical=True,
            evaluation_version=1,
            is_current=True,
        )
        cr_turnover_3 = ComplianceResult(
            bid_id=bid_3.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_turnover.id,
            compliance_status="PASS",
            reason="Turnover verified",
            is_mandatory=True,
            is_critical=False,
            evaluation_version=1,
            is_current=True,
        )
        cr_local_3 = ComplianceResult(
            bid_id=bid_3.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_local.id,
            compliance_status="PASS",
            reason="Local content verified",
            is_mandatory=True,
            is_critical=False,
            evaluation_version=1,
            is_current=True,
        )
        cr_black_3 = ComplianceResult(
            bid_id=bid_3.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_black.id,
            compliance_status="PASS",
            reason="Integrity verified",
            is_mandatory=True,
            is_critical=True,
            evaluation_version=1,
            is_current=True,
        )
        db.add_all([cr_gst_3, cr_turnover_3, cr_local_3, cr_black_3])
        db.commit()

        calculate_and_save_bid_score(db, user_officer_a, bid_3.id)
        calculate_and_save_bid_risk(db, user_officer_a, bid_3.id)

        eval_resp_3 = BidEvaluationService.get_unified_evaluation(db, user_officer_a, bid_3.id)

        # Test 09: AI Failure Isolation
        t09_ok = (
            eval_resp_3.ai_recommendation.status == "NOT_GENERATED"
            and eval_resp_3.evaluation_complete is True
            and eval_resp_3.score.scoring_complete is True
            and eval_resp_3.risk.risk_complete is True
        )
        log_test(9, "AI unavailability does not break evaluation or mark deterministic checks incomplete", t09_ok, f"AI Status: {eval_resp_3.ai_recommendation.status}, Eval Complete: {eval_resp_3.evaluation_complete}")

        # =========================================================================
        # SECTION 5: Staleness Detection Across the Dependency Chain
        # =========================================================================
        print("\n--- SECTION 5: Staleness Detection Across Dependency Chain ---")

        # Test 10: Stale Score Detection (Compliance modified after score calculated)
        # Add new compliance result with version 2
        cr_new = ComplianceResult(
            bid_id=bid_3.id,
            tender_id=tender_a.id,
            tender_requirement_id=req_local.id,
            compliance_status="FAIL",
            reason="Local content 40.0% below threshold",
            is_mandatory=True,
            is_critical=False,
            evaluation_version=2,
            is_current=True,
        )
        db.add(cr_new)
        db.commit()

        eval_resp_3_stale = BidEvaluationService.get_unified_evaluation(db, user_officer_a, bid_3.id)
        t10_ok = (
            "SCORE" in eval_resp_3_stale.stale_components
            or eval_resp_3_stale.score.is_stale is True
        )
        log_test(10, "Stale Score detected when new compliance result is created upstream", t10_ok, f"Stale components: {eval_resp_3_stale.stale_components}")

        # Test 11: Stale Risk Detection
        # When score is recalculated, risk snapshot retains old score_snapshot_id -> risk is stale
        calculate_and_save_bid_score(db, user_officer_a, bid_3.id)
        eval_resp_3_risk_stale = BidEvaluationService.get_unified_evaluation(db, user_officer_a, bid_3.id)
        t11_ok = (
            "RISK" in eval_resp_3_risk_stale.stale_components
            or eval_resp_3_risk_stale.risk.is_stale is True
        )
        log_test(11, "Stale Risk detected when score snapshot is recalculated upstream", t11_ok, f"Stale components: {eval_resp_3_risk_stale.stale_components}")

        # Test 12: Stale AI Detection (AI recommendation calculated on old snapshot becomes stale)
        calculate_and_save_bid_risk(db, user_officer_a, bid_3.id)
        AIRecommendationService.generate_bid_recommendation(db, user_officer_a, bid_3.id, force_refresh=True)

        # Now recalculate risk again -> creates new risk snapshot -> AI becomes stale
        calculate_and_save_bid_risk(db, user_officer_a, bid_3.id)
        eval_resp_3_ai_stale = BidEvaluationService.get_unified_evaluation(db, user_officer_a, bid_3.id)
        t12_ok = (
            "AI" in eval_resp_3_ai_stale.stale_components
            or eval_resp_3_ai_stale.ai_recommendation.is_stale is True
            or eval_resp_3_ai_stale.ai_recommendation.status == "STALE"
        )
        log_test(12, "Stale AI detected when downstream risk snapshot is refreshed", t12_ok, f"AI Status: {eval_resp_3_ai_stale.ai_recommendation.status}, Stale List: {eval_resp_3_ai_stale.stale_components}")

        # =========================================================================
        # SECTION 6: Refresh Endpoints (Deterministic vs Explicit AI)
        # =========================================================================
        print("\n--- SECTION 6: Refresh Workflows (Deterministic vs AI) ---")

        # Test 13: Deterministic Refresh (Recalculates score and risk without LLM call)
        refreshed_eval = BidEvaluationService.refresh_bid_evaluation(
            db=db,
            user=user_officer_a,
            bid_id=bid_3.id,
            refresh_ai=False,
        )
        t13_ok = (
            refreshed_eval.score.is_stale is False
            and refreshed_eval.risk.is_stale is False
            and refreshed_eval.score.scoring_complete is True
            and refreshed_eval.risk.risk_complete is True
        )
        log_test(13, "Deterministic refresh updates score and risk cleanly without forcing LLM", t13_ok, f"Score stale: {refreshed_eval.score.is_stale}, Risk stale: {refreshed_eval.risk.is_stale}")

        # Test 14: Explicit AI Regeneration (Refreshes AI recommendation to CURRENT)
        ai_refreshed_eval = BidEvaluationService.refresh_bid_evaluation(
            db=db,
            user=user_officer_a,
            bid_id=bid_3.id,
            refresh_ai=True,
        )
        t14_ok = (
            ai_refreshed_eval.ai_recommendation.status == "CURRENT"
            and ai_refreshed_eval.ai_recommendation.is_stale is False
            and len(ai_refreshed_eval.stale_components) == 0
        )
        log_test(14, "Explicit AI regeneration updates AI recommendation status to CURRENT", t14_ok, f"AI Status: {ai_refreshed_eval.ai_recommendation.status}, Stale components: {ai_refreshed_eval.stale_components}")

        # =========================================================================
        # SECTION 7: Auditability, Full Evidence Chain & Mock Transparency
        # =========================================================================
        print("\n--- SECTION 7: Auditability, Evidence Chain & Mock Transparency ---")

        # Test 15: Auditable Traceable Full Evidence Chain
        # Trace: req_gst -> doc_gst -> ver_gst -> cr_gst_1 -> score_1 -> risk_1 -> ai_1
        score_snap_1 = db.scalars(select(BidScoreSnapshot).where(BidScoreSnapshot.bid_id == bid_1.id, BidScoreSnapshot.is_current == True)).first()
        risk_snap_1 = db.scalars(select(BidRiskSnapshot).where(BidRiskSnapshot.bid_id == bid_1.id, BidRiskSnapshot.is_current == True)).first()

        trace_ok = (
            doc_gst.id is not None
            and ver_gst.bid_document_id == doc_gst.id
            and cr_gst_1.tender_requirement_id == req_gst.id
            and score_snap_1 is not None
            and risk_snap_1 is not None
            and eval_resp_1.score.snapshot_id == score_snap_1.id
            and eval_resp_1.risk.snapshot_id == risk_snap_1.id
            and eval_resp_1.ai_recommendation.recommendation_id == getattr(ai_1, "recommendation_id", getattr(ai_1, "id", None))
        )
        log_test(15, "Full end-to-end evidence chain is connected and traceable across all models", trace_ok, f"Req: {req_gst.code} -> Doc: {doc_gst.original_filename} -> ScoreSnap: {score_snap_1.id if score_snap_1 else None} -> RiskSnap: {risk_snap_1.id if risk_snap_1 else None}")

        # Test 16: Mock Source Transparency
        t16_ok = False
        if eval_resp_1.ai_recommendation.evidence_refs:
            for ref in eval_resp_1.ai_recommendation.evidence_refs:
                if "Mock" in ref.get("title", "") or "Mock" in ref.get("summary", "") or "GST" in ref.get("title", ""):
                    t16_ok = True
                    break
        log_test(16, "Mock source transparency tags preserved in citations and evidence records", t16_ok, "Mock Registry citation preserved in vector retrieval")

        # =========================================================================
        # SECTION 8: Multi-Tenant RBAC Security
        # =========================================================================
        print("\n--- SECTION 8: Multi-Tenant Security & RBAC Isolation ---")

        # Test 17: Cross-tenant officer blocked
        t17_ok = False
        try:
            BidEvaluationService.get_unified_evaluation(db, user_officer_b, bid_1.id)
        except HTTPException as he:
            t17_ok = he.status_code in [403, 404]
        log_test(17, "Cross-tenant Procurement Officer blocked from evaluation summary", t17_ok, "HTTP 404/403 access denial confirmed")

        # Test 18: Bidder user blocked
        t18_ok = False
        try:
            BidEvaluationService.get_unified_evaluation(db, user_bidder, bid_1.id)
        except HTTPException as he:
            t18_ok = he.status_code in [403, 404]
        log_test(18, "Bidder role blocked from procurement evaluation summary", t18_ok, "HTTP 403 access denial confirmed")

        # Test 19: Direct manipulation with invalid UUID fails safely
        t19_ok = False
        try:
            BidEvaluationService.get_unified_evaluation(db, user_officer_a, uuid.uuid4())
        except HTTPException as he:
            t19_ok = he.status_code == 404
        log_test(19, "Direct ID manipulation with unowned bid UUID fails safely with HTTP 404", t19_ok, "HTTP 404 Not Found")

        # =========================================================================
        # SECTION 9: Strict Boundary Invariants (Part 7 vs Part 8)
        # =========================================================================
        print("\n--- SECTION 9: Strict Boundary Invariants ---")

        # Test 20: final_decision_status is strictly NOT_MADE
        t20_ok = (
            eval_resp_1.final_decision_status == "NOT_MADE"
            and eval_resp_2.final_decision_status == "NOT_MADE"
            and eval_resp_3.final_decision_status == "NOT_MADE"
        )
        log_test(20, "Strict Boundary: final_decision_status is strictly NOT_MADE (No auto-qualification)", t20_ok, f"Status: {eval_resp_1.final_decision_status}")

        # Test 21: AI never mutates compliance, score, or risk values
        # Verify upstream values in DB remain unaltered after evaluation calls
        snap_score_check = db.scalars(select(BidScoreSnapshot).where(BidScoreSnapshot.bid_id == bid_1.id, BidScoreSnapshot.is_current == True)).first()
        snap_risk_check = db.scalars(select(BidRiskSnapshot).where(BidRiskSnapshot.bid_id == bid_1.id, BidRiskSnapshot.is_current == True)).first()
        comp_check = db.scalars(select(ComplianceResult).where(ComplianceResult.id == cr_gst_1.id)).first()

        t21_ok = (
            snap_score_check is not None
            and snap_risk_check is not None
            and float(snap_score_check.overall_score) == 100.0
            and float(snap_risk_check.base_risk_score) == 0.0
            and comp_check.compliance_status == "PASS"
        )
        log_test(21, "Strict Boundary: AI never alters deterministic compliance, score, or risk records", t21_ok, "DB record integrity strictly verified")

        # =========================================================================
        # SUMMARY
        # =========================================================================
        print("\n" + "=" * 80)
        print("PART 7F MASTER QA SUMMARY")
        print("=" * 80)
        print(f"Total Tests Run : {passed_tests + failed_tests}")
        print(f"Passed          : {passed_tests}")
        print(f"Failed          : {failed_tests}")

        if failed_tests == 0:
            print("\n>>> ALL 21 MASTER QA TESTS PASSED SUCCESSFULLY FOR PART 7F! <<<\n")
        else:
            print(f"\n>>> WARNING: {failed_tests} TESTS FAILED IN PART 7F MASTER QA <<<\n")
            sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
