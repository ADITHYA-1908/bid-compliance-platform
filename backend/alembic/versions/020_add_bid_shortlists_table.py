"""Add bid_shortlists table for Part 8B

Revision ID: 020_add_bid_shortlists
Revises: 019_add_pgvector_and_rag_tables
Create Date: 2026-08-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '020_add_bid_shortlists'
down_revision: Union[str, None] = '019_add_pgvector_and_rag_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create bid_shortlists table
    op.create_table(
        'bid_shortlists',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tender_id', UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bid_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_shortlisted', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('shortlisted_by_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tender_id', 'bid_id', name='uq_bid_shortlists_tender_bid'),
    )

    op.create_index('ix_bid_shortlists_tender_id', 'bid_shortlists', ['tender_id'])
    op.create_index('ix_bid_shortlists_bid_id', 'bid_shortlists', ['bid_id'])
    op.create_index('ix_bid_shortlists_shortlisted', 'bid_shortlists', ['tender_id', 'is_shortlisted'])


def downgrade() -> None:
    op.drop_index('ix_bid_shortlists_shortlisted', table_name='bid_shortlists')
    op.drop_index('ix_bid_shortlists_bid_id', table_name='bid_shortlists')
    op.drop_index('ix_bid_shortlists_tender_id', table_name='bid_shortlists')
    op.drop_table('bid_shortlists')
