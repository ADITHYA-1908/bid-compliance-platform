"""Add lifecycle timestamps to tenders table for Part 2E

Revision ID: 004_tender_lifecycle
Revises: 003_add_tenders_and_requirements
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_tender_lifecycle'
down_revision: Union[str, None] = '003_add_tenders_and_requirements'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add lifecycle audit timestamp columns to 'tenders' table
    op.add_column('tenders', sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenders', sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenders', sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenders', sa.Column('evaluation_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenders', sa.Column('awarded_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenders', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('tenders', 'archived_at')
    op.drop_column('tenders', 'awarded_at')
    op.drop_column('tenders', 'evaluation_started_at')
    op.drop_column('tenders', 'closed_at')
    op.drop_column('tenders', 'opened_at')
    op.drop_column('tenders', 'published_at')
