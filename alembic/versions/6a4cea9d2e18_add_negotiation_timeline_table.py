"""add negotiation_timeline table

Revision ID: 6a4cea9d2e18
Revises: 7ff14731ed24
Create Date: 2026-03-09 11:47:24.288114

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a4cea9d2e18'
down_revision: Union[str, None] = '7ff14731ed24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'negotiation_timeline',
        sa.Column('event_id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('case_id', sa.UUID(), nullable=False, index=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False),  # demand_sent, insurer_offer, attorney_counter, settlement_recorded
        sa.Column('event_sequence', sa.Integer(), nullable=False),  # 1, 2, 3, ...
        sa.Column('amount', sa.Integer(), nullable=True),  # dollar amount if applicable
        sa.Column('party', sa.String(50), nullable=True),  # attorney, insurer
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('event_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_negotiation_timeline_case_seq', 'case_id', 'event_sequence'),
        sa.Index('idx_negotiation_timeline_type', 'case_id', 'event_type'),
    )


def downgrade() -> None:
    op.drop_table('negotiation_timeline')
