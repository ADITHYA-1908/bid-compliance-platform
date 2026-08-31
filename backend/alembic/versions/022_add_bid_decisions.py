"""Add bid_decisions table for Part 8D Final Human Decision Workflow

Revision ID: 022_add_bid_decisions
Revises: 021_add_human_review_tables
Create Date: 2026-08-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '022_add_bid_decisions'
down_revision: Union[str, None] = '021_add_human_review_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create bid_decisions table
    op.create_table(
        'bid_decisions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tender_id', UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bid_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=False),
        sa.Column('decision', sa.String(50), nullable=False, server_default='NOT_DECIDED'),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('decision_summary', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('decided_by_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('decision_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('evaluation_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('score_snapshot_id', UUID(as_uuid=True), sa.ForeignKey('bid_score_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('risk_snapshot_id', UUID(as_uuid=True), sa.ForeignKey('bid_risk_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('ai_recommendation_id', UUID(as_uuid=True), sa.ForeignKey('ai_recommendations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_stale', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('stale_reason', sa.Text(), nullable=True),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by_decision_id', UUID(as_uuid=True), sa.ForeignKey('bid_decisions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # 2. Create indexes
    op.create_index('ix_bid_decisions_org_id', 'bid_decisions', ['organization_id'])
    op.create_index('ix_bid_decisions_tender_id', 'bid_decisions', ['tender_id'])
    op.create_index('ix_bid_decisions_bid_id', 'bid_decisions', ['bid_id'])
    op.create_index('ix_bid_decisions_decision', 'bid_decisions', ['decision'])
    op.create_index('ix_bid_decisions_is_current', 'bid_decisions', ['is_current'])
    op.create_index('ix_bid_decisions_decided_at', 'bid_decisions', ['decided_at'])
    op.create_index('ix_bid_decisions_bid_current', 'bid_decisions', ['bid_id', 'is_current'])


def downgrade() -> None:
    op.drop_index('ix_bid_decisions_bid_current', table_name='bid_decisions')
    op.drop_index('ix_bid_decisions_decided_at', table_name='bid_decisions')
    op.drop_index('ix_bid_decisions_is_current', table_name='bid_decisions')
    op.drop_index('ix_bid_decisions_decision', table_name='bid_decisions')
    op.drop_index('ix_bid_decisions_bid_id', table_name='bid_decisions')
    op.drop_index('ix_bid_decisions_tender_id', table_name='bid_decisions')
    op.drop_index('ix_bid_decisions_org_id', table_name='bid_decisions')
    op.drop_table('bid_decisions')
