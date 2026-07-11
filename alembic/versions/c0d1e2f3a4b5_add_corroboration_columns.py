"""add corroboration columns to settle_verdicts

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-07-11 03:30:00.000000

Multi-source corroboration: a verdict is promoted from review_status='pending'
to 'verified' ONLY when the same case (by official citation, or normalized
case name + state) appears in >=2 INDEPENDENT sources (static.case.law / CAP,
CourtListener, MoreLaw) that AGREE on the outcome amount. This is a machine
substitute for human verification — promotion requires real cross-source
agreement, never a guess. These columns record the evidence of that agreement
so any 'verified' status is auditable.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c0d1e2f3a4b5'
down_revision: Union[str, None] = 'b9c0d1e2f3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('settle_verdicts',
                  sa.Column('corroboration_count', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('settle_verdicts',
                  sa.Column('corroborating_sources', postgresql.JSONB(), nullable=True))
    op.create_index('idx_settle_verdicts_corroboration', 'settle_verdicts', ['corroboration_count'])


def downgrade() -> None:
    op.drop_index('idx_settle_verdicts_corroboration', table_name='settle_verdicts')
    op.drop_column('settle_verdicts', 'corroborating_sources')
    op.drop_column('settle_verdicts', 'corroboration_count')
