"""Add tenders and tender_requirements tables for Part 2A Tender Management

Revision ID: 003_add_tenders_and_requirements
Revises: 002_add_users_table
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_tenders_and_requirements'
down_revision: Union[str, None] = '002_add_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create 'tenders' table
    op.create_table(
        'tenders',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tender_number', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('procurement_type', sa.String(length=50), nullable=True),
        sa.Column('estimated_value', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('publish_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submission_start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submission_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evaluation_start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('created_by_profile_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='DRAFT', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_profile_id'], ['profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tenders_tender_number'), 'tenders', ['tender_number'], unique=True)
    op.create_index(op.f('ix_tenders_status'), 'tenders', ['status'], unique=False)
    op.create_index(op.f('ix_tenders_organization_id'), 'tenders', ['organization_id'], unique=False)
    op.create_index(op.f('ix_tenders_created_by_profile_id'), 'tenders', ['created_by_profile_id'], unique=False)

    # 2. Create 'tender_requirements' table
    op.create_table(
        'tender_requirements',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tender_id', sa.Uuid(), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), server_default='STATUTORY', nullable=False),
        sa.Column('requirement_type', sa.String(length=50), server_default='BOOLEAN', nullable=False),
        sa.Column('operator', sa.String(length=50), server_default='EQUALS', nullable=False),
        sa.Column('expected_value', sa.JSON(), nullable=True),
        sa.Column('is_mandatory', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('weight', sa.Numeric(precision=5, scale=2), server_default='10.0', nullable=True),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('weight >= 0', name='ck_tender_requirements_weight_positive'),
        sa.CheckConstraint('display_order >= 0', name='ck_tender_requirements_display_order_positive'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tender_requirements_tender_id'), 'tender_requirements', ['tender_id'], unique=False)
    op.create_index(op.f('ix_tender_requirements_code'), 'tender_requirements', ['code'], unique=False)


def downgrade() -> None:
    # 1. Drop 'tender_requirements' table
    op.drop_index(op.f('ix_tender_requirements_code'), table_name='tender_requirements')
    op.drop_index(op.f('ix_tender_requirements_tender_id'), table_name='tender_requirements')
    op.drop_table('tender_requirements')

    # 2. Drop 'tenders' table
    op.drop_index(op.f('ix_tenders_created_by_profile_id'), table_name='tenders')
    op.drop_index(op.f('ix_tenders_organization_id'), table_name='tenders')
    op.drop_index(op.f('ix_tenders_status'), table_name='tenders')
    op.drop_index(op.f('ix_tenders_tender_number'), table_name='tenders')
    op.drop_table('tenders')
