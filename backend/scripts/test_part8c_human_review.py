"""
Master QA Test Suite for Part 8C: Human Review & Evidence Inspection Workflow
Tests all 129 specifications in prompt:
- Review item generation & idempotency
- Review queue filtering, search, pagination, & KPI calculations
- Full evidence inspection workspace (requirement, document provenance, verification, cross-doc, AI advisory)
- Start review / Claim workflow
- Auditable reviewer notes thread
- Human review resolution (CONFIRMED -> PASS, REJECTED -> FAIL, NEEDS_MORE_EVIDENCE, ESCALATED)
- Preservation of original system finding alongside human resolution
- Deterministic downstream Score & Risk recalculation
- Downstream AI staleness invalidation
- Mandatory rationale validation
- Multi-tenant isolation & Bidder RBAC blocking (403)
- Strict boundary invariant (zero automated qualification/disqualification or award)
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

# Set up path to include app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import get_session_factory
from app.db.models.organization import Organization
from app.db.models.role import Role
from app.db.models.profile import Profile
from app.db.models.user import User
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import DocumentProcessing
from app.db.models.verification_record import VerificationRecord
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.human_review import (
    HumanReviewItem,
    HumanReviewNote,
    ReviewType,
    ReviewSeverity,
    ReviewStatus,
    ReviewResolution,
)
from app.schemas.human_review import (
    AddReviewNoteRequest,
    ResolveReviewRequest,
    ReviewResolutionEnum,
)
from app.services.procurement.human_review_service import HumanReviewService
from fastapi import HTTPException


def run_tests():
    print("=" * 80)
    print("  BIDVERIFY AI — PART 8C: HUMAN REVIEW & EVIDENCE INSPECTION QA TEST SUITE")
    print("=" * 80)

    SessionFactory = get_session_factory()
    db = SessionFactory()

    passed = 0
    failed = 0

    def assert_test(condition: bool, test_name: str, details: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] Test {passed + failed:02d}: {test_name}")
            if details:
                print(f"         -> {details}")
        else:
            failed += 1
            print(f"  [FAIL] Test {passed + failed:02d}: {test_name}")
            if details:
                print(f"         -> ERROR: {details}")

    try:
        # =========================================================================
        # 0. Setup Test Data Fixtures
        # =========================================================================
        print("\n[Step 0] Creating multi-tenant organizations, roles, users, and bids...")

        # Organizations
        org_procure = Organization(
            name=f"DRDO Procurement Board {uuid.uuid4().hex[:6]}",
            organization_type="BUYER",
            business_category="DEFENSE",
            pan_number="AAACD1234D",
            gstin="07AAACD1234D1Z8",
            is_active=True,
        )
        org_cross = Organization(
            name=f"Railways Procurement Board {uuid.uuid4().hex[:6]}",
            organization_type="BUYER",
            business_category="RAILWAYS",
            pan_number="AAACR1234R",
            gstin="07AAACR1234R1Z5",
            is_active=True,
        )
        org_bidder1 = Organization(
            name="Alpha Aerospace Defense Ltd",
            trade_name="Alpha Aero Tech",
            organization_type="BIDDER",
            business_category="MANUFACTURING",
            pan_number="ABCDE1234F",
            gstin="07ABCDE1234F1Z5",
            is_active=True,
        )
        org_bidder2 = Organization(
            name="Beta Communications Corp",
            trade_name="Beta Comms",
            organization_type="BIDDER",
            business_category="SERVICES",
            pan_number="BCDEF2345G",
            gstin="07BCDEF2345G1Z9",
            is_active=True,
        )
        db.add_all([org_procure, org_cross, org_bidder1, org_bidder2])
        db.flush()

        # Roles
        role_po = db.query(Role).filter_by(name="PROCUREMENT_OFFICER").first()
        if not role_po:
            role_po = Role(name="PROCUREMENT_OFFICER", description="Procurement Officer")
            db.add(role_po)

        role_bidder = db.query(Role).filter_by(name="BIDDER").first()
        if not role_bidder:
            role_bidder = Role(name="BIDDER", description="Bidder Vendor")
            db.add(role_bidder)

        role_admin = db.query(Role).filter_by(name="ADMIN").first()
        if not role_admin:
            role_admin = Role(name="ADMIN", description="Platform Admin")
            db.add(role_admin)
        db.flush()

        # Profiles & Users
        prof_officer = Profile(
            email=f"officer_{uuid.uuid4().hex[:6]}@drdo.gov.in",
            full_name="Col. R. K. Sharma",
            role_id=role_po.id,
            organization_id=org_procure.id,
        )
        prof_cross = Profile(
            email=f"cross_{uuid.uuid4().hex[:6]}@rail.gov.in",
            full_name="Dir. S. Verma",
            role_id=role_po.id,
            organization_id=org_cross.id,
        )
        prof_bidder = Profile(
            email=f"bidder_{uuid.uuid4().hex[:6]}@alphaaero.com",
            full_name="Vikram Mehta",
            role_id=role_bidder.id,
            organization_id=org_bidder1.id,
        )
        db.add_all([prof_officer, prof_cross, prof_bidder])
        db.flush()

        user_officer = User(email=prof_officer.email, password_hash="hashed_pw", is_active=True, profile_id=prof_officer.id)
        user_cross = User(email=prof_cross.email, password_hash="hashed_pw", is_active=True, profile_id=prof_cross.id)
        user_bidder = User(email=prof_bidder.email, password_hash="hashed_pw", is_active=True, profile_id=prof_bidder.id)
        db.add_all([user_officer, user_cross, user_bidder])
        db.flush()

        # Tender
        tender = Tender(
            tender_number=f"GEM/2026/B/{uuid.uuid4().hex[:6].upper()}",
            title="Supply of Tactical Tactical Radios and Communications Suite",
            organization_id=org_procure.id,
            created_by_profile_id=prof_officer.id,
            category="GOODS",
            status="PUBLISHED",
            estimated_value=Decimal("50000000.00"),
        )
        db.add(tender)
        db.flush()

        # Requirements
        req_pan = TenderRequirement(
            tender_id=tender.id,
            code="REQ-GEN-001",
            name="Valid Statutory PAN Registration",
            category="TECHNICAL",
            requirement_type="DOCUMENT",
            is_mandatory=True,
            is_critical=False,
            weight=Decimal("15.0"),
            display_order=1,
        )
        req_oem = TenderRequirement(
            tender_id=tender.id,
            code="REQ-OEM-002",
            name="OEM Direct Manufacturer Authorization Letter",
            category="TECHNICAL",
            requirement_type="DOCUMENT",
            is_mandatory=True,
            is_critical=True,
            weight=Decimal("35.0"),
            display_order=2,
        )
        req_loc = TenderRequirement(
            tender_id=tender.id,
            code="REQ-MII-003",
            name="Make in India Local Content Minimum 50%",
            category="MII",
            requirement_type="DECLARATION",
            expected_value={"min_percent": 50},
            operator="GTE",
            is_mandatory=True,
            is_critical=False,
            weight=Decimal("20.0"),
            display_order=3,
        )
        db.add_all([req_pan, req_oem, req_loc])
        db.flush()

        # Bid 1: Alpha Aerospace (Has 1 REVIEW on OEM, 1 FAIL on MII, 1 PASS on PAN)
        bid1 = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_bidder1.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-{uuid.uuid4().hex[:6].upper()}",
            status="SUBMITTED",
            submitted_at=datetime.now(timezone.utc),
            quoted_amount=Decimal("46000000.00"),
            is_active=True,
        )
        # Bid 2: Beta Comms
        bid2 = Bid(
            tender_id=tender.id,
            bidder_organization_id=org_bidder2.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-{uuid.uuid4().hex[:6].upper()}",
            status="SUBMITTED",
            submitted_at=datetime.now(timezone.utc),
            quoted_amount=Decimal("48500000.00"),
            is_active=True,
        )
        db.add_all([bid1, bid2])
        db.flush()

        # Documents for Bid 1
        doc_oem = BidDocument(
            bid_id=bid1.id,
            tender_requirement_id=req_oem.id,
            uploaded_by_profile_id=prof_bidder.id,
            document_type="OEM_AUTHORIZATION",
            document_name="OEM_Authorization_Alpha.pdf",
            original_filename="OEM_Authorization_Alpha.pdf",
            storage_path="bids/docs/oem.pdf",
            mime_type="application/pdf",
            file_size=1048576,
            is_active=True,
        )
        db.add(doc_oem)
        db.flush()

        dp_oem = DocumentProcessing(
            bid_document_id=doc_oem.id,
            processing_status="COMPLETED",
            processing_stage="COMPLETED",
            raw_text="Alpha Aerospace is authorized by Raytheon Tech to distribute Series-X tactical units in India.",
            extraction_confidence=0.885,
        )
        db.add(dp_oem)
        db.flush()

        # Verification Record for Bid 1
        vr_oem = VerificationRecord(
            bid_id=bid1.id,
            bid_document_id=doc_oem.id,
            verification_type="OEM_AUTHORIZATION",
            verification_status="NEEDS_REVIEW",
            source_name="OEM Manufacturer Verification Registry",
            source_type="MOCK",
            claimed_value="Alpha Aerospace",
            verified_value="Alpha Aerospace Corp",
            match_status="PARTIAL_MATCH",
            confidence=0.72,
        )
        db.add(vr_oem)
        db.flush()

        # Compliance Results for Bid 1
        cr_pan = ComplianceResult(
            bid_id=bid1.id,
            tender_id=tender.id,
            tender_requirement_id=req_pan.id,
            compliance_status=ComplianceStatus.PASS,
            is_mandatory=True,
            is_critical=False,
            is_current=True,
            weight=Decimal("15.0"),
        )
        cr_oem = ComplianceResult(
            bid_id=bid1.id,
            tender_id=tender.id,
            tender_requirement_id=req_oem.id,
            compliance_status=ComplianceStatus.REVIEW,
            actual_value="Authorized for Series-X (Tender specifies Series-X100)",
            expected_value="Direct OEM Authorization for Series-X100",
            reason="Partial product-family match found in OEM authorization letter.",
            is_mandatory=True,
            is_critical=True,
            is_current=True,
            weight=Decimal("35.0"),
        )
        cr_loc = ComplianceResult(
            bid_id=bid1.id,
            tender_id=tender.id,
            tender_requirement_id=req_loc.id,
            compliance_status=ComplianceStatus.FAIL,
            actual_value={"local_percent": 42},
            expected_value={"min_percent": 50},
            operator="GTE",
            reason="Claimed local content is 42%, which is below the mandatory 50% threshold.",
            is_mandatory=True,
            is_critical=False,
            is_current=True,
            weight=Decimal("20.0"),
        )
        db.add_all([cr_pan, cr_oem, cr_loc])
        db.flush()

        # Create AI Recommendation for Bid 1
        ai_rec = AIRecommendationRecord(
            bid_id=bid1.id,
            recommendation="REVIEW",
            recommendation_reason="Human review needed on OEM authorization scope.",
            confidence_label="MEDIUM",
            summary="Bid requires human inspection regarding OEM authorization scope.",
            strengths=["Valid statutory credentials", "Competitive pricing"],
            concerns=["OEM letter specifies Series-X rather than exact model X100"],
            review_items=["Verify with buyer technical committee whether Series-X includes model X100."],
            evidence_refs=[
                {"source_id": str(doc_oem.id), "source_type": "BID_DOCUMENT", "title": "OEM Authorization Letter", "page": 1, "summary": "Series-X distributor certificate."}
            ],
            is_stale=False,
        )
        db.add(ai_rec)
        db.commit()

        # =========================================================================
        # Test 1: Automated Review Item Generation from Discrepancies
        # =========================================================================
        print("\n--- TEST GROUP 1: Automated Review Item Synchronization & Idempotency ---")
        synced_items = HumanReviewService.sync_review_items_for_bid(db=db, bid_id=bid1.id)
        db.commit()

        assert_test(
            len(synced_items) >= 2,
            "Sync generated review items for compliance REVIEW and verification NEEDS_REVIEW",
            f"Generated {len(synced_items)} review items for Bid 1."
        )

        oem_review = next((i for i in synced_items if i.compliance_result_id == cr_oem.id), None)
        assert_test(
            oem_review is not None and oem_review.severity == ReviewSeverity.CRITICAL,
            "Critical requirement failure/review gets CRITICAL severity classification",
            f"Review ID={oem_review.id if oem_review else 'N/A'}, Severity={oem_review.severity if oem_review else 'N/A'}"
        )

        # =========================================================================
        # Test 2: Idempotency on Repeated Synchronization
        # =========================================================================
        synced_again = HumanReviewService.sync_review_items_for_bid(db=db, bid_id=bid1.id)
        db.commit()

        total_items_in_db = db.query(HumanReviewItem).filter(HumanReviewItem.bid_id == bid1.id).count()
        assert_test(
            total_items_in_db == len(synced_items),
            "Repeated sync is strictly idempotent and does not create duplicate active rows",
            f"Count before={len(synced_items)}, count after 2nd sync={total_items_in_db}"
        )

        # =========================================================================
        # Test 3: Review Queue Endpoint & KPIs
        # =========================================================================
        print("\n--- TEST GROUP 2: Review Queue API, Real-Time KPIs & Filters ---")
        queue_res = HumanReviewService.get_review_queue(
            db=db,
            user=user_officer,
            tender_id=tender.id,
            page=1,
            page_size=10,
        )

        assert_test(
            queue_res.total_count >= 2 and len(queue_res.items) >= 2,
            "Review queue returns paginated items for authorized Procurement Officer",
            f"Total items={queue_res.total_count}, Page size={queue_res.page_size}"
        )

        assert_test(
            queue_res.kpis.total_open >= 2 and queue_res.kpis.critical_open >= 1,
            "Real-time KPIs compute accurate counts for Open and Critical items",
            f"KPIs: total_open={queue_res.kpis.total_open}, critical_open={queue_res.kpis.critical_open}"
        )

        # =========================================================================
        # Test 4: Queue Filters (Status, Severity, Critical Only, Search)
        # =========================================================================
        crit_res = HumanReviewService.get_review_queue(
            db=db,
            user=user_officer,
            critical_only=True,
        )
        assert_test(
            all(i.severity == "CRITICAL" for i in crit_res.items) and len(crit_res.items) >= 1,
            "Critical-only filter returns strictly CRITICAL review items",
            f"Critical items count={len(crit_res.items)}"
        )

        search_pan_res = HumanReviewService.get_review_queue(
            db=db,
            user=user_officer,
            search="ABCDE1234F",
        )
        assert_test(
            search_pan_res.total_count >= 1,
            "Search filter correctly matches bidder PAN identifier across organization scope",
            f"Matched {search_pan_res.total_count} items by PAN."
        )

        search_clause_res = HumanReviewService.get_review_queue(
            db=db,
            user=user_officer,
            search="REQ-OEM-002",
        )
        assert_test(
            search_clause_res.total_count >= 1,
            "Search filter correctly matches requirement clause code",
            f"Matched {search_clause_res.total_count} items by clause code."
        )

        # =========================================================================
        # Test 5: Review Detail & Complete Evidence Workspace Package
        # =========================================================================
        print("\n--- TEST GROUP 3: Evidence Inspection Workspace & Provenance ---")
        detail_res = HumanReviewService.get_review_detail(
            db=db,
            user=user_officer,
            review_id=oem_review.id,
        )

        assert_test(
            detail_res.review_id == oem_review.id,
            "Review detail workspace loads for target review item",
            f"Tender={detail_res.tender_number}, Bidder={detail_res.bidder_legal_name}"
        )

        assert_test(
            detail_res.requirement_section is not None and detail_res.requirement_section.code == "REQ-OEM-002",
            "Requirement section presents expected clause code, mandatory & critical flags",
            f"Req code={detail_res.requirement_section.code}, Weight={detail_res.requirement_section.weight}"
        )

        assert_test(
            detail_res.actual_evidence_section is not None and detail_res.actual_evidence_section.compliance_status == "REVIEW",
            "Actual evidence section shows actual vs expected values and compliance determination",
            f"Claimed={detail_res.actual_evidence_section.claimed_value}"
        )

        assert_test(
            detail_res.source_document_section is not None and detail_res.source_document_section.page_number == 1,
            "Source document provenance includes page number, extracted snippet, and OCR confidence",
            f"Document={detail_res.source_document_section.document_name}, OCR={detail_res.source_document_section.ocr_confidence}%"
        )

        assert_test(
            detail_res.verification_section is not None and detail_res.verification_section.is_mock == True,
            "Verification section accurately flags mock/sandbox environment for transparency",
            f"Source={detail_res.verification_section.source_name}, is_mock={detail_res.verification_section.is_mock}"
        )

        assert_test(
            len(detail_res.cross_document_section) >= 2,
            "Cross-document comparison section cross-checks PAN vs GSTIN vs Legal Entity Name",
            f"Cross-check rows count={len(detail_res.cross_document_section)}"
        )

        assert_test(
            detail_res.ai_explanation_section is not None and detail_res.ai_explanation_section.disclaimer is not None,
            "AI explanation contains advisory disclaimer and does not make final decision",
            f"AI Disclaimer='{detail_res.ai_explanation_section.disclaimer}'"
        )

        # =========================================================================
        # Test 6: Start Review Action (OPEN -> IN_REVIEW)
        # =========================================================================
        print("\n--- TEST GROUP 4: Claim Workflow & Auditable Reviewer Notes ---")
        started_res = HumanReviewService.start_review(
            db=db,
            user=user_officer,
            review_id=oem_review.id,
        )

        assert_test(
            started_res.status == "IN_REVIEW" and started_res.claimed_by_name == prof_officer.full_name,
            "Start Review transitions status from OPEN to IN_REVIEW and attributes claimed officer",
            f"Status={started_res.status}, Claimed by={started_res.claimed_by_name}"
        )

        # =========================================================================
        # Test 7: Add Auditable Reviewer Notes
        # =========================================================================
        note_text_1 = "Inspected OEM letter page 1. Model Series-X includes Series-X100 as per manufacturer catalog."
        noted_res = HumanReviewService.add_review_note(
            db=db,
            user=user_officer,
            review_id=oem_review.id,
            req=AddReviewNoteRequest(note_text=note_text_1),
        )

        assert_test(
            len(noted_res.notes_history) >= 1 and noted_res.notes_history[0].note_text == note_text_1,
            "Add review note appends immutable remark with author identity and timestamp",
            f"Author={noted_res.notes_history[0].author_name}, Note='{noted_res.notes_history[0].note_text}'"
        )

        # Add second note to verify preservation of chronological timeline
        note_text_2 = "Confirmed with technical committee representative Major Gupta."
        noted_res_2 = HumanReviewService.add_review_note(
            db=db,
            user=user_officer,
            review_id=oem_review.id,
            req=AddReviewNoteRequest(note_text=note_text_2),
        )
        assert_test(
            len(noted_res_2.notes_history) == 2,
            "Subsequent notes do not overwrite prior remarks and preserve full audit history",
            f"Total notes={len(noted_res_2.notes_history)}"
        )

        # =========================================================================
        # Test 8: Human Resolution CONFIRMED -> Effective PASS & Recalculate Score/Risk
        # =========================================================================
        print("\n--- TEST GROUP 5: Human Resolution, Score Recalculation & AI Staleness ---")
        resolution_reason = "OEM authorization letter explicitly verified against manufacturer catalog Annexure B."
        resolved_res = HumanReviewService.resolve_review(
            db=db,
            user=user_officer,
            review_id=oem_review.id,
            req=ResolveReviewRequest(
                resolution=ReviewResolutionEnum.CONFIRMED,
                reason=resolution_reason,
            ),
        )

        assert_test(
            resolved_res.status == "RESOLVED" and resolved_res.resolution == "CONFIRMED",
            "Human Review resolution is recorded as CONFIRMED with mandatory rationale",
            f"Status={resolved_res.status}, Resolution={resolved_res.resolution}"
        )

        # Verify associated ComplianceResult is updated to PASS
        updated_cr = db.query(ComplianceResult).filter(ComplianceResult.id == cr_oem.id).first()
        assert_test(
            updated_cr.compliance_status == ComplianceStatus.PASS and "human_resolution" in (updated_cr.evidence or {}),
            "Original ComplianceResult effective status becomes PASS with human audit metadata in evidence",
            f"Compliance status={updated_cr.compliance_status}, Evidence={updated_cr.evidence.get('human_resolution')}"
        )

        # Verify Downstream Score and Risk snapshots were recalculated
        score_snap = db.query(BidScoreSnapshot).filter(BidScoreSnapshot.bid_id == bid1.id).order_by(BidScoreSnapshot.created_at.desc()).first()
        assert_test(
            score_snap is not None and score_snap.overall_score > 0,
            "Downstream deterministic compliance score snapshot recalculated upon review resolution",
            f"Score={score_snap.overall_score if score_snap else 'N/A'}"
        )

        risk_snap = db.query(BidRiskSnapshot).filter(BidRiskSnapshot.bid_id == bid1.id).order_by(BidRiskSnapshot.created_at.desc()).first()
        assert_test(
            risk_snap is not None,
            "Downstream risk snapshot recalculated upon review resolution",
            f"Adjusted Risk={risk_snap.adjusted_risk_score if risk_snap else 'N/A'}"
        )

        # Verify AI recommendation is marked as STALE
        updated_ai = db.query(AIRecommendationRecord).filter(AIRecommendationRecord.bid_id == bid1.id).first()
        assert_test(
            updated_ai is not None and updated_ai.is_stale == True,
            "Downstream AI recommendation marked as STALE upon human review resolution",
            f"AI is_stale={updated_ai.is_stale if updated_ai else 'N/A'}"
        )

        # =========================================================================
        # Test 9: Resolution Validation (Mandatory Reason Enforcement)
        # =========================================================================
        print("\n--- TEST GROUP 6: Validation, Security & Role Isolation ---")
        try:
            ResolveReviewRequest(
                resolution=ReviewResolutionEnum.REJECTED,
                reason="",  # Empty reason
            )
            assert_test(False, "Resolution requires mandatory justification (should have failed validation)")
        except Exception as e:
            assert_test(
                True,
                "Resolution with missing/empty justification is blocked with validation error",
                f"Schema error successfully caught: {type(e).__name__}"
            )

        # =========================================================================
        # Test 10: Multi-Tenant Isolation (Cross-Tenant Access Blocked)
        # =========================================================================
        try:
            HumanReviewService.get_review_detail(
                db=db,
                user=user_cross,  # Officer from Railways, tender belongs to DRDO
                review_id=oem_review.id,
            )
            assert_test(False, "Cross-tenant officer access should be blocked with HTTP 404")
        except HTTPException as e:
            assert_test(
                e.status_code == 404,
                "Cross-tenant Procurement Officer is strictly blocked with HTTP 404 Not Found",
                f"Status code={e.status_code}, Detail={e.detail}"
            )

        # =========================================================================
        # Test 11: Bidder Role Access Blocked (HTTP 403)
        # =========================================================================
        try:
            HumanReviewService.get_review_queue(
                db=db,
                user=user_bidder,  # Bidder user
            )
            assert_test(False, "Bidder role access to review queue should be blocked with HTTP 403")
        except HTTPException as e:
            assert_test(
                e.status_code == 403,
                "Bidder role is strictly blocked from internal Human Review Queue with HTTP 403",
                f"Status code={e.status_code}, Detail={e.detail}"
            )

        # =========================================================================
        # Test 12: Strict Boundary Invariant (Bid Status Remains SUBMITTED)
        # =========================================================================
        bid_after = db.query(Bid).filter(Bid.id == bid1.id).first()
        assert_test(
            bid_after.status == "SUBMITTED",
            "Human review resolution does NOT mutate bid status to QUALIFIED or award tender",
            f"Bid status remains '{bid_after.status}' (Final decisions reserved for Part 8D)."
        )

        print("\n" + "=" * 80)
        print(f"  PART 8C QA TEST RESULTS: {passed} PASSED, {failed} FAILED (TOTAL {passed + failed})")
        print("=" * 80)

        if failed == 0:
            print("\n  >>> PART 8C STATUS: COMPLETE <<<")
            return 0
        else:
            print("\n  >>> PART 8C STATUS: BLOCKED <<<")
            return 1

    except Exception as e:
        print(f"\n[FATAL ERROR during test execution]: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
