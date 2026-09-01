"""Add bulk_evaluation_jobs and bulk_evaluation_job_items tables for Part 9 Bulk Verification & Batch Processing

Revision ID: 024_add_bulk_evaluation_jobs
Revises: 023_add_audit_events
Create Date: 2026-08-31

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '024_add_bulk_evaluation_jobs'
down_revision: Union[str, None] = '023_add_audit_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create bulk_evaluation_jobs table
    op.create_table(
        'bulk_evaluation_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tender_id', UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='QUEUED'),
        sa.Column('total_bids', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_bids', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_bids', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_bids', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('review_required_bids', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('critical_findings_bids', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_summary', JSONB, nullable=True),
        sa.Column('started_by_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_bulk_jobs_tender_status', 'bulk_evaluation_jobs', ['tender_id', 'status'])
    op.create_index('ix_bulk_jobs_org_created', 'bulk_evaluation_jobs', ['organization_id', 'created_at'])
    op.create_index('ix_bulk_evaluation_jobs_tender_id', 'bulk_evaluation_jobs', ['tender_id'])
    op.create_index('ix_bulk_evaluation_jobs_organization_id', 'bulk_evaluation_jobs', ['organization_id'])
    op.create_index('ix_bulk_evaluation_jobs_status', 'bulk_evaluation_jobs', ['status'])

    # 2. Create bulk_evaluation_job_items table
    op.create_table(
        'bulk_evaluation_job_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('job_id', UUID(as_uuid=True), sa.ForeignKey('bulk_evaluation_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bid_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='QUEUED'),
        sa.Column('current_stage', sa.String(50), nullable=False, server_default='QUEUED'),
        sa.Column('document_processing_status', sa.String(50), nullable=False, server_default='NONE'),
        sa.Column('verification_status', sa.String(50), nullable=False, server_default='NONE'),
        sa.Column('compliance_status', sa.String(50), nullable=False, server_default='NONE'),
        sa.Column('score_status', sa.String(50), nullable=False, server_default='NONE'),
        sa.Column('risk_status', sa.String(50), nullable=False, server_default='NONE'),
        sa.Column('final_score', sa.Float(), nullable=True),
        sa.Column('risk_level', sa.String(50), nullable=True),
        sa.Column('review_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('critical_findings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('is_retryable', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('ix_bulk_items_job_status', 'bulk_evaluation_job_items', ['job_id', 'status'])
    op.create_index('ix_bulk_items_bid', 'bulk_evaluation_job_items', ['bid_id'])
    op.create_index('ix_bulk_evaluation_job_items_job_id', 'bulk_evaluation_job_items', ['job_id'])
    op.create_index('ix_bulk_evaluation_job_items_bid_id', 'bulk_evaluation_job_items', ['bid_id'])
    op.create_index('ix_bulk_evaluation_job_items_status', 'bulk_evaluation_job_items', ['status'])


def downgrade() -> None:
    op.drop_index('ix_bulk_evaluation_job_items_status', table_name='bulk_evaluation_job_items')
    op.drop_index('ix_bulk_evaluation_job_items_bid_id', table_name='bulk_evaluation_job_items')
    op.drop_index('ix_bulk_evaluation_job_items_job_id', table_name='bulk_evaluation_job_items')
    op.drop_index('ix_bulk_items_bid', table_name='bulk_evaluation_job_items')
    op.drop_index('ix_bulk_items_job_status', table_name='bulk_evaluation_job_items')
    op.drop_table('bulk_evaluation_job_items')

    op.drop_index('ix_bulk_evaluation_jobs_status', table_name='bulk_evaluation_jobs')
    op.drop_index('ix_bulk_evaluation_jobs_organization_id', table_name='bulk_evaluation_jobs')
    op.drop_index('ix_bulk_evaluation_jobs_tender_id', table_name='bulk_evaluation_jobs')
    op.drop_index('ix_bulk_jobs_org_created', table_name='bulk_evaluation_jobs')
    op.drop_index('ix_bulk_jobs_tender_status', table_name='bulk_evaluation_jobs')
    op.drop_table('bulk_evaluation_jobs')
