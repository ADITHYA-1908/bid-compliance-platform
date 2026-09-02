"""Add document_quality_results and document_page_qualities tables for Part 11: Advanced Document Quality Check

Revision ID: 026_add_document_quality
Revises: 025_add_duplicate_detection
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '026_add_document_quality'
down_revision: Union[str, None] = '025_add_duplicate_detection'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create document_quality_results table if not exists
    if 'document_quality_results' not in tables:
        op.create_table(
            'document_quality_results',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('bid_documents.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('processing_id', UUID(as_uuid=True), sa.ForeignKey('document_processing.id', ondelete='SET NULL'), nullable=True),
            sa.Column('quality_score', sa.Float(), nullable=False, server_default='100.0'),
            sa.Column('quality_level', sa.String(50), nullable=False, server_default='GOOD'),
            sa.Column('is_blurry', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('has_blank_pages', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('has_unreadable_pages', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('has_low_resolution_pages', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('has_skewed_pages', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('is_corrupted', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('is_password_protected', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('ocr_confidence', sa.Float(), nullable=True),
            sa.Column('average_ocr_confidence', sa.Float(), nullable=True),
            sa.Column('min_page_ocr_confidence', sa.Float(), nullable=True),
            sa.Column('page_count', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('review_required', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('review_reasons', JSONB, nullable=False, server_default='[]'),
            sa.Column('bidder_feedback', JSONB, nullable=False, server_default='[]'),
            sa.Column('metrics_summary', JSONB, nullable=False, server_default='{}'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_document_quality_doc_id', 'document_quality_results', ['document_id'])
        op.create_index('ix_document_quality_level', 'document_quality_results', ['quality_level'])
        op.create_index('ix_document_quality_review_req', 'document_quality_results', ['review_required'])

    # 2. Create document_page_qualities table if not exists
    if 'document_page_qualities' not in tables:
        op.create_table(
            'document_page_qualities',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('quality_result_id', UUID(as_uuid=True), sa.ForeignKey('document_quality_results.id', ondelete='CASCADE'), nullable=False),
            sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('bid_documents.id', ondelete='CASCADE'), nullable=False),
            sa.Column('page_number', sa.Integer(), nullable=False),
            sa.Column('blur_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('width', sa.Integer(), nullable=True),
            sa.Column('height', sa.Integer(), nullable=True),
            sa.Column('dpi', sa.Integer(), nullable=True),
            sa.Column('resolution', sa.String(50), nullable=True),
            sa.Column('ocr_confidence', sa.Float(), nullable=True),
            sa.Column('is_blank', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('is_unreadable', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('is_skewed', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('skew_angle', sa.Float(), nullable=True),
            sa.Column('quality_level', sa.String(50), nullable=False, server_default='GOOD'),
            sa.Column('review_reason', sa.String(500), nullable=True),
            sa.Column('issues', JSONB, nullable=False, server_default='[]'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_document_page_quality_doc_page', 'document_page_qualities', ['document_id', 'page_number'])
        op.create_index('ix_document_page_quality_result_id', 'document_page_qualities', ['quality_result_id'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'document_page_qualities' in tables:
        op.drop_table('document_page_qualities')
    if 'document_quality_results' in tables:
        op.drop_table('document_quality_results')
