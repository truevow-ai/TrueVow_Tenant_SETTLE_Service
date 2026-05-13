"""add contribution_type to settlement_records

Revision ID: ffd820027e8c
Revises: 2a2b34987e9e
Create Date: 2026-03-09 17:46:30.984636

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffd820027e8c'
down_revision: Union[str, None] = '2a2b34987e9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('settlement_records', 
        sa.Column('contribution_type', sa.String(50), nullable=False, server_default='settlement_record')
    )
    # Create index for contribution type filtering
    op.create_index('idx_settlement_records_contribution_type', 'settlement_records', ['contribution_type'])


def downgrade() -> None:
    op.drop_index('idx_settlement_records_contribution_type', 'settlement_records')
    op.drop_column('settlement_records', 'contribution_type')
