"""
Master QA Test Suite for Part 7D: Critical Overrides & Risk Adjustment Logic
Validates deterministic risk adjustments, minimum risk floors, level floors,
active blacklisting/debarment overrides, single vs multi-critical failures,
structural identity mismatches, conservative partial/address matching,
provisional uncertainty handling, snapshot persistence, versioning, idempotency,
multi-tenant RBAC security, and strict Part 7D boundary guards.
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
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.user import User

from app.services.risk.risk_config import RiskConfig, RiskIndicator, RiskLevel
from app.services.risk.risk_models import (
    RiskAssessment,
    RiskContribution,
    RiskFeatures,
    RiskOverride,
)
from app.services.risk.risk_engine import evaluate_base_risk
from app.services.risk.risk_override_config import (
    OverrideSeverity,
    RiskOverrideConfig,
    RiskOverrideType,
)
from app.services.risk.risk_override_engine import RiskOverrideEngine
from app.services.risk_service import (
    calculate_and_save_bid_risk,
    get_bid_risk,
)
from app.services.scoring.scoring_models import RuleScoreInput

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


def create_mock_base_assessment(
    score: Decimal = Decimal("34.00"),
    level: RiskLevel = RiskLevel.MEDIUM,
    provisional: bool = False,
    human_review: bool = False,
) -> RiskAssessment:
    """Helper to generate a base risk assessment fixture for unit testing."""
    features = RiskFeatures(
        overall_compliance_score=Decimal("80.00"),
        total_rules=10,
        applicable_rules=10,
        passed_count=8,
        fail_count=2,
        review_count=0,
        pending_count=0,
        mandatory_rules_count=5,
        mandatory_failure_count=0,
        critical_failure_count=0,
        scoring_complete=not provisional,
        human_review_required=human_review,
    )
    return RiskAssessment(
        bid_id=str(uuid.uuid4()),
        tender_id=str(uuid.uuid4()),
        risk_version=1,
        risk_formula_version="v1",
        base_risk_score=score,
        base_risk_level=level,
        risk_complete=not provisional,
        is_provisional=provisional,
        human_review_required=human_review,
        features=features,
        summary_reasons=["Base risk calculated from compliance metrics."],
    )


def run_unit_tests():
    test_section("1. No Override Triggered (Clean Pass Bid)")
    # Base: 34.00 MEDIUM, no critical failures -> Adjusted: 34.00 MEDIUM
    base_clean = create_mock_base_assessment(score=Decimal("34.00"), level=RiskLevel.MEDIUM)
    clean_rules = [
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="STAT-01",
            requirement_name="Statutory Registration",
            category="STATUTORY",
            weight=Decimal("20.00"),
            is_mandatory=True,
            is_critical=False,
            status=ComplianceStatus.PASS,
        )
    ]
    res_clean = RiskOverrideEngine.evaluate_risk_overrides(base_clean, clean_rules)
    if (
        res_clean.base_risk_score == Decimal("34.00")
        and res_clean.adjusted_risk_score == Decimal("34.00")
        and res_clean.adjusted_risk_level == RiskLevel.MEDIUM
        and res_clean.override_applied is False
        and res_clean.override_count == 0
    ):
        record_pass("Clean bid preserves base risk score without applying overrides", f"score={res_clean.adjusted_risk_score}, level={res_clean.adjusted_risk_level}")
    else:
        record_fail("No override test", f"score={res_clean.adjusted_risk_score}, applied={res_clean.override_applied}")

    test_section("2. Confirmed Blacklisting Critical Floor Override")
    # Base: 30.00 MEDIUM -> Blacklisted critical rule -> Floor: 90.00 CRITICAL
    base_bl = create_mock_base_assessment(score=Decimal("30.00"), level=RiskLevel.MEDIUM)
    bl_rules = [
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="NOT_BLACKLISTED",
            requirement_name="Non-Blacklisting Declaration",
            category="INTEGRITY",
            weight=Decimal("50.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.FAIL,
            critical_failure=True,
        )
    ]
    res_bl = RiskOverrideEngine.evaluate_risk_overrides(base_bl, bl_rules)
    if (
        res_bl.base_risk_score == Decimal("30.00")
        and res_bl.base_risk_level == RiskLevel.MEDIUM
        and res_bl.adjusted_risk_score == Decimal("90.00")
        and res_bl.adjusted_risk_level == RiskLevel.CRITICAL
        and res_bl.override_applied is True
        and res_bl.override_count >= 1
    ):
        record_pass("Active blacklisting applies minimum floor 90.00 and CRITICAL level while preserving base risk 30.00", f"base={res_bl.base_risk_score}, adjusted={res_bl.adjusted_risk_score}")
    else:
        record_fail("Blacklisting override", f"base={res_bl.base_risk_score}, adjusted={res_bl.adjusted_risk_score}, level={res_bl.adjusted_risk_level}")

    test_section("3. Base Risk Already Higher than Floor (Never Downgrade)")
    # Base: 95.00 CRITICAL -> Blacklisted (floor 90.00) -> Adjusted remains 95.00 CRITICAL
    base_high = create_mock_base_assessment(score=Decimal("95.00"), level=RiskLevel.CRITICAL)
    res_high = RiskOverrideEngine.evaluate_risk_overrides(base_high, bl_rules)
    if (
        res_high.base_risk_score == Decimal("95.00")
        and res_high.adjusted_risk_score == Decimal("95.00")
        and res_high.adjusted_risk_level == RiskLevel.CRITICAL
    ):
        record_pass("Higher base risk (95.00) is never reduced by lower override floor (90.00)", f"score={res_high.adjusted_risk_score}")
    else:
        record_fail("Base higher than floor", f"Expected 95.00, got {res_high.adjusted_risk_score}")

    test_section("4. Confirmed Active Debarment Override")
    # Base: 20.00 LOW -> Active Debarment critical rule -> Floor: 90.00 CRITICAL
    base_deb = create_mock_base_assessment(score=Decimal("20.00"), level=RiskLevel.LOW)
    deb_rules = [
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="DEBARMENT_REGISTRY",
            requirement_name="Debarment Registry Verification",
            category="INTEGRITY",
            weight=Decimal("50.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.FAIL,
            critical_failure=True,
        )
    ]
    res_deb = RiskOverrideEngine.evaluate_risk_overrides(base_deb, deb_rules)
    if res_deb.adjusted_risk_score == Decimal("90.00") and res_deb.adjusted_risk_level == RiskLevel.CRITICAL:
        record_pass("Active debarment escalates risk to 90.00 CRITICAL", f"score={res_deb.adjusted_risk_score}")
    else:
        record_fail("Active debarment override", f"score={res_deb.adjusted_risk_score}")

    test_section("5. Expired Debarment (No Active Override)")
    # Debarment requirement is PASS (e.g. historical/expired) -> no override
    deb_expired_rules = [
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="DEBARMENT_REGISTRY",
            requirement_name="Debarment Registry Verification",
            category="INTEGRITY",
            weight=Decimal("50.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.PASS,
            critical_failure=False,
        )
    ]
    res_exp = RiskOverrideEngine.evaluate_risk_overrides(base_clean, deb_expired_rules)
    if res_exp.adjusted_risk_score == Decimal("34.00") and res_exp.override_applied is False:
        record_pass("Expired debarment with PASS status does not trigger active override floor", "adjusted=34.00")
    else:
        record_fail("Expired debarment", f"score={res_exp.adjusted_risk_score}, applied={res_exp.override_applied}")

    test_section("6. Single Critical Requirement Failure Floor (OEM Authorization)")
    # Base: 35.00 MEDIUM -> OEM critical failure -> Floor: 70.00 HIGH
    base_35 = create_mock_base_assessment(score=Decimal("35.00"), level=RiskLevel.MEDIUM)
    crit_oem_rules = [
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="OEM_AUTHORIZATION",
            requirement_name="OEM Authorization Letter",
            category="OEM",
            weight=Decimal("30.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.FAIL,
            critical_failure=True,
        )
    ]
    res_oem = RiskOverrideEngine.evaluate_risk_overrides(base_35, crit_oem_rules)
    if res_oem.adjusted_risk_score == Decimal("70.00") and res_oem.adjusted_risk_level == RiskLevel.HIGH:
        record_pass("Single critical rule failure sets risk floor to 70.00 HIGH", f"score={res_oem.adjusted_risk_score}, level={res_oem.adjusted_risk_level}")
    else:
        record_fail("Single critical failure override", f"score={res_oem.adjusted_risk_score}, level={res_oem.adjusted_risk_level}")

    test_section("7. Multiple Critical Requirement Failures Escalation (>= 2 Critical Fails)")
    # Base: 35.00 MEDIUM -> 2 critical fails (OEM + BIS) -> Floor: 80.00 CRITICAL
    crit_multi_rules = [
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="OEM_AUTHORIZATION",
            requirement_name="OEM Authorization Letter",
            category="OEM",
            weight=Decimal("20.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.FAIL,
            critical_failure=True,
        ),
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="BIS_CERTIFICATION",
            requirement_name="BIS Product Certification",
            category="BIS",
            weight=Decimal("20.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.FAIL,
            critical_failure=True,
        ),
    ]
    res_multi = RiskOverrideEngine.evaluate_risk_overrides(base_35, crit_multi_rules)
    if res_multi.adjusted_risk_score == Decimal("80.00") and res_multi.adjusted_risk_level == RiskLevel.CRITICAL:
        record_pass("Multiple critical failures (2) escalate floor to 80.00 CRITICAL", f"score={res_multi.adjusted_risk_score}, level={res_multi.adjusted_risk_level}")
    else:
        record_fail("Multiple critical failures", f"score={res_multi.adjusted_risk_score}, level={res_multi.adjusted_risk_level}")

    test_section("8. Mandatory Non-Critical Failure (No Critical Floor Applied)")
    # Rule is mandatory=True but is_critical=False -> Should NOT trigger critical floor
    mand_non_crit_rules = [
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="EXPERIENCE_YEARS",
            requirement_name="Minimum Years in Business",
            category="EXPERIENCE",
            weight=Decimal("20.00"),
            is_mandatory=True,
            is_critical=False,
            status=ComplianceStatus.FAIL,
            critical_failure=False,
        )
    ]
    res_mand = RiskOverrideEngine.evaluate_risk_overrides(base_35, mand_non_crit_rules)
    if res_mand.adjusted_risk_score == Decimal("35.00") and res_mand.override_applied is False:
        record_pass("Mandatory non-critical failure does not trigger critical floor override", f"score={res_mand.adjusted_risk_score}")
    else:
        record_fail("Mandatory non-critical test", f"score={res_mand.adjusted_risk_score}, applied={res_mand.override_applied}")

    test_section("9. Severe Structural Identity Mismatch Override")
    # Base: 30.00 -> PAN/GST structural consistency failure -> Floor: 75.00 CRITICAL
    ident_rules = [
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="PAN_GST_CONSISTENCY",
            requirement_name="PAN and GST Structural Consistency",
            category="INTEGRITY",
            weight=Decimal("30.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.FAIL,
            critical_failure=True,
        )
    ]
    res_ident = RiskOverrideEngine.evaluate_risk_overrides(base_clean, ident_rules)
    if res_ident.adjusted_risk_score == Decimal("75.00") and res_ident.adjusted_risk_level == RiskLevel.CRITICAL:
        record_pass("Structural PAN/GST identifier mismatch applies 75.00 CRITICAL floor", f"score={res_ident.adjusted_risk_score}, level={res_ident.adjusted_risk_level}")
    else:
        record_fail("Structural identity mismatch", f"score={res_ident.adjusted_risk_score}, level={res_ident.adjusted_risk_level}")

    test_section("10. Critical Review Uncertainty Escalation")
    # Critical requirement in REVIEW -> Floor 50.00 HIGH, provisional=True, human_review_required=True
    crit_rev_rules = [
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="OEM_AUTHORIZATION",
            requirement_name="OEM Authorization Letter",
            category="OEM",
            weight=Decimal("30.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.REVIEW,
            review_required=True,
            review_reason="Name variations on OEM letter require manual inspection.",
        )
    ]
    res_crit_rev = RiskOverrideEngine.evaluate_risk_overrides(base_clean, crit_rev_rules)
    if (
        res_crit_rev.adjusted_risk_score == Decimal("50.00")
        and res_crit_rev.adjusted_risk_level == RiskLevel.HIGH
        and res_crit_rev.is_provisional is True
        and res_crit_rev.human_review_required is True
    ):
        record_pass("Critical review escalates provisional floor to 50.00 HIGH with human review required", f"score={res_crit_rev.adjusted_risk_score}, prov={res_crit_rev.is_provisional}")
    else:
        record_fail("Critical review escalation", f"score={res_crit_rev.adjusted_risk_score}, prov={res_crit_rev.is_provisional}")

    test_section("11. Critical Pending Check Handling")
    # Critical requirement in PENDING -> provisional=True, risk_complete=False
    crit_pend_rules = [
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="GST_REGISTRATION",
            requirement_name="GST Registration Status",
            category="STATUTORY",
            weight=Decimal("30.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.PENDING,
        )
    ]
    res_crit_pend = RiskOverrideEngine.evaluate_risk_overrides(base_clean, crit_pend_rules)
    if res_crit_pend.is_provisional is True and res_crit_pend.risk_complete is False:
        record_pass("Critical pending check marks assessment provisional and incomplete without false fail", f"prov={res_crit_pend.is_provisional}, complete={res_crit_pend.risk_complete}")
    else:
        record_fail("Critical pending handling", f"prov={res_crit_pend.is_provisional}")

    test_section("12. Multiple Floor Precedence (Highest Floor Wins)")
    # Blacklisting (90) + OEM Fail (70) + Identity Mismatch (75) -> Highest Floor = 90
    multi_floor_rules = [
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="NOT_BLACKLISTED",
            requirement_name="Non-Blacklisting Declaration",
            category="INTEGRITY",
            weight=Decimal("30.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.FAIL,
            critical_failure=True,
        ),
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="OEM_AUTHORIZATION",
            requirement_name="OEM Authorization Letter",
            category="OEM",
            weight=Decimal("20.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.FAIL,
            critical_failure=True,
        ),
        RuleScoreInput(
            requirement_id=uuid.uuid4(),
            requirement_code="PAN_GST_CONSISTENCY",
            requirement_name="PAN/GST Structural Consistency",
            category="INTEGRITY",
            weight=Decimal("20.00"),
            is_mandatory=True,
            is_critical=True,
            status=ComplianceStatus.FAIL,
            critical_failure=True,
        ),
    ]
    res_highest_floor = RiskOverrideEngine.evaluate_risk_overrides(base_clean, multi_floor_rules)
    if res_highest_floor.adjusted_risk_score == Decimal("90.00") and res_highest_floor.adjusted_risk_level == RiskLevel.CRITICAL:
        record_pass("Highest applicable floor (90.00) takes precedence among multiple overrides", f"score={res_highest_floor.adjusted_risk_score}")
    else:
        record_fail("Multiple floor precedence", f"Expected 90.00, got {res_highest_floor.adjusted_risk_score}")

    test_section("13. Determinism & Formula Versioning")
    res_repeat1 = RiskOverrideEngine.evaluate_risk_overrides(base_bl, bl_rules)
    res_repeat2 = RiskOverrideEngine.evaluate_risk_overrides(base_bl, bl_rules)
    if (
        res_repeat1.adjusted_risk_score == res_repeat2.adjusted_risk_score
        and res_repeat1.adjusted_risk_level == res_repeat2.adjusted_risk_level
        and res_repeat1.override_formula_version == "v1"
    ):
        record_pass("Deterministic override calculation produces identical scores and version v1", f"version={res_repeat1.override_formula_version}")
    else:
        record_fail("Determinism test", f"score1={res_repeat1.adjusted_risk_score}, score2={res_repeat2.adjusted_risk_score}")

    test_section("14. Override Evidence & Audit Fields")
    first_ovr = res_bl.applied_overrides[0]
    if (
        first_ovr.rule_code == "NOT_BLACKLISTED"
        and first_ovr.override_type == RiskOverrideType.RISK_FLOOR
        and first_ovr.previous_score == Decimal("30.00")
        and first_ovr.new_score == Decimal("90.00")
        and first_ovr.previous_level == "MEDIUM"
        and first_ovr.new_level == "CRITICAL"
        and first_ovr.reason
    ):
        record_pass("Override audit evidence contains rule, trigger, previous/new scores, levels, and explainable reason", f"reason='{first_ovr.reason}'")
    else:
        record_fail("Override audit fields", f"ovr={first_ovr}")


def run_database_integration_tests():
    test_section("15. Database Persistence, Snapshot Versioning & Overrides Storage")
    SessionFactory = get_session_factory()
    db = SessionFactory()

    try:
        ts = int(datetime.now(timezone.utc).timestamp())
        proc_org = Organization(name=f"Buyer Org 7D {ts}", organization_type="BUYER", is_active=True)
        bidder_org = Organization(name=f"Vendor Org 7D {ts}", organization_type="SELLER", is_active=True)
        db.add_all([proc_org, bidder_org])
        db.flush()

        po_role = db.query(Role).filter(Role.name == "PROCUREMENT_OFFICER").first()
        bid_role = db.query(Role).filter(Role.name == "BIDDER").first()

        proc_prof = Profile(
            id=uuid.uuid4(),
            organization_id=proc_org.id,
            role_id=po_role.id if po_role else None,
            full_name="Procurement Officer 7D",
            email=f"officer7d_{ts}@gem.gov.in",
            is_active=True,
        )
        bid_prof = Profile(
            id=uuid.uuid4(),
            organization_id=bidder_org.id,
            role_id=bid_role.id if bid_role else None,
            full_name="Bidder User 7D",
            email=f"vendor7d_{ts}@vendor.com",
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
            tender_number=f"GEM/7D/{ts}",
            title="Procurement Tender for Risk Overrides Evaluation",
            organization_id=proc_org.id,
            created_by_profile_id=proc_prof.id,
            currency="INR",
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)
        db.flush()

        # Add critical requirements
        req_pan = TenderRequirement(
            tender_id=tender.id,
            code="PAN-01",
            name="PAN Registration",
            category="STATUTORY",
            weight=Decimal("30.0000"),
            is_mandatory=True,
            is_critical=False,
            is_active=True,
        )
        req_oem = TenderRequirement(
            tender_id=tender.id,
            code="OEM-01",
            name="OEM Authorization Letter",
            category="OEM",
            weight=Decimal("30.0000"),
            is_mandatory=True,
            is_critical=True,
            is_active=True,
        )
        req_blacklist = TenderRequirement(
            tender_id=tender.id,
            code="NOT_BLACKLISTED",
            name="Non-Blacklisting Declaration",
            category="INTEGRITY",
            weight=Decimal("40.0000"),
            is_mandatory=True,
            is_critical=True,
            is_active=True,
        )
        db.add_all([req_pan, req_oem, req_blacklist])
        db.flush()

        # Add Bid
        bid = Bid(
            tender_id=tender.id,
            bidder_organization_id=bidder_org.id,
            created_by_profile_id=bid_prof.id,
            bid_number=f"BID/7D/{ts}",
            status="SUBMITTED",
            is_active=True,
        )
        db.add(bid)
        db.flush()

        # Add initial compliance results:
        # PAN-01: PASS
        # OEM-01: FAIL (Critical Failure -> triggers 70.00 floor)
        # NOT_BLACKLISTED: PASS
        cr_pan = ComplianceResult(
            bid_id=bid.id,
            tender_id=tender.id,
            tender_requirement_id=req_pan.id,
            compliance_status=ComplianceStatus.PASS,
            weight=Decimal("30.0000"),
            is_mandatory=True,
            is_critical=False,
            evaluation_version=1,
            is_current=True,
        )
        cr_oem = ComplianceResult(
            bid_id=bid.id,
            tender_id=tender.id,
            tender_requirement_id=req_oem.id,
            compliance_status=ComplianceStatus.FAIL,
            weight=Decimal("30.0000"),
            is_mandatory=True,
            is_critical=True,
            critical_failure=True,
            evaluation_version=1,
            is_current=True,
        )
        cr_bl = ComplianceResult(
            bid_id=bid.id,
            tender_id=tender.id,
            tender_requirement_id=req_blacklist.id,
            compliance_status=ComplianceStatus.PASS,
            weight=Decimal("40.0000"),
            is_mandatory=True,
            is_critical=True,
            critical_failure=False,
            evaluation_version=1,
            is_current=True,
        )
        db.add_all([cr_pan, cr_oem, cr_bl])
        db.commit()

        test_section("16. Calculate and Persist Snapshot v1 with Critical Failure Override")
        risk_v1 = calculate_and_save_bid_risk(db, proc_user, bid.id)

        # Base risk:
        # Score = 70% (30 + 40 = 70 earned out of 100) -> Deficit = 30% * 40 = 12.0
        # Failures = 1/3 * 20 = 6.6667
        # Mandatory = 1/3 * 10 = 3.3333
        # Total Base Risk = 22.00 (LOW)
        # Adjusted Risk after OEM Critical Failure Override = 70.00 (HIGH)
        if (
            risk_v1.risk_version == 1
            and risk_v1.base_risk_score == Decimal("22.00")
            and risk_v1.base_risk_level == "LOW"
            and risk_v1.adjusted_risk_score == Decimal("70.00")
            and risk_v1.adjusted_risk_level == "HIGH"
            and risk_v1.override_applied is True
            and risk_v1.override_count == 1
        ):
            record_pass("Snapshot v1 persisted with Base 22.00 LOW and Adjusted 70.00 HIGH", f"base={risk_v1.base_risk_score}, adjusted={risk_v1.adjusted_risk_score}")
        else:
            record_fail("Snapshot v1 calculation", f"base={risk_v1.base_risk_score}, adjusted={risk_v1.adjusted_risk_score}, level={risk_v1.adjusted_risk_level}")

        test_section("17. Idempotent Read Endpoint")
        read_v1 = get_bid_risk(db, proc_user, bid.id)
        if (
            read_v1.risk_version == 1
            and read_v1.adjusted_risk_score == Decimal("70.00")
            and len(read_v1.applied_overrides) == 1
        ):
            record_pass("Idempotent read returns current active snapshot v1 with overrides list", f"version={read_v1.risk_version}")
        else:
            record_fail("Idempotent read", f"version={read_v1.risk_version}")

        test_section("18. Re-evaluation Flow (CLEAR -> BLACKLISTED Escalates Floor to 90.00 CRITICAL)")
        # Blacklisting changes from PASS -> FAIL
        cr_bl.compliance_status = ComplianceStatus.FAIL
        cr_bl.critical_failure = True
        db.commit()

        risk_v2 = calculate_and_save_bid_risk(db, proc_user, bid.id)
        if (
            risk_v2.risk_version == 2
            and risk_v2.adjusted_risk_score == Decimal("90.00")
            and risk_v2.adjusted_risk_level == "CRITICAL"
            and risk_v2.override_applied is True
            and risk_v2.override_count >= 1
        ):
            record_pass("Re-evaluation reflects blacklisting: Snapshot v2 created with Adjusted 90.00 CRITICAL", f"version={risk_v2.risk_version}, adjusted={risk_v2.adjusted_risk_score}")
        else:
            record_fail("Blacklisting re-evaluation", f"adjusted={risk_v2.adjusted_risk_score}, level={risk_v2.adjusted_risk_level}")

        # Check prior snapshot v1 archived
        snap_v1 = db.query(BidRiskSnapshot).filter(BidRiskSnapshot.bid_id == bid.id, BidRiskSnapshot.risk_version == 1).first()
        snap_v2 = db.query(BidRiskSnapshot).filter(BidRiskSnapshot.bid_id == bid.id, BidRiskSnapshot.risk_version == 2).first()
        if snap_v1 and snap_v1.is_current is False and snap_v2 and snap_v2.is_current is True:
            record_pass("Snapshot v1 archived (is_current=False) and v2 is active (is_current=True)", "clean audit versioning")
        else:
            record_fail("Snapshot archiving", f"v1_current={snap_v1.is_current if snap_v1 else None}")

        test_section("19. Re-evaluation Flow (Fix All Failures -> Overrides Cleared)")
        # Both OEM and Blacklisting resolved to PASS
        cr_oem.compliance_status = ComplianceStatus.PASS
        cr_oem.critical_failure = False
        cr_bl.compliance_status = ComplianceStatus.PASS
        cr_bl.critical_failure = False
        db.commit()

        risk_v3 = calculate_and_save_bid_risk(db, proc_user, bid.id)
        if (
            risk_v3.risk_version == 3
            and risk_v3.base_risk_score == Decimal("0.00")
            and risk_v3.adjusted_risk_score == Decimal("0.00")
            and risk_v3.adjusted_risk_level == "LOW"
            and risk_v3.override_applied is False
            and risk_v3.override_count == 0
        ):
            record_pass("Resolving all failures clears overrides: Snapshot v3 created with 0.00 LOW risk", f"version={risk_v3.risk_version}, adjusted={risk_v3.adjusted_risk_score}")
        else:
            record_fail("Override resolution", f"adjusted={risk_v3.adjusted_risk_score}, applied={risk_v3.override_applied}")

        test_section("20. Multi-Tenant RBAC Isolation")
        # Create intruder
        unauth_org = Organization(name=f"Intruder Corp 7D {ts}", organization_type="SELLER", is_active=True)
        db.add(unauth_org)
        db.flush()
        unauth_prof = Profile(
            id=uuid.uuid4(),
            organization_id=unauth_org.id,
            role_id=bid_role.id if bid_role else None,
            full_name="Alien Vendor 7D",
            email=f"alien7d_{ts}@vendor.com",
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
            record_fail("Cross-tenant access", "Should have raised HTTP 404")
        except Exception as err:
            if hasattr(err, "status_code") and err.status_code == 404:
                record_pass("Cross-tenant bidder access to risk overrides blocked with HTTP 404 Not Found", "HTTP 404")
            else:
                record_fail("Cross-tenant error", f"Expected HTTP 404, got {err}")

        test_section("21. Strict Part 7D Architectural Boundary Guard")
        details = risk_v3.calculation_details
        if (
            "ai_recommendation" not in details
            and "llm_summary" not in details
            and "qualification_decision" not in details
            and "officer_award_decision" not in details
        ):
            record_pass("Strict boundary guard enforced: Zero AI recommendations or final qualification decisions in Part 7D", "clean boundary")
        else:
            record_fail("Boundary guard", "Found premature AI recommendation or award decision fields")

    finally:
        db.close()


def main():
    print("=" * 70)
    print("STARTING PART 7D MASTER QA TEST SUITE: CRITICAL OVERRIDES & RISK ADJUSTMENTS")
    print("=" * 70)

    run_unit_tests()
    run_database_integration_tests()

    print("\n" + "=" * 70)
    print("PART 7D MASTER QA SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run : {passed_count + failed_count}")
    print(f"Passed          : {passed_count}")
    print(f"Failed          : {failed_count}")

    if failed_count == 0:
        print("\n>>> ALL PART 7D MASTER OVERRIDES & RISK ADJUSTMENT TESTS PASSED! <<<\n")
    else:
        print(f"\n>>> PART 7D MASTER QA SUITE FAILED WITH {failed_count} ERRORS <<<\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
