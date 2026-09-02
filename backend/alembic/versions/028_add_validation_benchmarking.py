"""Add validation runs and case results tables for Empirical Validation & Benchmarking

Revision ID: 028_add_validation_benchmarking
Revises: 027_add_notifications
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '028_add_validation_benchmarking'
down_revision: Union[str, None] = '027_add_notifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'validation_runs' not in tables:
        op.create_table(
            'validation_runs',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('dataset_version', sa.String(50), nullable=False, server_default='v1.0'),
            sa.Column('engine_versions', JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
            sa.Column('total_cases', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('passed_cases', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('failed_cases', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('ocr_accuracy', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('classification_accuracy', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('field_extraction_accuracy', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('compliance_accuracy', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('true_positives', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('true_negatives', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('false_positives', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('false_negatives', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('precision', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('recall', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('f1_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('false_positive_rate', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('false_negative_rate', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('rag_retrieval_accuracy', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('rag_citation_accuracy', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('average_processing_time_ms', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('average_manual_time_sec', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('time_reduction_percentage', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('summary_json', JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        )
        op.create_index('ix_validation_runs_status_created', 'validation_runs', ['status', 'created_at'])
        op.create_index('ix_validation_runs_org_created', 'validation_runs', ['organization_id', 'created_at'])

    if 'validation_case_results' not in tables:
        op.create_table(
            'validation_case_results',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('validation_run_id', UUID(as_uuid=True), sa.ForeignKey('validation_runs.id', ondelete='CASCADE'), nullable=False),
            sa.Column('test_case_id', sa.String(100), nullable=False),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('category', sa.String(100), nullable=False),
            sa.Column('document_type', sa.String(100), nullable=False),
            sa.Column('quality_level', sa.String(50), nullable=False, server_default='GOOD'),
            sa.Column('expected_result_json', JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('actual_result_json', JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('is_correct', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('error_type', sa.String(50), nullable=False, server_default='NONE'),
            sa.Column('error_reason', sa.Text(), nullable=True),
            sa.Column('ocr_correct', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('ocr_accuracy', sa.Float(), nullable=False, server_default='100.0'),
            sa.Column('classification_correct', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('extraction_correct', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('compliance_correct', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('rag_correct', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('processing_time_ms', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('manual_baseline_sec', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('details_json', JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        )
        op.create_index('ix_case_results_run_correct', 'validation_case_results', ['validation_run_id', 'is_correct'])
        op.create_index('ix_case_results_category', 'validation_case_results', ['category'])


def downgrade() -> None:
    op.drop_table('validation_case_results')
    op.drop_table('validation_runs')
