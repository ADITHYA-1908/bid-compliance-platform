"""Add is_critical to tender_requirements and compliance_results for Part 6E

Revision ID: 014_add_critical_rule_fields
Revises: 013_compliance_results
Create Date: 2026-08-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '014_add_critical_rule_fields'
down_revision: Union[str, None] = '013_compliance_results'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_critical column to tender_requirements
    op.add_column(
        'tender_requirements',
        sa.Column('is_critical', sa.Boolean(), nullable=False, server_default='false'),
    )

    # Add is_critical and critical_failure columns to compliance_results
    op.add_column(
        'compliance_results',
        sa.Column('is_critical', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'compliance_results',
        sa.Column('critical_failure', sa.Boolean(), nullable=False, server_default='false'),
    )

    op.create_index(
        'ix_compliance_results_bid_critical_failure',
        'compliance_results',
        ['bid_id', 'critical_failure'],
    )


def downgrade() -> None:
    op.drop_index('ix_compliance_results_bid_critical_failure', table_name='compliance_results')
    op.drop_column('compliance_results', 'critical_failure')
    op.drop_column('compliance_results', 'is_critical')
    op.drop_column('tender_requirements', 'is_critical')
