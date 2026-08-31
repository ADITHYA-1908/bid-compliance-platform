"""Create bid_documents table and relationships for Part 3D

Revision ID: 007_bid_documents
Revises: 006_bid_creation
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_bid_documents'
down_revision: Union[str, None] = '006_bid_creation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bid_documents',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('bid_id', sa.Uuid(as_uuid=True), sa.ForeignKey('bids.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tender_requirement_id', sa.Uuid(as_uuid=True), sa.ForeignKey('tender_requirements.id', ondelete='SET NULL'), nullable=True),
        sa.Column('uploaded_by_profile_id', sa.Uuid(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('document_type', sa.String(length=100), nullable=False),
        sa.Column('document_name', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='UPLOADED', nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index(op.f('ix_bid_documents_bid_id'), 'bid_documents', ['bid_id'], unique=False)
    op.create_index(op.f('ix_bid_documents_tender_requirement_id'), 'bid_documents', ['tender_requirement_id'], unique=False)
    op.create_index(op.f('ix_bid_documents_uploaded_by_profile_id'), 'bid_documents', ['uploaded_by_profile_id'], unique=False)
    op.create_index(op.f('ix_bid_documents_document_type'), 'bid_documents', ['document_type'], unique=False)
    op.create_index(op.f('ix_bid_documents_is_active'), 'bid_documents', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_bid_documents_is_active'), table_name='bid_documents')
    op.drop_index(op.f('ix_bid_documents_document_type'), table_name='bid_documents')
    op.drop_index(op.f('ix_bid_documents_uploaded_by_profile_id'), table_name='bid_documents')
    op.drop_index(op.f('ix_bid_documents_tender_requirement_id'), table_name='bid_documents')
    op.drop_index(op.f('ix_bid_documents_bid_id'), table_name='bid_documents')
    op.drop_table('bid_documents')
