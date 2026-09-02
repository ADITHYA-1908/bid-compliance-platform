"""Add document_duplicate_matches table and hash columns for Part 10: Duplicate / Reuse Document Detection

Revision ID: 025_add_duplicate_detection
Revises: 024_add_bulk_evaluation_jobs
Create Date: 2026-09-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '025_add_duplicate_detection'
down_revision: Union[str, None] = '024_add_bulk_evaluation_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add file_hash to bid_documents (if not already added)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    bid_doc_cols = [c['name'] for c in inspector.get_columns('bid_documents')]
    if 'file_hash' not in bid_doc_cols:
        op.add_column('bid_documents', sa.Column('file_hash', sa.String(64), nullable=True))
        op.create_index('ix_bid_documents_file_hash', 'bid_documents', ['file_hash'])

    # 2. Add normalized_content_hash to document_processing (if not already added)
    doc_proc_cols = [c['name'] for c in inspector.get_columns('document_processing')]
    if 'normalized_content_hash' not in doc_proc_cols:
        op.add_column('document_processing', sa.Column('normalized_content_hash', sa.String(64), nullable=True))
        op.create_index('ix_document_processing_normalized_hash', 'document_processing', ['normalized_content_hash'])

    # 3. Create document_duplicate_matches table (if not exists)
    tables = inspector.get_table_names()
    if 'document_duplicate_matches' not in tables:
        op.create_table(
            'document_duplicate_matches',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('tender_id', UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False),
            sa.Column('document_a_id', UUID(as_uuid=True), sa.ForeignKey('bid_documents.id', ondelete='CASCADE'), nullable=False),
            sa.Column('bid_a_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=False),
            sa.Column('document_b_id', UUID(as_uuid=True), sa.ForeignKey('bid_documents.id', ondelete='CASCADE'), nullable=False),
            sa.Column('bid_b_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=False),
            sa.Column('match_type', sa.String(50), nullable=False, server_default='POSSIBLE_REUSE'),
            sa.Column('file_hash_match', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('content_hash_match', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('structured_field_match_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('text_similarity_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('overall_confidence', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('status', sa.String(50), nullable=False, server_default='REVIEW_REQUIRED'),
            sa.Column('review_required', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('matched_fields', JSONB, nullable=True),
            sa.Column('evidence_summary', JSONB, nullable=True),
            sa.Column('reviewer_notes', sa.Text(), nullable=True),
            sa.Column('reviewed_by_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL'), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )

        # 4. Create indexes for performance and rapid lookups
        op.create_index('ix_doc_dup_org_tender', 'document_duplicate_matches', ['organization_id', 'tender_id'])
        op.create_index('ix_doc_dup_tender_status', 'document_duplicate_matches', ['tender_id', 'status'])
        op.create_index('ix_doc_dup_pair', 'document_duplicate_matches', ['document_a_id', 'document_b_id'], unique=True)
        op.create_index('ix_doc_dup_bids', 'document_duplicate_matches', ['bid_a_id', 'bid_b_id'])
        op.create_index('ix_doc_dup_match_type', 'document_duplicate_matches', ['match_type'])


def downgrade() -> None:
    op.drop_index('ix_doc_dup_match_type', table_name='document_duplicate_matches')
    op.drop_index('ix_doc_dup_bids', table_name='document_duplicate_matches')
    op.drop_index('ix_doc_dup_pair', table_name='document_duplicate_matches')
    op.drop_index('ix_doc_dup_tender_status', table_name='document_duplicate_matches')
    op.drop_index('ix_doc_dup_org_tender', table_name='document_duplicate_matches')
    op.drop_table('document_duplicate_matches')
    op.drop_index('ix_document_processing_normalized_hash', table_name='document_processing')
    op.drop_column('document_processing', 'normalized_content_hash')
    op.drop_index('ix_bid_documents_file_hash', table_name='bid_documents')
    op.drop_column('bid_documents', 'file_hash')
