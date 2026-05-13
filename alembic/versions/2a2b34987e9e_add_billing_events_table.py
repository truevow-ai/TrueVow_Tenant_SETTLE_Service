"""add billing_events table

Revision ID: 2a2b34987e9e
Revises: 403bf5800eee
Create Date: 2026-03-09 12:45:33.343092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a2b34987e9e'
down_revision: Union[str, None] = '403bf5800eee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'billing_events',
        sa.Column('billing_event_id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('case_id', sa.UUID(), nullable=True, index=True),
        sa.Column('service', sa.String(50), nullable=False),  # settle, leverage, intake
        sa.Column('action', sa.String(100), nullable=False),  # settle_case_open, settlement_query_run, report_generated
        sa.Column('amount', sa.Integer(), nullable=True),  # billing amount in cents or units
        sa.Column('currency', sa.String(3), nullable=True, server_default='USD'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),  # pending, billed, waived, failed
        sa.Column('invoice_id', sa.String(100), nullable=True),  # reference to billing system invoice
        sa.Column('billed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Index('idx_billing_events_tenant_timestamp', 'tenant_id', 'timestamp'),
        sa.Index('idx_billing_events_service_action', 'service', 'action'),
        sa.Index('idx_billing_events_status', 'status'),
    )


def downgrade() -> None:
    op.drop_table('billing_events')
