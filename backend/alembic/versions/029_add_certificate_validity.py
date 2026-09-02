"""Add document validity records table for Certificate Validity Monitoring

Revision ID: 029_add_certificate_validity
Revises: 028_add_validation_benchmarking
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '029_add_certificate_validity'
down_revision: Union[str, None] = '028_add_validation_benchmarking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'document_validity_records' not in tables:
        op.create_table(
            'document_validity_records',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('bid_documents.id', ondelete='CASCADE'), nullable=False),
            sa.Column('bid_id', UUID(as_uuid=True), sa.ForeignKey('bids.id', ondelete='SET NULL'), nullable=True),
            sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('document_type', sa.String(100), nullable=False, server_default='OTHER'),
            sa.Column('issue_date', sa.Date(), nullable=True),
            sa.Column('expiry_date', sa.Date(), nullable=True),
            sa.Column('validity_status', sa.String(50), nullable=False, server_default='UNKNOWN'),
            sa.Column('days_until_expiry', sa.Integer(), nullable=True),
            sa.Column('date_source', sa.String(50), nullable=False, server_default='STRUCTURED_EXTRACTION'),
            sa.Column('source_page', sa.Integer(), nullable=True),
            sa.Column('source_text', sa.Text(), nullable=True),
            sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
            sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('submission_validity_status', sa.String(50), nullable=True),
            sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('next_check_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('metadata_json', JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

        op.create_index('ix_doc_validity_doc_id', 'document_validity_records', ['document_id'])
        op.create_index('ix_doc_validity_bid_id', 'document_validity_records', ['bid_id'])
        op.create_index('ix_doc_validity_org_id', 'document_validity_records', ['organization_id'])
        op.create_index('ix_doc_validity_status', 'document_validity_records', ['validity_status'])
        op.create_index('ix_doc_validity_expiry', 'document_validity_records', ['expiry_date'])
        op.create_index('ix_doc_validity_current', 'document_validity_records', ['is_current'])
        op.create_index('ix_doc_validity_org_status', 'document_validity_records', ['organization_id', 'validity_status'])
        op.create_index('ix_doc_validity_bid_current', 'document_validity_records', ['bid_id', 'is_current'])
        op.create_index('ix_doc_validity_expiry_status', 'document_validity_records', ['expiry_date', 'validity_status'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'document_validity_records' in tables:
        op.drop_table('document_validity_records')
