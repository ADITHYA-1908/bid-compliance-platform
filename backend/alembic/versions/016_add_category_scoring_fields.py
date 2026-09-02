"""Add category scoring fields to bid_score_snapshots for Part 7B

Revision ID: 016_add_category_scoring_fields
Revises: 015_add_score_snapshots
Create Date: 2026-08-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '016_add_category_scoring_fields'
down_revision: Union[str, None] = '015_add_score_snapshots'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'bid_score_snapshots',
        sa.Column('overall_score', sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        'bid_score_snapshots',
        sa.Column('is_provisional', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'bid_score_snapshots',
        sa.Column('category_scores', sa.JSON(), nullable=False, server_default='{}'),
    )


def downgrade() -> None:
    op.drop_column('bid_score_snapshots', 'category_scores')
    op.drop_column('bid_score_snapshots', 'is_provisional')
    op.drop_column('bid_score_snapshots', 'overall_score')
