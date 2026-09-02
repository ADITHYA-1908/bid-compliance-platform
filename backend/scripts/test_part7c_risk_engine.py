"""
Master QA Test Suite for Part 7C: Deterministic Risk Assessment Engine
Validates mathematical base risk calculation, indicator contributions, threshold boundaries,
clamping, zero division immunity, provisional pending handling, snapshot persistence,
re-evaluation updates, idempotency, RBAC security, and strict Part 7C boundary guards.
"""

import math
import os
import sys
import uuid
from decimal import Decimal
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.db.session import get_session_factory
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.bid import Bid
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.user import User

from app.services.risk.risk_config import RiskConfig, RiskIndicator, RiskLevel
from app.services.risk.risk_models import (
    RiskAssessment,
    RiskContribution,
    RiskFeatures,
)
from app.services.risk.risk_engine import (
    calculate_risk_contributions,
    evaluate_base_risk,
    extract_risk_features,
    generate_summary_reasons,
)
from app.services.risk_service import (
    calculate_and_save_bid_risk,
    get_bid_risk,
)
from app.services.scoring.scoring_config import ScoringConfig
from app.services.scoring.scoring_models import (
    CategoryScore,
    RuleScoreContribution,
    RuleScoreInput,
    ScoringCalculationResult,
    ScoringReadiness,
    ScoringStatus,
)
from app.services.scoring.scoring_engine import evaluate_scoring_foundation

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
    test_section("1. Perfect Bid Test (100% Compliance, Zero Defects)")
    # Compliance Score = 100, Fails = 0, Reviews = 0, Pending = 0, Mandatory Fails = 0, Integrity = 0
    f_perfect = RiskFeatures(
        overall_compliance_score=Decimal("100.00"),
        total_rules=10,
        applicable_rules=10,
        passed_count=10,
        fail_count=0,
        review_count=0,
        pending_count=0,
        not_applicable_count=0,
        mandatory_rules_count=5,
        mandatory_failure_count=0,
        critical_failure_count=0,
        integrity_rules_count=2,
        integrity_fail_count=0,
        integrity_review_count=0,
        cross_document_mismatch_count=0,
        scoring_complete=True,
        human_review_required=False,
    )
    res_perfect = evaluate_base_risk(f_perfect, uuid.uuid4(), uuid.uuid4())
    if (
        res_perfect.base_risk_score == Decimal("0.00")
        and res_perfect.base_risk_level == RiskLevel.LOW
        and res_perfect.risk_complete is True
        and res_perfect.is_provisional is False
    ):
        record_pass("Perfect bid evaluates to 0.00 score and LOW risk", f"score={res_perfect.base_risk_score}, level={res_perfect.base_risk_level}")
    else:
        record_fail("Perfect bid evaluation", f"score={res_perfect.base_risk_score}, level={res_perfect.base_risk_level}")

    test_section("2. Low Compliance Score Impact")
    # Score drops from 100% -> 60% with all else equal
    f_low_score = RiskFeatures(
        overall_compliance_score=Decimal("60.00"),
        total_rules=10,
        applicable_rules=10,
        passed_count=6,
        fail_count=4,
        review_count=0,
        pending_count=0,
        mandatory_rules_count=5,
        mandatory_failure_count=0,
        integrity_rules_count=1,
        integrity_fail_count=0,
        scoring_complete=True,
    )
    res_low_score = evaluate_base_risk(f_low_score, uuid.uuid4(), uuid.uuid4())
    # Deficit = 40% * 40 weight = 16.0 points; Failures = 4/10 * 20 weight = 8.0 points -> Total = 24.00
    if res_low_score.base_risk_score == Decimal("24.00") and res_low_score.base_risk_level == RiskLevel.LOW:
        record_pass("Lower compliance score increases base risk proportionally", f"score={res_low_score.base_risk_score}")
    else:
        record_fail("Low compliance score evaluation", f"Expected 24.00, got {res_low_score.base_risk_score}")

    test_section("3. Failure Rate Contribution")
    # Same compliance score (70%) with different fail rates
    # Case A: 1 fail out of 10 (10% fail rate) -> Deficit = 30% * 40 = 12.0; Failures = 1/10 * 20 = 2.0 -> 14.00
    f_fail_a = RiskFeatures(
        overall_compliance_score=Decimal("70.00"),
        total_rules=10,
        applicable_rules=10,
        passed_count=9,
        fail_count=1,
        mandatory_rules_count=5,
        mandatory_failure_count=0,
        scoring_complete=True,
    )
    # Case B: 3 fails out of 10 (30% fail rate) -> Deficit = 30% * 40 = 12.0; Failures = 3/10 * 20 = 6.0 -> 18.00
    f_fail_b = RiskFeatures(
        overall_compliance_score=Decimal("70.00"),
        total_rules=10,
        applicable_rules=10,
        passed_count=7,
        fail_count=3,
        mandatory_rules_count=5,
        mandatory_failure_count=0,
        scoring_complete=True,
    )
    res_fail_a = evaluate_base_risk(f_fail_a, uuid.uuid4(), uuid.uuid4())
    res_fail_b = evaluate_base_risk(f_fail_b, uuid.uuid4(), uuid.uuid4())
    if res_fail_b.base_risk_score > res_fail_a.base_risk_score:
        record_pass("Higher failure rate with same score yields higher risk", f"A={res_fail_a.base_risk_score}, B={res_fail_b.base_risk_score}")
    else:
        record_fail("Failure rate comparison", f"A={res_fail_a.base_risk_score}, B={res_fail_b.base_risk_score}")

    test_section("4. Review Uncertainty Rate vs Definite Failure")
    # Review uncertainty (weight 15) vs Failures (weight 20)
    f_rev = RiskFeatures(
        overall_compliance_score=Decimal("80.00"),
        total_rules=10,
        applicable_rules=10,
        passed_count=8,
        fail_count=0,
        review_count=2,
        pending_count=0,
        mandatory_rules_count=5,
        mandatory_failure_count=0,
        scoring_complete=True,
        human_review_required=True,
    )
    f_fail_only = RiskFeatures(
        overall_compliance_score=Decimal("80.00"),
        total_rules=10,
        applicable_rules=10,
        passed_count=8,
        fail_count=2,
        review_count=0,
        pending_count=0,
        mandatory_rules_count=5,
        mandatory_failure_count=0,
        scoring_complete=True,
    )
    res_rev = evaluate_base_risk(f_rev, uuid.uuid4(), uuid.uuid4())
    res_fail_only = evaluate_base_risk(f_fail_only, uuid.uuid4(), uuid.uuid4())
    # Review contrib = (20% deficit * 40 = 8.0) + (2/10 review * 15 = 3.0) = 11.00
    # Fail contrib = (20% deficit * 40 = 8.0) + (2/10 fail * 20 = 4.0) = 12.00
    if res_rev.base_risk_score == Decimal("11.00") and res_fail_only.base_risk_score == Decimal("12.00"):
        record_pass("Review uncertainty contributes points without penalizing as heavily as confirmed failure", f"review={res_rev.base_risk_score}, fail={res_fail_only.base_risk_score}")
    else:
        record_fail("Review vs failure contribution", f"rev={res_rev.base_risk_score}, fail={res_fail_only.base_risk_score}")

    test_section("5. Pending Uncertainty & Provisional Risk Marking")
    # Bid with pending rules
    f_pending = RiskFeatures(
        overall_compliance_score=Decimal("70.00"),
        total_rules=10,
        applicable_rules=10,
        passed_count=7,
        fail_count=0,
        review_count=0,
        pending_count=3,
        mandatory_rules_count=5,
        mandatory_failure_count=0,
        scoring_complete=False,
    )
    res_pending = evaluate_base_risk(f_pending, uuid.uuid4(), uuid.uuid4())
    if res_pending.risk_complete is False and res_pending.is_provisional is True:
        record_pass("Pending checks set risk_complete=False and is_provisional=True", f"complete={res_pending.risk_complete}, provisional={res_pending.is_provisional}")
    else:
        record_fail("Pending provisional marking", f"complete={res_pending.risk_complete}, provisional={res_pending.is_provisional}")

    test_section("6. Mandatory Failure Contribution without Hard Override")
    # Bid with 1 mandatory failure out of 5 mandatory rules (weight 10 max)
    # Deficit = 20% * 40 = 8.0; Failures = 1/10 * 20 = 2.0; Mandatory = 1/5 * 10 = 2.0 -> Total = 12.00
    f_mand = RiskFeatures(
        overall_compliance_score=Decimal("80.00"),
        total_rules=10,
        applicable_rules=10,
        passed_count=9,
        fail_count=1,
        review_count=0,
        pending_count=0,
        mandatory_rules_count=5,
        mandatory_failure_count=1,
        critical_failure_count=0,
        scoring_complete=True,
    )
    res_mand = evaluate_base_risk(f_mand, uuid.uuid4(), uuid.uuid4())
    if res_mand.base_risk_score == Decimal("12.00") and res_mand.base_risk_level == RiskLevel.LOW:
        record_pass("Mandatory failure contributes additional weighted risk without premature critical override", f"score={res_mand.base_risk_score}, level={res_mand.base_risk_level}")
    else:
        record_fail("Mandatory failure evaluation", f"score={res_mand.base_risk_score}, level={res_mand.base_risk_level}")

    test_section("7. Critical Failure Metadata Preservation without Premature Override")
    # Critical failure count = 1. Mathematical risk = 12.00 (LOW). In 7C, this must remain LOW.
    f_crit = RiskFeatures(
        overall_compliance_score=Decimal("80.00"),
        total_rules=10,
        applicable_rules=10,
        passed_count=9,
        fail_count=1,
        review_count=0,
        pending_count=0,
        mandatory_rules_count=5,
        mandatory_failure_count=1,
        critical_failure_count=1,
        scoring_complete=True,
    )
    res_crit = evaluate_base_risk(f_crit, uuid.uuid4(), uuid.uuid4())
    if res_crit.base_risk_score == Decimal("12.00") and res_crit.base_risk_level == RiskLevel.LOW:
        record_pass("Critical failure metadata recorded in features/reasons without forcing CRITICAL risk in Part 7C", f"score={res_crit.base_risk_score}, level={res_crit.base_risk_level}")
    else:
        record_fail("Critical failure override guard", f"Got score={res_crit.base_risk_score}, level={res_crit.base_risk_level}")

    test_section("8. Integrity & Cross-Document Mismatch Signal")
    # Integrity concerns (1 mismatch, 1 integrity fail)
    f_integ = RiskFeatures(
        overall_compliance_score=Decimal("70.00"),
        total_rules=10,
        applicable_rules=10,
        passed_count=8,
        fail_count=2,
        review_count=0,
        pending_count=0,
        mandatory_rules_count=5,
        mandatory_failure_count=1,
        integrity_rules_count=2,
        integrity_fail_count=1,
        integrity_review_count=0,
        cross_document_mismatch_count=1,
        scoring_complete=True,
    )
    res_integ = evaluate_base_risk(f_integ, uuid.uuid4(), uuid.uuid4())
    # Deficit = 30% * 40 = 12.0; Failures = 2/10 * 20 = 4.0; Mandatory = 1/5 * 10 = 2.0
    # Integrity = (1 fail + 0.5 mismatch) / 2 = 0.75 norm * 5 = 3.75 -> Total = 12 + 4 + 2 + 3.75 = 21.75
    if res_integ.base_risk_score == Decimal("21.75"):
        record_pass("Integrity findings and cross-document mismatches contribute explainable points", f"score={res_integ.base_risk_score}")
    else:
        record_fail("Integrity contribution", f"Expected 21.75, got {res_integ.base_risk_score}")

    test_section("9. Threshold Boundary Verification")
    # Boundary checks:
    # 24.99 -> LOW, 25.00 -> MEDIUM, 49.99 -> MEDIUM, 50.00 -> HIGH, 74.99 -> HIGH, 75.00 -> CRITICAL, 100.00 -> CRITICAL
    t_2499 = RiskConfig.get_risk_level(Decimal("24.99"))
    t_2500 = RiskConfig.get_risk_level(Decimal("25.00"))
    t_4999 = RiskConfig.get_risk_level(Decimal("49.99"))
    t_5000 = RiskConfig.get_risk_level(Decimal("50.00"))
    t_7499 = RiskConfig.get_risk_level(Decimal("74.99"))
    t_7500 = RiskConfig.get_risk_level(Decimal("75.00"))
    t_1000 = RiskConfig.get_risk_level(Decimal("100.00"))

    if (
        t_2499 == RiskLevel.LOW
        and t_2500 == RiskLevel.MEDIUM
        and t_4999 == RiskLevel.MEDIUM
        and t_5000 == RiskLevel.HIGH
        and t_7499 == RiskLevel.HIGH
        and t_7500 == RiskLevel.CRITICAL
        and t_1000 == RiskLevel.CRITICAL
    ):
        record_pass("All exact half-open threshold boundary classifications verified", "24.99=LOW, 25=MED, 49.99=MED, 50=HIGH, 74.99=HIGH, 75=CRIT, 100=CRIT")
    else:
        record_fail("Threshold boundaries", f"Got: {t_2499}, {t_2500}, {t_4999}, {t_5000}, {t_7499}, {t_7500}, {t_1000}")

    test_section("10. Score Clamping Safety (No Negative Risk, Max 100)")
    c_neg = RiskConfig.clamp_score(Decimal("-25.50"))
    c_over = RiskConfig.clamp_score(Decimal("150.00"))
    c_normal = RiskConfig.clamp_score(Decimal("63.4567"))

    if c_neg == Decimal("0.00") and c_over == Decimal("100.00") and c_normal == Decimal("63.46"):
        record_pass("Score clamping strictly enforces [0.00, 100.00] bounds with rounding", f"neg={c_neg}, over={c_over}, normal={c_normal}")
    else:
        record_fail("Score clamping", f"neg={c_neg}, over={c_over}, normal={c_normal}")

    test_section("11. Zero Denominator & Empty Rules Handling")
    f_empty = RiskFeatures(
        overall_compliance_score=None,
        total_rules=0,
        applicable_rules=0,
        passed_count=0,
        fail_count=0,
        review_count=0,
        pending_count=0,
        not_applicable_count=0,
    )
    res_empty = evaluate_base_risk(f_empty, uuid.uuid4(), uuid.uuid4())
    if res_empty.base_risk_score is None and res_empty.base_risk_level is None and res_empty.risk_complete is False:
        record_pass("Zero rules bid safely returns None score and incomplete state without division by zero", "base_risk_score=None")
    else:
        record_fail("Zero denominator handling", f"Got score={res_empty.base_risk_score}")

    test_section("12. Normalized Rates Across Different Rule Counts")
    # Bid with 5 rules and 1 fail (20% fail rate) vs Bid with 50 rules and 10 fails (20% fail rate)
    f_5 = RiskFeatures(
        overall_compliance_score=Decimal("80.00"),
        total_rules=5,
        applicable_rules=5,
        passed_count=4,
        fail_count=1,
        mandatory_rules_count=5,
        mandatory_failure_count=1,
        scoring_complete=True,
    )
    f_50 = RiskFeatures(
        overall_compliance_score=Decimal("80.00"),
        total_rules=50,
        applicable_rules=50,
        passed_count=40,
        fail_count=10,
        mandatory_rules_count=50,
        mandatory_failure_count=10,
        scoring_complete=True,
    )
    res_5 = evaluate_base_risk(f_5, uuid.uuid4(), uuid.uuid4())
    res_50 = evaluate_base_risk(f_50, uuid.uuid4(), uuid.uuid4())
    if res_5.base_risk_score == res_50.base_risk_score:
        record_pass("Normalized rates produce identical risk for proportional proposals (5 vs 50 rules)", f"score_5={res_5.base_risk_score}, score_50={res_50.base_risk_score}")
    else:
        record_fail("Rate normalization", f"score_5={res_5.base_risk_score}, score_50={res_50.base_risk_score}")

    test_section("13. Determinism & Formula Versioning")
    res_repeat1 = evaluate_base_risk(f_mand, uuid.uuid4(), uuid.uuid4())
    res_repeat2 = evaluate_base_risk(f_mand, uuid.uuid4(), uuid.uuid4())
    if (
        res_repeat1.base_risk_score == res_repeat2.base_risk_score
        and res_repeat1.base_risk_level == res_repeat2.base_risk_level
        and res_repeat1.risk_formula_version == "v1"
    ):
        record_pass("Deterministic calculation produces identical output across executions with formula version v1", f"formula={res_repeat1.risk_formula_version}")
    else:
        record_fail("Determinism test", f"score1={res_repeat1.base_risk_score}, score2={res_repeat2.base_risk_score}")


def run_database_integration_tests():
    test_section("14. Database Persistence, Snapshot Versioning & Re-evaluation Flow")
    SessionFactory = get_session_factory()
    db = SessionFactory()

    try:
        ts = int(datetime.now(timezone.utc).timestamp())
        proc_org = Organization(name=f"Buyer Ministry 7C {ts}", organization_type="BUYER", is_active=True)
        bidder_org = Organization(name=f"Vendor Tech 7C {ts}", organization_type="SELLER", is_active=True)
        db.add_all([proc_org, bidder_org])
        db.flush()

        po_role = db.query(Role).filter(Role.name == "PROCUREMENT_OFFICER").first()
        bid_role = db.query(Role).filter(Role.name == "BIDDER").first()

        proc_prof = Profile(
            id=uuid.uuid4(),
            organization_id=proc_org.id,
            role_id=po_role.id if po_role else None,
            full_name="Officer Part7C",
            email=f"officer7c_{ts}@gov.in",
            is_active=True,
        )
        bid_prof = Profile(
            id=uuid.uuid4(),
            organization_id=bidder_org.id,
            role_id=bid_role.id if bid_role else None,
            full_name="Bidder Part7C",
            email=f"bidder7c_{ts}@vendor.com",
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
            tender_number=f"GEM/7C/{ts}",
            title="Procurement Tender for Risk Assessment Engine",
            organization_id=proc_org.id,
            created_by_profile_id=proc_prof.id,
            currency="INR",
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)
        db.flush()

        # Add requirements across categories
        req_pan = TenderRequirement(
            tender_id=tender.id,
            code="STAT-01",
            name="PAN Registration",
            category="STATUTORY",
            weight=Decimal("20.0000"),
            is_mandatory=True,
            is_active=True,
        )
        req_turnover = TenderRequirement(
            tender_id=tender.id,
            code="FIN-01",
            name="Annual Turnover Certificate",
            category="FINANCIAL",
            weight=Decimal("30.0000"),
            is_mandatory=True,
            is_active=True,
        )
        req_debarment = TenderRequirement(
            tender_id=tender.id,
            code="INTEG-01",
            name="Non-Debarment Undertaking",
            category="INTEGRITY",
            weight=Decimal("50.0000"),
            is_mandatory=True,
            is_critical=True,
            is_active=True,
        )
        db.add_all([req_pan, req_turnover, req_debarment])
        db.flush()

        # Add Bid
        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=bidder_org.id,
            created_by_profile_id=bid_prof.id,
            bid_number=f"BID/7C/{ts}",
            status="SUBMITTED",
            is_active=True,
        )
        db.add(bid)
        db.flush()

        # Add Compliance Results:
        # STAT-01: PASS (wt 20)
        # FIN-01: FAIL (wt 30) -> Mandatory fail
        # INTEG-01: PASS (wt 50)
        # Overall score = 70.00%
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
        cr_integ = ComplianceResult(
            bid_id=bid.id,
            tender_id=tender.id,
            tender_requirement_id=req_debarment.id,
            compliance_status=ComplianceStatus.PASS,
            weight=Decimal("50.0000"),
            is_mandatory=True,
            is_critical=True,
            evaluation_version=1,
            is_current=True,
        )
        db.add_all([cr_pan, cr_fin, cr_integ])
        db.commit()

        test_section("15. Calculate and Persist Snapshot v1")
        risk_resp = calculate_and_save_bid_risk(db, proc_user, bid.id)

        # Expected score:
        # Deficit = 30% * 40 = 12.00
        # Failures = 1/3 * 20 = 6.6667
        # Mandatory = 1/3 * 10 = 3.3333
        # Total = 12.00 + 6.6667 + 3.3333 = 22.00 (quantized) -> Level = LOW (< 25.00)
        if risk_resp.risk_version == 1 and risk_resp.base_risk_score == Decimal("22.00") and risk_resp.base_risk_level == "LOW":
            record_pass("Base risk calculated and persisted as Snapshot v1 (22.00 / LOW)", f"version={risk_resp.risk_version}, score={risk_resp.base_risk_score}, level={risk_resp.base_risk_level}")
        else:
            record_fail("Snapshot v1 calculation", f"score={risk_resp.base_risk_score}, level={risk_resp.base_risk_level}")

        test_section("16. Idempotent Read Endpoint")
        read_risk = get_bid_risk(db, proc_user, bid.id)
        if read_risk.risk_version == 1 and read_risk.base_risk_score == Decimal("22.00"):
            record_pass("Idempotent read returns current active snapshot v1 without creating duplicates", f"version={read_risk.risk_version}")
        else:
            record_fail("Idempotent read", f"Got version {read_risk.risk_version}")

        test_section("17. Re-Evaluation Recalculation & Score Reduction")
        # Change Financial rule from FAIL -> PASS (now 100% compliance, 0 fails -> risk drops to 0.00)
        cr_fin.compliance_status = ComplianceStatus.PASS
        db.commit()

        risk_resp_v2 = calculate_and_save_bid_risk(db, proc_user, bid.id)
        if risk_resp_v2.risk_version == 2 and risk_resp_v2.base_risk_score == Decimal("0.00") and risk_resp_v2.base_risk_level == "LOW":
            record_pass("Recalculation reflects compliance improvement: Snapshot v2 created with 0.00 risk", f"version={risk_resp_v2.risk_version}, score={risk_resp_v2.base_risk_score}")
        else:
            record_fail("Recalculation update", f"Expected v2 with 0.00, got v{risk_resp_v2.risk_version} with {risk_resp_v2.base_risk_score}")

        # Check prior snapshot v1 marked is_current = False
        v1_snap = db.query(BidRiskSnapshot).filter(BidRiskSnapshot.bid_id == bid.id, BidRiskSnapshot.risk_version == 1).first()
        v2_snap = db.query(BidRiskSnapshot).filter(BidRiskSnapshot.bid_id == bid.id, BidRiskSnapshot.risk_version == 2).first()
        if v1_snap and v1_snap.is_current is False and v2_snap and v2_snap.is_current is True:
            record_pass("Snapshot v1 archived (is_current=False) and v2 is active (is_current=True)", "clean audit versioning")
        else:
            record_fail("Snapshot archiving", f"v1_current={v1_snap.is_current if v1_snap else None}")

        test_section("18. Pending Resolution State Transition")
        # Add a new requirement that is PENDING -> risk becomes provisional
        req_iso = TenderRequirement(
            tender_id=tender.id,
            code="TECH-02",
            name="ISO Security Certificate",
            category="TECHNICAL",
            weight=Decimal("20.0000"),
            is_mandatory=False,
            is_active=True,
        )
        db.add(req_iso)
        db.flush()

        cr_iso = ComplianceResult(
            bid_id=bid.id,
            tender_id=tender.id,
            tender_requirement_id=req_iso.id,
            compliance_status=ComplianceStatus.PENDING,
            weight=Decimal("20.0000"),
            is_mandatory=False,
            evaluation_version=1,
            is_current=True,
        )
        db.add(cr_iso)
        db.commit()

        risk_v3 = calculate_and_save_bid_risk(db, proc_user, bid.id)
        if risk_v3.risk_complete is False and risk_v3.is_provisional is True:
            record_pass("Pending requirement transitions risk to provisional (risk_complete=False, is_provisional=True)", "provisional=True")
        else:
            record_fail("Pending transition", f"complete={risk_v3.risk_complete}, provisional={risk_v3.is_provisional}")

        # Resolve PENDING -> PASS
        cr_iso.compliance_status = ComplianceStatus.PASS
        db.commit()

        risk_v4 = calculate_and_save_bid_risk(db, proc_user, bid.id)
        if risk_v4.risk_complete is True and risk_v4.is_provisional is False:
            record_pass("Resolving pending checks restores complete risk assessment (risk_complete=True, is_provisional=False)", "risk_complete=True")
        else:
            record_fail("Pending resolution", f"complete={risk_v4.risk_complete}, provisional={risk_v4.is_provisional}")

        test_section("19. Multi-Tenant RBAC Security Isolation")
        # Create unauthorized intruder
        unauth_org = Organization(name=f"Intruder Corp 7C {ts}", organization_type="SELLER", is_active=True)
        db.add(unauth_org)
        db.flush()
        unauth_prof = Profile(
            id=uuid.uuid4(),
            organization_id=unauth_org.id,
            role_id=bid_role.id if bid_role else None,
            full_name="Unauthorized Vendor 7C",
            email=f"intruder7c_{ts}@fake.com",
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
            get_bid_risk(db, unauth_user, bid.id)
            record_fail("Cross-tenant risk access", "Should have raised HTTP 404")
        except Exception as err:
            if hasattr(err, "status_code") and err.status_code == 404:
                record_pass("Cross-tenant bidder access to risk data blocked with HTTP 404 Not Found", "HTTP 404")
            else:
                record_fail("Cross-tenant error", f"Expected HTTP 404, got {err}")

        test_section("20. Strict Part 7C Architectural Boundary Guard")
        details = risk_v4.calculation_details
        if "critical_override" not in details and "ai_recommendation" not in details and "award_decision" not in details:
            record_pass("Strict boundary guard enforced: Zero critical overrides, AI recommendations, or award decisions in Part 7C", "clean boundary")
        else:
            record_fail("Boundary guard", "Found premature override or recommendation fields")

    finally:
        db.close()


def main():
    print("=" * 70)
    print("STARTING PART 7C MASTER QA TEST SUITE: DETERMINISTIC RISK ASSESSMENT ENGINE")
    print("=" * 70)

    run_unit_tests()
    run_database_integration_tests()

    print("\n" + "=" * 70)
    print("PART 7C MASTER QA SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run : {passed_count + failed_count}")
    print(f"Passed          : {passed_count}")
    print(f"Failed          : {failed_count}")

    if failed_count == 0:
        print("\n>>> ALL PART 7C MASTER RISK ENGINE TESTS PASSED! <<<\n")
    else:
        print(f"\n>>> PART 7C MASTER QA SUITE FAILED WITH {failed_count} ERRORS <<<\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
