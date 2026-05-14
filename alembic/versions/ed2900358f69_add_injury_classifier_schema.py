"""add_injury_classifier_schema

Revision ID: ed2900358f69
Revises: ec7e4c7db3be
Create Date: 2026-05-14 20:23:43.766492

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ed2900358f69'
down_revision: Union[str, None] = 'ec7e4c7db3be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Column 1: audit-trail JSONB for classifier provenance on settle_contributions.
    op.add_column(
        'settle_contributions',
        sa.Column(
            'injury_classification',
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    # Column 2: case-narrative TEXT (nullable; future Phase 3.5 populates from
    # news_provenance URLs via narrative-acquisition scraper cohort).
    op.add_column(
        'settle_contributions',
        sa.Column('case_narrative', sa.Text(), nullable=True),
    )

    # Table: injury_review_queue scaffold for Phase 4 review UI.
    # No rows inserted during Phase 3 — forward-looking schema only.
    op.create_table(
        'injury_review_queue',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            'contribution_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('settle_contributions.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('classification_snapshot', postgresql.JSONB(), nullable=False),
        sa.Column(
            'triggers',
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            'status',
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column('claimed_by', sa.Text(), nullable=True),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_action', sa.Text(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('final_tags', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        'idx_review_queue_status', 'injury_review_queue', ['status']
    )
    op.create_index(
        'idx_review_queue_contribution',
        'injury_review_queue',
        ['contribution_id'],
    )


def downgrade() -> None:
    op.drop_index('idx_review_queue_contribution', table_name='injury_review_queue')
    op.drop_index('idx_review_queue_status', table_name='injury_review_queue')
    op.drop_table('injury_review_queue')
    op.drop_column('settle_contributions', 'case_narrative')
    op.drop_column('settle_contributions', 'injury_classification')
