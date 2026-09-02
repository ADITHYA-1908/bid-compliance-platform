"""Add structured extraction fields to document_processing for Part 4E

Revision ID: 011_structured_entity_extraction
Revises: 010_document_classification
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011_structured_entity_extraction'
down_revision: Union[str, None] = '010_document_classification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'document_processing',
        sa.Column('extracted_data', sa.JSON(), nullable=True),
    )
    op.add_column(
        'document_processing',
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
    )
    op.add_column(
        'document_processing',
        sa.Column(
            'extraction_requires_review',
            sa.Boolean(),
            server_default='false',
            nullable=False,
        ),
    )
    op.add_column(
        'document_processing',
        sa.Column('structured_extraction_method', sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('document_processing', 'structured_extraction_method')
    op.drop_column('document_processing', 'extraction_requires_review')
    op.drop_column('document_processing', 'extraction_confidence')
    op.drop_column('document_processing', 'extracted_data')
