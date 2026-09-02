"""Add bid_score_snapshots table for Part 7A

Revision ID: 015_add_score_snapshots
Revises: 014_add_critical_rule_fields
Create Date: 2026-08-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '015_add_score_snapshots'
down_revision: Union[str, None] = '014_add_critical_rule_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bid_score_snapshots',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('bid_id', sa.Uuid(), nullable=False),
        sa.Column('tender_id', sa.Uuid(), nullable=False),
        sa.Column('scoring_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('scoring_formula_version', sa.String(length=50), nullable=False, server_default='v1.0'),
        sa.Column('scoring_status', sa.String(length=50), nullable=False, server_default='INCOMPLETE'),
        sa.Column('scoring_complete', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('human_review_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('earned_weight', sa.Numeric(precision=10, scale=4), nullable=False, server_default='0.0000'),
        sa.Column('eligible_weight', sa.Numeric(precision=10, scale=4), nullable=False, server_default='0.0000'),
        sa.Column('total_rules_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed_rules_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_rules_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('review_rules_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pending_rules_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('not_applicable_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mandatory_failures_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('critical_failures_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rule_contributions', sa.JSON(), nullable=False),
        sa.Column('calculation_details', sa.JSON(), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['bid_id'], ['bids.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('ix_bid_score_snapshots_bid_id', 'bid_score_snapshots', ['bid_id'])
    op.create_index('ix_bid_score_snapshots_tender_id', 'bid_score_snapshots', ['tender_id'])
    op.create_index('ix_bid_score_snapshots_bid_current', 'bid_score_snapshots', ['bid_id', 'is_current'])


def downgrade() -> None:
    op.drop_index('ix_bid_score_snapshots_bid_current', table_name='bid_score_snapshots')
    op.drop_index('ix_bid_score_snapshots_tender_id', table_name='bid_score_snapshots')
    op.drop_index('ix_bid_score_snapshots_bid_id', table_name='bid_score_snapshots')
    op.drop_table('bid_score_snapshots')
