"""Add verification_records table for Part 5A

Revision ID: 012_verification_records
Revises: 011_structured_entity_extraction
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012_verification_records'
down_revision: Union[str, None] = '011_structured_entity_extraction'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'verification_records',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            'bid_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('bids.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'bid_document_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('bid_documents.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column(
            'document_processing_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('document_processing.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('verification_type', sa.String(50), nullable=False),
        sa.Column(
            'verification_status',
            sa.String(50),
            server_default='PENDING',
            nullable=False,
        ),
        sa.Column('source_name', sa.String(100), nullable=False),
        sa.Column('source_type', sa.String(50), server_default='MOCK', nullable=False),
        sa.Column('claim_source', sa.String(50), server_default='DOCUMENT', nullable=False),
        sa.Column('claimed_value', sa.Text(), nullable=False),
        sa.Column('verified_value', sa.Text(), nullable=True),
        sa.Column('match_status', sa.String(50), server_default='UNKNOWN', nullable=False),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('request_payload', sa.JSON(), nullable=True),
        sa.Column('response_payload', sa.JSON(), nullable=True),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('attempt_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column(
            'triggered_by_profile_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('profiles.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('trigger_source', sa.String(50), server_default='SYSTEM', nullable=False),
        sa.Column('verification_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verification_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )

    op.create_index(
        'ix_verification_records_bid_id',
        'verification_records',
        ['bid_id'],
    )
    op.create_index(
        'ix_verification_records_bid_document_id',
        'verification_records',
        ['bid_document_id'],
    )
    op.create_index(
        'ix_verification_records_document_processing_id',
        'verification_records',
        ['document_processing_id'],
    )
    op.create_index(
        'ix_verification_records_verification_type',
        'verification_records',
        ['verification_type'],
    )
    op.create_index(
        'ix_verification_records_verification_status',
        'verification_records',
        ['verification_status'],
    )
    op.create_index(
        'ix_verification_records_is_active',
        'verification_records',
        ['is_active'],
    )


def downgrade() -> None:
    op.drop_index('ix_verification_records_is_active', table_name='verification_records')
    op.drop_index('ix_verification_records_verification_status', table_name='verification_records')
    op.drop_index('ix_verification_records_verification_type', table_name='verification_records')
    op.drop_index('ix_verification_records_document_processing_id', table_name='verification_records')
    op.drop_index('ix_verification_records_bid_document_id', table_name='verification_records')
    op.drop_index('ix_verification_records_bid_id', table_name='verification_records')
    op.drop_table('verification_records')
