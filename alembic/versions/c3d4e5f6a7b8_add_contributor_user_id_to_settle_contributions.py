"""add_contributor_user_id_to_settle_contributions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-18

Adds contributor_user_id to settle_contributions — required for:
- AnomalyDetector._check_velocity() queries
- ReputationService.recalculate() queries
- Proper attribution of contributions to users

This column was missing from the original reputation migration (b2c3d4e5f6a7)
which only added it to settle_contribution_reputation, not to settle_contributions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'settle_contributions',
        sa.Column('contributor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_index(
        'idx_settle_contributions_contributor_user_id',
        'settle_contributions',
        ['contributor_user_id'],
    )


def downgrade() -> None:
    op.drop_index('idx_settle_contributions_contributor_user_id', table_name='settle_contributions')
    op.drop_column('settle_contributions', 'contributor_user_id')
