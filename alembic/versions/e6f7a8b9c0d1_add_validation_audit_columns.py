"""add no-fabrication audit columns to settle_verdicts

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-07-09 08:30:00.000000

Per the no-fabrication prime directive: every field that reaches the DB is
verbatim-verified against source evidence. These columns record HOW MANY of a
record's fields were independently validated and the evidence (value + snippet
+ source_url) for each, so any row can be audited field-by-field.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('settle_verdicts',
                  sa.Column('validated_field_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('settle_verdicts',
                  sa.Column('validation_counts', postgresql.JSONB(), nullable=True))
    op.add_column('settle_verdicts',
                  sa.Column('field_evidence', postgresql.JSONB(), nullable=True))
    op.create_index('idx_settle_verdicts_validated_count', 'settle_verdicts',
                    ['validated_field_count'])


def downgrade() -> None:
    op.drop_index('idx_settle_verdicts_validated_count', table_name='settle_verdicts')
    op.drop_column('settle_verdicts', 'field_evidence')
    op.drop_column('settle_verdicts', 'validation_counts')
    op.drop_column('settle_verdicts', 'validated_field_count')
