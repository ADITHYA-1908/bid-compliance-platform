"""
Master QA Test Suite for Part 7B: Category-wise Compliance Scoring
Validates deterministic category aggregations, weighted scoring formulas, overall compliance score,
zero division immunity, N/A exclusions, provisional states, snapshot persistence, and boundary guards.
"""

import math
import os
import sys
import uuid
from decimal import Decimal
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import get_session_factory
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.bid import Bid
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus
from app.db.models.score_snapshot import BidScoreSnapshot, ScoringStatusEnum
from app.db.models.user import User

from app.services.scoring.scoring_config import ReviewPolicy, ScoringConfig
from app.services.scoring.scoring_models import (
    CategoryScore,
    RuleScoreContribution,
    RuleScoreInput,
    ScoringReadiness,
    ScoringStatus,
)
from app.services.scoring.scoring_engine import (
    aggregate_category_scores,
    calculate_rule_contribution,
    evaluate_scoring_foundation,
    resolve_rule_weight,
)
from app.services.scoring_service import (
    calculate_and_save_bid_score,
    get_bid_score,
)

passed_count = 0
failed_count = 0


def record_pass(test_name: str, detail: str = ""):
    global passed_count
    passed_count += 1
    msg = f"  [PASS] {test_name}"
    if detail:
        msg += f" -> {detail}"
    print(msg)


def record_fail(test_name: str, detail: str = ""):
    global failed_count
    failed_count += 1
    msg = f"  [FAIL] {test_name}"
    if detail:
        msg += f" -> {detail}"
    print(msg)


def test_section(title: str):
    print("\n" + "=" * 70)
    print(f"[TEST] {title}")
    print("=" * 70)


def run_unit_tests():
    test_section("1. Single Category Weighted Scoring & Formula")
    # Category with 2 rules: PASS (wt 10), FAIL (wt 30) -> earned = 10, eligible = 40 -> 25% (NOT 50%)
    c1 = RuleScoreContribution(
        requirement_id=str(uuid.uuid4()),
        requirement_code="FIN-01",
        requirement_name="Annual Turnover",
        category="FINANCIAL",
        status=ComplianceStatus.PASS,
        weight=Decimal("10.0000"),
        score_factor=Decimal("1.0000"),
        earned_weight=Decimal("10.0000"),
        eligible_weight=Decimal("10.0000"),
        is_mandatory=True,
        is_critical=False,
        critical_failure=False,
    )
    c2 = RuleScoreContribution(
        requirement_id=str(uuid.uuid4()),
        requirement_code="FIN-02",
        requirement_name="Net Worth Certificate",
        category="FINANCIAL",
        status=ComplianceStatus.FAIL,
        weight=Decimal("30.0000"),
        score_factor=Decimal("0.0000"),
        earned_weight=Decimal("0.0000"),
        eligible_weight=Decimal("30.0000"),
        is_mandatory=True,
        is_critical=False,
        critical_failure=False,
    )
    cat_scores = aggregate_category_scores([c1, c2])
    fin_cat = cat_scores.get("FINANCIAL")

    if fin_cat and fin_cat.earned_weight == Decimal("10.0000") and fin_cat.eligible_weight == Decimal("40.0000"):
        record_pass("Category weights aggregated correctly", f"earned={fin_cat.earned_weight}, eligible={fin_cat.eligible_weight}")
    else:
        record_fail("Category weights aggregation", f"Got earned={fin_cat.earned_weight if fin_cat else None}")

    if fin_cat and fin_cat.display_score == Decimal("25.00"):
        record_pass("Weighted category score calculated correctly (25.00%, not 50%)", f"score={fin_cat.display_score}%")
    else:
        record_fail("Weighted category score", f"Expected 25.00%, got {fin_cat.display_score if fin_cat else None}")

    test_section("2. NOT_APPLICABLE Exclusion from Category Denominator")
    # Category with PASS (wt 10) and NOT_APPLICABLE (wt 90) -> earned = 10, eligible = 10 -> 100%
    c3 = RuleScoreContribution(
        requirement_id=str(uuid.uuid4()),
        requirement_code="TECH-01",
        requirement_name="Cloud Architecture Specification",
        category="TECHNICAL",
        status=ComplianceStatus.PASS,
        weight=Decimal("10.0000"),
        score_factor=Decimal("1.0000"),
        earned_weight=Decimal("10.0000"),
        eligible_weight=Decimal("10.0000"),
        is_mandatory=True,
        is_critical=False,
        critical_failure=False,
        excluded_from_score=False,
    )
    c4 = RuleScoreContribution(
        requirement_id=str(uuid.uuid4()),
        requirement_code="TECH-02",
        requirement_name="Secondary Telecom Interface",
        category="TECHNICAL",
        status=ComplianceStatus.NOT_APPLICABLE,
        weight=Decimal("90.0000"),
        score_factor=Decimal("0.0000"),
        earned_weight=Decimal("0.0000"),
        eligible_weight=Decimal("0.0000"),
        is_mandatory=False,
        is_critical=False,
        critical_failure=False,
        excluded_from_score=True,
    )
    cat_scores_na = aggregate_category_scores([c3, c4])
    tech_cat = cat_scores_na.get("TECHNICAL")

    if tech_cat and tech_cat.eligible_weight == Decimal("10.0000") and tech_cat.earned_weight == Decimal("10.0000"):
        record_pass("N/A rule excluded from category denominator", f"eligible={tech_cat.eligible_weight}")
    else:
        record_fail("N/A category exclusion", f"Expected eligible=10.0000, got {tech_cat.eligible_weight if tech_cat else None}")

    if tech_cat and tech_cat.display_score == Decimal("100.00"):
        record_pass("Category score calculated on applicable rules only (100.00%)", f"score={tech_cat.display_score}%")
    else:
        record_fail("Category score with N/A", f"Expected 100.00%, got {tech_cat.display_score if tech_cat else None}")

    test_section("3. PENDING Rule Handling & Provisional Marking")
    # Category with PASS (wt 10) and PENDING (wt 10)
    c5 = RuleScoreContribution(
        requirement_id=str(uuid.uuid4()),
        requirement_code="EXP-01",
        requirement_name="Government Project Experience",
        category="EXPERIENCE",
        status=ComplianceStatus.PASS,
        weight=Decimal("10.0000"),
        score_factor=Decimal("1.0000"),
        earned_weight=Decimal("10.0000"),
        eligible_weight=Decimal("10.0000"),
        is_mandatory=True,
        is_critical=False,
        critical_failure=False,
    )
    c6 = RuleScoreContribution(
        requirement_id=str(uuid.uuid4()),
        requirement_code="EXP-02",
        requirement_name="Client Completion Certificate",
        category="EXPERIENCE",
        status=ComplianceStatus.PENDING,
        weight=Decimal("10.0000"),
        score_factor=Decimal("0.0000"),
        earned_weight=Decimal("0.0000"),
        eligible_weight=Decimal("10.0000"),
        is_mandatory=True,
        is_critical=False,
        critical_failure=False,
    )
    cat_scores_pend = aggregate_category_scores([c5, c6])
    exp_cat = cat_scores_pend.get("EXPERIENCE")

    if exp_cat and exp_cat.scoring_complete is False and exp_cat.is_provisional is True and exp_cat.pending_rules == 1:
        record_pass("PENDING rule sets category scoring_complete=False and is_provisional=True", f"pending={exp_cat.pending_rules}")
    else:
        record_fail("PENDING category handling", f"scoring_complete={exp_cat.scoring_complete if exp_cat else None}")

    test_section("4. Zero Denominator Category Handling (Zero Division Immunity)")
    # Category consisting only of N/A rules
    c7 = RuleScoreContribution(
        requirement_id=str(uuid.uuid4()),
        requirement_code="OEM-01",
        requirement_name="OEM Reseller Authorization",
        category="OEM",
        status=ComplianceStatus.NOT_APPLICABLE,
        weight=Decimal("50.0000"),
        score_factor=Decimal("0.0000"),
        earned_weight=Decimal("0.0000"),
        eligible_weight=Decimal("0.0000"),
        is_mandatory=False,
        is_critical=False,
        critical_failure=False,
        excluded_from_score=True,
    )
    cat_scores_zero = aggregate_category_scores([c7])
    oem_cat = cat_scores_zero.get("OEM")

    if oem_cat and oem_cat.eligible_weight == Decimal("0.0000") and oem_cat.raw_score is None and oem_cat.display_score is None:
        record_pass("Zero eligible weight category safely returns score=None without dividing by zero", "score=None")
    else:
        record_fail("Zero eligible weight handling", f"Got score={oem_cat.display_score if oem_cat else None}")

    test_section("5. Overall Weighted Score vs Category Average Trap Test")
    # Category A: 100% on wt 10 (earned 10 / eligible 10)
    # Category B: 50% on wt 90 (earned 45 / eligible 90)
    # Overall earned = 55, eligible = 100 -> overall score = 55% (NOT 75% category average)
    r_a = RuleScoreInput(
        requirement_id=uuid.uuid4(),
        requirement_code="CAT-A",
        requirement_name="Rule in Category A",
        category="STATUTORY",
        status=ComplianceStatus.PASS,
        weight=Decimal("10.0000"),
    )
    r_b1 = RuleScoreInput(
        requirement_id=uuid.uuid4(),
        requirement_code="CAT-B1",
        requirement_name="Rule in Category B1",
        category="FINANCIAL",
        status=ComplianceStatus.PASS,
        weight=Decimal("45.0000"),
    )
    r_b2 = RuleScoreInput(
        requirement_id=uuid.uuid4(),
        requirement_code="CAT-B2",
        requirement_name="Rule in Category B2",
        category="FINANCIAL",
        status=ComplianceStatus.FAIL,
        weight=Decimal("45.0000"),
    )
    res_overall = evaluate_scoring_foundation(
        bid_id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        rule_inputs=[r_a, r_b1, r_b2],
    )
    stat_score = res_overall.category_scores["STATUTORY"].display_score  # 100.00%
    fin_score = res_overall.category_scores["FINANCIAL"].display_score   # 50.00%
    overall = res_overall.overall_score

    if stat_score == Decimal("100.00") and fin_score == Decimal("50.00"):
        record_pass("Individual category percentages verified", f"STATUTORY={stat_score}%, FINANCIAL={fin_score}%")
    else:
        record_fail("Category percentage verification", f"STAT={stat_score}, FIN={fin_score}")

    if overall == Decimal("55.00"):
        record_pass("Overall score correctly weights rules (55.00%, NOT 75.00% blind category average)", f"overall={overall}%")
    else:
        record_fail("Overall score rule weighting", f"Expected 55.00%, got {overall}%")

    test_section("6. Mandatory & Critical Metadata Preservation without Premature Override")
    # A bid with 1 PASS (wt 90) and 1 Debarment FAIL (Critical, wt 10)
    # Mathematical score = 90.00%, critical_failures = 1
    r_pass = RuleScoreInput(
        requirement_id=uuid.uuid4(),
        requirement_code="TECH-99",
        requirement_name="Cloud Tech Spec",
        category="TECHNICAL",
        status=ComplianceStatus.PASS,
        weight=Decimal("90.0000"),
        is_mandatory=True,
    )
    r_crit_fail = RuleScoreInput(
        requirement_id=uuid.uuid4(),
        requirement_code="INTEG-01",
        requirement_name="Non-Debarment Certificate",
        category="INTEGRITY",
        status=ComplianceStatus.FAIL,
        weight=Decimal("10.0000"),
        is_mandatory=True,
        is_critical=True,
        critical_failure=True,
    )
    res_crit = evaluate_scoring_foundation(
        bid_id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        rule_inputs=[r_pass, r_crit_fail],
    )
    if res_crit.overall_score == Decimal("90.00"):
        record_pass("Mathematical score preserved at 90.00% without early critical override", f"score={res_crit.overall_score}%")
    else:
        record_fail("Early override check", f"Expected 90.00%, got {res_crit.overall_score}")

    if res_crit.readiness.critical_failures == 1 and res_crit.readiness.mandatory_failures == 1:
        record_pass("Critical and mandatory failure metadata preserved accurately", "crit_fails=1, mand_fails=1")
    else:
        record_fail("Failure metadata preservation", f"crit={res_crit.readiness.critical_failures}")

    test_section("7. Category Normalization & Canonical Mapping")
    # Test alias mappings: 'STATUTORY_LEGAL' -> 'STATUTORY', 'MAKE_IN_INDIA' -> 'LOCAL_CONTENT'
    norm_stat = ScoringConfig.normalize_category("STATUTORY_LEGAL")
    norm_loc = ScoringConfig.normalize_category("MAKE_IN_INDIA")
    disp_stat = ScoringConfig.get_category_display_name("STATUTORY")
    disp_loc = ScoringConfig.get_category_display_name("LOCAL_CONTENT")

    if norm_stat == "STATUTORY" and norm_loc == "LOCAL_CONTENT":
        record_pass("Category aliases normalized to canonical domain codes", f"{norm_stat}, {norm_loc}")
    else:
        record_fail("Category normalization", f"Got {norm_stat}, {norm_loc}")

    if "Statutory" in disp_stat and "Local Content" in disp_loc:
        record_pass("Human-friendly category display names resolved", f"'{disp_stat}', '{disp_loc}'")
    else:
        record_fail("Display name resolution", f"Got '{disp_stat}', '{disp_loc}'")


def run_database_integration_tests():
    test_section("8. End-to-End Database Snapshot Persistence & API Integration")
    SessionFactory = get_session_factory()
    db = SessionFactory()

    try:
        ts = int(datetime.now(timezone.utc).timestamp())
        proc_org = Organization(name=f"Buyer Ministry {ts}", organization_type="BUYER", is_active=True)
        bidder_org = Organization(name=f"Supplier Enterprise {ts}", organization_type="SELLER", is_active=True)
        db.add_all([proc_org, bidder_org])
        db.flush()

        po_role = db.query(Role).filter(Role.name == "PROCUREMENT_OFFICER").first()
        bid_role = db.query(Role).filter(Role.name == "BIDDER").first()

        proc_prof = Profile(
            id=uuid.uuid4(),
            organization_id=proc_org.id,
            role_id=po_role.id if po_role else None,
            full_name="Officer Part7B",
            email=f"officer7b_{ts}@gov.in",
            is_active=True,
        )
        bid_prof = Profile(
            id=uuid.uuid4(),
            organization_id=bidder_org.id,
            role_id=bid_role.id if bid_role else None,
            full_name="Bidder Part7B",
            email=f"bidder7b_{ts}@vendor.com",
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
            tender_number=f"GEM/7B/{ts}",
            title="Multi-Domain Enterprise IT Procurement",
            organization_id=proc_org.id,
            created_by_profile_id=proc_prof.id,
            currency="INR",
            status="PUBLISHED",
            is_active=True,
        )

        db.add(tender)
        db.flush()

        # Create requirements across multiple categories
        req_pan = TenderRequirement(
            tender_id=tender.id,
            code="STAT-01",
            name="PAN Card Verification",
            category="STATUTORY",
            weight=Decimal("20.0000"),
            is_mandatory=True,
            is_active=True,
        )
        req_turnover = TenderRequirement(
            tender_id=tender.id,
            code="FIN-01",
            name="Minimum Annual Turnover",
            category="FINANCIAL",
            weight=Decimal("30.0000"),
            is_mandatory=True,
            is_active=True,
        )
        req_tech = TenderRequirement(
            tender_id=tender.id,
            code="TECH-01",
            name="ISO 27001 Security Standard",
            category="TECHNICAL",
            weight=Decimal("50.0000"),
            is_mandatory=True,
            is_active=True,
        )
        db.add_all([req_pan, req_turnover, req_tech])
        db.flush()

        # Create Bid
        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=bidder_org.id,
            created_by_profile_id=bid_prof.id,
            bid_number=f"BID/7B/{ts}",
            status="SUBMITTED",
            is_active=True,
        )
        db.add(bid)
        db.flush()

        # Create Compliance Results:
        # STAT-01: PASS (wt 20 -> earned 20)
        # FIN-01: FAIL (wt 30 -> earned 0)
        # TECH-01: PASS (wt 50 -> earned 50)
        # Total earned = 70, eligible = 100 -> Overall score = 70.00%
        cr_pan = ComplianceResult(
            bid_id=bid.id,
            tender_id=tender.id,
            tender_requirement_id=req_pan.id,
            compliance_status=ComplianceStatus.PASS,
            weight=Decimal("20.0000"),
            is_mandatory=True,
            evaluation_version=1,
            is_current=True,
        )
        cr_fin = ComplianceResult(
            bid_id=bid.id,
            tender_id=tender.id,
            tender_requirement_id=req_turnover.id,
            compliance_status=ComplianceStatus.FAIL,
            weight=Decimal("30.0000"),
            is_mandatory=True,
            evaluation_version=1,
            is_current=True,
        )
        cr_tech = ComplianceResult(
            bid_id=bid.id,
            tender_id=tender.id,
            tender_requirement_id=req_tech.id,
            compliance_status=ComplianceStatus.PASS,
            weight=Decimal("50.0000"),
            is_mandatory=True,
            evaluation_version=1,
            is_current=True,
        )
        db.add_all([cr_pan, cr_fin, cr_tech])
        db.commit()


        test_section("9. Snapshot Calculation & Category Persistence")
        score_resp = calculate_and_save_bid_score(db, proc_user, bid.id)

        if score_resp.overall_score == Decimal("70.00") and score_resp.is_provisional is False:
            record_pass("Overall score calculated and returned accurately (70.00%)", f"score={score_resp.overall_score}%")
        else:
            record_fail("Overall score calculation", f"Expected 70.00%, got {score_resp.overall_score}")

        cat_map = score_resp.category_scores
        if "STATUTORY" in cat_map and "FINANCIAL" in cat_map and "TECHNICAL" in cat_map:
            record_pass("All category breakdown domains populated in response", f"categories={list(cat_map.keys())}")
        else:
            record_fail("Category breakdown response", f"Got categories={list(cat_map.keys())}")

        stat_cat = cat_map.get("STATUTORY")
        fin_cat = cat_map.get("FINANCIAL")
        tech_cat = cat_map.get("TECHNICAL")

        if stat_cat and stat_cat.display_score == Decimal("100.00"):
            record_pass("Statutory category score verified (100.00%)", f"earned={stat_cat.earned_weight}/{stat_cat.eligible_weight}")
        else:
            record_fail("Statutory category score", f"Got {stat_cat.display_score if stat_cat else None}")

        if fin_cat and fin_cat.display_score == Decimal("0.00"):
            record_pass("Financial category score verified (0.00%)", f"earned={fin_cat.earned_weight}/{fin_cat.eligible_weight}")
        else:
            record_fail("Financial category score", f"Got {fin_cat.display_score if fin_cat else None}")

        if tech_cat and tech_cat.display_score == Decimal("100.00"):
            record_pass("Technical category score verified (100.00%)", f"earned={tech_cat.earned_weight}/{tech_cat.eligible_weight}")
        else:
            record_fail("Technical category score", f"Got {tech_cat.display_score if tech_cat else None}")

        test_section("10. Database Snapshot Record Verification")
        snap_in_db = (
            db.query(BidScoreSnapshot)
            .filter(BidScoreSnapshot.bid_id == bid.id, BidScoreSnapshot.is_current == True)
            .first()
        )
        if snap_in_db and snap_in_db.overall_score == Decimal("70.00") and "FINANCIAL" in snap_in_db.category_scores:
            record_pass("Database snapshot record preserves overall_score and category_scores JSONB", f"snap_id={snap_in_db.id}")
        else:
            record_fail("Database snapshot record", f"overall={snap_in_db.overall_score if snap_in_db else None}")

        test_section("11. Re-Evaluation Recalculation & Score Updates")
        # Change Financial rule from FAIL -> PASS (now total earned = 100, score = 100.00%)
        cr_fin.compliance_status = ComplianceStatus.PASS
        db.commit()

        score_resp_v2 = calculate_and_save_bid_score(db, proc_user, bid.id)
        if score_resp_v2.scoring_version == 2 and score_resp_v2.overall_score == Decimal("100.00"):
            record_pass("Recalculation creates Snapshot v2 with updated 100.00% score", f"version={score_resp_v2.scoring_version}, score={score_resp_v2.overall_score}%")
        else:
            record_fail("Recalculation update", f"Expected v2 with 100%, got v{score_resp_v2.scoring_version} with {score_resp_v2.overall_score}%")

        # Verify old v1 snapshot marked is_current = False
        v1_snap = db.query(BidScoreSnapshot).filter(BidScoreSnapshot.bid_id == bid.id, BidScoreSnapshot.scoring_version == 1).first()
        if v1_snap and v1_snap.is_current is False:
            record_pass("Prior snapshot v1 successfully archived (is_current=False)", f"v1_current={v1_snap.is_current}")
        else:
            record_fail("Snapshot archiving", "v1 not archived properly")

        test_section("12. Idempotent Read Endpoint")
        read_score = get_bid_score(db, proc_user, bid.id)
        if read_score.scoring_version == 2 and read_score.overall_score == Decimal("100.00"):
            record_pass("Read endpoint idempotently retrieves current active snapshot v2", f"score={read_score.overall_score}%")
        else:
            record_fail("Idempotent read", f"Got version {read_score.scoring_version}")

        test_section("13. Multi-Tenant Security & RBAC Isolation")
        # Create unauthorized bidder
        unauth_org = Organization(name=f"Intruder Corp {ts}", organization_type="SELLER", is_active=True)
        db.add(unauth_org)
        db.flush()
        unauth_prof = Profile(
            id=uuid.uuid4(),
            organization_id=unauth_org.id,
            role_id=bid_role.id if bid_role else None,
            full_name="Unauthorized Vendor",
            email=f"intruder_{ts}@fake.com",
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
                record_pass("Cross-tenant access blocked with HTTP 404 Not Found", "HTTP 404")
            else:
                record_fail("Cross-tenant error", f"Expected HTTP 404, got {err}")

        test_section("14. Strict Compliance Separation Guard (Part 7B)")
        details = score_resp_v2.calculation_details
        if "risk_level" not in details and "ai_recommendation" not in details and "award_decision" not in details:
            record_pass("Strict boundary guard enforced: Zero risk levels, overrides, or AI recommendations in Part 7B", "clean boundary")
        else:
            record_fail("Boundary guard", "Found premature risk or decision fields")

    finally:
        db.close()


def main():
    print("=" * 70)
    print("STARTING PART 7B MASTER QA TEST SUITE: CATEGORY-WISE COMPLIANCE SCORING")
    print("=" * 70)

    run_unit_tests()
    run_database_integration_tests()

    print("\n" + "=" * 70)
    print("PART 7B MASTER QA SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run : {passed_count + failed_count}")
    print(f"Passed          : {passed_count}")
    print(f"Failed          : {failed_count}")

    if failed_count == 0:
        print("\n>>> ALL PART 7B MASTER CATEGORY SCORING TESTS PASSED! <<<\n")
    else:
        print(f"\n>>> PART 7B MASTER QA SUITE FAILED WITH {failed_count} ERRORS <<<\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
