"""Add audit_events table for Part 8E Audit Trail & Decision History

Revision ID: 023_add_audit_events
Revises: 022_add_bid_decisions
Create Date: 2026-08-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '023_add_audit_events'
down_revision: Union[str, None] = '022_add_bid_decisions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create audit_events table
    op.create_table(
        'audit_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tender_id', UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=True),
        sa.Column('bid_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=True),
        sa.Column('actor_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_name', sa.String(255), nullable=True),
        sa.Column('actor_role', sa.String(50), nullable=True),
        sa.Column('actor_source', sa.String(50), nullable=False, server_default='HUMAN'),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('metadata_json', JSONB, nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(100), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # 2. Compound and single-column indexes for fast multi-dimensional search & timelines
    op.create_index('ix_audit_events_org_created', 'audit_events', ['organization_id', 'created_at'])
    op.create_index('ix_audit_events_tender_created', 'audit_events', ['tender_id', 'created_at'])
    op.create_index('ix_audit_events_bid_created', 'audit_events', ['bid_id', 'created_at'])
    op.create_index('ix_audit_events_type_created', 'audit_events', ['event_type', 'created_at'])
    op.create_index('ix_audit_events_actor_created', 'audit_events', ['actor_user_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_audit_events_actor_created', table_name='audit_events')
    op.drop_index('ix_audit_events_type_created', table_name='audit_events')
    op.drop_index('ix_audit_events_bid_created', table_name='audit_events')
    op.drop_index('ix_audit_events_tender_created', table_name='audit_events')
    op.drop_index('ix_audit_events_org_created', table_name='audit_events')
    op.drop_table('audit_events')
