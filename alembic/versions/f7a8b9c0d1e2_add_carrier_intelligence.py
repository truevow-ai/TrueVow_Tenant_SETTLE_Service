"""add settle_carrier_intelligence table

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-07-10 23:55:00.000000

Links verified insurance-carrier intelligence facts (NAIC complaint indices,
SEC filings/reserves) to the carrier names used in settle_verdicts. Keyed by
the canonical carrier name so a verdict row can join to its carrier's
intelligence. Every fact retains source_url + evidence per the no-fabrication
directive; nothing enters this table without passing cis_fabrication_gate.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'settle_carrier_intelligence',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        # Canonical carrier name (matches settle_verdicts.insurance_carrier).
        sa.Column('carrier_name', sa.String(200), nullable=False, unique=True),
        sa.Column('naic_code', sa.String(10), nullable=True),
        sa.Column('legal_entity_names', postgresql.JSONB(), nullable=True),
        # Aggregated verified facts, each with value + source_url (+ evidence).
        sa.Column('fact_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('facts', postgresql.JSONB(), nullable=True),
        # Convenience rollups (all traceable back into facts[]).
        sa.Column('complaint_total', sa.Integer(), nullable=True),
        sa.Column('complaint_years', postgresql.JSONB(), nullable=True),
        sa.Column('has_sec_filings', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('source_datasets', postgresql.JSONB(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_carrier_intel_name', 'settle_carrier_intelligence', ['carrier_name'])
    op.create_index('idx_carrier_intel_naic', 'settle_carrier_intelligence', ['naic_code'])


def downgrade() -> None:
    op.drop_table('settle_carrier_intelligence')
