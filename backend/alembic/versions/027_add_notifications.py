"""Add notifications table for Part 12: Notification Center

Revision ID: 027_add_notifications
Revises: 026_add_document_quality
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '027_add_notifications'
down_revision: Union[str, None] = '026_add_document_quality'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'notifications' not in tables:
        op.create_table(
            'notifications',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('recipient_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
            sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('tender_id', UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=True),
            sa.Column('bid_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=True),
            sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('bid_documents.id', ondelete='SET NULL'), nullable=True),
            sa.Column('notification_type', sa.String(64), nullable=False),
            sa.Column('severity', sa.String(32), nullable=False, server_default='INFO'),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('action_url', sa.String(512), nullable=True),
            sa.Column('dedupe_key', sa.String(255), nullable=True),
            sa.Column('metadata_json', JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        )

        op.create_index('ix_notifications_recipient_profile_id', 'notifications', ['recipient_profile_id'])
        op.create_index('ix_notifications_organization_id', 'notifications', ['organization_id'])
        op.create_index('ix_notifications_tender_id', 'notifications', ['tender_id'])
        op.create_index('ix_notifications_bid_id', 'notifications', ['bid_id'])
        op.create_index('ix_notifications_document_id', 'notifications', ['document_id'])
        op.create_index('ix_notifications_notification_type', 'notifications', ['notification_type'])
        op.create_index('ix_notifications_severity', 'notifications', ['severity'])
        op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
        op.create_index('ix_notifications_dedupe_key', 'notifications', ['dedupe_key'])
        op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])
        op.create_index(
            'ix_notifications_recipient_unread_created',
            'notifications',
            ['recipient_profile_id', 'is_read', 'created_at']
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'notifications' in tables:
        op.drop_index('ix_notifications_recipient_unread_created', table_name='notifications')
        op.drop_index('ix_notifications_created_at', table_name='notifications')
        op.drop_index('ix_notifications_dedupe_key', table_name='notifications')
        op.drop_index('ix_notifications_is_read', table_name='notifications')
        op.drop_index('ix_notifications_severity', table_name='notifications')
        op.drop_index('ix_notifications_notification_type', table_name='notifications')
        op.drop_index('ix_notifications_document_id', table_name='notifications')
        op.drop_index('ix_notifications_bid_id', table_name='notifications')
        op.drop_index('ix_notifications_tender_id', table_name='notifications')
        op.drop_index('ix_notifications_organization_id', table_name='notifications')
        op.drop_index('ix_notifications_recipient_profile_id', table_name='notifications')
        op.drop_table('notifications')
