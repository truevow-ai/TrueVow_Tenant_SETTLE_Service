"""add soft-delete columns to settle_verdicts

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-07-11 00:10:00.000000

The verdict search service filters every query by `deleted_at IS NULL`
(soft-delete). The initial settle_verdicts migration omitted these columns, so
the search API 400'd against live data. Add them so search works and rows can
be soft-deleted (never hard-deleted) by reviewers.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('settle_verdicts', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('settle_verdicts', sa.Column('deleted_by', sa.UUID(), nullable=True))
    op.create_index('idx_settle_verdicts_deleted_at', 'settle_verdicts', ['deleted_at'])


def downgrade() -> None:
    op.drop_index('idx_settle_verdicts_deleted_at', table_name='settle_verdicts')
    op.drop_column('settle_verdicts', 'deleted_by')
    op.drop_column('settle_verdicts', 'deleted_at')
