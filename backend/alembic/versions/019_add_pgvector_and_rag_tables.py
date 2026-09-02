"""Add pgvector extension, rag_chunks and ai_recommendations tables for Part 7E

Revision ID: 019_add_pgvector_and_rag_tables
Revises: 018_add_risk_overrides
Create Date: 2026-08-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '019_add_pgvector_and_rag_tables'
down_revision: Union[str, None] = '018_add_risk_overrides'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension in PostgreSQL / Supabase
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create rag_chunks table
    op.create_table(
        'rag_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tender_id', UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bid_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=True),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('bid_documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_type', sa.String(length=100), nullable=False),
        sa.Column('source_id', sa.String(length=100), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('metadata_json', JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # 3. Create indexes on rag_chunks
    op.create_index('ix_rag_chunks_tender_active', 'rag_chunks', ['tender_id', 'is_active'])
    op.create_index('ix_rag_chunks_bid_active', 'rag_chunks', ['bid_id', 'is_active'])
    op.create_index('ix_rag_chunks_source', 'rag_chunks', ['source_type', 'source_id'])
    op.create_index('ix_rag_chunks_org', 'rag_chunks', ['organization_id'])

    # HNSW Cosine vector index on embedding column
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_rag_chunks_embedding_hnsw ON rag_chunks USING hnsw (embedding vector_cosine_ops);"
    )

    # 4. Create ai_recommendations table
    op.create_table(
        'ai_recommendations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('bid_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=False),
        sa.Column('score_snapshot_id', UUID(as_uuid=True), sa.ForeignKey('bid_score_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('risk_snapshot_id', UUID(as_uuid=True), sa.ForeignKey('bid_risk_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('compliance_evaluation_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('recommendation', sa.String(length=50), nullable=False),
        sa.Column('recommendation_reason', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('strengths', JSONB(), nullable=False, server_default='[]'),
        sa.Column('concerns', JSONB(), nullable=False, server_default='[]'),
        sa.Column('review_items', JSONB(), nullable=False, server_default='[]'),
        sa.Column('evidence_refs', JSONB(), nullable=False, server_default='[]'),
        sa.Column('limitations', JSONB(), nullable=False, server_default='[]'),
        sa.Column('confidence_label', sa.String(length=20), nullable=False, server_default='MEDIUM'),
        sa.Column('model_provider', sa.String(length=50), nullable=False, server_default='local_fallback'),
        sa.Column('model_name', sa.String(length=100), nullable=False, server_default='default'),
        sa.Column('prompt_version', sa.String(length=50), nullable=False, server_default='v1'),
        sa.Column('guardrail_applied', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('guardrail_reason', sa.Text(), nullable=True),
        sa.Column('is_stale', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # 5. Create indexes on ai_recommendations
    op.create_index('ix_ai_recommendations_bid_stale', 'ai_recommendations', ['bid_id', 'is_stale'])
    op.create_index('ix_ai_recommendations_bid_created', 'ai_recommendations', ['bid_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_ai_recommendations_bid_created', table_name='ai_recommendations')
    op.drop_index('ix_ai_recommendations_bid_stale', table_name='ai_recommendations')
    op.drop_table('ai_recommendations')

    op.execute("DROP INDEX IF EXISTS ix_rag_chunks_embedding_hnsw;")
    op.drop_index('ix_rag_chunks_org', table_name='rag_chunks')
    op.drop_index('ix_rag_chunks_source', table_name='rag_chunks')
    op.drop_index('ix_rag_chunks_bid_active', table_name='rag_chunks')
    op.drop_index('ix_rag_chunks_tender_active', table_name='rag_chunks')
    op.drop_table('rag_chunks')
