"""
RAG Indexing Service for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
Converts procurement requirements, documents, extractions, verifications, compliance rules,
scores, and risk findings into searchable dense vector embeddings stored in pgvector.
"""

import json
import logging
import uuid
from typing import Dict, List, Optional
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.compliance_result import ComplianceResult
from app.db.models.document_processing import DocumentProcessing, ProcessingStatus
from app.db.models.rag_chunk import RAGChunk
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.verification_record import VerificationRecord
from app.services.ai.ai_config import RAGSourceType
from app.services.ai.ai_models import RAGIndexResult
from app.services.ai.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RAGIndexingService:
    """
    Orchestrates the ingestion, chunking, embedding, and idempotent storage
    of multi-source procurement knowledge into the `rag_chunks` pgvector table.
    """

    @classmethod
    def index_full_bid_knowledge(cls, db: Session, bid_id: uuid.UUID) -> RAGIndexResult:
        """
        Orchestrates full idempotent indexing of all active evidence for a specific Bid submission.
        """
        bid = db.get(Bid, bid_id)
        if not bid:
            raise ValueError(f"Bid {bid_id} not found.")

        breakdown: Dict[str, int] = {}

        # 1. Tender Requirements
        breakdown[RAGSourceType.TENDER_REQUIREMENT.value] = cls.index_tender_requirements(db, bid.tender_id)

        # 2. Bid Documents & OCR text
        breakdown[RAGSourceType.BID_DOCUMENT.value] = cls.index_bid_documents(db, bid.id)

        # 3. Structured Extractions
        breakdown[RAGSourceType.STRUCTURED_EXTRACTION.value] = cls.index_structured_extractions(db, bid.id)

        # 4. Verification Records
        breakdown[RAGSourceType.VERIFICATION_RESULT.value] = cls.index_verification_results(db, bid.id)

        # 5. Compliance Results
        breakdown[RAGSourceType.COMPLIANCE_RESULT.value] = cls.index_compliance_results(db, bid.id)

        # 6. Scoring & Risk Results
        score_risk_counts = cls.index_scoring_and_risk_results(db, bid.id)
        breakdown.update(score_risk_counts)

        total = sum(breakdown.values())
        logger.info(f"Indexed {total} RAG chunks for Bid {bid_id} across {len(breakdown)} domains.")

        return RAGIndexResult(
            tender_id=str(bid.tender_id),
            bid_id=str(bid.id),
            total_chunks_created=total,
            source_breakdown=breakdown,
        )

    @classmethod
    def index_tender_requirements(cls, db: Session, tender_id: uuid.UUID) -> int:
        """Indexes all active requirements for a Tender."""
        tender = db.get(Tender, tender_id)
        if not tender:
            return 0

        reqs = db.scalars(
            select(TenderRequirement).where(
                TenderRequirement.tender_id == tender_id,
                TenderRequirement.is_active == True,  # noqa: E712
            )
        ).all()

        # Idempotent cleanup for tender requirements
        db.execute(
            delete(RAGChunk).where(
                RAGChunk.tender_id == tender_id,
                RAGChunk.source_type == RAGSourceType.TENDER_REQUIREMENT.value,
                RAGChunk.bid_id == None,  # noqa: E711
            )
        )

        chunks_to_add: List[RAGChunk] = []
        for req in reqs:
            content = (
                f"Tender Requirement: {req.name}\n"
                f"Rule Code: {req.code}\n"
                f"Category: {req.category}\n"
                f"Mandatory: {'Yes' if req.is_mandatory else 'No'}\n"
                f"Critical: {'Yes' if req.is_critical else 'No'}\n"
                f"Evaluation Weight: {req.weight or 10.0}\n"
                f"Clause Description: {req.description or 'No additional description provided.'}"
            )
            emb = EmbeddingService.generate_embedding(content)
            chunk = RAGChunk(
                organization_id=tender.organization_id,
                tender_id=tender.id,
                bid_id=None,
                source_type=RAGSourceType.TENDER_REQUIREMENT.value,
                source_id=str(req.id),
                chunk_index=0,
                content=content,
                embedding=emb,
                metadata_json={
                    "requirement_id": str(req.id),
                    "requirement_code": req.code,
                    "requirement_name": req.name,
                    "category": req.category,
                    "is_mandatory": req.is_mandatory,
                    "is_critical": req.is_critical,
                },
                is_active=True,
                version=1,
            )
            chunks_to_add.append(chunk)

        if chunks_to_add:
            db.add_all(chunks_to_add)
            db.commit()

        return len(chunks_to_add)

    @classmethod
    def index_bid_documents(cls, db: Session, bid_id: uuid.UUID) -> int:
        """Indexes OCR and normalized text from all active BidDocuments."""
        bid = db.get(Bid, bid_id)
        if not bid:
            return 0

        # Handle superseded/inactive documents: deactivate old chunks
        inactive_docs = db.scalars(
            select(BidDocument).where(
                BidDocument.bid_id == bid_id,
                BidDocument.is_active == False,  # noqa: E712
            )
        ).all()
        for idoc in inactive_docs:
            db.execute(
                update(RAGChunk)
                .where(
                    RAGChunk.bid_id == bid_id,
                    RAGChunk.document_id == idoc.id,
                )
                .values(is_active=False)
            )

        # Clear existing active bid document chunks to ensure idempotency
        db.execute(
            delete(RAGChunk).where(
                RAGChunk.bid_id == bid_id,
                RAGChunk.source_type == RAGSourceType.BID_DOCUMENT.value,
                RAGChunk.is_active == True,  # noqa: E712
            )
        )

        active_docs = db.scalars(
            select(BidDocument).where(
                BidDocument.bid_id == bid_id,
                BidDocument.is_active == True,  # noqa: E712
            )
        ).all()

        chunks_to_add: List[RAGChunk] = []
        for doc in active_docs:
            proc = db.scalars(
                select(DocumentProcessing).where(
                    DocumentProcessing.bid_document_id == doc.id,
                    DocumentProcessing.processing_status == ProcessingStatus.COMPLETED,
                )
            ).first()

            if not proc or not (proc.normalized_text or proc.raw_text):
                continue

            full_text = proc.normalized_text or proc.raw_text or ""
            # Paragraph / page chunking
            paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
            if not paragraphs:
                paragraphs = [full_text]

            doc_name = getattr(doc, "original_filename", getattr(doc, "document_name", getattr(doc, "file_name", "document.pdf")))
            doc_type = getattr(proc, "detected_document_type", getattr(proc, "document_type", "General"))
            for idx, p_text in enumerate(paragraphs[:10]):  # Limit to top 10 substantial chunks per doc
                content = (
                    f"Bid Document: {doc_name}\n"
                    f"Document Classification: {doc_type}\n"
                    f"Document ID: {doc.id}\n"
                    f"Excerpt [Chunk {idx + 1}]:\n{p_text}"
                )
                emb = EmbeddingService.generate_embedding(content)
                chunk = RAGChunk(
                    organization_id=bid.bidder_organization_id,
                    tender_id=bid.tender_id,
                    bid_id=bid.id,
                    document_id=doc.id,
                    source_type=RAGSourceType.BID_DOCUMENT.value,
                    source_id=str(doc.id),
                    chunk_index=idx,
                    content=content,
                    embedding=emb,
                    metadata_json={
                        "document_id": str(doc.id),
                        "file_name": doc_name,
                        "document_type": doc_type,
                        "page_count": proc.page_count,
                        "chunk_index": idx,
                    },
                    is_active=True,
                    version=doc.version,
                )
                chunks_to_add.append(chunk)

        if chunks_to_add:
            db.add_all(chunks_to_add)
            db.commit()

        return len(chunks_to_add)

    @classmethod
    def index_structured_extractions(cls, db: Session, bid_id: uuid.UUID) -> int:
        """Indexes key-value structured entities extracted from BidDocuments."""
        bid = db.get(Bid, bid_id)
        if not bid:
            return 0

        db.execute(
            delete(RAGChunk).where(
                RAGChunk.bid_id == bid_id,
                RAGChunk.source_type == RAGSourceType.STRUCTURED_EXTRACTION.value,
            )
        )

        active_docs = db.scalars(
            select(BidDocument).where(
                BidDocument.bid_id == bid_id,
                BidDocument.is_active == True,  # noqa: E712
            )
        ).all()

        chunks_to_add: List[RAGChunk] = []
        for doc in active_docs:
            proc = db.scalars(
                select(DocumentProcessing).where(
                    DocumentProcessing.bid_document_id == doc.id,
                    DocumentProcessing.processing_status == ProcessingStatus.COMPLETED,
                )
            ).first()

            extracted = proc.extracted_data if (proc and proc.extracted_data) else (getattr(proc, "structured_fields", None) if proc else None)
            if not proc or not extracted:
                continue

            doc_name = getattr(doc, "original_filename", getattr(doc, "document_name", getattr(doc, "file_name", "document.pdf")))
            doc_type = getattr(proc, "detected_document_type", getattr(proc, "document_type", "General"))
            fields_text = "\n".join(f"• {k}: {v}" for k, v in extracted.items())
            content = (
                f"Structured Entity Extraction\n"
                f"Source Document: {doc_name} ({doc_type})\n"
                f"Extracted Verified Entities:\n{fields_text}"
            )
            emb = EmbeddingService.generate_embedding(content)
            chunk = RAGChunk(
                organization_id=bid.bidder_organization_id,
                tender_id=bid.tender_id,
                bid_id=bid.id,
                document_id=doc.id,
                source_type=RAGSourceType.STRUCTURED_EXTRACTION.value,
                source_id=str(doc.id),
                chunk_index=0,
                content=content,
                embedding=emb,
                metadata_json={
                    "document_id": str(doc.id),
                    "file_name": doc_name,
                    "fields_count": len(extracted),
                },
                is_active=True,
                version=doc.version,
            )

            chunks_to_add.append(chunk)



        if chunks_to_add:
            db.add_all(chunks_to_add)
            db.commit()

        return len(chunks_to_add)

    @classmethod
    def index_verification_results(cls, db: Session, bid_id: uuid.UUID) -> int:
        """Indexes external and cross-document verification records."""
        bid = db.get(Bid, bid_id)
        if not bid:
            return 0

        db.execute(
            delete(RAGChunk).where(
                RAGChunk.bid_id == bid_id,
                RAGChunk.source_type == RAGSourceType.VERIFICATION_RESULT.value,
            )
        )

        verifications = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_id == bid_id,
                VerificationRecord.is_active == True,  # noqa: E712
            )
        ).all()

        chunks_to_add: List[RAGChunk] = []
        for v in verifications:
            v_type = getattr(v, "verification_type", getattr(v, "claim_type", "GENERAL"))
            v_status = getattr(v, "verification_status", getattr(v, "status", "VERIFIED"))
            v_match = getattr(v, "match_status", "MATCH")
            s_name = getattr(v, "source_name", "Registry")
            s_type = getattr(v, "source_type", "REGISTRY")

            source_notice = (
                f"Source: {s_name} ({s_type})"
                if "mock" not in (s_name or "").lower()
                else f"Source: {s_name} (Simulated Mock Registry)"
            )
            content = (
                f"Verification Record: {v_type}\n"
                f"Verification Status: {v_status} (Match: {v_match})\n"
                f"Claimed Value: {v.claimed_value or 'N/A'}\n"
                f"Verified Value: {v.verified_value or 'N/A'}\n"
                f"Confidence Score: {v.confidence or 1.0}\n"
                f"{source_notice}\n"
                f"Audit Details: {json.dumps(v.evidence or {})}"
            )
            emb = EmbeddingService.generate_embedding(content)
            chunk = RAGChunk(
                organization_id=bid.bidder_organization_id,
                tender_id=bid.tender_id,
                bid_id=bid.id,
                document_id=v.bid_document_id,
                source_type=RAGSourceType.VERIFICATION_RESULT.value,
                source_id=str(v.id),
                chunk_index=0,
                content=content,
                embedding=emb,
                metadata_json={
                    "verification_id": str(v.id),
                    "claim_type": v_type,
                    "status": v_status,
                    "match_status": v_match,
                    "source_name": s_name,
                },
                is_active=True,
                version=1,
            )
            chunks_to_add.append(chunk)

        if chunks_to_add:
            db.add_all(chunks_to_add)
            db.commit()


        return len(chunks_to_add)

    @classmethod
    def index_compliance_results(cls, db: Session, bid_id: uuid.UUID) -> int:
        """Indexes deterministic rule compliance findings."""
        bid = db.get(Bid, bid_id)
        if not bid:
            return 0

        db.execute(
            delete(RAGChunk).where(
                RAGChunk.bid_id == bid_id,
                RAGChunk.source_type == RAGSourceType.COMPLIANCE_RESULT.value,
            )
        )

        results = db.scalars(
            select(ComplianceResult).where(
                ComplianceResult.bid_id == bid_id,
                ComplianceResult.is_current == True,  # noqa: E712
            )
        ).all()

        chunks_to_add: List[RAGChunk] = []
        for cr in results:
            req = db.get(TenderRequirement, cr.tender_requirement_id)
            req_code = req.code if req else "REQ"
            req_name = req.name if req else "Requirement"
            category = req.category if req else "GENERAL"

            content = (
                f"Compliance Rule Evaluation: {req_name} (Rule: {req_code})\n"
                f"Category: {category}\n"
                f"Compliance Determination: {cr.compliance_status}\n"
                f"Mandatory Clause: {'Yes' if cr.is_mandatory else 'No'}\n"
                f"Critical Clause: {'Yes' if getattr(cr, 'is_critical', False) else 'No'}\n"
                f"Critical Failure Triggered: {'Yes' if getattr(cr, 'critical_failure', False) else 'No'}\n"
                f"Required Condition: {cr.expected_value or 'Met'}\n"
                f"Actual Observed Evidence: {cr.actual_value or 'Submitted'}\n"
                f"Compliance Reason: {cr.reason or 'Evaluated based on submitted evidence.'}"
            )
            emb = EmbeddingService.generate_embedding(content)
            chunk = RAGChunk(
                organization_id=bid.bidder_organization_id,
                tender_id=bid.tender_id,
                bid_id=bid.id,
                source_type=RAGSourceType.COMPLIANCE_RESULT.value,
                source_id=str(cr.id),
                chunk_index=0,
                content=content,
                embedding=emb,
                metadata_json={
                    "compliance_result_id": str(cr.id),
                    "requirement_id": str(cr.tender_requirement_id),
                    "requirement_code": req_code,
                    "category": category,
                    "compliance_status": cr.compliance_status,
                    "is_mandatory": cr.is_mandatory,
                    "is_critical": getattr(cr, "is_critical", False),
                },
                is_active=True,
                version=cr.evaluation_version or 1,
            )
            chunks_to_add.append(chunk)

        if chunks_to_add:
            db.add_all(chunks_to_add)
            db.commit()

        return len(chunks_to_add)

    @classmethod
    def index_scoring_and_risk_results(cls, db: Session, bid_id: uuid.UUID) -> Dict[str, int]:
        """Indexes active score snapshots and deterministic risk assessments."""
        bid = db.get(Bid, bid_id)
        if not bid:
            return {}

        db.execute(
            delete(RAGChunk).where(
                RAGChunk.bid_id == bid_id,
                RAGChunk.source_type.in_([
                    RAGSourceType.SCORING_RESULT.value,
                    RAGSourceType.RISK_RESULT.value,
                ]),
            )
        )

        counts = {
            RAGSourceType.SCORING_RESULT.value: 0,
            RAGSourceType.RISK_RESULT.value: 0,
        }
        chunks_to_add: List[RAGChunk] = []

        # 1. Scoring Snapshot
        score_snap = db.scalars(
            select(BidScoreSnapshot).where(
                BidScoreSnapshot.bid_id == bid_id,
                BidScoreSnapshot.is_current == True,  # noqa: E712
            )
        ).first()
        if score_snap:
            cat_lines = []
            if score_snap.category_scores:
                for cat_code, cat_data in score_snap.category_scores.items():
                    c_score = cat_data.get("score")
                    cat_lines.append(f"  • {cat_code}: {c_score if c_score is not None else 'N/A'}%")

            score_ver = getattr(score_snap, "scoring_version", getattr(score_snap, "score_version", 1))
            mand_fails = getattr(score_snap, "mandatory_failures_count", getattr(score_snap, "mandatory_failure_count", 0))
            crit_fails = getattr(score_snap, "critical_failures_count", getattr(score_snap, "critical_failure_count", 0))

            score_content = (
                f"Overall Compliance Scoring Snapshot (v{score_ver})\n"
                f"Overall Compliance Score: {score_snap.overall_score}%\n"
                f"Earned Weight: {score_snap.earned_weight} / Eligible: {score_snap.eligible_weight}\n"
                f"Mandatory Failures: {mand_fails}\n"
                f"Critical Failures: {crit_fails}\n"
                f"Category Breakdown:\n" + ("\n".join(cat_lines) if cat_lines else "  • No categories computed")
            )
            emb = EmbeddingService.generate_embedding(score_content)
            chunk = RAGChunk(
                organization_id=bid.bidder_organization_id,
                tender_id=bid.tender_id,
                bid_id=bid.id,
                source_type=RAGSourceType.SCORING_RESULT.value,
                source_id=str(score_snap.id),
                chunk_index=0,
                content=score_content,
                embedding=emb,
                metadata_json={
                    "score_snapshot_id": str(score_snap.id),
                    "overall_score": float(score_snap.overall_score) if score_snap.overall_score is not None else None,
                    "version": score_ver,
                },
                is_active=True,
                version=score_ver,
            )

            chunks_to_add.append(chunk)
            counts[RAGSourceType.SCORING_RESULT.value] = 1

        # 2. Risk Snapshot
        risk_snap = db.scalars(
            select(BidRiskSnapshot).where(
                BidRiskSnapshot.bid_id == bid_id,
                BidRiskSnapshot.is_current == True,  # noqa: E712
            )
        ).first()
        if risk_snap:
            reasons_text = "\n".join(f"  • {r}" for r in (risk_snap.summary_reasons or []))
            risk_content = (
                f"Deterministic Risk Assessment (v{risk_snap.risk_version})\n"
                f"Base Mathematical Risk: {risk_snap.base_risk_score}/100 ({risk_snap.base_risk_level})\n"
                f"Adjusted Risk Score: {risk_snap.adjusted_risk_score}/100 ({risk_snap.adjusted_risk_level})\n"
                f"Critical Overrides Applied: {'Yes' if risk_snap.override_applied else 'No'} ({risk_snap.override_count} overrides)\n"
                f"Assessment Complete: {'Yes' if risk_snap.risk_complete else 'No (Provisional)'}\n"
                f"Audit Findings & Reasons:\n{reasons_text if reasons_text else '  • No specific risk escalations'}"
            )
            emb = EmbeddingService.generate_embedding(risk_content)
            chunk = RAGChunk(
                organization_id=bid.bidder_organization_id,
                tender_id=bid.tender_id,
                bid_id=bid.id,
                source_type=RAGSourceType.RISK_RESULT.value,
                source_id=str(risk_snap.id),
                chunk_index=0,
                content=risk_content,
                embedding=emb,
                metadata_json={
                    "risk_snapshot_id": str(risk_snap.id),
                    "base_risk_score": float(risk_snap.base_risk_score) if risk_snap.base_risk_score is not None else None,
                    "adjusted_risk_score": float(risk_snap.adjusted_risk_score) if risk_snap.adjusted_risk_score is not None else None,
                    "adjusted_risk_level": risk_snap.adjusted_risk_level,
                    "override_applied": risk_snap.override_applied,
                },
                is_active=True,
                version=risk_snap.risk_version,
            )
            chunks_to_add.append(chunk)
            counts[RAGSourceType.RISK_RESULT.value] = 1

        if chunks_to_add:
            db.add_all(chunks_to_add)
            db.commit()

        return counts
