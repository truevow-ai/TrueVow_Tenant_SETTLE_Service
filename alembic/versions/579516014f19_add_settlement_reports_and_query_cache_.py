"""add settlement_reports and query_cache tables

Revision ID: 579516014f19
Revises: 33175e3b6200
Create Date: 2026-03-09 11:22:56.408457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '579516014f19'
down_revision: Union[str, None] = '33175e3b6200'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # settlement_reports table
    op.create_table(
        'settlement_reports',
        sa.Column('report_id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('case_id', sa.UUID(), nullable=False, index=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('query_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('p25', sa.Integer(), nullable=False),
        sa.Column('median', sa.Integer(), nullable=False),
        sa.Column('p75', sa.Integer(), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False),
        sa.Column('confidence_score', sa.Integer(), nullable=False),
        sa.Column('avg_similarity_score', sa.Float(), nullable=False),
        sa.Column('expansion_level', sa.String(20), nullable=False, server_default='county'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # settlement_query_cache table
    op.create_table(
        'settlement_query_cache',
        sa.Column('cache_id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('query_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('incident_type', sa.String(50), nullable=False),
        sa.Column('injury_category', sa.String(50), nullable=False),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('county', sa.String(100), nullable=True),
        sa.Column('p25', sa.Integer(), nullable=False),
        sa.Column('median', sa.Integer(), nullable=False),
        sa.Column('p75', sa.Integer(), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Index('idx_query_cache_expires', 'expires_at'),
    )


def downgrade() -> None:
    op.drop_table('settlement_query_cache')
    op.drop_table('settlement_reports')
