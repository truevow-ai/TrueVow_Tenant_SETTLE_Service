"""add settle_case_snapshots table

Revision ID: 6244ebfd45df
Revises: 
Create Date: 2026-03-09 11:18:57.601262

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6244ebfd45df'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'settle_case_snapshots',
        sa.Column('snapshot_id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('case_id', sa.UUID(), nullable=False, index=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('incident_type', sa.String(50), nullable=False),
        sa.Column('injury_category', sa.String(50), nullable=False),
        sa.Column('county', sa.String(100), nullable=False),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('policy_limit_band', sa.String(20), nullable=True),
        sa.Column('insurer', sa.String(100), nullable=True),
        sa.Column('litigation_stage', sa.String(50), nullable=False, server_default='pre_suit'),
        sa.Column('medical_specials_band', sa.String(20), nullable=True),
        sa.Column('liability_strength', sa.String(20), nullable=False, server_default='moderate'),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Index('idx_settle_snapshots_case_active', 'case_id', 'is_active'),
        sa.Index('idx_settle_snapshots_query', 'state', 'county', 'incident_type', 'injury_category'),
    )


def downgrade() -> None:
    op.drop_table('settle_case_snapshots')
