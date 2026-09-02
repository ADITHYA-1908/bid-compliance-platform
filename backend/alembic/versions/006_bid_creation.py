"""Create bids table and relationships for Part 3C

Revision ID: 006_bid_creation
Revises: 005_bidder_profile
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_bid_creation'
down_revision: Union[str, None] = '005_bidder_profile'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bids',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('tender_id', sa.Uuid(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('bidder_organization_id', sa.Uuid(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_by_profile_id', sa.Uuid(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('bid_number', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='DRAFT', nullable=False),
        sa.Column('quoted_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('technical_summary', sa.Text(), nullable=True),
        sa.Column('commercial_notes', sa.Text(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('tender_id', 'bidder_organization_id', name='uq_bids_tender_organization'),
    )

    op.create_index(op.f('ix_bids_tender_id'), 'bids', ['tender_id'], unique=False)
    op.create_index(op.f('ix_bids_bidder_organization_id'), 'bids', ['bidder_organization_id'], unique=False)
    op.create_index(op.f('ix_bids_created_by_profile_id'), 'bids', ['created_by_profile_id'], unique=False)
    op.create_index(op.f('ix_bids_bid_number'), 'bids', ['bid_number'], unique=True)
    op.create_index(op.f('ix_bids_status'), 'bids', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_bids_status'), table_name='bids')
    op.drop_index(op.f('ix_bids_bid_number'), table_name='bids')
    op.drop_index(op.f('ix_bids_created_by_profile_id'), table_name='bids')
    op.drop_index(op.f('ix_bids_bidder_organization_id'), table_name='bids')
    op.drop_index(op.f('ix_bids_tender_id'), table_name='bids')
    op.drop_table('bids')
