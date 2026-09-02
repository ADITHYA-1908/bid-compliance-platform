"""Add submission and declaration audit fields to bids for Part 3E

Revision ID: 008_bid_submission
Revises: 007_bid_documents
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_bid_submission'
down_revision: Union[str, None] = '007_bid_documents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'bids',
        sa.Column(
            'submitted_by_profile_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('profiles.id', ondelete='RESTRICT'),
            nullable=True,
        )
    )
    op.add_column(
        'bids',
        sa.Column(
            'declaration_accepted',
            sa.Boolean(),
            server_default='false',
            nullable=False,
        )
    )
    op.add_column(
        'bids',
        sa.Column(
            'declaration_accepted_at',
            sa.DateTime(timezone=True),
            nullable=True,
        )
    )
    op.add_column(
        'bids',
        sa.Column(
            'submission_reference',
            sa.String(100),
            nullable=True,
        )
    )
    op.create_index(
        'ix_bids_submitted_by_profile_id',
        'bids',
        ['submitted_by_profile_id'],
    )
    op.create_index(
        'ix_bids_submission_reference',
        'bids',
        ['submission_reference'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_bids_submission_reference', table_name='bids')
    op.drop_index('ix_bids_submitted_by_profile_id', table_name='bids')
    op.drop_column('bids', 'submission_reference')
    op.drop_column('bids', 'declaration_accepted_at')
    op.drop_column('bids', 'declaration_accepted')
    op.drop_column('bids', 'submitted_by_profile_id')
