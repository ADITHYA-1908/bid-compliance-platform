"""Add tender requirement versions table and link to compliance results for Part 15

Revision ID: 030_add_rule_versions
Revises: 029_add_certificate_validity
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '030_add_rule_versions'
down_revision: Union[str, None] = '029_add_certificate_validity'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create tender_requirement_versions table
    if 'tender_requirement_versions' not in tables:
        op.create_table(
            'tender_requirement_versions',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('tender_requirement_id', UUID(as_uuid=True), sa.ForeignKey('tender_requirements.id', ondelete='CASCADE'), nullable=False),
            sa.Column('tender_id', UUID(as_uuid=True), sa.ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False),
            sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('code', sa.String(100), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('category', sa.String(50), nullable=False, server_default='STATUTORY'),
            sa.Column('requirement_type', sa.String(50), nullable=False, server_default='BOOLEAN'),
            sa.Column('operator', sa.String(50), nullable=False, server_default='EQUALS'),
            sa.Column('expected_value', JSONB, nullable=True),
            sa.Column('unit', sa.String(50), nullable=True),
            sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('is_critical', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('weight', sa.Numeric(precision=5, scale=2), nullable=True, server_default='10.0'),
            sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('source_clause', sa.String(255), nullable=True),
            sa.Column('source_page', sa.Integer(), nullable=True),
            sa.Column('corrigendum_number', sa.String(100), nullable=True),
            sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
            sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
            sa.Column('change_reason', sa.Text(), nullable=True),
            sa.Column('changed_by_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL'), nullable=True),
            sa.Column('change_metadata', JSONB, nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

        op.create_index('ix_tender_req_ver_req_id', 'tender_requirement_versions', ['tender_requirement_id'])
        op.create_index('ix_tender_req_ver_tender_id', 'tender_requirement_versions', ['tender_id'])
        op.create_index('ix_tender_req_ver_num', 'tender_requirement_versions', ['tender_requirement_id', 'version_number'], unique=True)
        op.create_index('ix_tender_req_ver_active', 'tender_requirement_versions', ['is_active'])

    # 2. Add columns to tender_requirements if missing
    req_cols = [c['name'] for c in inspector.get_columns('tender_requirements')]
    if 'current_version_number' not in req_cols:
        op.add_column('tender_requirements', sa.Column('current_version_number', sa.Integer(), nullable=False, server_default='1'))
    if 'unit' not in req_cols:
        op.add_column('tender_requirements', sa.Column('unit', sa.String(50), nullable=True))
    if 'source_clause' not in req_cols:
        op.add_column('tender_requirements', sa.Column('source_clause', sa.String(255), nullable=True))
    if 'source_page' not in req_cols:
        op.add_column('tender_requirements', sa.Column('source_page', sa.Integer(), nullable=True))
    if 'corrigendum_number' not in req_cols:
        op.add_column('tender_requirements', sa.Column('corrigendum_number', sa.String(100), nullable=True))
    if 'effective_from' not in req_cols:
        op.add_column('tender_requirements', sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True))
    if 'effective_to' not in req_cols:
        op.add_column('tender_requirements', sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True))
    if 'change_reason' not in req_cols:
        op.add_column('tender_requirements', sa.Column('change_reason', sa.Text(), nullable=True))
    if 'last_changed_by_profile_id' not in req_cols:
        op.add_column('tender_requirements', sa.Column('last_changed_by_profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL'), nullable=True))

    # 3. Add columns to compliance_results if missing
    comp_cols = [c['name'] for c in inspector.get_columns('compliance_results')]
    if 'rule_version_id' not in comp_cols:
        op.add_column('compliance_results', sa.Column('rule_version_id', UUID(as_uuid=True), sa.ForeignKey('tender_requirement_versions.id', ondelete='SET NULL'), nullable=True))
        op.create_index('ix_compliance_results_rule_ver_id', 'compliance_results', ['rule_version_id'])
    if 'rule_version_number' not in comp_cols:
        op.add_column('compliance_results', sa.Column('rule_version_number', sa.Integer(), nullable=True, server_default='1'))

    # 4. Data Migration: Seed Version 1 records for existing tender_requirements
    conn.execute(sa.text("""
        INSERT INTO tender_requirement_versions (
            id,
            tender_requirement_id,
            tender_id,
            version_number,
            code,
            name,
            description,
            category,
            requirement_type,
            operator,
            expected_value,
            unit,
            is_mandatory,
            is_critical,
            weight,
            display_order,
            source_clause,
            source_page,
            corrigendum_number,
            change_reason,
            is_active,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),
            id,
            tender_id,
            1,
            code,
            name,
            description,
            category,
            requirement_type,
            operator,
            expected_value,
            unit,
            is_mandatory,
            is_critical,
            weight,
            display_order,
            source_clause,
            source_page,
            corrigendum_number,
            'Initial baseline requirement version',
            is_active,
            created_at,
            created_at
        FROM tender_requirements
        ON CONFLICT (tender_requirement_id, version_number) DO NOTHING;
    """))

    # 5. Data Migration: Backfill compliance_results with matching rule_version_id
    conn.execute(sa.text("""
        UPDATE compliance_results
        SET rule_version_id = trv.id,
            rule_version_number = 1
        FROM tender_requirement_versions trv
        WHERE compliance_results.tender_requirement_id = trv.tender_requirement_id
          AND trv.version_number = 1
          AND compliance_results.rule_version_id IS NULL;
    """))


def downgrade() -> None:
    op.drop_index('ix_compliance_results_rule_ver_id', table_name='compliance_results')
    op.drop_column('compliance_results', 'rule_version_number')
    op.drop_column('compliance_results', 'rule_version_id')

    op.drop_column('tender_requirements', 'last_changed_by_profile_id')
    op.drop_column('tender_requirements', 'change_reason')
    op.drop_column('tender_requirements', 'effective_to')
    op.drop_column('tender_requirements', 'effective_from')
    op.drop_column('tender_requirements', 'corrigendum_number')
    op.drop_column('tender_requirements', 'source_page')
    op.drop_column('tender_requirements', 'source_clause')
    op.drop_column('tender_requirements', 'unit')
    op.drop_column('tender_requirements', 'current_version_number')

    op.drop_index('ix_tender_req_ver_active', table_name='tender_requirement_versions')
    op.drop_index('ix_tender_req_ver_num', table_name='tender_requirement_versions')
    op.drop_index('ix_tender_req_ver_tender_id', table_name='tender_requirement_versions')
    op.drop_index('ix_tender_req_ver_req_id', table_name='tender_requirement_versions')
    op.drop_table('tender_requirement_versions')
