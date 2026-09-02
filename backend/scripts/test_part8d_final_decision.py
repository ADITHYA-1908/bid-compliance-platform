"""
Part 8D: Final Human Decision Workflow — Master QA Test Suite
Validates the complete human-controlled qualification decision lifecycle,
readiness engine, blocking safeguards, atomic versioning with superseding,
snapshot references, staleness invalidation, and multi-tenant security.

Execute with:
  python backend/scripts/test_part8d_final_decision.py
"""

import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

# Add backend directory to sys.path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException
from sqlalchemy import select
from app.db.session import get_session_factory
from app.db.models.user import User
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.organization import Organization
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.bid import Bid
from app.db.models.compliance_result import ComplianceResult
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.human_review import HumanReviewItem, ReviewStatus, ReviewSeverity, ReviewType
from app.db.models.bid_decision import BidDecision, BidDecisionStatus, DisqualificationReasonCategory
from app.schemas.bid_decision import RecordBidDecisionRequest
from app.services.procurement.bid_decision_service import BidDecisionService
from app.services.procurement.human_review_service import HumanReviewService
from app.services.procurement.procurement_dashboard_service import ProcurementDashboardService
from app.services.procurement.bid_comparison_service import BidComparisonService


class Part8DTestSuite:
    def __init__(self):
        self.Session = get_session_factory()
        self.db = self.Session()
        self.test_prefix = f"p8d_test_{uuid.uuid4().hex[:6]}"
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0

    def log(self, message: str):
        print(f"[Part 8D QA] {message}")

    def assert_true(self, condition: bool, test_name: str, details: str = ""):
        self.total_tests += 1
        if condition:
            self.passed_tests += 1
            print(f"  [PASS] Test {self.total_tests:02d}: {test_name}")
        else:
            self.failed_tests += 1
            print(f"  [FAIL] Test {self.total_tests:02d}: {test_name}")
            if details:
                print(f"         Details: {details}")

    def setup_fixtures(self):
        """Creates organizations, users, tender, requirements, bids, and evaluation snapshots."""
        self.log("Setting up multi-tenant test fixtures...")

        # 1. Organizations
        self.org_buyer = Organization(
            id=uuid.uuid4(),
            name=f"Govt Dept {self.test_prefix}",
            organization_type="BUYER",
            is_active=True,
        )
        self.org_buyer_other = Organization(
            id=uuid.uuid4(),
            name=f"Other Dept {self.test_prefix}",
            organization_type="BUYER",
            is_active=True,
        )
        self.org_seller_1 = Organization(
            id=uuid.uuid4(),
            name=f"Alpha Tech {self.test_prefix}",
            organization_type="SELLER",
            is_active=True,
        )
        self.org_seller_2 = Organization(
            id=uuid.uuid4(),
            name=f"Beta Infotech {self.test_prefix}",
            organization_type="SELLER",
            is_active=True,
        )
        self.db.add_all([self.org_buyer, self.org_buyer_other, self.org_seller_1, self.org_seller_2])
        self.db.flush()

        # 2. Roles
        role_po = self.db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
        if not role_po:
            role_po = Role(id=uuid.uuid4(), name="PROCUREMENT_OFFICER", description="Procurement Officer")
            self.db.add(role_po)
            self.db.flush()

        role_bidder = self.db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        if not role_bidder:
            role_bidder = Role(id=uuid.uuid4(), name="BIDDER", description="Bidder")
            self.db.add(role_bidder)
            self.db.flush()

        # 3. Profiles & Users
        self.profile_officer = Profile(
            id=uuid.uuid4(),
            email=f"officer_{self.test_prefix}@buyer.gov.in",
            role_id=role_po.id,
            full_name=f"Officer Ramesh {self.test_prefix}",
            organization_id=self.org_buyer.id,
            is_active=True,
        )
        self.profile_officer_other = Profile(
            id=uuid.uuid4(),
            email=f"officer_other_{self.test_prefix}@other.gov.in",
            role_id=role_po.id,
            full_name=f"Officer Suresh {self.test_prefix}",
            organization_id=self.org_buyer_other.id,
            is_active=True,
        )
        self.profile_bidder = Profile(
            id=uuid.uuid4(),
            email=f"bidder_{self.test_prefix}@alpha.com",
            role_id=role_bidder.id,
            full_name=f"Bidder Vikram {self.test_prefix}",
            organization_id=self.org_seller_1.id,
            is_active=True,
        )
        self.db.add_all([self.profile_officer, self.profile_officer_other, self.profile_bidder])
        self.db.flush()

        self.user_officer = User(
            id=uuid.uuid4(),
            email=self.profile_officer.email,
            password_hash="testhash",
            profile_id=self.profile_officer.id,
            is_active=True,
        )
        self.user_officer_other = User(
            id=uuid.uuid4(),
            email=self.profile_officer_other.email,
            password_hash="testhash",
            profile_id=self.profile_officer_other.id,
            is_active=True,
        )
        self.user_bidder = User(
            id=uuid.uuid4(),
            email=self.profile_bidder.email,
            password_hash="testhash",
            profile_id=self.profile_bidder.id,
            is_active=True,
        )
        self.db.add_all([self.user_officer, self.user_officer_other, self.user_bidder])
        self.db.flush()

        # 4. Tender & Requirements
        self.tender = Tender(
            id=uuid.uuid4(),
            organization_id=self.org_buyer.id,
            created_by_profile_id=self.profile_officer.id,
            tender_number=f"GEM/2026/B/{self.test_prefix.upper()}",
            title=f"National Cloud Computing Procurement {self.test_prefix}",
            description="Testing Part 8D Final Human Decision Workflow",
            status="CLOSED",  # Closed and under evaluation
            currency="INR",
            is_active=True,
        )
        self.db.add(self.tender)
        self.db.flush()

        self.req_turnover = TenderRequirement(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            category="FINANCIAL",
            code="FIN_TURNOVER_01",
            name="Minimum Annual Turnover",
            description="Annual turnover >= 50 Cr",
            is_mandatory=True,
            is_critical=True,
            weight=Decimal("30.0"),
            is_active=True,
        )
        self.req_gst = TenderRequirement(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            category="STATUTORY",
            code="STAT_GST_01",
            name="GST Registration Certificate",
            description="Active GSTIN certificate",
            is_mandatory=True,
            is_critical=False,
            weight=Decimal("20.0"),
            is_active=True,
        )
        self.db.add_all([self.req_turnover, self.req_gst])
        self.db.flush()

        # 5. Bids
        # Bid 1: Clean, passing evaluation (Ready to Qualify)
        self.bid_1 = Bid(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            bidder_organization_id=self.org_seller_1.id,
            created_by_profile_id=self.profile_bidder.id,
            bid_number=f"BID-ALPHA-{self.test_prefix.upper()}",
            status="SUBMITTED",
            submitted_at=datetime.now(timezone.utc),
            quoted_amount=Decimal("45000000.00"),
            is_active=True,
        )
        # Bid 2: Incomplete with open critical review (Blocked from Qualify)
        self.bid_2 = Bid(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            bidder_organization_id=self.org_seller_2.id,
            created_by_profile_id=self.profile_bidder.id,
            bid_number=f"BID-BETA-{self.test_prefix.upper()}",
            status="SUBMITTED",
            submitted_at=datetime.now(timezone.utc),
            quoted_amount=Decimal("42000000.00"),
            is_active=True,
        )
        self.db.add_all([self.bid_1, self.bid_2])
        self.db.flush()

        # 6. Compliance, Score, Risk & AI for Bid 1 (Clean)
        self.comp_1_fin = ComplianceResult(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            bid_id=self.bid_1.id,
            tender_requirement_id=self.req_turnover.id,
            compliance_status="PASS",
            is_mandatory=True,
            is_critical=True,
            weight=Decimal("30.0"),
            is_current=True,
        )
        self.comp_1_gst = ComplianceResult(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            bid_id=self.bid_1.id,
            tender_requirement_id=self.req_gst.id,
            compliance_status="PASS",
            is_mandatory=True,
            is_critical=False,
            weight=Decimal("20.0"),
            is_current=True,
        )
        self.score_1 = BidScoreSnapshot(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            bid_id=self.bid_1.id,
            overall_score=Decimal("95.00"),
            earned_weight=Decimal("50.0000"),
            eligible_weight=Decimal("50.0000"),
            mandatory_failures_count=0,
            critical_failures_count=0,
            is_provisional=False,
            scoring_complete=True,
            is_current=True,
        )
        self.risk_1 = BidRiskSnapshot(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            bid_id=self.bid_1.id,
            base_risk_score=Decimal("10.00"),
            base_risk_level="LOW",
            adjusted_risk_score=Decimal("10.00"),
            adjusted_risk_level="LOW",
            override_applied=False,
            is_provisional=False,
            risk_complete=True,
            is_current=True,
        )
        self.ai_1 = AIRecommendationRecord(
            id=uuid.uuid4(),
            bid_id=self.bid_1.id,
            recommendation="PROCEED",
            recommendation_reason="All statutory and technical criteria verified with high confidence.",
            confidence_label="HIGH",
            summary="All statutory and technical requirements verified with high authenticity.",
            strengths=["Strong turnover", "Active GST"],
            concerns=[],
            is_stale=False,
        )
        self.db.add_all([self.comp_1_fin, self.comp_1_gst, self.score_1, self.risk_1, self.ai_1])

        # 7. Compliance, Score, Risk & Open Critical Review for Bid 2 (Blocked)
        self.comp_2_fin = ComplianceResult(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            bid_id=self.bid_2.id,
            tender_requirement_id=self.req_turnover.id,
            compliance_status="FAIL",
            is_mandatory=True,
            is_critical=True,
            weight=Decimal("30.0"),
            is_current=True,
        )
        self.score_2 = BidScoreSnapshot(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            bid_id=self.bid_2.id,
            overall_score=Decimal("40.00"),
            earned_weight=Decimal("20.0000"),
            eligible_weight=Decimal("50.0000"),
            mandatory_failures_count=1,
            critical_failures_count=1,
            is_provisional=True,
            scoring_complete=False,
            is_current=True,
        )
        self.risk_2 = BidRiskSnapshot(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            bid_id=self.bid_2.id,
            base_risk_score=Decimal("75.00"),
            base_risk_level="HIGH",
            adjusted_risk_score=Decimal("85.00"),
            adjusted_risk_level="CRITICAL",
            override_applied=True,
            is_provisional=True,
            risk_complete=False,
            is_current=True,
        )
        self.review_item_bid2 = HumanReviewItem(
            id=uuid.uuid4(),
            organization_id=self.org_buyer.id,
            tender_id=self.tender.id,
            bid_id=self.bid_2.id,
            review_type=ReviewType.COMPLIANCE_REVIEW,
            severity=ReviewSeverity.CRITICAL,
            status=ReviewStatus.OPEN,
            source_type="COMPLIANCE_RESULT",
            source_id=str(self.comp_2_fin.id),
            title="Turnover Verification Discrepancy",
            reason="Turnover CA certificate below mandatory 50 Cr threshold.",
            system_finding={
                "claimed_value": "40 Cr",
                "extracted_value": "38 Cr",
                "is_mandatory": True,
                "is_critical": True,
            },
        )
        self.db.add_all([self.comp_2_fin, self.score_2, self.risk_2, self.review_item_bid2])
        self.db.commit()
        self.log("Fixtures created successfully.")

    def test_decision_readiness_engine(self):
        """Tests decision readiness evaluation for both clean and blocked bids."""
        self.log("\n--- Executing Test Group 1: Decision Readiness Safeguards ---")

        # 1. Readiness for Bid 1 (Clean & Complete)
        readiness_1 = BidDecisionService.get_decision_readiness(
            self.db, self.user_officer, self.tender.id, self.bid_1.id
        )
        self.assert_true(
            readiness_1.can_qualify is True,
            "Clean bid has can_qualify == True",
        )
        self.assert_true(
            len(readiness_1.blocking_reasons) == 0,
            "Clean bid has 0 blocking reasons",
        )
        self.assert_true(
            readiness_1.can_disqualify is True and readiness_1.can_defer is True,
            "Clean bid can be disqualified or deferred",
        )

        # 2. Readiness for Bid 2 (Blocked by open critical review and incomplete evaluation)
        readiness_2 = BidDecisionService.get_decision_readiness(
            self.db, self.user_officer, self.tender.id, self.bid_2.id
        )
        self.assert_true(
            readiness_2.can_qualify is False,
            "Incomplete/Critical defective bid has can_qualify == False",
        )
        self.assert_true(
            len(readiness_2.blocking_reasons) >= 1,
            "Blocked bid has descriptive blocking reasons",
            f"Blockers: {readiness_2.blocking_reasons}",
        )
        self.assert_true(
            readiness_2.can_disqualify is True,
            "Blocked bid can still be disqualified by Procurement Officer",
        )

    def test_initial_not_decided_state(self):
        """Tests get_current_decision when no decision has been made yet."""
        self.log("\n--- Executing Test Group 2: Initial Decision State & Telemetry ---")

        dec = BidDecisionService.get_current_decision(
            self.db, self.user_officer, self.tender.id, self.bid_1.id
        )
        self.assert_true(
            dec.decision == "NOT_DECIDED",
            "Initial decision status is NOT_DECIDED",
        )
        self.assert_true(
            dec.decision_version == 0,
            "Initial decision version is 0",
        )
        self.assert_true(
            dec.readiness is not None and dec.readiness.can_qualify is True,
            "Live readiness telemetry embedded in response",
        )

    def test_record_qualified_decision_lifecycle(self):
        """Tests recording a QUALIFIED decision and verifying system invariants."""
        self.log("\n--- Executing Test Group 3: Authoritative Qualification Workflow ---")

        req = RecordBidDecisionRequest(
            decision="QUALIFIED",
            reason="All financial turnovers, GST certificates, and OEM authorisations verified successfully.",
            decision_summary="Technical and statutory criteria fully compliant.",
        )
        result = BidDecisionService.record_decision(
            self.db, self.user_officer, self.tender.id, self.bid_1.id, req
        )

        self.assert_true(
            result.decision == "QUALIFIED",
            "Decision correctly recorded as QUALIFIED",
        )
        self.assert_true(
            result.decision_version == 1,
            "First decision recorded with decision_version == 1",
        )
        self.assert_true(
            result.is_current is True and result.is_stale is False,
            "Decision is current and active (not stale)",
        )
        self.assert_true(
            result.decided_by.full_name == self.profile_officer.full_name,
            "Deciding officer full name attributed in audit metadata",
        )
        self.assert_true(
            result.snapshot_reference.overall_score == 95.0,
            "Evaluation snapshot reference captured score at decision time",
        )

        # Invariant checks: Bid.status and Tender.status must NOT change to AWARDED
        bid_refreshed = self.db.get(Bid, self.bid_1.id)
        tender_refreshed = self.db.get(Tender, self.tender.id)
        self.assert_true(
            bid_refreshed.status == "SUBMITTED",
            "Bid.status remains SUBMITTED (lifecycle preserved, no auto-award)",
        )
        self.assert_true(
            tender_refreshed.status == "CLOSED",
            "Tender.status remains CLOSED (not changed to AWARDED)",
        )

    def test_strict_blocker_enforcement(self):
        """Tests that attempting to QUALIFY a blocked bid is strictly rejected."""
        self.log("\n--- Executing Test Group 4: Strict Safeguard Enforcement ---")

        req = RecordBidDecisionRequest(
            decision="QUALIFIED",
            reason="Attempting to override critical failures without resolving review.",
        )
        try:
            BidDecisionService.record_decision(
                self.db, self.user_officer, self.tender.id, self.bid_2.id, req
            )
            self.assert_true(False, "Qualifying blocked bid should raise HTTP 400")
        except HTTPException as e:
            self.assert_true(
                e.status_code == 400 and "blocked" in e.detail.lower(),
                "Blocked qualification raised HTTP 400 Bad Request with blocker explanation",
                f"Error detail: {e.detail}",
            )

        # Short reason validation (< 10 chars)
        try:
            RecordBidDecisionRequest(
                decision="DISQUALIFIED",
                reason="Too short",
            )
            self.assert_true(False, "Short reason (< 10 chars) should raise validation error")
        except Exception as e:
            self.assert_true(
                "at least 10 characters" in str(e).lower() or "too_short" in str(e).lower(),
                "Reason length safeguard enforced (< 10 chars rejected by Pydantic/Service)",
            )

    def test_disqualification_workflow(self):
        """Tests recording DISQUALIFIED with categorical reason."""
        self.log("\n--- Executing Test Group 5: Categorical Disqualification Workflow ---")

        req = RecordBidDecisionRequest(
            decision="DISQUALIFIED",
            reason="Bidder failed mandatory annual turnover threshold of 50 Cr (submitted 38 Cr).",
            decision_summary="Disqualified due to statutory financial shortfall.",
            category="MANDATORY_REQUIREMENT_FAILURE",
        )
        result = BidDecisionService.record_decision(
            self.db, self.user_officer, self.tender.id, self.bid_2.id, req
        )

        self.assert_true(
            result.decision == "DISQUALIFIED",
            "Bid 2 successfully recorded as DISQUALIFIED",
        )
        self.assert_true(
            result.category == "MANDATORY_REQUIREMENT_FAILURE",
            "Disqualification category recorded as MANDATORY_REQUIREMENT_FAILURE",
        )
        self.assert_true(
            result.is_current is True,
            "Disqualification decision marked is_current == True",
        )

    def test_versioning_and_superseding(self):
        """Tests updating an existing decision and verifying version increment and history."""
        self.log("\n--- Executing Test Group 6: Decision Versioning & Superseding ---")

        # Update Bid 1 from QUALIFIED to UNDER_REVIEW
        req_update = RecordBidDecisionRequest(
            decision="UNDER_REVIEW",
            reason="Temporarily deferred pending clarification on OEM warranty duration from third-party vendor.",
            decision_summary="Under review for OEM warranty validation.",
        )
        res_v2 = BidDecisionService.record_decision(
            self.db, self.user_officer, self.tender.id, self.bid_1.id, req_update
        )

        self.assert_true(
            res_v2.decision == "UNDER_REVIEW",
            "Updated decision is UNDER_REVIEW",
        )
        self.assert_true(
            res_v2.decision_version == 2,
            "Decision version atomically incremented to 2",
        )
        self.assert_true(
            res_v2.is_current is True,
            "Version 2 is the current active decision",
        )

        # Check history endpoint (ordered newest to oldest)
        history = BidDecisionService.get_decision_history(
            self.db, self.user_officer, self.tender.id, self.bid_1.id
        )
        self.assert_true(
            len(history) == 2,
            "Decision history contains exactly 2 versions",
            f"History count: {len(history)}",
        )
        self.assert_true(
            history[0].decision_version == 2 and history[0].is_current is True,
            "Version 2 in history is marked is_current == True",
        )
        self.assert_true(
            history[1].decision_version == 1 and history[1].is_current is False,
            "Version 1 in history is marked is_current == False and has superseded_at",
        )
        self.assert_true(
            history[1].superseded_at is not None,
            "Version 1 has superseded_at timestamp recorded",
        )

    def test_staleness_invalidation(self):
        """Tests that upstream evaluation changes mark decision as stale without auto-reversal."""
        self.log("\n--- Executing Test Group 7: Staleness Tracking on Upstream Changes ---")

        # Mark current decision on Bid 1 as stale
        stale_count = BidDecisionService.check_and_mark_decision_staleness(
            self.db, self.bid_1.id, "Compliance re-evaluation triggered by Procurement Officer"
        )
        self.assert_true(
            stale_count == 1,
            "Exactly 1 active decision marked as stale",
        )

        current_dec = BidDecisionService.get_current_decision(
            self.db, self.user_officer, self.tender.id, self.bid_1.id
        )
        self.assert_true(
            current_dec.is_stale is True,
            "Current decision flagged with is_stale == True",
        )
        self.assert_true(
            current_dec.decision == "UNDER_REVIEW",
            "Decision outcome preserved (not auto-reversed or wiped)",
        )
        self.assert_true(
            "Compliance re-evaluation" in (current_dec.stale_reason or ""),
            "Stale reason contains explanation of upstream change",
        )

    def test_dashboard_and_comparison_integration(self):
        """Tests that tender evaluation listings and comparison endpoints reflect human decision status."""
        self.log("\n--- Executing Test Group 8: Listing & Comparison View Integration ---")

        # 1. Tender Bid Evaluations List
        eval_list = ProcurementDashboardService.get_tender_bid_evaluations(
            self.db, self.user_officer, self.tender.id
        )
        bids_by_num = {b.bid_number: b for b in eval_list.bids}
        self.assert_true(
            bids_by_num[self.bid_1.bid_number].human_decision_status == "UNDER_REVIEW",
            "Tender bid list reflects Bid 1 human_decision_status == UNDER_REVIEW",
        )
        self.assert_true(
            bids_by_num[self.bid_2.bid_number].human_decision_status == "DISQUALIFIED",
            "Tender bid list reflects Bid 2 human_decision_status == DISQUALIFIED",
        )

        # 2. Bid Comparison Endpoint
        comp_res = BidComparisonService.compare_tender_bids(
            self.db, self.user_officer, self.tender.id, [self.bid_1.id, self.bid_2.id]
        )
        comp_map = {b.bid_id: b for b in comp_res.bids}
        self.assert_true(
            comp_map[self.bid_1.id].human_decision_status == "UNDER_REVIEW",
            "Bid Comparison reflects Bid 1 human_decision_status == UNDER_REVIEW",
        )
        self.assert_true(
            comp_map[self.bid_2.id].human_decision_status == "DISQUALIFIED",
            "Bid Comparison reflects Bid 2 human_decision_status == DISQUALIFIED",
        )

    def test_multi_tenant_and_role_authorization(self):
        """Tests multi-tenant isolation and role-based access controls."""
        self.log("\n--- Executing Test Group 9: Multi-Tenant & Role Authorization ---")

        # 1. Cross-Tenant Officer attempting to access or record decision
        try:
            BidDecisionService.get_current_decision(
                self.db, self.user_officer_other, self.tender.id, self.bid_1.id
            )
            self.assert_true(False, "Cross-tenant officer should get HTTP 404/403")
        except HTTPException as e:
            self.assert_true(
                e.status_code in [403, 404],
                "Cross-tenant officer access rejected with HTTP 403 or 404",
            )

        # 2. Bidder role attempting to record decision
        req = RecordBidDecisionRequest(
            decision="QUALIFIED",
            reason="Attempting unauthorized self-qualification.",
        )
        try:
            BidDecisionService.record_decision(
                self.db, self.user_bidder, self.tender.id, self.bid_1.id, req
            )
            self.assert_true(False, "Bidder role should be blocked with HTTP 403")
        except HTTPException as e:
            self.assert_true(
                e.status_code == 403,
                "Bidder role blocked from recording decision with HTTP 403 Forbidden",
            )

    def run_all(self):
        """Executes all test groups and outputs final score."""
        self.log("=================================================================")
        self.log("Starting Part 8D: Final Human Decision Workflow Test Suite")
        self.log("=================================================================")
        try:
            self.setup_fixtures()
            self.test_decision_readiness_engine()
            self.test_initial_not_decided_state()
            self.test_record_qualified_decision_lifecycle()
            self.test_strict_blocker_enforcement()
            self.test_disqualification_workflow()
            self.test_versioning_and_superseding()
            self.test_staleness_invalidation()
            self.test_dashboard_and_comparison_integration()
            self.test_multi_tenant_and_role_authorization()
        finally:
            self.db.close()

        self.log("=================================================================")
        self.log(f"Test Execution Finished: {self.passed_tests}/{self.total_tests} Tests Passed")
        if self.failed_tests == 0:
            self.log("ALL TESTS PASSED! PART 8D VERIFICATION: SUCCESS (100%)")
        else:
            self.log(f"{self.failed_tests} TESTS FAILED.")
        self.log("=================================================================")
        return self.failed_tests == 0


if __name__ == "__main__":
    runner = Part8DTestSuite()
    success = runner.run_all()
    sys.exit(0 if success else 1)
