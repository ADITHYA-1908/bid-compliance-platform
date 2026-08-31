"""Add human_review_items and human_review_notes tables for Part 8C

Revision ID: 021_add_human_review_tables
Revises: 020_add_bid_shortlists
Create Date: 2026-08-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '021_add_human_review_tables'
down_revision: Union[str, None] = '020_add_bid_shortlists'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create human_review_items table
    op.create_table(
        'human_review_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tender_id', UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bid_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=False),
        sa.Column('compliance_result_id', UUID(as_uuid=True), sa.ForeignKey('compliance_results.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tender_requirement_id', UUID(as_uuid=True), sa.ForeignKey('tender_requirements.id', ondelete='SET NULL'), nullable=True),
        sa.Column('verification_record_id', UUID(as_uuid=True), sa.ForeignKey('verification_records.id', ondelete='SET NULL'), nullable=True),
        sa.Column('bid_document_id', UUID(as_uuid=True), sa.ForeignKey('bid_documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('review_type', sa.String(50), nullable=False, server_default='COMPLIANCE_REVIEW'),
        sa.Column('severity', sa.String(50), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(50), nullable=False, server_default='OPEN'),
        sa.Column('source_type', sa.String(50), nullable=False, server_default='COMPLIANCE_RESULT'),
        sa.Column('source_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('system_finding', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('resolution', sa.String(50), nullable=True),
        sa.Column('resolution_reason', sa.Text(), nullable=True),
        sa.Column('effective_compliance_status', sa.String(50), nullable=True),
        sa.Column('claimed_by_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolved_by_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('ix_human_review_items_org_status', 'human_review_items', ['organization_id', 'status'])
    op.create_index('ix_human_review_items_tender_bid', 'human_review_items', ['tender_id', 'bid_id'])
    op.create_index('ix_human_review_items_source_key', 'human_review_items', ['tender_id', 'bid_id', 'source_type', 'source_id'])
    op.create_index('ix_human_review_items_severity', 'human_review_items', ['severity'])
    op.create_index('ix_human_review_items_status', 'human_review_items', ['status'])

    # 2. Create human_review_notes table
    op.create_table(
        'human_review_notes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('review_item_id', UUID(as_uuid=True), sa.ForeignKey('human_review_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('note_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('ix_human_review_notes_review_created', 'human_review_notes', ['review_item_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_human_review_notes_review_created', table_name='human_review_notes')
    op.drop_table('human_review_notes')

    op.drop_index('ix_human_review_items_status', table_name='human_review_items')
    op.drop_index('ix_human_review_items_severity', table_name='human_review_items')
    op.drop_index('ix_human_review_items_source_key', table_name='human_review_items')
    op.drop_index('ix_human_review_items_tender_bid', table_name='human_review_items')
    op.drop_index('ix_human_review_items_org_status', table_name='human_review_items')
    op.drop_table('human_review_items')
