"""Add classification fields to document_processing for Part 4D

Revision ID: 010_document_classification
Revises: 009_document_processing
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_document_classification'
down_revision: Union[str, None] = '009_document_processing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'document_processing',
        sa.Column('detected_document_type', sa.String(100), nullable=True),
    )
    op.add_column(
        'document_processing',
        sa.Column('classification_confidence', sa.Float(), nullable=True),
    )
    op.add_column(
        'document_processing',
        sa.Column('classification_method', sa.String(50), nullable=True),
    )
    op.add_column(
        'document_processing',
        sa.Column('classification_reason', sa.Text(), nullable=True),
    )
    op.add_column(
        'document_processing',
        sa.Column(
            'classification_requires_review',
            sa.Boolean(),
            server_default='false',
            nullable=False,
        ),
    )

    op.create_index(
        'ix_document_processing_detected_document_type',
        'document_processing',
        ['detected_document_type'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_document_processing_detected_document_type',
        table_name='document_processing',
    )
    op.drop_column('document_processing', 'classification_requires_review')
    op.drop_column('document_processing', 'classification_reason')
    op.drop_column('document_processing', 'classification_method')
    op.drop_column('document_processing', 'classification_confidence')
    op.drop_column('document_processing', 'detected_document_type')
