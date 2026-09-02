"""Add document_processing table for Part 4A

Revision ID: 009_document_processing
Revises: 008_bid_submission
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009_document_processing'
down_revision: Union[str, None] = '008_bid_submission'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_processing',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            'bid_document_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('bid_documents.id', ondelete='CASCADE'),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            'processing_status',
            sa.String(50),
            server_default='QUEUED',
            nullable=False,
        ),
        sa.Column(
            'processing_stage',
            sa.String(50),
            server_default='INGESTION',
            nullable=False,
        ),
        sa.Column(
            'extraction_method',
            sa.String(50),
            server_default='NONE',
            nullable=False,
        ),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('normalized_text', sa.Text(), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )

    op.create_index(
        'ix_document_processing_bid_document_id',
        'document_processing',
        ['bid_document_id'],
        unique=True,
    )
    op.create_index(
        'ix_document_processing_processing_status',
        'document_processing',
        ['processing_status'],
    )
    op.create_index(
        'ix_document_processing_processing_stage',
        'document_processing',
        ['processing_stage'],
    )


def downgrade() -> None:
    op.drop_index('ix_document_processing_processing_stage', table_name='document_processing')
    op.drop_index('ix_document_processing_processing_status', table_name='document_processing')
    op.drop_index('ix_document_processing_bid_document_id', table_name='document_processing')
    op.drop_table('document_processing')
