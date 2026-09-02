"""Add clarification requests and responses tables for Part 16

Revision ID: 031_add_clarifications
Revises: 030_add_rule_versions
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '031_add_clarifications'
down_revision: Union[str, None] = '030_add_rule_versions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create clarification_requests table
    if 'clarification_requests' not in tables:
        op.create_table(
            'clarification_requests',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('tender_id', UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False),
            sa.Column('bid_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=False),
            sa.Column('tender_organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('bidder_organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('created_by_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('assigned_bidder_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL'), nullable=True),
            sa.Column('subject', sa.String(255), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('clarification_type', sa.String(50), nullable=False, server_default='OTHER'),
            sa.Column('priority', sa.String(20), nullable=False, server_default='NORMAL'),
            sa.Column('status', sa.String(30), nullable=False, server_default='SENT'),
            sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('related_document_id', UUID(as_uuid=True), sa.ForeignKey('bid_documents.id', ondelete='SET NULL'), nullable=True),
            sa.Column('related_requirement_id', UUID(as_uuid=True), sa.ForeignKey('tender_requirements.id', ondelete='SET NULL'), nullable=True),
            sa.Column('related_rule_version_id', UUID(as_uuid=True), sa.ForeignKey('tender_requirement_versions.id', ondelete='SET NULL'), nullable=True),
            sa.Column('related_rule_version_number', sa.Integer(), nullable=True),
            sa.Column('related_verification_record_id', UUID(as_uuid=True), sa.ForeignKey('verification_records.id', ondelete='SET NULL'), nullable=True),
            sa.Column('related_compliance_result_id', UUID(as_uuid=True), sa.ForeignKey('compliance_results.id', ondelete='SET NULL'), nullable=True),
            sa.Column('related_review_item_id', UUID(as_uuid=True), sa.ForeignKey('human_review_items.id', ondelete='SET NULL'), nullable=True),
            sa.Column('related_duplicate_match_id', UUID(as_uuid=True), sa.ForeignKey('document_duplicate_matches.id', ondelete='SET NULL'), nullable=True),
            sa.Column('resolved_by_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL'), nullable=True),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('resolution_note', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        )

        op.create_index('ix_clarification_requests_tender_status', 'clarification_requests', ['tender_id', 'status'])
        op.create_index('ix_clarification_requests_bid_status', 'clarification_requests', ['bid_id', 'status'])
        op.create_index('ix_clarification_requests_tender_org', 'clarification_requests', ['tender_organization_id', 'status'])
        op.create_index('ix_clarification_requests_bidder_org', 'clarification_requests', ['bidder_organization_id', 'status'])
        op.create_index('ix_clarification_requests_due_date', 'clarification_requests', ['due_date'])
        op.create_index('ix_clarification_requests_type', 'clarification_requests', ['clarification_type'])
        op.create_index('ix_clarification_requests_priority', 'clarification_requests', ['priority'])

    # 2. Create clarification_responses table
    if 'clarification_responses' not in tables:
        op.create_table(
            'clarification_responses',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('clarification_request_id', UUID(as_uuid=True), sa.ForeignKey('clarification_requests.id', ondelete='CASCADE'), nullable=False),
            sa.Column('responded_by_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('response_text', sa.Text(), nullable=False),
            sa.Column('attached_document_id', UUID(as_uuid=True), sa.ForeignKey('bid_documents.id', ondelete='SET NULL'), nullable=True),
            sa.Column('is_replacement_document', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('replaced_document_id', UUID(as_uuid=True), sa.ForeignKey('bid_documents.id', ondelete='SET NULL'), nullable=True),
            sa.Column('metadata_json', JSONB, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        )

        op.create_index('ix_clarification_responses_request_id', 'clarification_responses', ['clarification_request_id'])
        op.create_index('ix_clarification_responses_created_at', 'clarification_responses', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'clarification_responses' in tables:
        op.drop_table('clarification_responses')
    if 'clarification_requests' in tables:
        op.drop_table('clarification_requests')
