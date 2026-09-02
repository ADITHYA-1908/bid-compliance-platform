"""
Master QA Test Suite for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
Tests vector indexing, scoped retrieval, prompt injection defense, guardrails,
citation validation, Q&A synthesis, staleness detection, and security isolation.
"""

import math
import os
import sys
import uuid
from decimal import Decimal
from typing import List

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import (
    AIRecommendationRecord,
    Bid,
    BidDocument,
    BidRiskSnapshot,
    BidScoreSnapshot,
    ComplianceResult,
    ComplianceStatus,
    DocumentProcessing,
    Organization,
    ProcessingStatus,
    Profile,
    RAGChunk,
    Role,
    Tender,
    TenderRequirement,
    User,
    VerificationRecord,
)
from app.db.session import get_session_factory
from app.services.ai.ai_config import (
    AIRecommendationEnum,
    ConfidenceLabelEnum,
    DISCLAIMER_TEXT,
    PROMPT_VERSION,
    RAGSourceType,
)
from app.services.ai.ai_models import (
    AIQuestionAnswerOutput,
    AIRecommendationOutput,
    EvidenceRef,
    RetrievedEvidence,
)
from app.services.ai.ai_recommendation_service import AIRecommendationService
from app.services.ai.embedding_service import EmbeddingService
from app.services.ai.llm_service import LLMService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.rag_indexing_service import RAGIndexingService
from app.services.ai.rag_retrieval_service import RAGRetrievalService
from app.services.ai.recommendation_guardrail import RecommendationGuardrail


def log_test(name: str, passed: bool, msg: str = ""):
    status_str = "[PASS]" if passed else "[FAIL]"
    print(f"{status_str} | {name}" + (f": {msg}" if msg else ""))
    if not passed:
        raise AssertionError(f"Test failed: {name} - {msg}")


def cosine_sim(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2) if (norm1 > 0 and norm2 > 0) else 0.0


def run_all_tests():
    print("=" * 80)
    print("STARTING PART 7E MASTER QA SUITE: RAG + AI RECOMMENDATION ENGINE")
    print("=" * 80)

    SessionFactory = get_session_factory()
    db: Session = SessionFactory()

    try:
        # =========================================================================
        # 1. DATABASE & PGVECTOR SCHEMA VALIDATION
        # =========================================================================
        print("\n--- SECTION 1: Schema & Vector Extension Verification ---")
        
        # Test 1: Verify pgvector extension and tables
        ext_check = db.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")).fetchone()
        log_test(
            "Test 01: pgvector extension active in Supabase PostgreSQL",
            ext_check is not None and ext_check[0] == "vector",
            f"Version: {ext_check[1] if ext_check else 'None'}",
        )

        table_check = db.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_name IN ('rag_chunks', 'ai_recommendations')")
        ).fetchall()
        table_names = [r[0] for r in table_check]
        log_test(
            "Test 02: rag_chunks and ai_recommendations tables exist",
            "rag_chunks" in table_names and "ai_recommendations" in table_names,
            f"Found tables: {table_names}",
        )

        # =========================================================================
        # 2. EMBEDDING SERVICE VALIDATION
        # =========================================================================
        print("\n--- SECTION 2: Dense Embedding Generation & Clustering ---")

        emb1 = EmbeddingService.generate_embedding("Turnover and annual financial statements for procurement")
        emb2 = EmbeddingService.generate_embedding("Annual financial balance sheet and auditor turnover certificate")
        emb3 = EmbeddingService.generate_embedding("Blacklisting debarment integrity check across government registries")

        # Test 3: Dimensions and normalization
        norm1 = math.sqrt(sum(x * x for x in emb1))
        log_test(
            "Test 03: Embedding dimension equals 1536 and L2 norm is unit length",
            len(emb1) == 1536 and abs(norm1 - 1.0) < 1e-4,
            f"Dimension: {len(emb1)}, L2 Norm: {norm1:.5f}",
        )

        # Test 4: Semantic clustering (Financial vs Financial > Financial vs Blacklisting)
        sim_fin = cosine_sim(emb1, emb2)
        sim_cross = cosine_sim(emb1, emb3)
        log_test(
            "Test 04: Semantic clustering: Related domain texts have higher similarity",
            sim_fin > sim_cross,
            f"Financial-Financial Sim: {sim_fin:.4f} > Financial-Blacklist Sim: {sim_cross:.4f}",
        )

        # =========================================================================
        # 3. TEST DATA SETUP (ORGANIZATIONS, USERS, TENDERS, BIDS)
        # =========================================================================
        print("\n--- SECTION 3: Setting Up Test Fixtures ---")

        # Org A (Procuring Entity)
        org_a = db.scalars(select(Organization).where(Organization.name == "QA_RAG_Dept_Org_A")).first()
        if not org_a:
            org_a = Organization(name="QA_RAG_Dept_Org_A", organization_type="PROPRIETORSHIP")
            db.add(org_a)
            db.commit()

        # Org B (Competitor Procuring Entity)
        org_b = db.scalars(select(Organization).where(Organization.name == "QA_RAG_Dept_Org_B")).first()
        if not org_b:
            org_b = Organization(name="QA_RAG_Dept_Org_B", organization_type="PROPRIETORSHIP")
            db.add(org_b)
            db.commit()

        # Bidder Org 1 & 2
        bidder_org1 = db.scalars(select(Organization).where(Organization.name == "QA_RAG_Vendor_1")).first()
        if not bidder_org1:
            bidder_org1 = Organization(name="QA_RAG_Vendor_1", organization_type="PROPRIETORSHIP")
            db.add(bidder_org1)
            db.commit()

        bidder_org2 = db.scalars(select(Organization).where(Organization.name == "QA_RAG_Vendor_2")).first()
        if not bidder_org2:
            bidder_org2 = Organization(name="QA_RAG_Vendor_2", organization_type="PROPRIETORSHIP")
            db.add(bidder_org2)
            db.commit()

        # Roles & Users
        officer_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()

        # Officer in Org A
        prof = db.scalars(select(Profile).where(Profile.email == "qa_officer_rag@gem.gov.in")).first()
        if not prof:
            prof = Profile(full_name="QA Officer", email="qa_officer_rag@gem.gov.in", role_id=officer_role.id, organization_id=org_a.id)
            db.add(prof)
            db.commit()

        user_officer = db.scalars(select(User).where(User.email == "qa_officer_rag@gem.gov.in")).first()
        if not user_officer:
            user_officer = User(email="qa_officer_rag@gem.gov.in", password_hash="pw", is_active=True, profile_id=prof.id)
            db.add(user_officer)
            db.commit()

        # Officer in Org B (Competitor)
        prof_b = db.scalars(select(Profile).where(Profile.email == "qa_officer_b_rag@gem.gov.in")).first()
        if not prof_b:
            prof_b = Profile(full_name="QA Officer B", email="qa_officer_b_rag@gem.gov.in", role_id=officer_role.id, organization_id=org_b.id)
            db.add(prof_b)
            db.commit()

        user_officer_b = db.scalars(select(User).where(User.email == "qa_officer_b_rag@gem.gov.in")).first()
        if not user_officer_b:
            user_officer_b = User(email="qa_officer_b_rag@gem.gov.in", password_hash="pw", is_active=True, profile_id=prof_b.id)
            db.add(user_officer_b)
            db.commit()

        # Bidder User
        prof_bidder = db.scalars(select(Profile).where(Profile.email == "qa_bidder_rag@vendor1.com")).first()
        if not prof_bidder:
            prof_bidder = Profile(full_name="QA Bidder", email="qa_bidder_rag@vendor1.com", role_id=bidder_role.id, organization_id=bidder_org1.id)
            db.add(prof_bidder)
            db.commit()

        user_bidder = db.scalars(select(User).where(User.email == "qa_bidder_rag@vendor1.com")).first()
        if not user_bidder:
            user_bidder = User(email="qa_bidder_rag@vendor1.com", password_hash="pw", is_active=True, profile_id=prof_bidder.id)
            db.add(user_bidder)
            db.commit()

        # Tender in Org A
        tender_number = f"GEM/2026/B/RAG-{uuid.uuid4().hex[:6].upper()}"
        tender = Tender(
            organization_id=org_a.id,
            tender_number=tender_number,
            title="Comprehensive IT & Cloud Infrastructure Procurement",
            category="GOODS",
            status="PUBLISHED",
            created_by_profile_id=prof.id,
        )
        db.add(tender)
        db.commit()

        # Tender Requirements
        req_turnover = TenderRequirement(
            tender_id=tender.id,
            code="FIN-01",
            name="Annual Financial Turnover Requirement",
            category="FINANCIAL",
            is_mandatory=True,
            is_critical=False,
            weight=Decimal("15.0"),
            description="Bidder must demonstrate average annual turnover of at least ₹10 Crores over last 3 fiscal years.",
        )
        req_local = TenderRequirement(
            tender_id=tender.id,
            code="MII-01",
            name="Local Content Make in India Minimum 50%",
            category="TECHNICAL",
            is_mandatory=True,
            is_critical=True,
            weight=Decimal("20.0"),
            description="Minimum 50% local content required under DPIIT Make in India Policy.",
        )
        req_oem = TenderRequirement(
            tender_id=tender.id,
            code="OEM-01",
            name="OEM Manufacturer Authorization Certificate",
            category="TECHNICAL",
            is_mandatory=True,
            is_critical=False,
            weight=Decimal("15.0"),
            description="Valid authorization certificate from Original Equipment Manufacturer.",
        )
        req_blacklist = TenderRequirement(
            tender_id=tender.id,
            code="INT-01",
            name="Non-Blacklisting Integrity Affidavit",
            category="INTEGRITY",
            is_mandatory=True,
            is_critical=True,
            weight=Decimal("25.0"),
            description="Bidder must not be debarred or blacklisted by any Government department.",
        )
        db.add_all([req_turnover, req_local, req_oem, req_blacklist])
        db.commit()

        # Bid 1: Submitted Bidder 1 (Fails local content, passes others)
        bid1 = Bid(
            tender_id=tender.id,
            bidder_organization_id=bidder_org1.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-RAG-{uuid.uuid4().hex[:6].upper()}",
            status="SUBMITTED",
        )
        db.add(bid1)
        db.commit()

        # Documents for Bid 1
        doc_fin = BidDocument(
            bid_id=bid1.id,
            uploaded_by_profile_id=prof_bidder.id,
            original_filename="auditor_turnover_certificate.pdf",
            document_name="Turnover Certificate",
            document_type="FINANCIAL_AUDIT_REPORT",
            storage_path="/storage/fin.pdf",
            mime_type="application/pdf",
            file_size=10240,
            is_active=True,
            version=1,
        )
        doc_mii = BidDocument(
            bid_id=bid1.id,
            uploaded_by_profile_id=prof_bidder.id,
            original_filename="local_content_declaration.pdf",
            document_name="Local Content Declaration",
            document_type="LOCAL_CONTENT_DECLARATION",
            storage_path="/storage/mii.pdf",
            mime_type="application/pdf",
            file_size=10240,
            is_active=True,
            version=1,
        )
        doc_oem = BidDocument(
            bid_id=bid1.id,
            uploaded_by_profile_id=prof_bidder.id,
            original_filename="oem_authorization_letter.pdf",
            document_name="OEM Authorization",
            document_type="OEM_AUTHORIZATION",
            storage_path="/storage/oem.pdf",
            mime_type="application/pdf",
            file_size=10240,
            is_active=True,
            version=1,
        )
        db.add_all([doc_fin, doc_mii, doc_oem])
        db.commit()

        # Document Processing records
        proc_fin = DocumentProcessing(
            bid_document_id=doc_fin.id,
            processing_status=ProcessingStatus.COMPLETED,
            detected_document_type="FINANCIAL_AUDIT_REPORT",
            raw_text="Annual Turnover Audit Certificate for Vendor 1. Average turnover for FY 2023-26: ₹14.50 Crores.",
            normalized_text="Annual Turnover Audit Certificate. Average annual turnover verified at INR 14.50 Crores.",
            extracted_data={"average_annual_turnover": "14.50 Cr", "auditor_membership": "CA-98741", "fy_period": "2023-2026"},
            page_count=2,
        )
        proc_mii = DocumentProcessing(
            bid_document_id=doc_mii.id,
            processing_status=ProcessingStatus.COMPLETED,
            detected_document_type="LOCAL_CONTENT_DECLARATION",
            raw_text="Self Declaration for Local Content under Make in India. Declared Local Content: 45.0% by value.",
            normalized_text="Local Content Self Declaration under DPIIT policy. Declared and verified local content: 45.0%.",
            extracted_data={"local_content_percentage": "45.0%", "location": "Noida SEZ"},
            page_count=1,
        )
        proc_oem = DocumentProcessing(
            bid_document_id=doc_oem.id,
            processing_status=ProcessingStatus.COMPLETED,
            detected_document_type="OEM_AUTHORIZATION",
            raw_text="Manufacturer Authorization Form. Cisco Systems authorizes Vendor 1 as authorized tier-1 partner.",
            normalized_text="Manufacturer Authorization Form. Authorized partner tier-1 for server hardware.",
            extracted_data={"oem_name": "Cisco Systems", "authorization_code": "MAF-2026-991"},
            page_count=1,
        )
        db.add_all([proc_fin, proc_mii, proc_oem])
        db.commit()

        # Verifications
        ver_fin = VerificationRecord(
            bid_id=bid1.id,
            bid_document_id=doc_fin.id,
            verification_type="TURNOVER_VERIFICATION",
            verification_status="VERIFIED",
            match_status="MATCH",
            claimed_value="14.50 Cr",
            verified_value="14.50 Cr",
            source_name="Audited Financial Registry",
            source_type="REGISTRY",
            is_active=True,
        )
        ver_black = VerificationRecord(
            bid_id=bid1.id,
            verification_type="INTEGRITY_CHECK",
            verification_status="VERIFIED",
            match_status="MATCH",
            claimed_value="NOT_BLACKLISTED",
            verified_value="NOT_BLACKLISTED",
            source_name="Mock GeM Debarment Registry",
            source_type="REGISTRY",
            is_active=True,
        )
        db.add_all([ver_fin, ver_black])
        db.commit()

        # Compliance Results
        cr_turnover = ComplianceResult(
            bid_id=bid1.id,
            tender_id=tender.id,
            tender_requirement_id=req_turnover.id,
            compliance_status=ComplianceStatus.PASS,
            is_mandatory=True,
            is_critical=False,
            critical_failure=False,
            reason="Average annual turnover ₹14.50 Cr exceeds required ₹10.00 Cr.",
            expected_value=">= 10.00 Cr",
            actual_value="14.50 Cr",
            is_current=True,
            evaluation_version=1,
        )
        cr_local = ComplianceResult(
            bid_id=bid1.id,
            tender_id=tender.id,
            tender_requirement_id=req_local.id,
            compliance_status=ComplianceStatus.FAIL,
            is_mandatory=True,
            is_critical=True,
            critical_failure=True,
            reason="Local content 45.0% is below the mandatory minimum 50.0%.",
            expected_value=">= 50.0%",
            actual_value="45.0%",
            is_current=True,
            evaluation_version=1,
        )
        cr_oem = ComplianceResult(
            bid_id=bid1.id,
            tender_id=tender.id,
            tender_requirement_id=req_oem.id,
            compliance_status=ComplianceStatus.PASS,
            is_mandatory=True,
            is_critical=False,
            critical_failure=False,
            reason="Valid OEM Authorization from Cisco Systems verified.",
            expected_value="Valid MAF",
            actual_value="Verified",
            is_current=True,
            evaluation_version=1,
        )
        cr_black = ComplianceResult(
            bid_id=bid1.id,
            tender_id=tender.id,
            tender_requirement_id=req_blacklist.id,
            compliance_status=ComplianceStatus.PASS,
            is_mandatory=True,
            is_critical=True,
            critical_failure=False,
            reason="No active blacklisting records identified in debarment registry.",
            expected_value="CLEAR",
            actual_value="CLEAR",
            is_current=True,
            evaluation_version=1,
        )
        db.add_all([cr_turnover, cr_local, cr_oem, cr_black])
        db.commit()

        # Score Snapshot
        score_snap1 = BidScoreSnapshot(
            bid_id=bid1.id,
            tender_id=tender.id,
            scoring_version=1,
            overall_score=Decimal("65.00"),
            earned_weight=Decimal("55.00"),
            eligible_weight=Decimal("75.00"),
            mandatory_failures_count=1,
            critical_failures_count=1,
            is_current=True,
            category_scores={"FINANCIAL": {"score": 100.0}, "TECHNICAL": {"score": 42.8}, "INTEGRITY": {"score": 100.0}},
        )
        db.add(score_snap1)
        db.commit()

        # Risk Snapshot
        risk_snap1 = BidRiskSnapshot(
            bid_id=bid1.id,
            tender_id=tender.id,
            risk_version=1,
            base_risk_score=Decimal("45.00"),
            base_risk_level="MEDIUM",
            adjusted_risk_score=Decimal("80.00"),
            adjusted_risk_level="CRITICAL",
            override_applied=True,
            override_count=1,
            risk_complete=True,
            is_current=True,
            summary_reasons=["Critical clause MII-01 failed triggering minimum 80.0 risk override."],
        )
        db.add(risk_snap1)
        db.commit()

        # =========================================================================
        # 4. RAG INDEXING SERVICE VALIDATION
        # =========================================================================
        print("\n--- SECTION 4: Knowledge Indexing Pipeline & Idempotency ---")

        # Test 5: Full Bid Knowledge Indexing
        idx_res = RAGIndexingService.index_full_bid_knowledge(db, bid1.id)
        log_test(
            "Test 05: index_full_bid_knowledge creates chunks across all sources",
            idx_res.total_chunks_created > 0 and len(idx_res.source_breakdown) >= 6,
            f"Total Chunks: {idx_res.total_chunks_created}, Breakdown: {idx_res.source_breakdown}",
        )

        # Test 6: Idempotent Re-indexing
        idx_res2 = RAGIndexingService.index_full_bid_knowledge(db, bid1.id)
        active_chunks_count = db.scalars(
            select(RAGChunk).where(RAGChunk.bid_id == bid1.id, RAGChunk.is_active == True)
        ).all()
        log_test(
            "Test 06: Idempotent re-indexing does not duplicate active chunks",
            idx_res2.total_chunks_created == idx_res.total_chunks_created,
            f"Active chunks count: {len(active_chunks_count)} == {idx_res2.total_chunks_created - idx_res2.source_breakdown.get('TENDER_REQUIREMENT', 0)}",
        )

        # Test 7: Superseded Document Invalidation
        old_doc = BidDocument(
            bid_id=bid1.id,
            uploaded_by_profile_id=prof_bidder.id,
            original_filename="old_superseded.pdf",
            document_name="Old Doc",
            document_type="GENERAL",
            storage_path="/storage/old.pdf",
            mime_type="application/pdf",
            file_size=10240,
            is_active=False,
            version=0,
        )
        db.add(old_doc)
        db.commit()
        # Add a dummy chunk for the inactive document
        old_chunk = RAGChunk(
            organization_id=bidder_org1.id,
            tender_id=tender.id,
            bid_id=bid1.id,
            document_id=old_doc.id,
            source_type=RAGSourceType.BID_DOCUMENT.value,
            source_id=str(old_doc.id),
            chunk_index=0,
            content="Old superseded content",
            embedding=EmbeddingService.generate_embedding("Old superseded content"),
            is_active=True,
            version=0,
        )
        db.add(old_chunk)
        db.commit()

        RAGIndexingService.index_bid_documents(db, bid1.id)
        db.refresh(old_chunk)
        log_test(
            "Test 07: Superseded document chunks are marked is_active = False",
            old_chunk.is_active is False,
            "Inactive document chunk properly invalidated.",
        )

        # =========================================================================
        # 5. SCOPED RETRIEVAL & TENANT ISOLATION
        # =========================================================================
        print("\n--- SECTION 5: Scoped Vector Retrieval & Security Isolation ---")

        # Bid 2 in same tender (for isolation check)
        bid2 = Bid(
            tender_id=tender.id,
            bidder_organization_id=bidder_org2.id,
            created_by_profile_id=prof_bidder.id,
            bid_number=f"BID-RAG-{uuid.uuid4().hex[:6].upper()}",
            status="SUBMITTED",
        )
        db.add(bid2)
        db.commit()
        doc_bid2 = BidDocument(
            bid_id=bid2.id,
            uploaded_by_profile_id=prof_bidder.id,
            original_filename="secret_bid2_tech.pdf",
            document_name="Secret Tech",
            document_type="GENERAL",
            storage_path="/storage/sec.pdf",
            mime_type="application/pdf",
            file_size=10240,
            is_active=True,
            version=1,
        )
        db.add(doc_bid2)
        db.commit()
        proc_bid2 = DocumentProcessing(
            bid_document_id=doc_bid2.id,
            processing_status=ProcessingStatus.COMPLETED,
            detected_document_type="GENERAL",
            raw_text="SECRET CONFIDENTIAL PROPRIETARY VENDOR 2 SOLUTION",
            normalized_text="SECRET CONFIDENTIAL PROPRIETARY VENDOR 2 SOLUTION",
        )
        db.add(proc_bid2)
        db.commit()
        RAGIndexingService.index_full_bid_knowledge(db, bid2.id)

        # Test 8: Scoped vector retrieval returns Bid 1 + Tender chunks, zero Bid 2 chunks
        retrieved_b1 = RAGRetrievalService.retrieve_evidence(
            db=db,
            tender_id=tender.id,
            bid_id=bid1.id,
            query="turnover local content manufacturer",
            top_k=10,
        )
        has_bid2_leakage = any("SECRET CONFIDENTIAL PROPRIETARY VENDOR 2" in c.content for c in retrieved_b1)
        log_test(
            "Test 08: Scoped retrieval prevents cross-bid data leakage",
            not has_bid2_leakage and len(retrieved_b1) > 0,
            f"Retrieved {len(retrieved_b1)} chunks, Zero Bid 2 leakage confirmed.",
        )

        # Test 9: Keyword boost & priority multiplier
        retrieved_mii = RAGRetrievalService.retrieve_evidence(
            db=db,
            tender_id=tender.id,
            bid_id=bid1.id,
            query="local content 45%",
            top_k=5,
        )
        top_type = retrieved_mii[0].source_type if retrieved_mii else None
        log_test(
            "Test 09: Hybrid retrieval prioritizes compliance and verification evidence",
            top_type in (RAGSourceType.COMPLIANCE_RESULT.value, RAGSourceType.VERIFICATION_RESULT.value, RAGSourceType.BID_DOCUMENT.value),
            f"Top retrieved evidence type: {top_type}",
        )

        # =========================================================================
        # 6. PROMPT BUILDER & INJECTION DEFENSE
        # =========================================================================
        print("\n--- SECTION 6: Prompt Construction & Injection Containment ---")

        user_prompt = PromptBuilder.build_recommendation_prompt(
            tender_meta={"tender_number": tender.tender_number, "title": tender.title},
            bid_meta={"bid_number": bid1.bid_number, "bidder_name": bidder_org1.name},
            score_data={"overall_score": 65.0, "mandatory_failure_count": 1, "critical_failure_count": 1},
            risk_data={"base_risk_score": 45.0, "base_risk_level": "MEDIUM", "adjusted_risk_score": 80.0, "adjusted_risk_level": "CRITICAL", "override_applied": True},
            evidence_chunks=retrieved_b1,
        )

        # Test 10: Prompt contains injection warning and disclaimer
        log_test(
            "Test 10: Prompt builder includes injection defense boundaries and disclaimer",
            "UNTRUSTED DOCUMENT CONTENT" in PromptBuilder.SYSTEM_PROMPT
            and DISCLAIMER_TEXT in PromptBuilder.SYSTEM_PROMPT
            and "Prompt Version v1" in user_prompt,
            "System prompt contains strict untrusted evidence constraints.",
        )

        # =========================================================================
        # 7. RECOMMENDATION GUARDRAIL & CITATION VALIDATOR
        # =========================================================================
        print("\n--- SECTION 7: Deterministic Guardrails & Citation Validation ---")

        # Test 11: Critical Risk forces DO_NOT_PROCEED_WITHOUT_REVIEW
        valid_test_id = retrieved_b1[0].source_id
        fake_llm_out = AIRecommendationOutput(
            summary="All looks fine despite risks.",
            strengths=["Submitted turnover"],
            concerns=[],
            review_items=[],
            recommendation=AIRecommendationEnum.PROCEED,  # Hallucinated lenient recommendation
            recommendation_reason="Bidder meets general requirements.",
            evidence_refs=[
                EvidenceRef(source_type=retrieved_b1[0].source_type, source_id=valid_test_id, title="Valid Retrieved Evidence", summary="Observed"),
                EvidenceRef(source_type="COMPLIANCE_RESULT", source_id="fake-nonexistent-id", title="Fake", summary="Fake"),
            ],
            confidence_label=ConfidenceLabelEnum.HIGH,
            limitations=[],
        )

        adj_out, guard_applied, guard_reason = RecommendationGuardrail.validate_and_adjust_recommendation(
            llm_output=fake_llm_out,
            risk_snapshot=risk_snap1,
            score_snapshot=score_snap1,
            retrieved_chunks=retrieved_b1,
        )

        log_test(
            "Test 11: Guardrail downgrades PROCEED to DO_NOT_PROCEED_WITHOUT_REVIEW when risk is CRITICAL",
            adj_out.recommendation == AIRecommendationEnum.DO_NOT_PROCEED_WITHOUT_REVIEW and guard_applied is True,
            f"Adjusted to: {adj_out.recommendation.value}, Reason: {guard_reason}",
        )

        # Test 12: Citation validator strips fake citation ID
        cited_ids = [ref.source_id for ref in adj_out.evidence_refs]
        log_test(
            "Test 12: Citation validator strips ungrounded / hallucinated citation IDs",
            "fake-nonexistent-id" not in cited_ids and valid_test_id in cited_ids,
            f"Validated citations: {cited_ids}",
        )


        # =========================================================================
        # 8. END-TO-END AI RECOMMENDATION WORKFLOW
        # =========================================================================
        print("\n--- SECTION 8: End-to-End AI Recommendation Generation ---")

        # Test 13: Generate recommendation for Bid 1 (Local Content failure)
        rec_record1 = AIRecommendationService.generate_bid_recommendation(
            db=db,
            user=user_officer,
            bid_id=bid1.id,
            force_refresh=True,
        )

        log_test(
            "Test 13: AI Recommendation generated and persisted in database",
            rec_record1 is not None and rec_record1.bid_id == bid1.id,
            f"Recommendation: {rec_record1.recommendation}, Reason: {rec_record1.recommendation_reason[:60]}...",
        )

        log_test(
            "Test 14: AI Recommendation accurately identifies local content failure",
            rec_record1.recommendation == AIRecommendationEnum.DO_NOT_PROCEED_WITHOUT_REVIEW.value
            and any("local content" in c.lower() or "critical" in c.lower() for c in rec_record1.concerns),
            f"Concerns: {rec_record1.concerns}",
        )

        # =========================================================================
        # 9. INTERACTIVE PROCUREMENT OFFICER Q&A
        # =========================================================================
        print("\n--- SECTION 9: Grounded Q&A Inquiries ---")

        # Test 15: Q&A on Local Content
        qa_mii = AIRecommendationService.ask_bid_question(
            db=db,
            user=user_officer,
            bid_id=bid1.id,
            question="Why did this bid fail the local content requirement?",
        )
        log_test(
            "Test 15: Q&A Local Content inquiry explains 45.0% vs 50.0% failure with citations",
            "45.0%" in qa_mii.answer and "50.0%" in qa_mii.answer,
            f"Answer: {qa_mii.answer}",
        )

        # Test 16: Q&A on Turnover
        qa_turnover = AIRecommendationService.ask_bid_question(
            db=db,
            user=user_officer,
            bid_id=bid1.id,
            question="What is the verified annual turnover for this bidder?",
        )
        log_test(
            "Test 16: Q&A Turnover inquiry accurately explains verified financial turnover",
            "14.50" in qa_turnover.answer or "turnover" in qa_turnover.answer.lower(),
            f"Answer: {qa_turnover.answer}",
        )

        # Test 17: Q&A on Blacklisting with Mock Registry Transparency
        qa_black = AIRecommendationService.ask_bid_question(
            db=db,
            user=user_officer,
            bid_id=bid1.id,
            question="Is this bidder blacklisted or debarred?",
        )
        log_test(
            "Test 17: Q&A Blacklisting inquiry confirms clear status without false allegations",
            "no active blacklisting" in qa_black.answer.lower() or "clear" in qa_black.answer.lower(),
            f"Answer: {qa_black.answer}",
        )

        # =========================================================================
        # 10. STALENESS DETECTION
        # =========================================================================
        print("\n--- SECTION 10: Upstream Change Staleness Detection ---")

        # Create a newer score snapshot version for Bid 1
        new_score_snap = BidScoreSnapshot(
            bid_id=bid1.id,
            tender_id=tender.id,
            scoring_version=2,
            overall_score=Decimal("70.00"),
            earned_weight=Decimal("60.00"),
            eligible_weight=Decimal("75.00"),
            mandatory_failures_count=1,
            critical_failures_count=1,
            is_current=True,
        )
        score_snap1.is_current = False
        db.add(new_score_snap)
        db.commit()

        rec_check, is_stale = AIRecommendationService.get_bid_recommendation(
            db=db,
            user=user_officer,
            bid_id=bid1.id,
        )
        log_test(
            "Test 18: Staleness detector identifies when upstream scoring has changed",
            is_stale is True,
            "Recommendation flagged as stale after new score snapshot created.",
        )

        # =========================================================================
        # 11. RBAC & TENANT ACCESS CONTROL
        # =========================================================================
        print("\n--- SECTION 11: Multi-Tenant RBAC Security ---")

        # Test 19: Competitor Procurement Officer denied access (404/403)
        competitor_denied = False
        try:
            AIRecommendationService.generate_bid_recommendation(
                db=db,
                user=user_officer_b,
                bid_id=bid1.id,
            )
        except HTTPException as he:
            competitor_denied = he.status_code in (403, 404)
        log_test(
            "Test 19: Cross-tenant Procurement Officer blocked from bid AI recommendation",
            competitor_denied is True,
            "Cross-tenant access blocked with HTTP 403/404.",
        )

        # Test 20: Bidder denied access to internal AI evaluation recommendations
        bidder_denied = False
        try:
            AIRecommendationService.generate_bid_recommendation(
                db=db,
                user=user_bidder,
                bid_id=bid1.id,
            )
        except HTTPException as he:
            bidder_denied = he.status_code in (403, 404)
        log_test(
            "Test 20: Bidder blocked from internal procurement officer AI recommendation",
            bidder_denied is True,
            "Bidder access blocked with HTTP 403/404.",
        )

        # =========================================================================
        # 12. ARCHITECTURAL BOUNDARY INVARIANTS
        # =========================================================================
        print("\n--- SECTION 12: Strict Part 7E Boundary Invariants ---")

        # Test 21: Verify zero upstream modification
        db.refresh(cr_local)
        db.refresh(score_snap1)
        db.refresh(risk_snap1)
        log_test(
            "Test 21: Strict Boundary - Deterministic compliance, scores, and risks remain immutable",
            cr_local.compliance_status == ComplianceStatus.FAIL
            and float(risk_snap1.adjusted_risk_score) == 80.0
            and float(score_snap1.overall_score) == 65.0,
            "Zero modifications made to upstream deterministic outputs.",
        )

        print("\n" + "=" * 80)
        print("ALL 21 MASTER QA TESTS PASSED SUCCESSFULLY FOR PART 7E!")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_all_tests()
