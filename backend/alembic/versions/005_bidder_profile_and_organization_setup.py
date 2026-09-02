"""Add bidder profile and organization setup fields for Part 3A

Revision ID: 005_bidder_profile_and_organization_setup
Revises: 004_tender_lifecycle
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_bidder_profile'
down_revision: Union[str, None] = '004_tender_lifecycle'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add extended organization details & statutory fields to 'organizations'
    op.add_column('organizations', sa.Column('trade_name', sa.String(length=255), nullable=True))
    op.add_column('organizations', sa.Column('business_category', sa.String(length=100), nullable=True))
    op.add_column('organizations', sa.Column('year_established', sa.Integer(), nullable=True))
    op.add_column('organizations', sa.Column('registered_address', sa.Text(), nullable=True))
    op.add_column('organizations', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('organizations', sa.Column('state', sa.String(length=100), nullable=True))
    op.add_column('organizations', sa.Column('pincode', sa.String(length=20), nullable=True))
    op.add_column('organizations', sa.Column('country', sa.String(length=100), server_default='India', nullable=True))
    op.add_column('organizations', sa.Column('official_email', sa.String(length=255), nullable=True))
    op.add_column('organizations', sa.Column('official_phone', sa.String(length=50), nullable=True))
    op.add_column('organizations', sa.Column('website', sa.String(length=255), nullable=True))
    op.add_column('organizations', sa.Column('pan_number', sa.String(length=20), nullable=True))
    op.add_column('organizations', sa.Column('gstin', sa.String(length=25), nullable=True))
    op.add_column('organizations', sa.Column('udyam_number', sa.String(length=50), nullable=True))
    op.add_column('organizations', sa.Column('cin_llpin', sa.String(length=50), nullable=True))
    op.add_column('organizations', sa.Column('startup_india_number', sa.String(length=50), nullable=True))
    op.add_column('organizations', sa.Column('nsic_number', sa.String(length=50), nullable=True))
    op.add_column('organizations', sa.Column('epfo_code', sa.String(length=50), nullable=True))
    op.add_column('organizations', sa.Column('esic_code', sa.String(length=50), nullable=True))

    op.create_index(op.f('ix_organizations_pan_number'), 'organizations', ['pan_number'], unique=False)
    op.create_index(op.f('ix_organizations_gstin'), 'organizations', ['gstin'], unique=False)
    op.create_index(op.f('ix_organizations_udyam_number'), 'organizations', ['udyam_number'], unique=False)

    # Add contact phone and designation to 'profiles'
    op.add_column('profiles', sa.Column('phone', sa.String(length=50), nullable=True))
    op.add_column('profiles', sa.Column('designation', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Drop profile columns
    op.drop_column('profiles', 'designation')
    op.drop_column('profiles', 'phone')

    # Drop organization indices and columns
    op.drop_index(op.f('ix_organizations_udyam_number'), table_name='organizations')
    op.drop_index(op.f('ix_organizations_gstin'), table_name='organizations')
    op.drop_index(op.f('ix_organizations_pan_number'), table_name='organizations')

    op.drop_column('organizations', 'esic_code')
    op.drop_column('organizations', 'epfo_code')
    op.drop_column('organizations', 'nsic_number')
    op.drop_column('organizations', 'startup_india_number')
    op.drop_column('organizations', 'cin_llpin')
    op.drop_column('organizations', 'udyam_number')
    op.drop_column('organizations', 'gstin')
    op.drop_column('organizations', 'pan_number')
    op.drop_column('organizations', 'website')
    op.drop_column('organizations', 'official_phone')
    op.drop_column('organizations', 'official_email')
    op.drop_column('organizations', 'country')
    op.drop_column('organizations', 'pincode')
    op.drop_column('organizations', 'state')
    op.drop_column('organizations', 'city')
    op.drop_column('organizations', 'registered_address')
    op.drop_column('organizations', 'year_established')
    op.drop_column('organizations', 'business_category')
    op.drop_column('organizations', 'trade_name')
