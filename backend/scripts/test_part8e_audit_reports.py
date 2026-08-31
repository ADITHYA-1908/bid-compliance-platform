"""
Part 8E: Audit Trail, Decision History & Reports — Master QA Test Suite
Validates append-only immutable audit logging, multi-dimensional search & filtering,
actor/source distinction, sensitive data sanitization, real-time KPI metrics,
chronological timelines, structured procurement reports (Tender Summary & Bid Dossier),
advisory AI vs authoritative human decision separation, mock verification transparency,
staleness warnings, and vector PDF exports with multi-tenant RBAC enforcement.

Execute with:
  venv\\Scripts\\python.exe backend/scripts/test_part8e_audit_reports.py
"""

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

# Add backend directory to sys.path
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
from app.db.models.bid_document import BidDocument
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.human_review import HumanReviewItem, ReviewStatus, ReviewSeverity, ReviewType, ReviewResolution
from app.db.models.bid_shortlist import BidShortlist
from app.db.models.bid_decision import BidDecision, BidDecisionStatus
from app.db.models.verification_record import VerificationRecord
from app.db.models.audit_event import AuditActorSource, AuditEntityType, AuditEventType, AuditEvent

from app.schemas.audit import RecordAuditEventDTO
from app.schemas.bid_decision import RecordBidDecisionRequest, BidDecisionStatusEnum
from app.schemas.human_review import ResolveReviewRequest, ReviewResolutionEnum
from app.services.audit.audit_service import AuditService, MAX_METADATA_SIZE_BYTES
from app.services.reports.procurement_report_service import ProcurementReportService
from app.services.procurement.bid_decision_service import BidDecisionService
from app.services.procurement.human_review_service import HumanReviewService
from app.services.procurement.bid_comparison_service import BidComparisonService


class Part8ETestSuite:
    def __init__(self):
        self.Session = get_session_factory()
        self.db = self.Session()
        self.test_prefix = f"p8e_test_{uuid.uuid4().hex[:6]}"
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0

    def log(self, message: str):
        print(f"[Part 8E QA] {message}")

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
        self.org_buyer_a = Organization(
            id=uuid.uuid4(),
            name=f"Ministry of Electronics {self.test_prefix}",
            organization_type="BUYER",
            is_active=True,
        )
        self.org_buyer_b = Organization(
            id=uuid.uuid4(),
            name=f"Department of Telecomm {self.test_prefix}",
            organization_type="BUYER",
            is_active=True,
        )
        self.org_seller_1 = Organization(
            id=uuid.uuid4(),
            name=f"Zenith Tech Solutions {self.test_prefix}",
            organization_type="SELLER",
            pan_number="ABCDE1234F",
            gstin="27ABCDE1234F1Z5",
            udyam_number="UDYAM-MH-01-0012345",
            business_category="PRIVATE_LIMITED",
            state="Maharashtra",
            city="Mumbai",
            is_active=True,
        )
        self.org_seller_2 = Organization(
            id=uuid.uuid4(),
            name=f"Apex Cyber Systems {self.test_prefix}",
            organization_type="SELLER",
            pan_number="XYZAB5678G",
            gstin="07XYZAB5678G1Z2",
            udyam_number="UDYAM-DL-02-0054321",
            business_category="PARTNERSHIP",
            state="Delhi",
            city="New Delhi",
            is_active=True,
        )
        self.db.add_all([self.org_buyer_a, self.org_buyer_b, self.org_seller_1, self.org_seller_2])
        self.db.flush()

        # 2. Roles
        role_po = self.db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
        role_bidder = self.db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        role_admin = self.db.scalars(select(Role).where(Role.name == "ADMIN")).first()

        # 3. Profiles & Users
        self.officer_a_profile = Profile(
            id=uuid.uuid4(),
            email=f"officer.a.{self.test_prefix}@gem.gov.in",
            organization_id=self.org_buyer_a.id,
            role_id=role_po.id,
            full_name=f"Dr. Ramesh Sharma {self.test_prefix}",
            phone="9876543210",
            is_active=True,
        )
        self.officer_b_profile = Profile(
            id=uuid.uuid4(),
            email=f"officer.b.{self.test_prefix}@gem.gov.in",
            organization_id=self.org_buyer_b.id,
            role_id=role_po.id,
            full_name=f"Col. Suresh Verma {self.test_prefix}",
            phone="9876543211",
            is_active=True,
        )
        self.bidder_profile = Profile(
            id=uuid.uuid4(),
            email=f"bidder.{self.test_prefix}@zenith.com",
            organization_id=self.org_seller_1.id,
            role_id=role_bidder.id,
            full_name=f"Amit Kumar {self.test_prefix}",
            phone="9876543212",
            is_active=True,
        )
        self.admin_profile = Profile(
            id=uuid.uuid4(),
            email=f"admin.{self.test_prefix}@gem.gov.in",
            organization_id=self.org_buyer_a.id,
            role_id=role_admin.id,
            full_name=f"System Admin {self.test_prefix}",
            phone="9876543213",
            is_active=True,
        )
        self.db.add_all([
            self.officer_a_profile,
            self.officer_b_profile,
            self.bidder_profile,
            self.admin_profile,
        ])
        self.db.flush()

        self.officer_a_user = User(
            id=uuid.uuid4(),
            email=self.officer_a_profile.email,
            password_hash="fakehash",
            profile_id=self.officer_a_profile.id,
            is_active=True,
        )
        self.officer_b_user = User(
            id=uuid.uuid4(),
            email=self.officer_b_profile.email,
            password_hash="fakehash",
            profile_id=self.officer_b_profile.id,
            is_active=True,
        )
        self.bidder_user = User(
            id=uuid.uuid4(),
            email=self.bidder_profile.email,
            password_hash="fakehash",
            profile_id=self.bidder_profile.id,
            is_active=True,
        )
        self.admin_user = User(
            id=uuid.uuid4(),
            email=self.admin_profile.email,
            password_hash="fakehash",
            profile_id=self.admin_profile.id,
            is_active=True,
        )
        self.db.add_all([
            self.officer_a_user,
            self.officer_b_user,
            self.bidder_user,
            self.admin_user,
        ])
        self.db.flush()

        # 4. Tender & Requirements
        now = datetime.now(timezone.utc)
        self.tender = Tender(
            id=uuid.uuid4(),
            tender_number=f"GEM/2026/B/{self.test_prefix.upper()}",
            title="High-Performance Server Infrastructure Procurement",
            organization_id=self.org_buyer_a.id,
            created_by_profile_id=self.officer_a_profile.id,
            status="EVALUATION",
            category="GOODS",
            procurement_type="OPEN_TENDER",
            estimated_value=Decimal("5000000.00"),
            currency="INR",
            publish_date=now - timedelta(days=10),
            submission_start_date=now - timedelta(days=9),
            submission_end_date=now - timedelta(days=1),
            is_active=True,
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=1),
        )
        self.db.add(self.tender)
        self.db.flush()

        self.req_oem = TenderRequirement(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            code="REQ-OEM-AUTH",
            name="OEM Manufacturer Authorization Certificate",
            category="TECHNICAL",
            requirement_type="DOCUMENT",
            operator="EXISTS",
            is_mandatory=True,
            is_critical=True,
            weight=Decimal("20.00"),
            display_order=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.req_turnover = TenderRequirement(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            code="REQ-FIN-TURNOVER",
            name="Minimum Annual Turnover >= 50 Lakhs",
            category="FINANCIAL",
            requirement_type="NUMERIC",
            operator="GTE",
            expected_value=5000000,
            is_mandatory=True,
            is_critical=False,
            weight=Decimal("30.00"),
            display_order=2,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.db.add_all([self.req_oem, self.req_turnover])
        self.db.flush()

        # 5. Bids
        self.bid_1 = Bid(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            bidder_organization_id=self.org_seller_1.id,
            created_by_profile_id=self.bidder_profile.id,
            submitted_by_profile_id=self.bidder_profile.id,
            bid_number=f"BID-1-{self.test_prefix}",
            status="SUBMITTED",
            quoted_amount=Decimal("4600000.00"),
            currency="INR",
            submitted_at=now - timedelta(days=2),
            is_active=True,
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=2),
        )
        self.bid_2 = Bid(
            id=uuid.uuid4(),
            tender_id=self.tender.id,
            bidder_organization_id=self.org_seller_2.id,
            created_by_profile_id=self.bidder_profile.id,
            submitted_by_profile_id=self.bidder_profile.id,
            bid_number=f"BID-2-{self.test_prefix}",
            status="SUBMITTED",
            quoted_amount=Decimal("4950000.00"),
            currency="INR",
            submitted_at=now - timedelta(days=2),
            is_active=True,
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=2),
        )
        self.db.add_all([self.bid_1, self.bid_2])
        self.db.flush()

        # 6. Evaluation Snapshots for Bid 1
        self.cr_oem_1 = ComplianceResult(
            id=uuid.uuid4(),
            bid_id=self.bid_1.id,
            tender_id=self.tender.id,
            tender_requirement_id=self.req_oem.id,
            compliance_status=ComplianceStatus.PASS,
            is_mandatory=True,
            is_critical=True,
            critical_failure=False,
            reason="OEM Authorization verified successfully.",
            evaluation_version=1,
            is_current=True,
            created_at=now - timedelta(hours=5),
        )
        self.cr_turnover_1 = ComplianceResult(
            id=uuid.uuid4(),
            bid_id=self.bid_1.id,
            tender_id=self.tender.id,
            tender_requirement_id=self.req_turnover.id,
            compliance_status=ComplianceStatus.PASS,
            is_mandatory=True,
            is_critical=False,
            critical_failure=False,
            reason="Audited turnover INR 75 Lakhs exceeds requirement.",
            evaluation_version=1,
            is_current=True,
            created_at=now - timedelta(hours=5),
        )
        self.db.add_all([self.cr_oem_1, self.cr_turnover_1])

        self.score_snap_1 = BidScoreSnapshot(
            id=uuid.uuid4(),
            bid_id=self.bid_1.id,
            tender_id=self.tender.id,
            overall_score=Decimal("94.50"),
            scoring_version=1,
            scoring_complete=True,
            earned_weight=Decimal("50.00"),
            eligible_weight=Decimal("50.00"),
            category_scores={
                "TECHNICAL": {"percentage_score": 95.0, "passed_count": 1, "total_count": 1},
                "FINANCIAL": {"percentage_score": 94.0, "passed_count": 1, "total_count": 1},
            },
            critical_failures_count=0,
            is_current=True,
            created_at=now - timedelta(hours=4),
        )
        self.risk_snap_1 = BidRiskSnapshot(
            id=uuid.uuid4(),
            bid_id=self.bid_1.id,
            tender_id=self.tender.id,
            base_risk_score=Decimal("12.00"),
            base_risk_level="LOW",
            adjusted_risk_score=Decimal("12.00"),
            adjusted_risk_level="LOW",
            risk_complete=True,
            risk_version=1,
            override_applied=False,
            applied_overrides=[],
            is_current=True,
            created_at=now - timedelta(hours=4),
        )
        self.db.add_all([self.score_snap_1, self.risk_snap_1])
        self.db.flush()

        self.ai_rec_1 = AIRecommendationRecord(
            id=uuid.uuid4(),
            bid_id=self.bid_1.id,
            score_snapshot_id=self.score_snap_1.id,
            risk_snapshot_id=self.risk_snap_1.id,
            recommendation="RECOMMENDED",
            recommendation_reason="Strong statutory and technical compliance across all required parameters.",
            summary="Proposal meets all OEM, financial, and technical standards.",
            strengths=["Direct OEM partnership certificate", "Strong liquidity ratio"],
            concerns=[],
            confidence_label="HIGH",
            model_provider="Gemini-AI",
            model_name="gemini-1.5-pro",
            prompt_version="2.0",
            guardrail_applied=False,
            is_stale=False,
            created_at=now - timedelta(hours=3),
        )
        self.db.add(self.ai_rec_1)

        # Mock verification record to validate disclaimer transparency
        self.verif_mock = VerificationRecord(
            id=uuid.uuid4(),
            bid_id=self.bid_1.id,
            verification_type="GST_ACTIVE",
            verification_status="VERIFIED",
            source_type="MOCK",
            source_name="GSTN Sandbox Registry",
            claimed_value="27ABCDE1234F1Z5",
            verified_value="27ABCDE1234F1Z5",
            match_status="MATCH",
            confidence=0.98,
            created_at=now - timedelta(hours=6),
        )
        self.db.add(self.verif_mock)
        self.db.commit()
        self.log("Fixtures initialized successfully.")

    def run_tests(self):
        self.log("Starting Part 8E Master QA Test Suite...")
        self.setup_fixtures()

        # -------------------------------------------------------------
        # 1. Append-Only Audit Event Creation
        # -------------------------------------------------------------
        self.log("Executing Section 1: Append-Only Audit Logging & Metadata Sanitization...")

        # 1.1 Tender Created Event
        tender_evt = AuditService.record_tender_event(
            db=self.db,
            organization_id=self.org_buyer_a.id,
            tender_id=self.tender.id,
            event_type=AuditEventType.TENDER_CREATED,
            action="CREATE",
            summary=f"Tender {self.tender.tender_number} created by officer.",
            metadata={"title": self.tender.title, "estimated_value": 5000000},
            user=self.officer_a_user,
        )
        self.db.commit()
        self.assert_true(
            tender_evt.id is not None and tender_evt.actor_source == AuditActorSource.HUMAN,
            "Tender Created audit event recorded with correct human actor",
        )

        # 1.2 Sensitive Data Stripping & Size Limit Check
        sensitive_meta = {
            "password": "secretpassword",
            "api_key": "sk-1234567890",
            "safe_metric": 42,
            "large_blob": "x" * 20000,  # exceeds 16KB limit
        }
        sanitized_evt = AuditService.record_event(
            db=self.db,
            event_dto=RecordAuditEventDTO(
                organization_id=self.org_buyer_a.id,
                tender_id=self.tender.id,
                actor_source=AuditActorSource.SYSTEM,
                event_type=AuditEventType.COMPLIANCE_EVALUATED,
                entity_type=AuditEntityType.COMPLIANCE_RESULT,
                action="EVALUATE",
                summary="System compliance evaluation completed.",
                metadata=sensitive_meta,
            ),
        )
        self.db.commit()
        self.assert_true(
            "password" not in sanitized_evt.metadata_json and "api_key" not in sanitized_evt.metadata_json,
            "Sensitive credentials stripped from audit metadata",
        )
        self.assert_true(
            sanitized_evt.metadata_json.get("truncated") is True,
            "Oversized metadata payload correctly bounded (<16KB)",
        )

        # 1.3 AI Service Attribution & Guardrails
        ai_evt = AuditService.record_event(
            db=self.db,
            event_dto=RecordAuditEventDTO(
                organization_id=self.org_buyer_a.id,
                tender_id=self.tender.id,
                bid_id=self.bid_1.id,
                actor_source=AuditActorSource.AI_SERVICE,
                event_type=AuditEventType.AI_RECOMMENDATION_GENERATED,
                entity_type=AuditEntityType.AI_RECOMMENDATION,
                entity_id=self.ai_rec_1.id,
                action="SYNTHESIZE",
                summary="AI recommendation generated.",
                metadata={
                    "model_provider": "Gemini-AI",
                    "model_name": "gemini-1.5-pro",
                    "prompt_version": "2.0",
                    "guardrail_applied": False,
                },
            ),
        )
        self.db.commit()
        self.assert_true(
            ai_evt.actor_source == AuditActorSource.AI_SERVICE and ai_evt.metadata_json["model_name"] == "gemini-1.5-pro",
            "AI Service actor attribution and model metadata preserved",
        )

        # -------------------------------------------------------------
        # 2. Human Review & Decision Audit Trail
        # -------------------------------------------------------------
        self.log("Executing Section 2: Human Review & Decision Event Tracing...")

        # 2.1 Final Human Decision Created & Audited
        dec_res = BidDecisionService.record_decision(
            db=self.db,
            user=self.officer_a_user,
            tender_id=self.tender.id,
            bid_id=self.bid_1.id,
            req=RecordBidDecisionRequest(
                decision=BidDecisionStatusEnum.QUALIFIED,
                reason="All technical and statutory parameters verified with direct OEM support.",
                decision_summary="Proposal fully compliant.",
            ),
        )
        self.assert_true(
            dec_res.decision == BidDecisionStatusEnum.QUALIFIED and dec_res.decision_version == 1,
            "Final human decision recorded with version 1",
        )

        # Verify audit event exists for decision
        dec_audit_events = self.db.scalars(
            select(AuditEvent).where(
                AuditEvent.bid_id == self.bid_1.id,
                AuditEvent.event_type == AuditEventType.BID_DECISION_CREATED,
            )
        ).all()
        self.assert_true(
            len(dec_audit_events) == 1,
            "BID_DECISION_CREATED audit event generated in transaction",
        )

        # 2.2 Decision Superseded Version 2
        dec_res_v2 = BidDecisionService.record_decision(
            db=self.db,
            user=self.officer_a_user,
            tender_id=self.tender.id,
            bid_id=self.bid_1.id,
            req=RecordBidDecisionRequest(
                decision=BidDecisionStatusEnum.QUALIFIED,
                reason="Updated with supplementary OEM warranty endorsement.",
                decision_summary="Proposal fully compliant with warranty extension.",
            ),
        )
        self.assert_true(
            dec_res_v2.decision_version == 2 and dec_res_v2.is_current is True,
            "Decision updated to Version 2 and marked current",
        )

        superseded_events = self.db.scalars(
            select(AuditEvent).where(
                AuditEvent.bid_id == self.bid_1.id,
                AuditEvent.event_type == AuditEventType.BID_DECISION_SUPERSEDED,
            )
        ).all()
        self.assert_true(
            len(superseded_events) >= 1,
            "BID_DECISION_SUPERSEDED audit event generated on version update",
        )

        # 2.3 Shortlist Action & Audit
        shortlist_res = BidComparisonService.add_to_shortlist(
            db=self.db,
            user=self.officer_a_user,
            tender_id=self.tender.id,
            bid_id=self.bid_1.id,
            reason="High score and robust technical proposal.",
        )
        self.assert_true(
            shortlist_res.is_shortlisted is True,
            "Bid added to shortlist by officer",
        )
        shortlist_events = self.db.scalars(
            select(AuditEvent).where(
                AuditEvent.bid_id == self.bid_1.id,
                AuditEvent.event_type == AuditEventType.BID_SHORTLISTED,
            )
        ).all()
        self.assert_true(
            len(shortlist_events) == 1,
            "BID_SHORTLISTED audit event recorded",
        )

        # -------------------------------------------------------------
        # 3. Multi-Dimensional Audit Query & Security
        # -------------------------------------------------------------
        self.log("Executing Section 3: Audit Queries, Search, KPIs & Multi-Tenant RBAC...")

        # 3.1 Officer A Audit Query
        list_res = AuditService.get_audit_events(
            db=self.db,
            user=self.officer_a_user,
            tender_id=self.tender.id,
            page=1,
            page_size=20,
        )
        self.assert_true(
            list_res.total > 0 and len(list_res.items) > 0,
            "Officer queries tenant audit events with pagination",
        )
        self.assert_true(
            list_res.kpis.decisions_recorded >= 2,
            "Real-time audit KPIs calculate correct decision counts",
        )

        # 3.2 Search Filter
        search_res = AuditService.get_audit_events(
            db=self.db,
            user=self.officer_a_user,
            tender_id=self.tender.id,
            search="OEM",
        )
        self.assert_true(
            search_res.total > 0,
            "Full-text search locates events by keyword",
        )

        # 3.3 Bid Chronological Timeline
        timeline = AuditService.get_bid_timeline(
            db=self.db,
            user=self.officer_a_user,
            tender_id=self.tender.id,
            bid_id=self.bid_1.id,
        )
        self.assert_true(
            len(timeline) >= 3 and timeline[0].created_at <= timeline[-1].created_at,
            "Chronological timeline returns events in oldest-to-newest order",
        )

        # 3.4 Cross-Tenant Isolation (Officer B cannot see Officer A events)
        officer_b_events = AuditService.get_audit_events(
            db=self.db,
            user=self.officer_b_user,
            tender_id=self.tender.id,
        )
        self.assert_true(
            officer_b_events.total == 0,
            "Cross-tenant isolation blocks Officer B from viewing Officer A audit events",
        )

        # 3.5 Bidder Access Forbidden (403)
        bidder_forbidden = False
        try:
            AuditService.get_audit_events(
                db=self.db,
                user=self.bidder_user,
                tender_id=self.tender.id,
            )
        except HTTPException as he:
            if he.status_code == 403:
                bidder_forbidden = True
        self.assert_true(
            bidder_forbidden,
            "BIDDER role blocked from internal procurement audit trail with HTTP 403",
        )

        # -------------------------------------------------------------
        # 4. Procurement Reports (Tender Summary & Bid Dossier)
        # -------------------------------------------------------------
        self.log("Executing Section 4: Procurement Reports & PDF Generation...")

        # 4.1 Tender Evaluation Summary Report
        tender_rep = ProcurementReportService.get_tender_summary_report(
            db=self.db,
            user=self.officer_a_user,
            tender_id=self.tender.id,
        )
        self.assert_true(
            tender_rep.total_bids_submitted == 2 and tender_rep.total_qualified == 1,
            "Tender Summary Report calculates accurate aggregate metrics",
        )
        self.assert_true(
            len(tender_rep.bids) == 2,
            "Tender Summary Report contains itemized bid roster",
        )

        # 4.2 Bid Evaluation Dossier
        bid_rep = ProcurementReportService.get_bid_evaluation_report(
            db=self.db,
            user=self.officer_a_user,
            tender_id=self.tender.id,
            bid_id=self.bid_1.id,
        )
        self.assert_true(
            bid_rep.final_human_decision.decision == "QUALIFIED" and bid_rep.final_human_decision.decision_version == 2,
            "Bid Dossier reflects authoritative final human decision Version 2",
        )
        self.assert_true(
            len(bid_rep.decision_history) == 2,
            "Bid Dossier preserves complete decision history version ledger",
        )
        self.assert_true(
            bid_rep.ai_recommendation is not None and "advisory" in bid_rep.ai_recommendation.advisory_disclaimer.lower(),
            "Bid Dossier clearly labels AI recommendation as advisory guidance",
        )
        self.assert_true(
            bid_rep.mock_verification_disclaimer is not None and "SANDBOX" in bid_rep.mock_verification_disclaimer,
            "Mock verification disclaimer transparently disclosed in report",
        )

        # 4.3 Un-decided Bid Report Status
        bid_2_rep = ProcurementReportService.get_bid_evaluation_report(
            db=self.db,
            user=self.officer_a_user,
            tender_id=self.tender.id,
            bid_id=self.bid_2.id,
        )
        self.assert_true(
            bid_2_rep.final_human_decision.decision == "NOT_DECIDED",
            "Undecided bid displays 'NOT_DECIDED' status without errors",
        )

        # 4.4 Vector PDF Generation
        pdf_bytes_tender = ProcurementReportService.generate_tender_summary_pdf(
            db=self.db,
            user=self.officer_a_user,
            tender_id=self.tender.id,
        )
        self.assert_true(
            len(pdf_bytes_tender) > 1000 and pdf_bytes_tender.startswith(b"%PDF-"),
            "Tender Summary vector PDF generated successfully with valid binary header",
        )

        pdf_bytes_bid = ProcurementReportService.generate_bid_evaluation_pdf(
            db=self.db,
            user=self.officer_a_user,
            tender_id=self.tender.id,
            bid_id=self.bid_1.id,
        )
        self.assert_true(
            len(pdf_bytes_bid) > 1000 and pdf_bytes_bid.startswith(b"%PDF-"),
            "Bid Evaluation Dossier vector PDF generated successfully with valid binary header",
        )

        # 4.5 Report Cross-Tenant Access Blocked (404/403)
        report_blocked = False
        try:
            ProcurementReportService.get_tender_summary_report(
                db=self.db,
                user=self.officer_b_user,
                tender_id=self.tender.id,
            )
        except HTTPException as he:
            if he.status_code in (403, 404):
                report_blocked = True
        self.assert_true(
            report_blocked,
            "Cross-tenant report access strictly blocked for unauthorized officers",
        )

        # -------------------------------------------------------------
        # Summary & Final Assertion
        # -------------------------------------------------------------
        self.log("=" * 60)
        self.log(f"Part 8E Test Run Complete: {self.passed_tests}/{self.total_tests} Tests Passed.")
        self.log("=" * 60)

        if self.failed_tests == 0:
            print("\nPART 8E STATUS: COMPLETE\n")
            return 0
        else:
            print(f"\nPART 8E STATUS: BLOCKED ({self.failed_tests} tests failed)\n")
            return 1


if __name__ == "__main__":
    suite = Part8ETestSuite()
    exit_code = suite.run_tests()
    sys.exit(exit_code)
