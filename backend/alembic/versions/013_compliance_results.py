"""Add compliance_results table for Part 6A

Revision ID: 013_compliance_results
Revises: 012_verification_records
Create Date: 2026-08-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013_compliance_results'
down_revision: Union[str, None] = '012_verification_records'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'compliance_results',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            'bid_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('bids.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'tender_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('tenders.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'tender_requirement_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('tender_requirements.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('compliance_status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('actual_value', sa.JSON(), nullable=True),
        sa.Column('expected_value', sa.JSON(), nullable=True),
        sa.Column('operator', sa.String(50), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('source_verification_ids', sa.JSON(), nullable=True),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('weight', sa.Numeric(precision=5, scale=2), nullable=True, server_default='10.0'),
        sa.Column('evaluation_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('ix_compliance_results_bid_id', 'compliance_results', ['bid_id'])
    op.create_index('ix_compliance_results_tender_id', 'compliance_results', ['tender_id'])
    op.create_index('ix_compliance_results_tender_requirement_id', 'compliance_results', ['tender_requirement_id'])
    op.create_index('ix_compliance_results_compliance_status', 'compliance_results', ['compliance_status'])
    op.create_index('ix_compliance_results_is_current', 'compliance_results', ['is_current'])
    op.create_index('ix_compliance_results_bid_req_current', 'compliance_results', ['bid_id', 'tender_requirement_id', 'is_current'])
    op.create_index('ix_compliance_results_bid_status', 'compliance_results', ['bid_id', 'compliance_status'])


def downgrade() -> None:
    op.drop_index('ix_compliance_results_bid_status', table_name='compliance_results')
    op.drop_index('ix_compliance_results_bid_req_current', table_name='compliance_results')
    op.drop_index('ix_compliance_results_is_current', table_name='compliance_results')
    op.drop_index('ix_compliance_results_compliance_status', table_name='compliance_results')
    op.drop_index('ix_compliance_results_tender_requirement_id', table_name='compliance_results')
    op.drop_index('ix_compliance_results_tender_id', table_name='compliance_results')
    op.drop_index('ix_compliance_results_bid_id', table_name='compliance_results')
    op.drop_table('compliance_results')
