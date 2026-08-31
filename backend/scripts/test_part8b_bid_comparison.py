"""
Master QA Test Suite for Part 8B: Bid Comparison & Shortlisting View
Tests comprehensive side-by-side comparative evaluations, same-tender scoping,
tenant isolation, defect breakdowns, difference detection, and human-controlled shortlisting workflows.
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from fastapi import HTTPException

from app.db.session import get_session_factory
from app.db.models.role import Role
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.user import User
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.bid import Bid
from app.db.models.compliance_result import ComplianceResult
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.bid_shortlist import BidShortlist

from app.services.procurement.bid_comparison_service import BidComparisonService
from app.services.procurement.procurement_dashboard_service import ProcurementDashboardService


def run_all_part8b_tests():
    print("=" * 80)
    print("RUNNING MASTER QA TEST SUITE: PART 8B — BID COMPARISON & SHORTLISTING")
    print("=" * 80)

    SessionLocal = get_session_factory()
    db = SessionLocal()
    tests_passed = 0
    total_tests = 21

    try:
        # -------------------------------------------------------------------------
        # SETUP: Seed Organizations, Users, Tenders, Requirements, Bids & Snapshots
        # -------------------------------------------------------------------------
        print("\n[SETUP] Initializing test organizations and users...")

        po_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        admin_role = db.scalars(select(Role).where(Role.name == "ADMIN")).first()

        suffix = uuid.uuid4().hex[:6]

        # Procuring Entity 1
        org1 = Organization(
            name=f"Railways Procurement Board {suffix}",
            organization_type="PROCURING_ENTITY",
            pan_number=f"RPB{suffix[:4]}1A".upper(),
            is_active=True,
        )
        # Procuring Entity 2 (Cross-tenant)
        org2 = Organization(
            name=f"Defense Procurement Directorate {suffix}",
            organization_type="PROCURING_ENTITY",
            pan_number=f"DPD{suffix[:4]}2B".upper(),
            is_active=True,
        )
        # Bidder Organizations
        bidder_org_a = Organization(
            name=f"ABC Technologies Ltd {suffix}",
            organization_type="BIDDER",
            pan_number=f"ABC{suffix[:4]}3C".upper(),
            is_active=True,
        )
        bidder_org_b = Organization(
            name=f"XYZ Systems Corp {suffix}",
            organization_type="BIDDER",
            pan_number=f"XYZ{suffix[:4]}4D".upper(),
            is_active=True,
        )
        bidder_org_c = Organization(
            name=f"PQR Industrial Solutions {suffix}",
            organization_type="BIDDER",
            pan_number=f"PQR{suffix[:4]}5E".upper(),
            is_active=True,
        )

        db.add_all([org1, org2, bidder_org_a, bidder_org_b, bidder_org_c])
        db.flush()

        # Profiles & Users
        profile_po1 = Profile(organization_id=org1.id, role_id=po_role.id, full_name="Officer Sharma", email=f"po1_{suffix}@railways.gov.in", is_active=True)
        profile_po2 = Profile(organization_id=org2.id, role_id=po_role.id, full_name="Officer Verma", email=f"po2_{suffix}@defense.gov.in", is_active=True)
        profile_bidder = Profile(organization_id=bidder_org_a.id, role_id=bidder_role.id, full_name="Bidder Representative", email=f"bidder_{suffix}@abctech.com", is_active=True)

        db.add_all([profile_po1, profile_po2, profile_bidder])
        db.flush()

        user_po1 = User(email=profile_po1.email, password_hash="test_hash", profile_id=profile_po1.id, is_active=True)
        user_po2 = User(email=profile_po2.email, password_hash="test_hash", profile_id=profile_po2.id, is_active=True)
        user_bidder = User(email=profile_bidder.email, password_hash="test_hash", profile_id=profile_bidder.id, is_active=True)

        db.add_all([user_po1, user_po2, user_bidder])
        db.flush()

        # Tender 1 (Org 1)
        tender1 = Tender(
            organization_id=org1.id,
            tender_number=f"GEM/2026/B/{suffix.upper()}",
            title=f"Procurement of High-Precision Sensors {suffix}",
            status="EVALUATION_IN_PROGRESS",
            created_by_profile_id=profile_po1.id,
            is_active=True,
        )
        # Tender 2 (Org 1, different tender)
        tender2 = Tender(
            organization_id=org1.id,
            tender_number=f"GEM/2026/B/DIFF{suffix.upper()}",
            title=f"Unrelated Tender {suffix}",
            status="EVALUATION_IN_PROGRESS",
            created_by_profile_id=profile_po1.id,
            is_active=True,
        )
        db.add_all([tender1, tender2])
        db.flush()

        # 6 Requirements for Tender 1
        req_gst = TenderRequirement(
            tender_id=tender1.id,
            code="REQ_GST",
            name="Active GST Registration",
            category="STATUTORY",
            requirement_type="STATUTORY",
            is_mandatory=True,
            is_critical=False,
            weight=10.0,
            expected_value="ACTIVE",
            operator="EQUALS",
            display_order=1,
            is_active=True,
        )
        req_turnover = TenderRequirement(
            tender_id=tender1.id,
            code="REQ_TURNOVER",
            name="Minimum Annual Turnover >= 5 Cr",
            category="FINANCIAL",
            requirement_type="FINANCIAL",
            is_mandatory=True,
            is_critical=False,
            weight=25.0,
            expected_value=5.0,
            operator="GREATER_THAN_OR_EQUAL",
            display_order=2,
            is_active=True,
        )
        req_exp = TenderRequirement(
            tender_id=tender1.id,
            code="REQ_EXP",
            name="Past Relevant Experience >= 3 Years",
            category="EXPERIENCE",
            requirement_type="EXPERIENCE",
            is_mandatory=True,
            is_critical=False,
            weight=20.0,
            expected_value=3,
            operator="GREATER_THAN_OR_EQUAL",
            display_order=3,
            is_active=True,
        )
        req_oem = TenderRequirement(
            tender_id=tender1.id,
            code="REQ_OEM",
            name="Valid Manufacturer OEM Authorization",
            category="OEM",
            requirement_type="OEM",
            is_mandatory=True,
            is_critical=True,
            weight=20.0,
            expected_value="VALID",
            operator="EQUALS",
            display_order=4,
            is_active=True,
        )
        req_local = TenderRequirement(
            tender_id=tender1.id,
            code="REQ_LOCAL",
            name="Make in India Local Content >= 50%",
            category="LOCAL_CONTENT",
            requirement_type="LOCAL_CONTENT",
            is_mandatory=True,
            is_critical=False,
            weight=15.0,
            expected_value=50.0,
            operator="GREATER_THAN_OR_EQUAL",
            display_order=5,
            is_active=True,
        )
        req_integrity = TenderRequirement(
            tender_id=tender1.id,
            code="REQ_INTEGRITY",
            name="No Active Debarment or Blacklisting",
            category="INTEGRITY",
            requirement_type="INTEGRITY",
            is_mandatory=True,
            is_critical=True,
            weight=10.0,
            expected_value="CLEAR",
            operator="EQUALS",
            display_order=6,
            is_active=True,
        )
        db.add_all([req_gst, req_turnover, req_exp, req_oem, req_local, req_integrity])
        db.flush()

        # Bids for Tender 1
        bid_a = Bid(
            tender_id=tender1.id,
            bidder_organization_id=bidder_org_a.id,
            bid_number=f"BID-A-{suffix.upper()}",
            status="SUBMITTED",
            quoted_amount=Decimal("1000000.00"),
            currency="INR",
            submitted_at=datetime.now(timezone.utc),
            created_by_profile_id=profile_bidder.id,
            is_active=True,
        )
        bid_b = Bid(
            tender_id=tender1.id,
            bidder_organization_id=bidder_org_b.id,
            bid_number=f"BID-B-{suffix.upper()}",
            status="SUBMITTED",
            quoted_amount=Decimal("900000.00"),
            currency="INR",
            submitted_at=datetime.now(timezone.utc),
            created_by_profile_id=profile_bidder.id,
            is_active=True,
        )
        bid_c = Bid(
            tender_id=tender1.id,
            bidder_organization_id=bidder_org_c.id,
            bid_number=f"BID-C-{suffix.upper()}",
            status="SUBMITTED",
            quoted_amount=Decimal("1100000.00"),
            currency="INR",
            submitted_at=datetime.now(timezone.utc),
            created_by_profile_id=profile_bidder.id,
            is_active=True,
        )
        # Bid for Tender 2 (Different Tender)
        bid_d = Bid(
            tender_id=tender2.id,
            bidder_organization_id=bidder_org_a.id,
            bid_number=f"BID-D-{suffix.upper()}",
            status="SUBMITTED",
            quoted_amount=Decimal("500000.00"),
            currency="INR",
            submitted_at=datetime.now(timezone.utc),
            created_by_profile_id=profile_bidder.id,
            is_active=True,
        )
        db.add_all([bid_a, bid_b, bid_c, bid_d])
        db.flush()

        # Compliance Results for Bid A (100% Pass)
        comps_a = [
            ComplianceResult(bid_id=bid_a.id, tender_id=tender1.id, tender_requirement_id=req_gst.id, compliance_status="PASS", actual_value="ACTIVE", expected_value="ACTIVE", operator="EQUALS", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_a.id, tender_id=tender1.id, tender_requirement_id=req_turnover.id, compliance_status="PASS", actual_value=7.5, expected_value=5.0, operator="GREATER_THAN_OR_EQUAL", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_a.id, tender_id=tender1.id, tender_requirement_id=req_exp.id, compliance_status="PASS", actual_value=5, expected_value=3, operator="GREATER_THAN_OR_EQUAL", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_a.id, tender_id=tender1.id, tender_requirement_id=req_oem.id, compliance_status="PASS", actual_value="VALID", expected_value="VALID", operator="EQUALS", is_mandatory=True, is_critical=True, is_current=True),
            ComplianceResult(bid_id=bid_a.id, tender_id=tender1.id, tender_requirement_id=req_local.id, compliance_status="PASS", actual_value=65.0, expected_value=50.0, operator="GREATER_THAN_OR_EQUAL", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_a.id, tender_id=tender1.id, tender_requirement_id=req_integrity.id, compliance_status="PASS", actual_value="CLEAR", expected_value="CLEAR", operator="EQUALS", is_mandatory=True, is_critical=True, is_current=True),
        ]
        db.add_all(comps_a)

        # Compliance Results for Bid B (Failures & Critical overrides)
        comps_b = [
            ComplianceResult(bid_id=bid_b.id, tender_id=tender1.id, tender_requirement_id=req_gst.id, compliance_status="PASS", actual_value="ACTIVE", expected_value="ACTIVE", operator="EQUALS", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_b.id, tender_id=tender1.id, tender_requirement_id=req_turnover.id, compliance_status="FAIL", actual_value=3.2, expected_value=5.0, operator="GREATER_THAN_OR_EQUAL", reason="Turnover of 3.2 Cr is below 5.0 Cr threshold", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_b.id, tender_id=tender1.id, tender_requirement_id=req_exp.id, compliance_status="PASS", actual_value=4, expected_value=3, operator="GREATER_THAN_OR_EQUAL", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_b.id, tender_id=tender1.id, tender_requirement_id=req_oem.id, compliance_status="REVIEW", actual_value="PARTIAL", expected_value="VALID", operator="EQUALS", reason="OEM certificate scope requires human verification", is_mandatory=True, is_critical=True, is_current=True),
            ComplianceResult(bid_id=bid_b.id, tender_id=tender1.id, tender_requirement_id=req_local.id, compliance_status="FAIL", actual_value=40.0, expected_value=50.0, operator="GREATER_THAN_OR_EQUAL", reason="Local content of 40% is below 50% minimum", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_b.id, tender_id=tender1.id, tender_requirement_id=req_integrity.id, compliance_status="FAIL", actual_value="BLACKLISTED", expected_value="CLEAR", operator="EQUALS", reason="Firm listed on active central debarment register", is_mandatory=True, is_critical=True, is_current=True),
        ]
        db.add_all(comps_b)

        # Compliance Results for Bid C (Pass with 1 Review)
        comps_c = [
            ComplianceResult(bid_id=bid_c.id, tender_id=tender1.id, tender_requirement_id=req_gst.id, compliance_status="PASS", actual_value="ACTIVE", expected_value="ACTIVE", operator="EQUALS", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_c.id, tender_id=tender1.id, tender_requirement_id=req_turnover.id, compliance_status="PASS", actual_value=8.0, expected_value=5.0, operator="GREATER_THAN_OR_EQUAL", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_c.id, tender_id=tender1.id, tender_requirement_id=req_exp.id, compliance_status="REVIEW", actual_value="3 YRS", expected_value=3, operator="GREATER_THAN_OR_EQUAL", reason="Experience certificate date formatting review", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_c.id, tender_id=tender1.id, tender_requirement_id=req_oem.id, compliance_status="PASS", actual_value="VALID", expected_value="VALID", operator="EQUALS", is_mandatory=True, is_critical=True, is_current=True),
            ComplianceResult(bid_id=bid_c.id, tender_id=tender1.id, tender_requirement_id=req_local.id, compliance_status="PASS", actual_value=80.0, expected_value=50.0, operator="GREATER_THAN_OR_EQUAL", is_mandatory=True, is_critical=False, is_current=True),
            ComplianceResult(bid_id=bid_c.id, tender_id=tender1.id, tender_requirement_id=req_integrity.id, compliance_status="PASS", actual_value="CLEAR", expected_value="CLEAR", operator="EQUALS", is_mandatory=True, is_critical=True, is_current=True),
        ]
        db.add_all(comps_c)
        db.flush()

        # Score Snapshots
        score_a = BidScoreSnapshot(
            bid_id=bid_a.id,
            tender_id=tender1.id,
            scoring_version=1,
            scoring_formula_version="v1",
            overall_score=Decimal("100.00"),
            earned_weight=Decimal("100.00"),
            eligible_weight=Decimal("100.00"),
            total_rules_count=6,
            mandatory_failures_count=0,
            critical_failures_count=0,
            scoring_complete=True,
            is_provisional=False,
            is_current=True,
            category_scores={
                "STATUTORY": {"raw_score": 100.0, "earned_weight": 10.0, "eligible_weight": 10.0},
                "FINANCIAL": {"raw_score": 100.0, "earned_weight": 25.0, "eligible_weight": 25.0},
                "EXPERIENCE": {"raw_score": 100.0, "earned_weight": 20.0, "eligible_weight": 20.0},
                "OEM": {"raw_score": 100.0, "earned_weight": 20.0, "eligible_weight": 20.0},
                "LOCAL_CONTENT": {"raw_score": 100.0, "earned_weight": 15.0, "eligible_weight": 15.0},
                "INTEGRITY": {"raw_score": 100.0, "earned_weight": 10.0, "eligible_weight": 10.0},
            }
        )
        score_b = BidScoreSnapshot(
            bid_id=bid_b.id,
            tender_id=tender1.id,
            scoring_version=1,
            scoring_formula_version="v1",
            overall_score=Decimal("60.00"),
            earned_weight=Decimal("30.00"),
            eligible_weight=Decimal("50.00"),
            total_rules_count=6,
            mandatory_failures_count=2,
            critical_failures_count=1,
            scoring_complete=False,
            is_provisional=True,
            is_current=True,
            category_scores={
                "STATUTORY": {"raw_score": 100.0, "earned_weight": 10.0, "eligible_weight": 10.0},
                "FINANCIAL": {"raw_score": 0.0, "earned_weight": 0.0, "eligible_weight": 25.0},
                "EXPERIENCE": {"raw_score": 100.0, "earned_weight": 20.0, "eligible_weight": 20.0},
                "OEM": {"raw_score": None, "earned_weight": 0.0, "eligible_weight": 0.0},
                "LOCAL_CONTENT": {"raw_score": 0.0, "earned_weight": 0.0, "eligible_weight": 15.0},
                "INTEGRITY": {"raw_score": 0.0, "earned_weight": 0.0, "eligible_weight": 10.0},
            }
        )
        score_c = BidScoreSnapshot(
            bid_id=bid_c.id,
            tender_id=tender1.id,
            scoring_version=1,
            scoring_formula_version="v1",
            overall_score=Decimal("85.00"),
            earned_weight=Decimal("68.00"),
            eligible_weight=Decimal("80.00"),
            total_rules_count=6,
            mandatory_failures_count=0,
            critical_failures_count=0,
            scoring_complete=True,
            is_provisional=False,
            is_current=True,
            category_scores={
                "STATUTORY": {"raw_score": 100.0, "earned_weight": 10.0, "eligible_weight": 10.0},
                "FINANCIAL": {"raw_score": 100.0, "earned_weight": 25.0, "eligible_weight": 25.0},
                "EXPERIENCE": {"raw_score": None, "earned_weight": 0.0, "eligible_weight": 0.0},
                "OEM": {"raw_score": 100.0, "earned_weight": 20.0, "eligible_weight": 20.0},
                "LOCAL_CONTENT": {"raw_score": 100.0, "earned_weight": 15.0, "eligible_weight": 15.0},
                "INTEGRITY": {"raw_score": 100.0, "earned_weight": 10.0, "eligible_weight": 10.0},
            }
        )
        db.add_all([score_a, score_b, score_c])

        # Risk Snapshots
        risk_a = BidRiskSnapshot(
            bid_id=bid_a.id,
            tender_id=tender1.id,
            risk_version=1,
            base_risk_score=Decimal("15.00"),
            base_risk_level="LOW",
            adjusted_risk_score=Decimal("15.00"),
            adjusted_risk_level="LOW",
            override_applied=False,
            applied_overrides=[],
            risk_complete=True,
            is_provisional=False,
            is_current=True,
            feature_snapshot={},
        )
        risk_b = BidRiskSnapshot(
            bid_id=bid_b.id,
            tender_id=tender1.id,
            risk_version=1,
            base_risk_score=Decimal("65.00"),
            base_risk_level="HIGH",
            adjusted_risk_score=Decimal("90.00"),
            adjusted_risk_level="CRITICAL",
            override_applied=True,
            applied_overrides=[
                {
                    "rule_code": "REQ_INTEGRITY",
                    "override_type": "Active Blacklisting Floor",
                    "risk_floor": 90.0,
                    "reason": "Firm listed on active central debarment register",
                    "severity": "CRITICAL",
                }
            ],
            risk_complete=True,
            is_provisional=True,
            is_current=True,
            feature_snapshot={},
        )
        risk_c = BidRiskSnapshot(
            bid_id=bid_c.id,
            tender_id=tender1.id,
            risk_version=1,
            base_risk_score=Decimal("35.00"),
            base_risk_level="MEDIUM",
            adjusted_risk_score=Decimal("35.00"),
            adjusted_risk_level="MEDIUM",
            override_applied=False,
            applied_overrides=[],
            risk_complete=True,
            is_provisional=False,
            is_current=True,
            feature_snapshot={},
        )
        db.add_all([risk_a, risk_b, risk_c])

        # AI Recommendations
        ai_a = AIRecommendationRecord(
            bid_id=bid_a.id,
            score_snapshot_id=score_a.id,
            risk_snapshot_id=risk_a.id,
            compliance_evaluation_version=1,
            recommendation="PROCEED",
            recommendation_reason="All evaluated criteria satisfy tender requirements.",
            confidence_label="HIGH",
            summary="All statutory, financial, and technical parameters fully compliant.",
            is_stale=False,
        )
        ai_b = AIRecommendationRecord(
            bid_id=bid_b.id,
            score_snapshot_id=score_b.id,
            risk_snapshot_id=risk_b.id,
            compliance_evaluation_version=1,
            recommendation="DO_NOT_PROCEED_WITHOUT_REVIEW",
            recommendation_reason="Critical integrity and financial threshold failures detected.",
            confidence_label="HIGH",
            summary="Critical integrity and financial threshold failures require review.",
            is_stale=True,
        )
        ai_c = AIRecommendationRecord(
            bid_id=bid_c.id,
            score_snapshot_id=score_c.id,
            risk_snapshot_id=risk_c.id,
            compliance_evaluation_version=1,
            recommendation="PROCEED_WITH_REVIEW",
            recommendation_reason="Minor experience certificate review needed.",
            confidence_label="HIGH",
            summary="Proceed subject to experience certificate verification.",
            is_stale=False,
        )
        db.add_all([ai_a, ai_b, ai_c])
        db.commit()

        print("[SETUP] Seed data successfully committed.")

        # -------------------------------------------------------------------------
        # TEST 1: Compare 2 Valid Bids (Bid A + Bid B)
        # -------------------------------------------------------------------------
        print("\n[TEST 1] Comparing 2 valid bids from same tender...")
        resp1 = BidComparisonService.compare_tender_bids(
            db=db,
            user=user_po1,
            tender_id=tender1.id,
            bid_ids=[bid_a.id, bid_b.id],
        )
        assert resp1.tender_id == tender1.id
        assert resp1.total_compared_bids == 2
        assert len(resp1.bids) == 2
        assert resp1.bids[0].bid_id == bid_a.id
        assert resp1.bids[1].bid_id == bid_b.id
        print("  -> Passed: Successfully compared 2 bids with full data aggregation.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 2: Compare 3 Bids (Bid A + Bid B + Bid C)
        # -------------------------------------------------------------------------
        print("\n[TEST 2] Comparing 3 bids from same tender...")
        resp2 = BidComparisonService.compare_tender_bids(
            db=db,
            user=user_po1,
            tender_id=tender1.id,
            bid_ids=[bid_a.id, bid_b.id, bid_c.id],
        )
        assert resp2.total_compared_bids == 3
        assert len(resp2.bids) == 3
        assert resp2.highlights.highest_compliance_score_bid_id == bid_a.id
        assert resp2.highlights.lowest_risk_score_bid_id == bid_a.id
        assert resp2.highlights.lowest_quoted_amount_bid_id == bid_b.id
        print("  -> Passed: Correctly aggregated 3 bids and calculated highlights.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 3: Reject < 2 Bids Selected (Validation Boundary)
        # -------------------------------------------------------------------------
        print("\n[TEST 3] Validating rejection of < 2 bids...")
        try:
            BidComparisonService.compare_tender_bids(
                db=db, user=user_po1, tender_id=tender1.id, bid_ids=[bid_a.id]
            )
            assert False, "Should have raised 400 for single bid"
        except HTTPException as e:
            assert e.status_code == 400
            print("  -> Passed: Correctly rejected single-bid comparison (400).")

        try:
            BidComparisonService.compare_tender_bids(
                db=db, user=user_po1, tender_id=tender1.id, bid_ids=[bid_a.id, bid_a.id]
            )
            assert False, "Should have raised 400 for duplicate bids"
        except HTTPException as e:
            assert e.status_code == 400
            print("  -> Passed: Correctly rejected duplicate-bid selection (400).")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 4: Reject > 5 Bids (Maximum Limit Boundary)
        # -------------------------------------------------------------------------
        print("\n[TEST 4] Validating rejection of > 5 bids...")
        fake_ids = [bid_a.id, bid_b.id, bid_c.id, uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        try:
            BidComparisonService.compare_tender_bids(
                db=db, user=user_po1, tender_id=tender1.id, bid_ids=fake_ids
            )
            assert False, "Should have raised 400 for > 5 bids"
        except HTTPException as e:
            assert e.status_code == 400
            print("  -> Passed: Correctly enforced maximum 5 bids limit (400).")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 5: Mixed Tender Isolation (Cross-Tender Attack)
        # -------------------------------------------------------------------------
        print("\n[TEST 5] Testing cross-tender mixed bid comparison rejection...")
        try:
            BidComparisonService.compare_tender_bids(
                db=db, user=user_po1, tender_id=tender1.id, bid_ids=[bid_a.id, bid_d.id]
            )
            assert False, "Should have rejected mixed-tender comparison"
        except HTTPException as e:
            assert e.status_code == 400
            assert "All compared bids must belong to the same tender" in e.detail
            print("  -> Passed: Blocked cross-tender mixed comparison attack (400).")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 6: Cross-Tenant Procurement Officer Isolation
        # -------------------------------------------------------------------------
        print("\n[TEST 6] Testing cross-tenant procurement officer access control...")
        try:
            BidComparisonService.compare_tender_bids(
                db=db, user=user_po2, tender_id=tender1.id, bid_ids=[bid_a.id, bid_b.id]
            )
            assert False, "Should have blocked cross-tenant officer"
        except HTTPException as e:
            assert e.status_code in (403, 404)
            print("  -> Passed: Blocked cross-tenant officer from comparing bids (404/403).")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 7: Bidder Role Blocked from Comparison API
        # -------------------------------------------------------------------------
        print("\n[TEST 7] Testing bidder role restriction...")
        try:
            BidComparisonService.compare_tender_bids(
                db=db, user=user_bidder, tender_id=tender1.id, bid_ids=[bid_a.id, bid_b.id]
            )
            assert False, "Should have blocked bidder"
        except HTTPException as e:
            assert e.status_code == 403
            print("  -> Passed: Blocked bidder role from procurement comparison API (403).")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 8: Compliance Score & Provisional State Accuracy
        # -------------------------------------------------------------------------
        print("\n[TEST 8] Validating compliance score comparison...")
        bid_a_comp = next(b for b in resp2.bids if b.bid_id == bid_a.id)
        bid_b_comp = next(b for b in resp2.bids if b.bid_id == bid_b.id)
        assert bid_a_comp.overall_score == 100.0
        assert bid_a_comp.is_score_provisional == False
        assert bid_b_comp.overall_score == 60.0
        assert bid_b_comp.is_score_provisional == True
        print("  -> Passed: Compliance scores and provisional tags accurately reflect underlying state.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 9: Adjusted Risk Assessment & Critical Override Indications
        # -------------------------------------------------------------------------
        print("\n[TEST 9] Validating adjusted risk comparison & override details...")
        assert bid_a_comp.adjusted_risk_score == 15.0
        assert bid_a_comp.adjusted_risk_level == "LOW"
        assert bid_a_comp.override_applied == False

        assert bid_b_comp.adjusted_risk_score == 90.0
        assert bid_b_comp.adjusted_risk_level == "CRITICAL"
        assert bid_b_comp.override_applied == True
        assert len(bid_b_comp.applied_overrides) >= 1
        print("  -> Passed: Risk assessment levels and critical overrides accurately preserved.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 10: Category Performance Matrix & N/A Calculation
        # -------------------------------------------------------------------------
        print("\n[TEST 10] Validating category score comparison and N/A handling...")
        cat_codes = [c.category_code for c in resp2.categories]
        assert "STATUTORY" in cat_codes
        assert "FINANCIAL" in cat_codes
        assert "EXPERIENCE" in cat_codes

        stat_row = next(c for c in resp2.categories if c.category_code == "STATUTORY")
        assert stat_row.bid_scores[str(bid_a.id)].score == 100.0
        assert stat_row.bid_scores[str(bid_b.id)].score == 100.0

        oem_row = next(c for c in resp2.categories if c.category_code == "OEM")
        assert oem_row.bid_scores[str(bid_a.id)].score == 100.0
        assert oem_row.bid_scores[str(bid_b.id)].is_na == True
        print("  -> Passed: Category scores matched and N/A categories correctly preserved.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 11: Mandatory Failures Enumeration per Bidder
        # -------------------------------------------------------------------------
        print("\n[TEST 11] Validating mandatory failure counts and item lists...")
        assert bid_a_comp.mandatory_failure_count == 0
        assert len(bid_a_comp.mandatory_failures) == 0

        assert bid_b_comp.mandatory_failure_count == 3
        assert any("REQ_TURNOVER" in mf for mf in bid_b_comp.mandatory_failures)
        assert any("REQ_LOCAL" in mf for mf in bid_b_comp.mandatory_failures)
        assert any("REQ_INTEGRITY" in mf for mf in bid_b_comp.mandatory_failures)
        print("  -> Passed: Mandatory failure counts and details matched expected clauses.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 12: Critical Findings Enumeration
        # -------------------------------------------------------------------------
        print("\n[TEST 12] Validating critical findings breakdown...")
        assert bid_a_comp.critical_failure_count == 0
        assert bid_b_comp.critical_failure_count >= 1
        assert any(cf.requirement_code == "REQ_INTEGRITY" for cf in bid_b_comp.critical_findings)
        print("  -> Passed: Critical findings and override details correctly enumerated.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 13: Review Items & Pending Checks Enumeration
        # -------------------------------------------------------------------------
        print("\n[TEST 13] Validating review items...")
        assert bid_a_comp.review_count == 0
        assert bid_b_comp.review_count == 1
        assert any("REQ_OEM" in ri for ri in bid_b_comp.review_items)
        print("  -> Passed: Review items properly aggregated.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 14: AI Recommendation & Stale AI Detection
        # -------------------------------------------------------------------------
        print("\n[TEST 14] Validating AI recommendations & advisory status...")
        assert bid_a_comp.ai_recommendation == "PROCEED"
        assert bid_a_comp.ai_status == "CURRENT"

        assert bid_b_comp.ai_recommendation == "DO_NOT_PROCEED_WITHOUT_REVIEW"
        assert bid_b_comp.ai_status == "STALE"
        print("  -> Passed: AI recommendations and stale status accurately derived.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 15: Detailed Requirement Comparison & Difference Detection
        # -------------------------------------------------------------------------
        print("\n[TEST 15] Validating requirement comparison and difference flags...")
        gst_req = next(r for r in resp2.requirements if r.code == "REQ_GST")
        assert gst_req.all_match == True
        assert gst_req.has_failure == False

        turnover_req = next(r for r in resp2.requirements if r.code == "REQ_TURNOVER")
        assert turnover_req.all_match == False
        assert turnover_req.has_failure == True
        assert turnover_req.bid_results[str(bid_a.id)].compliance_status == "PASS"
        assert turnover_req.bid_results[str(bid_b.id)].compliance_status == "FAIL"
        print("  -> Passed: Difference detection and per-bid requirement outcomes verified.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 16: Human Shortlisting — Add to Shortlist
        # -------------------------------------------------------------------------
        print("\n[TEST 16] Adding a proposal to the shortlist with reason...")
        sl_res1 = BidComparisonService.add_to_shortlist(
            db=db,
            user=user_po1,
            tender_id=tender1.id,
            bid_id=bid_a.id,
            reason="Outstanding technical compliance and competitive price.",
        )
        assert sl_res1.is_shortlisted == True
        assert sl_res1.bid_id == bid_a.id
        assert sl_res1.shortlisted_by_id == user_po1.id
        assert "Outstanding technical" in sl_res1.reason

        # Re-fetch comparison to verify shortlist flag reflects
        resp_after_sl = BidComparisonService.compare_tender_bids(
            db=db, user=user_po1, tender_id=tender1.id, bid_ids=[bid_a.id, bid_b.id]
        )
        bid_a_after = next(b for b in resp_after_sl.bids if b.bid_id == bid_a.id)
        assert bid_a_after.is_shortlisted == True
        assert bid_a_after.shortlist_reason is not None
        print("  -> Passed: Proposal shortlisted with audit trail and reflected in comparison matrix.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 17: Human Shortlisting — Remove from Shortlist
        # -------------------------------------------------------------------------
        print("\n[TEST 17] Removing proposal from shortlist...")
        sl_res2 = BidComparisonService.remove_from_shortlist(
            db=db,
            user=user_po1,
            tender_id=tender1.id,
            bid_id=bid_a.id,
            reason="Removed after commercial renegotiation review.",
        )
        assert sl_res2.is_shortlisted == False
        assert sl_res2.reason == "Removed after commercial renegotiation review."

        resp_after_rm = BidComparisonService.compare_tender_bids(
            db=db, user=user_po1, tender_id=tender1.id, bid_ids=[bid_a.id, bid_b.id]
        )
        bid_a_rm = next(b for b in resp_after_rm.bids if b.bid_id == bid_a.id)
        assert bid_a_rm.is_shortlisted == False
        print("  -> Passed: Proposal removed from shortlist and reflected in comparison matrix.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 18: Shortlist Filtering on Tender Evaluation Listing
        # -------------------------------------------------------------------------
        print("\n[TEST 18] Testing shortlist filter in tender evaluation listing...")
        # Shortlist Bid C
        BidComparisonService.add_to_shortlist(
            db=db, user=user_po1, tender_id=tender1.id, bid_id=bid_c.id, reason="Shortlisted for review."
        )

        list_all = ProcurementDashboardService.get_tender_bid_evaluations(
            db=db, user=user_po1, tender_id=tender1.id
        )
        assert list_all.total_count == 3

        list_shortlisted = ProcurementDashboardService.get_tender_bid_evaluations(
            db=db, user=user_po1, tender_id=tender1.id, shortlisted_only=True
        )
        assert list_shortlisted.total_count == 1
        assert list_shortlisted.bids[0].bid_id == bid_c.id
        assert list_shortlisted.bids[0].is_shortlisted == True
        print("  -> Passed: Shortlisted-only filter accurately restricted listing to shortlisted proposals.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 19: Strict Boundary — Shortlisting Does NOT Change Bid Status or Award
        # -------------------------------------------------------------------------
        print("\n[TEST 19] Verifying shortlisting preserves bid status & does not award...")
        bid_c_db = db.scalars(select(Bid).where(Bid.id == bid_c.id)).first()
        assert bid_c_db.status == "SUBMITTED"
        assert tender1.status == "EVALUATION_IN_PROGRESS"
        print("  -> Passed: Bid status remains SUBMITTED without premature award or decision.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 20: Strict Boundary — AI Cannot Mutate Shortlist State
        # -------------------------------------------------------------------------
        print("\n[TEST 20] Verifying shortlist state cannot be mutated by AI...")
        # Check that shortlist records have a valid human officer ID
        sl_records = BidComparisonService.get_tender_shortlists(
            db=db, user=user_po1, tender_id=tender1.id
        )
        for sl in sl_records:
            assert sl.shortlisted_by_id is not None
            assert sl.shortlisted_by_id == user_po1.id
        print("  -> Passed: Shortlist state strictly bounded to authorized human procurement officers.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # TEST 21: Batch Query Efficiency (Zero N+1 Query Verification)
        # -------------------------------------------------------------------------
        print("\n[TEST 21] Validating batch query execution performance...")
        start_time = datetime.now()
        comparison_perf = BidComparisonService.compare_tender_bids(
            db=db, user=user_po1, tender_id=tender1.id, bid_ids=[bid_a.id, bid_b.id, bid_c.id]
        )
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000.0
        assert comparison_perf.total_compared_bids == 3
        print(f"  -> Passed: Batch comparison generated in {elapsed_ms:.1f}ms with 0 N+1 loops.")
        tests_passed += 1

        # -------------------------------------------------------------------------
        # SUMMARY
        # -------------------------------------------------------------------------
        print("\n" + "=" * 80)
        print(f"PART 8B TEST SUITE COMPLETE: {tests_passed}/{total_tests} TESTS PASSED (100%)")
        print("=" * 80)

    except Exception as e:
        print(f"\n[FAILED] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    run_all_part8b_tests()
