"""Add bid_risk_snapshots table for Part 7C: Deterministic Risk Assessment Engine

Revision ID: 017_add_bid_risk_snapshots
Revises: 016_add_category_scoring_fields
Create Date: 2026-08-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '017_add_bid_risk_snapshots'
down_revision: Union[str, None] = '016_add_category_scoring_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bid_risk_snapshots',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('bid_id', sa.Uuid(), nullable=False),
        sa.Column('tender_id', sa.Uuid(), nullable=False),
        sa.Column('risk_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('risk_formula_version', sa.String(length=50), nullable=False, server_default='v1'),
        sa.Column('base_risk_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('base_risk_level', sa.String(length=50), nullable=True),
        sa.Column('risk_complete', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_provisional', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('human_review_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('feature_snapshot', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('contribution_details', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('summary_reasons', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('calculation_details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['bid_id'], ['bids.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('ix_bid_risk_snapshots_bid_id', 'bid_risk_snapshots', ['bid_id'])
    op.create_index('ix_bid_risk_snapshots_tender_id', 'bid_risk_snapshots', ['tender_id'])
    op.create_index('ix_bid_risk_snapshots_bid_current', 'bid_risk_snapshots', ['bid_id', 'is_current'])


def downgrade() -> None:
    op.drop_index('ix_bid_risk_snapshots_bid_current', table_name='bid_risk_snapshots')
    op.drop_index('ix_bid_risk_snapshots_tender_id', table_name='bid_risk_snapshots')
    op.drop_index('ix_bid_risk_snapshots_bid_id', table_name='bid_risk_snapshots')
    op.drop_table('bid_risk_snapshots')
