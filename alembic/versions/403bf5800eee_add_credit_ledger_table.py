"""add credit_ledger table

Revision ID: 403bf5800eee
Revises: 6a4cea9d2e18
Create Date: 2026-03-09 12:42:05.473943

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '403bf5800eee'
down_revision: Union[str, None] = '6a4cea9d2e18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'credit_ledger',
        sa.Column('credit_id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('credit_type', sa.String(50), nullable=False),  # reward_validation, settle_success_credit
        sa.Column('source', sa.String(100), nullable=False),  # settlement_recorded, council_contribution, etc.
        sa.Column('source_reference', sa.String(100), nullable=True),  # case_id, contribution_id, etc.
        sa.Column('amount', sa.Integer(), nullable=False, server_default='1'),  # credit units
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),  # null = no expiration
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),  # null = unused
        sa.Column('consumed_by', sa.String(100), nullable=True),  # action that consumed the credit
        sa.Column('status', sa.String(20), nullable=False, server_default='available'),  # available, consumed, expired
        sa.Index('idx_credit_ledger_tenant_status', 'tenant_id', 'status'),
        sa.Index('idx_credit_ledger_expires', 'expires_at'),
        sa.Index('idx_credit_ledger_type', 'tenant_id', 'credit_type'),
    )


def downgrade() -> None:
    op.drop_table('credit_ledger')
