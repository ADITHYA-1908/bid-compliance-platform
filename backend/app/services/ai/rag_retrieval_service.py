"""
RAG Retrieval Service for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
Performs tenant-isolated, scoped vector similarity and hybrid keyword retrieval from pgvector.
"""

import logging
import re
import uuid
from typing import List, Optional
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.rag_chunk import RAGChunk
from app.services.ai.ai_config import SOURCE_PRIORITY_MULTIPLIERS
from app.services.ai.ai_models import RetrievedEvidence
from app.services.ai.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RAGRetrievalService:
    """
    Executes scoped similarity retrieval on `rag_chunks` pgvector storage
    with tenant isolation, keyword boosting, and evidence type prioritization.
    """

    @classmethod
    def retrieve_evidence(
        cls,
        db: Session,
        tender_id: uuid.UUID,
        bid_id: Optional[uuid.UUID],
        query: str,
        top_k: Optional[int] = None,
        source_types: Optional[List[str]] = None,
    ) -> List[RetrievedEvidence]:
        """
        Retrieves top-k evidence chunks scoped strictly to the given tender_id and bid_id.
        Prevents cross-tenant / cross-bid data leakage at the query level.
        """
        k = top_k or settings.RAG_TOP_K
        query_vec = EmbeddingService.generate_embedding(query)

        # 1. Base query scope filters
        conditions = [
            RAGChunk.tender_id == tender_id,
            RAGChunk.is_active == True,  # noqa: E712
        ]

        if bid_id:
            # Only include chunks belonging to this specific bid OR general tender requirements
            conditions.append(or_(RAGChunk.bid_id == bid_id, RAGChunk.bid_id == None))  # noqa: E711
        else:
            conditions.append(RAGChunk.bid_id == None)  # noqa: E711

        if source_types:
            conditions.append(RAGChunk.source_type.in_(source_types))

        # 2. Vector distance expression
        # cosine_distance = 1 - cosine_similarity
        distance_expr = RAGChunk.embedding.cosine_distance(query_vec)

        stmt = (
            select(RAGChunk, distance_expr.label("distance"))
            .where(and_(*conditions))
            .order_by(distance_expr.asc())
            .limit(k * 2)  # Over-fetch for hybrid re-ranking
        )

        results = db.execute(stmt).all()

        # 3. Hybrid scoring & domain keyword boost
        scored_evidence: List[RetrievedEvidence] = []
        clean_q_tokens = set(re.findall(r"\w+", query.lower()))

        for chunk, distance in results:
            # Base similarity (0.0 to 1.0)
            base_similarity = max(0.0, 1.0 - float(distance or 0.0))

            # Domain type priority multiplier
            priority_mult = SOURCE_PRIORITY_MULTIPLIERS.get(chunk.source_type, 1.0)
            final_score = base_similarity * priority_mult

            # Exact keyword / identifier match boost
            chunk_content_lower = chunk.content.lower()
            matched_tokens = sum(1 for token in clean_q_tokens if len(token) > 2 and token in chunk_content_lower)
            if matched_tokens > 0:
                final_score += min(0.2, matched_tokens * 0.05)

            meta = chunk.metadata_json or {}
            page_num = meta.get("page_number") or meta.get("page_count")

            scored_evidence.append(
                RetrievedEvidence(
                    chunk_id=str(chunk.id),
                    source_type=chunk.source_type,
                    source_id=chunk.source_id,
                    document_id=str(chunk.document_id) if chunk.document_id else None,
                    content=chunk.content,
                    similarity_score=round(final_score, 4),
                    page_number=int(page_num) if page_num and str(page_num).isdigit() else None,
                    metadata=meta,
                )
            )

        # 4. Sort by hybrid score and limit to top_k
        scored_evidence.sort(key=lambda item: item.similarity_score, reverse=True)
        return scored_evidence[:k]
