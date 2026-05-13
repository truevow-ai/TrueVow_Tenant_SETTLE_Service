"""add settlement_records table

Revision ID: 33175e3b6200
Revises: 6244ebfd45df
Create Date: 2026-03-09 11:21:23.349622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33175e3b6200'
down_revision: Union[str, None] = '6244ebfd45df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'settlement_records',
        sa.Column('record_id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('contributor_tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('case_fingerprint_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('county', sa.String(100), nullable=False),
        sa.Column('incident_type', sa.String(50), nullable=False),
        sa.Column('injury_category', sa.String(50), nullable=False),
        sa.Column('medical_specials_band', sa.String(20), nullable=True),
        sa.Column('policy_limit_band', sa.String(20), nullable=True),
        sa.Column('insurer', sa.String(100), nullable=True),
        sa.Column('litigation_stage', sa.String(50), nullable=False, server_default='pre_suit'),
        sa.Column('liability_strength', sa.String(20), nullable=False, server_default='moderate'),
        sa.Column('settlement_band', sa.String(20), nullable=False),
        sa.Column('settlement_month', sa.Date(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Index('idx_settlement_records_fingerprint', 'case_fingerprint_hash'),
        sa.Index('idx_settlement_records_query', 'state', 'county', 'incident_type', 'injury_category'),
        sa.Index('idx_settlement_records_submitted', 'submitted_at'),
    )


def downgrade() -> None:
    op.drop_table('settlement_records')
