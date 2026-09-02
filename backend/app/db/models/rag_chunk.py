"""
RAG Chunk Model for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
Stores dense vector embeddings and metadata of procurement knowledge sources
(tender requirements, clauses, bid documents, extractions, verifications, compliance, scores, risks).
"""

import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.bid import Bid
    from app.db.models.bid_document import BidDocument
    from app.db.models.organization import Organization
    from app.db.models.tender import Tender


class RAGChunk(Base, TimestampMixin):
    """
    Stores an indexed document or structured entity chunk with a dense vector embedding
    scoped strictly to organization (tenant), tender, and optionally bid and document.
    """
    __tablename__ = "rag_chunks"
    __table_args__ = (
        Index("ix_rag_chunks_tender_active", "tender_id", "is_active"),
        Index("ix_rag_chunks_bid_active", "bid_id", "is_active"),
        Index("ix_rag_chunks_source", "source_type", "source_id"),
        Index("ix_rag_chunks_org", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    tender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        nullable=False,
    )

    bid_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=True,
    )

    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bid_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    source_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="TENDER_REQUIREMENT, TENDER_CLAUSE, BID_DOCUMENT, STRUCTURED_EXTRACTION, VERIFICATION_RESULT, COMPLIANCE_RESULT, SCORING_RESULT, RISK_RESULT",
    )

    source_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Unique identifier of the source entity (e.g. requirement_id, result_id, document_id)",
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Clean, grounded text representation used for similarity search and LLM context",
    )

    embedding: Mapped[Any] = mapped_column(
        Vector(1536),
        nullable=False,
        comment="1536-dimensional dense embedding vector",
    )

    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Structured metadata (requirement_code, category, page_number, doc_type, etc.)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="True if chunk belongs to current active version; False if superseded/replaced",
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    tender: Mapped["Tender"] = relationship("Tender")
    bid: Mapped[Optional["Bid"]] = relationship("Bid")
    document: Mapped[Optional["BidDocument"]] = relationship("BidDocument")
