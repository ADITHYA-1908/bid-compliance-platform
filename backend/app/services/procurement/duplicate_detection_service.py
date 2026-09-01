"""
Duplicate / Reuse Document Detection Service for Part 10
Implements multi-signal comparison (File SHA-256 hash, Normalized content hash,
Structured field matching, and Text similarity) across cross-bidder document submissions for a Tender.
"""

import hashlib
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.models.audit_event import (
    AuditActorSource,
    AuditEventType,
    AuditEntityType,
)
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_duplicate_match import (
    DocumentDuplicateMatch,
    DuplicateMatchStatus,
    DuplicateMatchType,
)
from app.db.models.document_processing import (
    DocumentProcessing,
    ProcessingStage,
    ProcessingStatus,
)
from app.db.models.human_review import (
    HumanReviewItem,
    ReviewResolution,
    ReviewSeverity,
    ReviewStatus,
    ReviewType,
)
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.user import User
from app.schemas.audit import RecordAuditEventDTO
from app.schemas.duplicate_detection import (
    DocumentComparisonMeta,
    DuplicateMatchDetailResponse,
    DuplicateMatchListItemResponse,
    DuplicateMatchListResponse,
    DuplicateMatchSummaryCounts,
    DuplicateReviewRequest,
    DuplicateReviewResponse,
    DuplicateScanResponse,
    MatchedFieldDetail,
)
from app.services.ai.embedding_service import EmbeddingService
from app.services.audit.audit_service import AuditService

logger = logging.getLogger(__name__)


# Structured field comparison weights
STRUCTURED_FIELD_WEIGHTS: Dict[str, Tuple[str, float]] = {
    "certificate_number": ("Certificate Number", 0.40),
    "document_number": ("Document Number", 0.40),
    "registration_number": ("Registration Number", 0.40),
    "gstin": ("GSTIN", 0.30),
    "pan": ("PAN", 0.30),
    "cin": ("CIN", 0.30),
    "udyam_number": ("Udyam Registration Number", 0.30),
    "oem_authorization_number": ("OEM Authorization Number", 0.35),
    "issuer": ("Issuing Authority", 0.15),
    "organization_name": ("Organization Name", 0.20),
    "entity_name": ("Entity Name", 0.20),
    "issue_date": ("Issue Date", 0.10),
    "expiry_date": ("Expiry Date", 0.10),
}


def _verify_procurement_access(
    db: Session,
    user: User,
    tender_id: uuid.UUID,
) -> Tuple[Profile, Tender]:
    """
    Enforces RBAC and multi-tenant isolation.
    Only Procurement Officers and Admins from the organization owning the tender may access duplicate scan data.
    """
    profile = db.scalars(
        select(Profile)
        .options(joinedload(Profile.role))
        .where(Profile.id == user.profile_id)
    ).first()

    if not profile or not profile.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user profile or role not found.",
        )

    role_name = (profile.role.name or "").upper()
    if role_name not in ["PROCUREMENT_OFFICER", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Procurement Officers and System Administrators.",
        )

    tender = db.scalars(
        select(Tender)
        .options(joinedload(Tender.organization))
        .where(Tender.id == tender_id, Tender.is_active == True)
    ).first()

    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found.",
        )

    if role_name != "ADMIN" and tender.organization_id != profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found or does not belong to your organization.",
        )

    return profile, tender


class DuplicateDetectionService:
    """
    Core service coordinating multi-signal duplicate and reuse detection across bidder documents.
    """

    @classmethod
    def compute_file_hash(cls, content: bytes) -> str:
        """Computes secure SHA-256 hex digest for document file bytes."""
        return hashlib.sha256(content).hexdigest()

    @classmethod
    def compute_normalized_text_hash(cls, text: Optional[str]) -> Tuple[str, Optional[str]]:
        """
        Normalizes extracted text (lowercase, whitespace collapse, punctuation trim)
        and computes SHA-256 digest of the normalized representation.
        """
        if not text:
            return "", None

        # 1. Lowercase
        normalized = text.lower()
        # 2. Replace all non-alphanumeric characters with spaces
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        # 3. Collapse multiple whitespace and newlines to single space
        normalized = re.sub(r"\s+", " ", normalized).strip()

        if len(normalized) < 10:
            return normalized, None

        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return normalized, digest

    @classmethod
    def compare_structured_fields(
        cls,
        fields_a: Dict[str, Any],
        fields_b: Dict[str, Any],
    ) -> Tuple[float, List[MatchedFieldDetail], Dict[str, Any]]:
        """
        Performs weighted comparison on extracted structured fields (certificates, PAN, GSTIN, dates, etc.).
        Returns (match_score, matched_details, summary_dict).
        """
        if not fields_a or not fields_b:
            return 0.0, [], {}

        total_weight = 0.0
        matched_weight = 0.0
        matched_details: List[MatchedFieldDetail] = []
        summary_dict: Dict[str, Any] = {}

        for key, (label, weight) in STRUCTURED_FIELD_WEIGHTS.items():
            val_a_obj = fields_a.get(key)
            val_b_obj = fields_b.get(key)

            val_a = (val_a_obj.get("value") if isinstance(val_a_obj, dict) else str(val_a_obj or "")).strip().lower()
            val_b = (val_b_obj.get("value") if isinstance(val_b_obj, dict) else str(val_b_obj or "")).strip().lower()

            if val_a and val_b:
                total_weight += weight
                # Exact value match (ignoring case and leading/trailing whitespace)
                if val_a == val_b and len(val_a) > 2:
                    matched_weight += weight
                    matched_details.append(
                        MatchedFieldDetail(
                            field_key=key,
                            label=label,
                            value_a=val_a,
                            value_b=val_b,
                            is_exact_match=True,
                            weight=weight,
                        )
                    )
                    summary_dict[key] = {
                        "label": label,
                        "value": val_a,
                        "match": True,
                    }

        if total_weight == 0.0:
            return 0.0, [], {}

        match_score = round(min(1.0, matched_weight / max(total_weight, 0.40)), 3)
        return match_score, matched_details, summary_dict

    @classmethod
    def calculate_text_similarity(cls, text_a: Optional[str], text_b: Optional[str]) -> float:
        """
        Calculates cosine similarity or token overlap similarity between two extracted document texts.
        Reuses EmbeddingService for dense semantic vector comparison.
        """
        if not text_a or not text_b:
            return 0.0

        clean_a = re.sub(r"\s+", " ", text_a.lower()).strip()
        clean_b = re.sub(r"\s+", " ", text_b.lower()).strip()

        if clean_a == clean_b:
            return 1.0

        # Character trigram Jaccard baseline for high fidelity text comparison
        def get_trigrams(t: str) -> Set[str]:
            return {t[i : i + 3] for i in range(len(t) - 2)}

        tri_a = get_trigrams(clean_a[:3000])
        tri_b = get_trigrams(clean_b[:3000])

        if not tri_a or not tri_b:
            return 0.0

        jaccard = len(tri_a.intersection(tri_b)) / float(len(tri_a.union(tri_b)))

        # Also evaluate embedding cosine similarity on head content
        vec_a = EmbeddingService.generate_embedding(clean_a[:1000])
        vec_b = EmbeddingService.generate_embedding(clean_b[:1000])

        # Dot product of unit normalized vectors
        cos_sim = max(0.0, min(1.0, sum(a * b for a, b in zip(vec_a, vec_b))))

        # Weighted blend (70% trigram Jaccard + 30% dense embedding)
        similarity = round((0.70 * jaccard) + (0.30 * cos_sim), 3)
        return similarity

    @classmethod
    def evaluate_document_pair(
        cls,
        doc_a: BidDocument,
        doc_b: BidDocument,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates a pair of documents from two different bidders for duplicate/reuse signals.
        Returns match telemetry dictionary if a potential duplicate is detected, or None if benign.
        """
        proc_a = doc_a.processing
        proc_b = doc_b.processing

        file_hash_match = False
        content_hash_match = False
        structured_score = 0.0
        text_similarity = 0.0
        matched_field_details: List[MatchedFieldDetail] = []
        structured_summary: Dict[str, Any] = {}

        # 1. Exact File SHA-256 Match
        hash_a = doc_a.file_hash
        hash_b = doc_b.file_hash
        if hash_a and hash_b and hash_a == hash_b:
            file_hash_match = True

        # 2. Normalized Content SHA-256 Match
        norm_hash_a = proc_a.normalized_content_hash if proc_a else None
        norm_hash_b = proc_b.normalized_content_hash if proc_b else None
        if norm_hash_a and norm_hash_b and norm_hash_a == norm_hash_b:
            content_hash_match = True

        # 3. Structured Field Comparison
        fields_a = (proc_a.extracted_data or {}).get("fields", {}) if proc_a else {}
        fields_b = (proc_b.extracted_data or {}).get("fields", {}) if proc_b else {}
        if fields_a and fields_b:
            structured_score, matched_field_details, structured_summary = cls.compare_structured_fields(fields_a, fields_b)

        # 4. Extracted Text Similarity
        text_a = (proc_a.normalized_text or proc_a.raw_text) if proc_a else ""
        text_b = (proc_b.normalized_text or proc_b.raw_text) if proc_b else ""
        if text_a and text_b:
            text_similarity = cls.calculate_text_similarity(text_a, text_b)

        # Multi-Signal Classification & Confidence Scoring
        match_type: Optional[str] = None
        overall_confidence: float = 0.0

        if file_hash_match:
            match_type = DuplicateMatchType.EXACT_FILE_DUPLICATE
            overall_confidence = 1.0
        elif content_hash_match:
            match_type = DuplicateMatchType.CONTENT_DUPLICATE
            overall_confidence = 0.98
        elif structured_score >= 0.70:
            match_type = DuplicateMatchType.STRUCTURED_DATA_MATCH
            overall_confidence = round(0.80 + (0.18 * structured_score), 2)
        elif text_similarity >= 0.90:
            match_type = DuplicateMatchType.HIGH_SIMILARITY
            overall_confidence = round(text_similarity, 2)
        elif text_similarity >= 0.80 or (structured_score >= 0.40 and text_similarity >= 0.70):
            match_type = DuplicateMatchType.POSSIBLE_REUSE
            overall_confidence = round(max(text_similarity, structured_score), 2)

        # Return None if no suspicious signal detected
        if not match_type or overall_confidence < 0.75:
            return None

        # Build evidence summary
        evidence_summary = {
            "file_hash_match": file_hash_match,
            "content_hash_match": content_hash_match,
            "structured_field_match_score": structured_score,
            "text_similarity_score": text_similarity,
            "matched_fields_count": len(matched_field_details),
            "matched_fields": [m.dict() for m in matched_field_details],
            "document_a_meta": {
                "id": str(doc_a.id),
                "name": doc_a.document_name,
                "filename": doc_a.original_filename,
                "file_size": doc_a.file_size,
                "file_hash": doc_a.file_hash,
            },
            "document_b_meta": {
                "id": str(doc_b.id),
                "name": doc_b.document_name,
                "filename": doc_b.original_filename,
                "file_size": doc_b.file_size,
                "file_hash": doc_b.file_hash,
            },
        }

        return {
            "match_type": match_type,
            "file_hash_match": file_hash_match,
            "content_hash_match": content_hash_match,
            "structured_field_match_score": structured_score,
            "text_similarity_score": text_similarity,
            "overall_confidence": overall_confidence,
            "matched_fields": structured_summary,
            "evidence_summary": evidence_summary,
            "matched_field_details": matched_field_details,
        }

    @classmethod
    def scan_tender_for_duplicates(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
    ) -> DuplicateScanResponse:
        """
        Executes comprehensive cross-bidder duplicate and reuse scan across all active submitted bids of a tender.
        1. Filters active documents by document type and cross-bidder boundary (ignoring same-bidder revisions).
        2. Applies rapid hash lookups and pairwise multi-signal evaluation.
        3. Persists matches idempotently in PostgreSQL.
        4. Synchronizes actionable HumanReviewItem records.
        5. Logs immutable AuditEvent.
        """
        start_time = time.time()
        profile, tender = _verify_procurement_access(db, user, tender_id)

        # 1. Fetch eligible bids (SUBMITTED, UNDER_VERIFICATION, UNDER_EVALUATION)
        bids = db.scalars(
            select(Bid)
            .options(
                joinedload(Bid.bidder_organization),
                joinedload(Bid.documents).joinedload(BidDocument.processing),
            )
            .where(
                Bid.tender_id == tender.id,
                Bid.is_active == True,
                Bid.status.in_(["SUBMITTED", "UNDER_VERIFICATION", "UNDER_EVALUATION", "EVALUATED"]),
            )
        ).unique().all()

        # Collect active documents with their bid and org context
        eligible_docs: List[BidDocument] = []
        for bid in bids:
            for doc in bid.documents:
                if doc.is_active:
                    eligible_docs.append(doc)

        new_matches_count = 0

        # 2. Pairwise comparison across different bidders
        for i in range(len(eligible_docs)):
            doc_a = eligible_docs[i]
            bid_a = doc_a.bid
            org_a_id = bid_a.bidder_organization_id

            for j in range(i + 1, len(eligible_docs)):
                doc_b = eligible_docs[j]
                bid_b = doc_b.bid
                org_b_id = bid_b.bidder_organization_id

                # RULE 1: Skip documents belonging to the SAME bidder organization (legitimate version replacements)
                if org_a_id == org_b_id:
                    continue

                # RULE 2: Skip documents of completely different document types
                type_a = (doc_a.document_type or "").upper()
                type_b = (doc_b.document_type or "").upper()
                if type_a != type_b and type_a != "OTHER" and type_b != "OTHER":
                    continue

                # Canonical ordering for deterministic pair key
                if str(doc_a.id) > str(doc_b.id):
                    d_first, d_second = doc_b, doc_a
                    b_first, b_second = bid_b, bid_a
                else:
                    d_first, d_second = doc_a, doc_b
                    b_first, b_second = bid_a, bid_b

                eval_result = cls.evaluate_document_pair(d_first, d_second)
                if not eval_result:
                    continue

                # Check if match record already exists
                existing_match = db.scalars(
                    select(DocumentDuplicateMatch).where(
                        DocumentDuplicateMatch.document_a_id == d_first.id,
                        DocumentDuplicateMatch.document_b_id == d_second.id,
                    )
                ).first()

                if not existing_match:
                    match_record = DocumentDuplicateMatch(
                        id=uuid.uuid4(),
                        organization_id=tender.organization_id,
                        tender_id=tender.id,
                        document_a_id=d_first.id,
                        bid_a_id=b_first.id,
                        document_b_id=d_second.id,
                        bid_b_id=b_second.id,
                        match_type=eval_result["match_type"],
                        file_hash_match=eval_result["file_hash_match"],
                        content_hash_match=eval_result["content_hash_match"],
                        structured_field_match_score=eval_result["structured_field_match_score"],
                        text_similarity_score=eval_result["text_similarity_score"],
                        overall_confidence=eval_result["overall_confidence"],
                        status=DuplicateMatchStatus.REVIEW_REQUIRED,
                        review_required=True,
                        matched_fields=eval_result["matched_fields"],
                        evidence_summary=eval_result["evidence_summary"],
                    )
                    db.add(match_record)
                    new_matches_count += 1

                    # 3. Synchronize HumanReviewItem for Procurement Officer inspection
                    cls._sync_human_review_item_for_match(db, tender, b_first, b_second, match_record)
                else:
                    # Update telemetry on existing unreviewed match
                    if existing_match.status in [DuplicateMatchStatus.DETECTED, DuplicateMatchStatus.REVIEW_REQUIRED]:
                        existing_match.match_type = eval_result["match_type"]
                        existing_match.file_hash_match = eval_result["file_hash_match"]
                        existing_match.content_hash_match = eval_result["content_hash_match"]
                        existing_match.structured_field_match_score = eval_result["structured_field_match_score"]
                        existing_match.text_similarity_score = eval_result["text_similarity_score"]
                        existing_match.overall_confidence = eval_result["overall_confidence"]
                        existing_match.matched_fields = eval_result["matched_fields"]
                        existing_match.evidence_summary = eval_result["evidence_summary"]
                        existing_match.updated_at = datetime.now(timezone.utc)

        db.commit()

        # Fetch total active matches for tender
        total_active = db.scalars(
            select(func.count(DocumentDuplicateMatch.id)).where(
                DocumentDuplicateMatch.tender_id == tender.id,
                DocumentDuplicateMatch.status.in_([DuplicateMatchStatus.DETECTED, DuplicateMatchStatus.REVIEW_REQUIRED]),
            )
        ).one()

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # 4. Audit Log Entry
        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=tender.organization_id,
                    tender_id=tender.id,
                    actor_user_id=user.id,
                    actor_profile_id=profile.id,
                    actor_name=profile.full_name,
                    actor_role=profile.role.name if profile.role else "PROCUREMENT_OFFICER",
                    actor_source=AuditActorSource.HUMAN,
                    event_type=AuditEventType.DOCUMENT_DUPLICATE_DETECTED,
                    entity_type=AuditEntityType.TENDER,
                    entity_id=tender.id,
                    action="SCAN_TENDER_DUPLICATES",
                    summary=f"Completed duplicate document scan for tender '{tender.tender_number}': {new_matches_count} new potential duplicate anomalies identified.",
                    metadata={
                        "tender_id": str(tender.id),
                        "scanned_documents": len(eligible_docs),
                        "scanned_bids": len(bids),
                        "new_matches_found": new_matches_count,
                        "total_active_matches": total_active,
                        "duration_ms": duration_ms,
                    },
                ),
            )
            db.commit()
        except Exception as audit_err:
            logger.warning("Failed to record duplicate scan audit event: %s", audit_err)

        return DuplicateScanResponse(
            tender_id=tender.id,
            tender_number=tender.tender_number,
            scanned_documents=len(eligible_docs),
            scanned_bids=len(bids),
            new_matches_found=new_matches_count,
            total_active_matches=total_active,
            duration_ms=duration_ms,
            summary=f"Scanned {len(eligible_docs)} documents across {len(bids)} bids. {new_matches_count} new potential duplicate signals flagged.",
        )

    @classmethod
    def _sync_human_review_item_for_match(
        cls,
        db: Session,
        tender: Tender,
        bid_a: Bid,
        bid_b: Bid,
        match: DocumentDuplicateMatch,
    ) -> None:
        """
        Creates or updates a HumanReviewItem for cross-bidder document reuse.
        """
        source_key = ("DOCUMENT_DUPLICATE", str(match.id))
        existing_hr = db.scalars(
            select(HumanReviewItem).where(
                HumanReviewItem.tender_id == tender.id,
                HumanReviewItem.source_type == "DOCUMENT_DUPLICATE",
                HumanReviewItem.source_id == str(match.id),
            )
        ).first()

        bidder_a_name = bid_a.bidder_organization.name if bid_a.bidder_organization else "Bidder A"
        bidder_b_name = bid_b.bidder_organization.name if bid_b.bidder_organization else "Bidder B"

        if not existing_hr:
            hr_item = HumanReviewItem(
                id=uuid.uuid4(),
                organization_id=tender.organization_id,
                tender_id=tender.id,
                bid_id=bid_a.id,
                source_type="DOCUMENT_DUPLICATE",
                source_id=str(match.id),
                review_type=ReviewType.POTENTIAL_DOCUMENT_REUSE,
                severity=ReviewSeverity.HIGH if match.overall_confidence >= 0.90 else ReviewSeverity.MEDIUM,
                status=ReviewStatus.OPEN,
                title=f"Potential Document Reuse: {bidder_a_name} - {bidder_b_name}",
                reason=(
                    f"Possible document reuse detected between '{bidder_a_name}' and '{bidder_b_name}'. "
                    f"Signal: {match.match_type} with confidence {int(match.overall_confidence * 100)}%."
                ),
                system_finding={
                    "match_id": str(match.id),
                    "match_type": match.match_type,
                    "confidence": match.overall_confidence,
                    "bid_a_id": str(bid_a.id),
                    "bid_b_id": str(bid_b.id),
                    "bidder_a": bidder_a_name,
                    "bidder_b": bidder_b_name,
                },
            )
            db.add(hr_item)

    @classmethod
    def get_tender_duplicate_matches(
        cls,
        db: Session,
        user: User,
        tender_id: uuid.UUID,
        status_filter: Optional[str] = None,
        match_type_filter: Optional[str] = None,
    ) -> DuplicateMatchListResponse:
        """
        Retrieves list of duplicate match alerts for a tender with breakdown summary counts.
        """
        _, tender = _verify_procurement_access(db, user, tender_id)

        query = (
            select(DocumentDuplicateMatch)
            .options(
                joinedload(DocumentDuplicateMatch.document_a),
                joinedload(DocumentDuplicateMatch.document_b),
                joinedload(DocumentDuplicateMatch.bid_a).joinedload(Bid.bidder_organization),
                joinedload(DocumentDuplicateMatch.bid_b).joinedload(Bid.bidder_organization),
            )
            .where(DocumentDuplicateMatch.tender_id == tender.id)
            .order_by(DocumentDuplicateMatch.overall_confidence.desc(), DocumentDuplicateMatch.created_at.desc())
        )

        all_matches = db.scalars(query).unique().all()

        # Calculate counts
        counts = DuplicateMatchSummaryCounts(
            total=len(all_matches),
            detected=sum(1 for m in all_matches if m.status == DuplicateMatchStatus.DETECTED),
            review_required=sum(1 for m in all_matches if m.status == DuplicateMatchStatus.REVIEW_REQUIRED),
            confirmed_reuse=sum(1 for m in all_matches if m.status == DuplicateMatchStatus.CONFIRMED_REUSE),
            confirmed_benign=sum(1 for m in all_matches if m.status == DuplicateMatchStatus.CONFIRMED_BENIGN),
            dismissed=sum(1 for m in all_matches if m.status == DuplicateMatchStatus.DISMISSED),
            exact_file_duplicates=sum(1 for m in all_matches if m.match_type == DuplicateMatchType.EXACT_FILE_DUPLICATE),
            content_duplicates=sum(1 for m in all_matches if m.match_type == DuplicateMatchType.CONTENT_DUPLICATE),
            structured_matches=sum(1 for m in all_matches if m.match_type == DuplicateMatchType.STRUCTURED_DATA_MATCH),
            high_similarity=sum(1 for m in all_matches if m.match_type == DuplicateMatchType.HIGH_SIMILARITY),
        )

        # Apply filters if provided
        filtered = all_matches
        if status_filter:
            filtered = [m for m in filtered if m.status.upper() == status_filter.upper()]
        if match_type_filter:
            filtered = [m for m in filtered if m.match_type.upper() == match_type_filter.upper()]

        items: List[DuplicateMatchListItemResponse] = []
        for m in filtered:
            doc_a = m.document_a
            doc_b = m.document_b
            bid_a = m.bid_a
            bid_b = m.bid_b

            matched_keys = list((m.matched_fields or {}).keys())
            items.append(
                DuplicateMatchListItemResponse(
                    id=m.id,
                    organization_id=m.organization_id,
                    tender_id=m.tender_id,
                    document_a_id=m.document_a_id,
                    bid_a_id=m.bid_a_id,
                    bid_a_number=bid_a.bid_number if bid_a else None,
                    bidder_a_name=bid_a.bidder_organization.name if (bid_a and bid_a.bidder_organization) else "Bidder A",
                    document_a_name=doc_a.document_name if doc_a else "Document A",
                    document_b_id=m.document_b_id,
                    bid_b_id=m.bid_b_id,
                    bid_b_number=bid_b.bid_number if bid_b else None,
                    bidder_b_name=bid_b.bidder_organization.name if (bid_b and bid_b.bidder_organization) else "Bidder B",
                    document_b_name=doc_b.document_name if doc_b else "Document B",
                    document_type=doc_a.document_type if doc_a else "UNKNOWN",
                    match_type=m.match_type,
                    file_hash_match=m.file_hash_match,
                    content_hash_match=m.content_hash_match,
                    structured_field_match_score=m.structured_field_match_score,
                    text_similarity_score=m.text_similarity_score,
                    overall_confidence=m.overall_confidence,
                    status=m.status,
                    review_required=m.review_required,
                    matched_fields_summary=matched_keys,
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                )
            )

        return DuplicateMatchListResponse(
            items=items,
            total=len(items),
            counts=counts,
        )

    @classmethod
    def get_duplicate_match_detail(
        cls,
        db: Session,
        user: User,
        match_id: uuid.UUID,
    ) -> DuplicateMatchDetailResponse:
        """
        Retrieves detailed side-by-side inspection payload for a specific duplicate match.
        """
        match = db.scalars(
            select(DocumentDuplicateMatch)
            .options(
                joinedload(DocumentDuplicateMatch.tender),
                joinedload(DocumentDuplicateMatch.document_a).joinedload(BidDocument.processing),
                joinedload(DocumentDuplicateMatch.document_b).joinedload(BidDocument.processing),
                joinedload(DocumentDuplicateMatch.bid_a).joinedload(Bid.bidder_organization),
                joinedload(DocumentDuplicateMatch.bid_b).joinedload(Bid.bidder_organization),
                joinedload(DocumentDuplicateMatch.reviewed_by_profile),
            )
            .where(DocumentDuplicateMatch.id == match_id)
        ).first()

        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Duplicate match record not found.",
            )

        _verify_procurement_access(db, user, match.tender_id)

        doc_a = match.document_a
        doc_b = match.document_b
        bid_a = match.bid_a
        bid_b = match.bid_b
        tender = match.tender

        proc_a = doc_a.processing if doc_a else None
        proc_b = doc_b.processing if doc_b else None

        fields_a = (proc_a.extracted_data or {}).get("fields", {}) if proc_a else {}
        fields_b = (proc_b.extracted_data or {}).get("fields", {}) if proc_b else {}

        # Re-derive field details with labels
        _, matched_details, _ = cls.compare_structured_fields(fields_a, fields_b)

        meta_a = DocumentComparisonMeta(
            document_id=doc_a.id,
            bid_id=bid_a.id,
            bid_number=bid_a.bid_number,
            bidder_organization_id=bid_a.bidder_organization_id,
            bidder_name=bid_a.bidder_organization.name if bid_a.bidder_organization else "Bidder A",
            document_type=doc_a.document_type,
            document_name=doc_a.document_name,
            original_filename=doc_a.original_filename,
            file_size=doc_a.file_size,
            mime_type=doc_a.mime_type,
            file_hash=doc_a.file_hash,
            normalized_content_hash=proc_a.normalized_content_hash if proc_a else None,
            uploaded_at=doc_a.created_at,
            extracted_fields=fields_a,
            text_snippet=(proc_a.raw_text[:500] + "...") if (proc_a and proc_a.raw_text) else None,
        )

        meta_b = DocumentComparisonMeta(
            document_id=doc_b.id,
            bid_id=bid_b.id,
            bid_number=bid_b.bid_number,
            bidder_organization_id=bid_b.bidder_organization_id,
            bidder_name=bid_b.bidder_organization.name if bid_b.bidder_organization else "Bidder B",
            document_type=doc_b.document_type,
            document_name=doc_b.document_name,
            original_filename=doc_b.original_filename,
            file_size=doc_b.file_size,
            mime_type=doc_b.mime_type,
            file_hash=doc_b.file_hash,
            normalized_content_hash=proc_b.normalized_content_hash if proc_b else None,
            uploaded_at=doc_b.created_at,
            extracted_fields=fields_b,
            text_snippet=(proc_b.raw_text[:500] + "...") if (proc_b and proc_b.raw_text) else None,
        )

        return DuplicateMatchDetailResponse(
            id=match.id,
            organization_id=match.organization_id,
            tender_id=match.tender_id,
            tender_title=tender.title if tender else None,
            tender_number=tender.tender_number if tender else None,
            document_a=meta_a,
            document_b=meta_b,
            match_type=match.match_type,
            file_hash_match=match.file_hash_match,
            content_hash_match=match.content_hash_match,
            structured_field_match_score=match.structured_field_match_score,
            text_similarity_score=match.text_similarity_score,
            overall_confidence=match.overall_confidence,
            status=match.status,
            review_required=match.review_required,
            matched_fields_details=matched_details,
            evidence_summary=match.evidence_summary or {},
            reviewer_notes=match.reviewer_notes,
            reviewed_by_profile_id=match.reviewed_by_profile_id,
            reviewed_by_name=match.reviewed_by_profile.full_name if match.reviewed_by_profile else None,
            reviewed_at=match.reviewed_at,
            created_at=match.created_at,
            updated_at=match.updated_at,
        )

    @classmethod
    def review_duplicate_match(
        cls,
        db: Session,
        user: User,
        match_id: uuid.UUID,
        review_dto: DuplicateReviewRequest,
    ) -> DuplicateReviewResponse:
        """
        Records the Procurement Officer's human evaluation decision on a duplicate document alert:
        - CONFIRMED_BENIGN (Legitimate co-submission, authorized multi-dealer certificate, or common public template)
        - CONFIRMED_REUSE (Confirmed unauthorized cross-bidder document reuse anomaly)
        - DISMISSED (False alarm / benign coincidence)
        """
        match = db.scalars(
            select(DocumentDuplicateMatch)
            .options(
                joinedload(DocumentDuplicateMatch.tender),
                joinedload(DocumentDuplicateMatch.bid_a).joinedload(Bid.bidder_organization),
                joinedload(DocumentDuplicateMatch.bid_b).joinedload(Bid.bidder_organization),
            )
            .where(DocumentDuplicateMatch.id == match_id)
        ).first()

        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Duplicate match record not found.",
            )

        profile, tender = _verify_procurement_access(db, user, match.tender_id)

        resolution = review_dto.resolution.upper().strip()
        if resolution not in [
            DuplicateMatchStatus.CONFIRMED_BENIGN,
            DuplicateMatchStatus.CONFIRMED_REUSE,
            DuplicateMatchStatus.DISMISSED,
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid resolution. Must be one of {DuplicateMatchStatus.CONFIRMED_BENIGN}, {DuplicateMatchStatus.CONFIRMED_REUSE}, or {DuplicateMatchStatus.DISMISSED}.",
            )

        now = datetime.now(timezone.utc)
        match.status = resolution
        match.review_required = False
        match.reviewer_notes = review_dto.reviewer_notes
        match.reviewed_by_profile_id = profile.id
        match.reviewed_at = now
        match.updated_at = now

        # Update linked HumanReviewItem if present
        hr_item = db.scalars(
            select(HumanReviewItem).where(
                HumanReviewItem.tender_id == tender.id,
                HumanReviewItem.source_type == "DOCUMENT_DUPLICATE",
                HumanReviewItem.source_id == str(match.id),
            )
        ).first()

        if hr_item:
            hr_item.status = ReviewStatus.RESOLVED
            hr_item.resolution = resolution
            hr_item.resolution_reason = review_dto.reviewer_notes
            hr_item.resolved_by_profile_id = profile.id
            hr_item.resolved_at = now
            hr_item.updated_at = now

        db.commit()

        # Audit Event Log
        audit_event_type = (
            AuditEventType.DOCUMENT_REUSE_CONFIRMED
            if resolution == DuplicateMatchStatus.CONFIRMED_REUSE
            else (
                AuditEventType.DOCUMENT_DUPLICATE_DISMISSED
                if resolution == DuplicateMatchStatus.DISMISSED
                else AuditEventType.DOCUMENT_DUPLICATE_REVIEWED
            )
        )

        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=tender.organization_id,
                    tender_id=tender.id,
                    actor_user_id=user.id,
                    actor_profile_id=profile.id,
                    actor_name=profile.full_name,
                    actor_role=profile.role.name if profile.role else "PROCUREMENT_OFFICER",
                    actor_source=AuditActorSource.HUMAN,
                    event_type=audit_event_type,
                    entity_type=AuditEntityType.DOCUMENT_DUPLICATE_MATCH,
                    entity_id=match.id,
                    action=f"REVIEW_DUPLICATE_{resolution}",
                    summary=f"Procurement Officer recorded resolution '{resolution}' on duplicate alert between {match.bid_a_id} and {match.bid_b_id}.",
                    metadata={
                        "match_id": str(match.id),
                        "resolution": resolution,
                        "tender_id": str(tender.id),
                        "bid_a_id": str(match.bid_a_id),
                        "bid_b_id": str(match.bid_b_id),
                        "reviewer_notes": review_dto.reviewer_notes,
                    },
                ),
            )
            db.commit()
        except Exception as audit_err:
            logger.warning("Failed to record duplicate review audit event: %s", audit_err)

        return DuplicateReviewResponse(
            match_id=match.id,
            status=match.status,
            resolution=resolution,
            reviewed_by_name=profile.full_name,
            reviewed_at=now,
            reviewer_notes=match.reviewer_notes,
            message=f"Duplicate match successfully reviewed and marked as '{resolution}'.",
        )
