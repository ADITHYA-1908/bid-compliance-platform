"""Add risk overrides and adjusted risk fields to bid_risk_snapshots for Part 7D

Revision ID: 018_add_risk_overrides
Revises: 017_add_bid_risk_snapshots
Create Date: 2026-08-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '018_add_risk_overrides'
down_revision: Union[str, None] = '017_add_bid_risk_snapshots'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'bid_risk_snapshots',
        sa.Column('override_formula_version', sa.String(length=50), nullable=False, server_default='v1'),
    )
    op.add_column(
        'bid_risk_snapshots',
        sa.Column('adjusted_risk_score', sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        'bid_risk_snapshots',
        sa.Column('adjusted_risk_level', sa.String(length=50), nullable=True),
    )
    op.add_column(
        'bid_risk_snapshots',
        sa.Column('override_applied', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'bid_risk_snapshots',
        sa.Column('override_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'bid_risk_snapshots',
        sa.Column('applied_overrides', sa.JSON(), nullable=False, server_default='[]'),
    )


def downgrade() -> None:
    op.drop_column('bid_risk_snapshots', 'applied_overrides')
    op.drop_column('bid_risk_snapshots', 'override_count')
    op.drop_column('bid_risk_snapshots', 'override_applied')
    op.drop_column('bid_risk_snapshots', 'adjusted_risk_level')
    op.drop_column('bid_risk_snapshots', 'adjusted_risk_score')
    op.drop_column('bid_risk_snapshots', 'override_formula_version')
