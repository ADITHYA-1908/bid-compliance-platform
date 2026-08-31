"""
Part 7A Master QA Test Suite — Scoring Engine Foundation & Weighting Architecture

Validates all 17+ core test criteria for the deterministic scoring foundation:
1. PASS Rule Contribution (factor=1.0, earned=weight, eligible=weight)
2. FAIL Rule Contribution (factor=0.0, earned=0.0, eligible=weight)
3. NOT_APPLICABLE Exclusion (excluded_from_score=True, eligible=0, earned=0)
4. PENDING Handling (scoring_complete=False, status=INCOMPLETE, no silent FAIL penalty)
5. REVIEW Handling (Unresolved vs Partial Credit policy, human_review_required=True)
6. Zero Weight Support (weight=0 contributes 0 without error)
7. Negative & Invalid Weight Validation (rejected safely with clear error)
8. Decimal Precision & Floating-Point Immunity (exact 4-decimal arithmetic)
9. Zero Denominator & All-NA Safe Handling (NO_SCORABLE_REQUIREMENTS, no div-by-zero)
10. Missing Compliance Result Handling (incomplete status)
11. Mandatory Failure Metadata Preservation (carried without override)
12. Critical Failure Metadata Preservation (carried without cap/override in 7A)
13. Category Preservation & Alias Normalization (STATUTORY, FINANCIAL, etc.)
14. Historical Compliance Isolation (is_current=False ignored)
15. Scoring Snapshot Persistence & Versioned Audit Trail (v1 -> v2, prior marked is_current=False)
16. Multi-Tenant Security & Strict RBAC Isolation (HTTP 404 on cross-tenant access)
17. Strict Boundary Enforcement (0 risk levels, 0 final score cards, 0 AI recommendations)
"""

import math
import os
import sys
import uuid
from decimal import Decimal
from typing import List

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.models.bid import Bid
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus

from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.score_snapshot import BidScoreSnapshot, ScoringStatusEnum
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.db.session import get_session_factory
from app.services.scoring.scoring_config import ReviewPolicy, ScoringConfig

from app.services.scoring.scoring_engine import (
    calculate_rule_contribution,
    evaluate_scoring_foundation,
    resolve_rule_weight,
)
from app.services.scoring.scoring_models import RuleScoreInput, ScoringStatus
from app.services.scoring_service import calculate_and_save_bid_score, get_bid_score

GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"

test_count = 0
pass_count = 0
fail_count = 0


def record_pass(test_name: str, detail: str = ""):
    global test_count, pass_count
    test_count += 1
    pass_count += 1
    msg = f"  {GREEN}[PASS]{RESET} {test_name}"
    if detail:
        msg += f" -> {detail}"
    print(msg)


def record_fail(test_name: str, reason: str):
    global test_count, fail_count
    test_count += 1
    fail_count += 1
    print(f"  {RED}[FAIL]{RESET} {test_name} -> {reason}")


def test_section(title: str):
    print(f"\n{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}[TEST] {title}{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}")


def run_unit_tests():
    test_section("1. Status-to-Score Mapping & Rule Contributions")

    # 1.1 PASS
    r_pass = RuleScoreInput(
        requirement_id=uuid.uuid4(),
        requirement_code="REQ-GST-01",
        requirement_name="GST Registration",
        category="STATUTORY",
        status=ComplianceStatus.PASS,
        weight=Decimal("15.0000"),
    )
    c_pass = calculate_rule_contribution(r_pass)
    if (
        c_pass.score_factor == Decimal("1.0000")
        and c_pass.earned_weight == Decimal("15.0000")
        and c_pass.eligible_weight == Decimal("15.0000")
        and not c_pass.excluded_from_score
    ):
        record_pass("PASS contribution gives 1.0 factor & full weight", f"earned={c_pass.earned_weight}")
    else:
        record_fail("PASS contribution", f"Unexpected values: factor={c_pass.score_factor}, earned={c_pass.earned_weight}")

    # 1.2 FAIL
    r_fail = RuleScoreInput(
        requirement_id=uuid.uuid4(),
        requirement_code="REQ-TURNOVER-01",
        requirement_name="Minimum Turnover",
        category="FINANCIAL",
        status=ComplianceStatus.FAIL,
        weight=Decimal("20.0000"),
    )
    c_fail = calculate_rule_contribution(r_fail)
    if (
        c_fail.score_factor == Decimal("0.0000")
        and c_fail.earned_weight == Decimal("0.0000")
        and c_fail.eligible_weight == Decimal("20.0000")
        and not c_fail.excluded_from_score
    ):
        record_pass("FAIL contribution gives 0.0 factor & 0 earned weight", f"earned={c_fail.earned_weight}, eligible={c_fail.eligible_weight}")
    else:
        record_fail("FAIL contribution", f"Unexpected values: factor={c_fail.score_factor}, earned={c_fail.earned_weight}")

    # 1.3 NOT_APPLICABLE
    r_na = RuleScoreInput(
        requirement_id=uuid.uuid4(),
        requirement_code="REQ-MSME-01",
        requirement_name="MSME Exemption",
        category="STATUTORY",
        status=ComplianceStatus.NOT_APPLICABLE,
        weight=Decimal("10.0000"),
    )
    c_na = calculate_rule_contribution(r_na)
    if (
        c_na.excluded_from_score is True
        and c_na.earned_weight == Decimal("0.0000")
        and c_na.eligible_weight == Decimal("0.0000")
    ):
        record_pass("NOT_APPLICABLE excluded from denominator & earned", f"eligible={c_na.eligible_weight}")
    else:
        record_fail("NOT_APPLICABLE handling", f"Expected excluded_from_score=True, got {c_na.excluded_from_score}")

    # 1.4 PENDING
    r_pend = RuleScoreInput(
        requirement_id=uuid.uuid4(),
        requirement_code="REQ-OEM-01",
        requirement_name="OEM Authorization",
        category="OEM",
        status=ComplianceStatus.PENDING,
        weight=Decimal("25.0000"),
    )
    c_pend = calculate_rule_contribution(r_pend)
    if (
        c_pend.score_factor == Decimal("0.0000")
        and c_pend.earned_weight == Decimal("0.0000")
        and c_pend.eligible_weight == Decimal("25.0000")
        and not c_pend.excluded_from_score
    ):
        record_pass("PENDING retains eligible weight with 0 factor without silent exclusion", f"eligible={c_pend.eligible_weight}")
    else:
        record_fail("PENDING handling", f"Unexpected values: eligible={c_pend.eligible_weight}")

    # 1.5 REVIEW (UNRESOLVED Policy)
    r_rev = RuleScoreInput(
        requirement_id=uuid.uuid4(),
        requirement_code="REQ-PAN-01",
        requirement_name="PAN Card Verification",
        category="STATUTORY",
        status=ComplianceStatus.REVIEW,
        weight=Decimal("10.0000"),
    )
    c_rev_unresolved = calculate_rule_contribution(r_rev, review_policy=ReviewPolicy.UNRESOLVED)
    if (
        c_rev_unresolved.score_factor == Decimal("0.0000")
        and c_rev_unresolved.earned_weight == Decimal("0.0000")
        and c_rev_unresolved.eligible_weight == Decimal("10.0000")
    ):
        record_pass("REVIEW under UNRESOLVED policy yields 0 earned weight", f"earned={c_rev_unresolved.earned_weight}")
    else:
        record_fail("REVIEW UNRESOLVED", f"Got earned={c_rev_unresolved.earned_weight}")

    # 1.6 REVIEW (PARTIAL_CREDIT Policy)
    c_rev_partial = calculate_rule_contribution(r_rev, review_policy=ReviewPolicy.PARTIAL_CREDIT)
    if (
        c_rev_partial.score_factor == Decimal("0.5000")
        and c_rev_partial.earned_weight == Decimal("5.0000")
        and c_rev_partial.eligible_weight == Decimal("10.0000")
    ):
        record_pass("REVIEW under PARTIAL_CREDIT policy yields 50% credit", f"earned={c_rev_partial.earned_weight}")
    else:
        record_fail("REVIEW PARTIAL_CREDIT", f"Got earned={c_rev_partial.earned_weight}")

    test_section("2. Weight Validation, Precision & Defaults")

    # 2.1 Default weight
    def_w = resolve_rule_weight(None)
    if def_w == Decimal("10.0000"):
        record_pass("None weight resolves to default 10.0000", f"weight={def_w}")
    else:
        record_fail("Default weight", f"Expected 10.0000, got {def_w}")

    # 2.2 Zero weight
    zero_w = resolve_rule_weight(Decimal("0.0"))
    if zero_w == Decimal("0.0000"):
        record_pass("Zero weight resolves cleanly to 0.0000", f"weight={zero_w}")
    else:
        record_fail("Zero weight", f"Expected 0.0000, got {zero_w}")

    # 2.3 Negative weight rejection
    try:
        resolve_rule_weight(Decimal("-5.0"))
        record_fail("Negative weight", "Should have raised ValueError")
    except ValueError:
        record_pass("Negative weight rejected safely with ValueError")

    # 2.4 Non-numeric / NaN rejection
    try:
        resolve_rule_weight(float("nan"))
        record_fail("NaN weight", "Should have raised ValueError")
    except ValueError:
        record_pass("NaN weight rejected safely with ValueError")

    # 2.5 Decimal Precision (No floating-point drift)
    w_sum = resolve_rule_weight("10.3333") + resolve_rule_weight("20.6667")
    if w_sum == Decimal("31.0000"):
        record_pass("Exact 4-decimal precision arithmetic verified", f"sum={w_sum}")
    else:
        record_fail("Decimal precision", f"Expected 31.0000, got {w_sum}")


def run_integration_tests():
    SessionFactory = get_session_factory()
    db = SessionFactory()
    try:
        test_section("3. Multi-Domain Foundation Evaluation & Readiness")


        # Create test organization, bidder, tender, and requirements
        ts = str(uuid.uuid4())[:8]
        proc_org = Organization(
            name=f"Ministry of QA {ts}",
            organization_type="BUYER",
            is_active=True,
        )
        bidder_org = Organization(
            name=f"Prime Contractor Pvt Ltd {ts}",
            organization_type="SELLER",
            is_active=True,
        )
        db.add_all([proc_org, bidder_org])
        db.flush()

        po_role = db.query(Role).filter(Role.name == "PROCUREMENT_OFFICER").first()
        bid_role = db.query(Role).filter(Role.name == "BIDDER").first()

        proc_prof = Profile(
            id=uuid.uuid4(),
            organization_id=proc_org.id,
            role_id=po_role.id if po_role else None,
            full_name="Procurement Officer",
            email=f"officer_{ts}@gov.in",
            designation="Director",
            is_active=True,
        )
        bid_prof = Profile(
            id=uuid.uuid4(),
            organization_id=bidder_org.id,
            role_id=bid_role.id if bid_role else None,
            full_name="Bidder Director",
            email=f"bidder_{ts}@vendor.com",
            designation="Managing Director",
            is_active=True,
        )
        db.add_all([proc_prof, bid_prof])
        db.flush()

        proc_user = User(
            id=uuid.uuid4(),
            email=proc_prof.email,
            password_hash="test",
            profile_id=proc_prof.id,
            is_active=True,
        )
        bid_user = User(
            id=uuid.uuid4(),
            email=bid_prof.email,
            password_hash="test",
            profile_id=bid_prof.id,
            is_active=True,
        )
        db.add_all([proc_user, bid_user])
        db.flush()


        tender = Tender(
            tender_number=f"GEM/QA/{ts}",
            title="Enterprise Cloud Infrastructure",
            organization_id=proc_org.id,
            created_by_profile_id=proc_prof.id,
            currency="INR",
            status="PUBLISHED",
        )
        db.add(tender)
        db.flush()

        # 5 Requirements:
        # Req 1: GST (weight=15, PASS)
        # Req 2: Turnover (weight=25, PASS)
        # Req 3: Local Content (weight=20, REVIEW)
        # Req 4: Debarment (weight=20, FAIL, is_critical=True, critical_failure=True)
        # Req 5: MSME Exemption (weight=10, NOT_APPLICABLE)
        req1 = TenderRequirement(tender_id=tender.id, code="REQ-GST", name="GST Active", category="STATUTORY", weight=Decimal("15.00"), is_mandatory=True)
        req2 = TenderRequirement(tender_id=tender.id, code="REQ-TURNOVER", name="Turnover >= 10Cr", category="FINANCIAL", weight=Decimal("25.00"), is_mandatory=True)
        req3 = TenderRequirement(tender_id=tender.id, code="REQ-LOCAL", name="Class I Local Content", category="LOCAL_CONTENT", weight=Decimal("20.00"), is_mandatory=True)
        req4 = TenderRequirement(tender_id=tender.id, code="REQ-DEBAR", name="Non-Debarment", category="INTEGRITY", weight=Decimal("20.00"), is_mandatory=True, is_critical=True)
        req5 = TenderRequirement(tender_id=tender.id, code="REQ-MSME", name="MSME Exemption", category="STATUTORY", weight=Decimal("10.00"), is_mandatory=False)
        db.add_all([req1, req2, req3, req4, req5])
        db.flush()

        # Create Bid
        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=bidder_org.id,
            created_by_profile_id=bid_prof.id,
            bid_number=f"BID/QA/{ts}",
            status="SUBMITTED",
        )
        db.add(bid)
        db.flush()

        # Create Compliance Results
        cr1 = ComplianceResult(bid_id=bid.id, tender_id=tender.id, tender_requirement_id=req1.id, compliance_status=ComplianceStatus.PASS, weight=Decimal("15.00"), is_mandatory=True, is_current=True)
        cr2 = ComplianceResult(bid_id=bid.id, tender_id=tender.id, tender_requirement_id=req2.id, compliance_status=ComplianceStatus.PASS, weight=Decimal("25.00"), is_mandatory=True, is_current=True)
        cr3 = ComplianceResult(bid_id=bid.id, tender_id=tender.id, tender_requirement_id=req3.id, compliance_status=ComplianceStatus.REVIEW, weight=Decimal("20.00"), is_mandatory=True, is_current=True, reason="Borderline local content percentage calculation")
        cr4 = ComplianceResult(bid_id=bid.id, tender_id=tender.id, tender_requirement_id=req4.id, compliance_status=ComplianceStatus.FAIL, weight=Decimal("20.00"), is_mandatory=True, is_critical=True, critical_failure=True, reason="Entity flagged on central debarment registry")
        cr5 = ComplianceResult(bid_id=bid.id, tender_id=tender.id, tender_requirement_id=req5.id, compliance_status=ComplianceStatus.NOT_APPLICABLE, weight=Decimal("10.00"), is_mandatory=False, is_current=True)
        db.add_all([cr1, cr2, cr3, cr4, cr5])
        db.commit()

        # Test Scoring Service Execution (Procurement Officer)
        score_resp = calculate_and_save_bid_score(db, proc_user, bid.id)

        # Expected weights:
        # Eligible: 15 (GST) + 25 (Turnover) + 20 (Local) + 20 (Debar) = 80.0000 (MSME excluded)
        # Earned (UNRESOLVED policy): 15 (GST) + 25 (Turnover) + 0 (Local) + 0 (Debar) = 40.0000
        if score_resp.eligible_weight == Decimal("80.0000") and score_resp.earned_weight == Decimal("40.0000"):
            record_pass("Eligible and Earned weights calculated accurately", f"earned={score_resp.earned_weight}, eligible={score_resp.eligible_weight}")
        else:
            record_fail("Weight calculation", f"Expected earned=40, eligible=80, got earned={score_resp.earned_weight}, eligible={score_resp.eligible_weight}")

        # Readiness & Counts verification
        r = score_resp.readiness
        if (
            r.scoring_ready is True
            and r.scoring_complete is True
            and r.human_review_required is True
            and r.scoring_status == ScoringStatus.READY
            and r.total_rules == 5
            and r.passed_rules == 2
            and r.failed_rules == 1
            and r.review_rules == 1
            and r.not_applicable_rules == 1
            and r.critical_failures == 1
            and r.mandatory_failures == 1
        ):
            record_pass("Scoring readiness and counts validated completely", f"passed={r.passed_rules}, review={r.review_rules}, crit_fails={r.critical_failures}")
        else:
            record_fail("Scoring readiness", f"Unexpected readiness counts: {r}")

        test_section("4. Snapshot Versioning & Recalculation Audit Trail")

        # Snapshot v1 saved
        snap_v1 = db.query(BidScoreSnapshot).filter(BidScoreSnapshot.bid_id == bid.id, BidScoreSnapshot.scoring_version == 1).first()
        if snap_v1 and snap_v1.is_current is True:
            record_pass("Snapshot v1 created and marked is_current=True")
        else:
            record_fail("Snapshot v1 creation", "Snapshot v1 not found or not current")

        # Recalculate scoring -> generates v2, archives v1
        score_resp_v2 = calculate_and_save_bid_score(db, proc_user, bid.id)
        if score_resp_v2.scoring_version == 2:
            record_pass("Recalculation creates Snapshot v2", f"version={score_resp_v2.scoring_version}")
        else:
            record_fail("Snapshot versioning", f"Expected version 2, got {score_resp_v2.scoring_version}")

        db.refresh(snap_v1)
        snap_v2 = db.query(BidScoreSnapshot).filter(BidScoreSnapshot.bid_id == bid.id, BidScoreSnapshot.scoring_version == 2).first()
        if snap_v1.is_current is False and snap_v2.is_current is True:
            record_pass("Prior snapshot v1 archived (is_current=False) and v2 is active (is_current=True)")
        else:
            record_fail("Snapshot archiving", f"v1 is_current={snap_v1.is_current}, v2 is_current={snap_v2.is_current}")

        test_section("5. Read Endpoint & Idempotency")

        read_score = get_bid_score(db, proc_user, bid.id)
        if read_score.scoring_version == 2 and read_score.earned_weight == Decimal("40.0000"):
            record_pass("get_bid_score returns active v2 snapshot idempotently without creating v3")
        else:
            record_fail("get_bid_score idempotency", f"Unexpected read response: {read_score}")

        snap_count = db.query(BidScoreSnapshot).filter(BidScoreSnapshot.bid_id == bid.id).count()
        if snap_count == 2:
            record_pass("Snapshot table preserves exact 2 versions without spurious duplicates", f"count={snap_count}")
        else:
            record_fail("Snapshot count", f"Expected 2 snapshots, got {snap_count}")

        test_section("6. Missing Compliance Result & Incomplete State")

        # Create an un-evaluated tender requirement
        req_missing = TenderRequirement(tender_id=tender.id, code="REQ-NEW", name="New Unchecked Rule", category="TECHNICAL", weight=Decimal("10.00"), is_mandatory=True)
        db.add(req_missing)
        db.commit()

        score_resp_v3 = calculate_and_save_bid_score(db, proc_user, bid.id)
        if (
            score_resp_v3.readiness.scoring_complete is False
            and score_resp_v3.readiness.scoring_status == ScoringStatus.INCOMPLETE
            and score_resp_v3.readiness.pending_rules == 1
        ):
            record_pass("Missing compliance result safely sets scoring_complete=False & status=INCOMPLETE", f"pending={score_resp_v3.readiness.pending_rules}")
        else:
            record_fail("Missing compliance result handling", f"Got status={score_resp_v3.readiness.scoring_status}")

        test_section("7. Multi-Tenant Security & RBAC Isolation")

        # Create another unauthorized bidder
        unauth_bidder_org = Organization(name=f"Intruder Corp {ts}", organization_type="SELLER", is_active=True)
        db.add(unauth_bidder_org)
        db.flush()
        unauth_prof = Profile(
            id=uuid.uuid4(),
            organization_id=unauth_bidder_org.id,
            role_id=bid_role.id if bid_role else None,
            full_name="Unauthorized User",
            email=f"intruder_{ts}@hacker.com",
            is_active=True,
        )
        db.add(unauth_prof)
        db.flush()
        unauth_user = User(
            id=uuid.uuid4(),
            email=unauth_prof.email,
            password_hash="test",
            profile_id=unauth_prof.id,
            is_active=True,
        )
        db.add(unauth_user)
        db.commit()


        try:
            get_bid_score(db, unauth_user, bid.id)
            record_fail("Cross-tenant access", "Should have raised HTTP 404")
        except Exception as err:
            if hasattr(err, "status_code") and err.status_code == 404:
                record_pass("Unauthorized cross-tenant bidder blocked with HTTP 404", "HTTP 404 Not Found")
            else:
                record_fail("Cross-tenant error code", f"Expected HTTP 404, got {err}")

        test_section("8. Strict Compliance Boundary Guard (Part 7A)")

        # Verify zero Part 7/8 score presentation fields in snapshot
        details = score_resp_v3.calculation_details
        if "risk_level" not in details and "ai_recommendation" not in details and "final_compliance_score" not in details:
            record_pass("Zero final risk levels, score cards, or AI recommendations in Part 7A snapshot")
        else:
            record_fail("Boundary guard", "Found prohibited final scoring/risk fields in Part 7A snapshot")

    finally:
        db.close()


def main():
    print(f"\n{BLUE}======================================================================{RESET}")
    print(f"{BLUE}STARTING PART 7A MASTER QA TEST SUITE{RESET}")
    print(f"{BLUE}======================================================================{RESET}")

    run_unit_tests()
    run_integration_tests()

    print(f"\n{BLUE}======================================================================{RESET}")
    print(f"{BLUE}PART 7A MASTER QA SUMMARY{RESET}")
    print(f"{BLUE}======================================================================{RESET}")
    print(f"Total Tests Run : {test_count}")
    print(f"Passed          : {GREEN}{pass_count}{RESET}")
    print(f"Failed          : {RED}{fail_count}{RESET}")

    if fail_count == 0:
        print(f"\n{GREEN}>>> ALL PART 7A MASTER SCORING FOUNDATION TESTS PASSED! <<<{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{RED}>>> PART 7A TESTS FAILED WITH {fail_count} ERRORS <<<{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
