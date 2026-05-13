"""add settle_events table

Revision ID: 7ff14731ed24
Revises: 579516014f19
Create Date: 2026-03-09 11:24:33.875988

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ff14731ed24'
down_revision: Union[str, None] = '579516014f19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'settle_events',
        sa.Column('event_id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('case_id', sa.UUID(), nullable=True, index=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_source', sa.String(50), nullable=False, server_default='settle_service'),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_settle_events_type', 'event_type'),
        sa.Index('idx_settle_events_occurred', 'occurred_at'),
        sa.Index('idx_settle_events_tenant_type', 'tenant_id', 'event_type'),
    )


def downgrade() -> None:
    op.drop_table('settle_events')
