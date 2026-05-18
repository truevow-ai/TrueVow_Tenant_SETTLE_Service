"""add_reputation_and_anomaly_detection

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-17

Adds reputation scoring and anomaly detection infrastructure:
- settle_contribution_reputation table (per-attorney trust scores)
- settle_anomaly_flags table (per-submission anomaly tracking)
- New columns on settle_contributions for reputation integration
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Table: settle_contribution_reputation
    # Purpose: Per-attorney trust scores that affect submission weighting
    # =========================================================================

    op.create_table(
        'settle_contribution_reputation',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column('contributor_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'reputation_score',
            sa.Numeric(),
            nullable=False,
            server_default=sa.text("'0.0'"),
        ),
        sa.Column(
            'tier',
            sa.Text(),
            nullable=False,
            server_default=sa.text("'unverified'"),
        ),
        sa.Column('total_submissions', sa.Integer(), nullable=False, server_default=sa.text("'0'")),
        sa.Column('approved_submissions', sa.Integer(), nullable=False, server_default=sa.text("'0'")),
        sa.Column('rejected_submissions', sa.Integer(), nullable=False, server_default=sa.text("'0'")),
        sa.Column('flagged_submissions', sa.Integer(), nullable=False, server_default=sa.text("'0'")),
        sa.Column('average_z_score', sa.Numeric(), nullable=True),
        sa.Column('last_submission_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint('contributor_user_id', name='uq_reputation_contributor'),
    )

    op.create_index(
        'idx_reputation_user_id',
        'settle_contribution_reputation',
        ['contributor_user_id'],
    )

    op.create_index(
        'idx_reputation_tier',
        'settle_contribution_reputation',
        ['tier'],
    )

    op.create_index(
        'idx_reputation_score',
        'settle_contribution_reputation',
        ['reputation_score'],
    )

    # Constraints
    op.create_check_constraint(
        'valid_reputation_score',
        'settle_contribution_reputation',
        'reputation_score >= 0 AND reputation_score <= 1'
    )

    op.create_check_constraint(
        'valid_reputation_tier',
        'settle_contribution_reputation',
        "tier IN ('unverified', 'probationary', 'trusted', 'founding')"
    )

    op.create_check_constraint(
        'valid_reputation_submissions',
        'settle_contribution_reputation',
        'total_submissions >= 0 AND approved_submissions >= 0 AND rejected_submissions >= 0 AND flagged_submissions >= 0'
    )

    # =========================================================================
    # Table: settle_anomaly_flags
    # Purpose: Per-submission anomaly tracking for admin review
    # =========================================================================

    op.create_table(
        'settle_anomaly_flags',
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
        sa.Column('flag_type', sa.Text(), nullable=False),
        sa.Column('severity', sa.Text(), nullable=False),
        sa.Column('z_score', sa.Numeric(), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index(
        'idx_anomaly_flags_contribution',
        'settle_anomaly_flags',
        ['contribution_id'],
    )

    op.create_index(
        'idx_anomaly_flags_severity',
        'settle_anomaly_flags',
        ['severity'],
    )

    op.create_index(
        'idx_anomaly_flags_unresolved',
        'settle_anomaly_flags',
        ['resolved'],
        postgresql_where=sa.text('resolved = FALSE'),
    )

    # Constraints
    op.create_check_constraint(
        'valid_anomaly_severity',
        'settle_anomaly_flags',
        "severity IN ('warning', 'critical')"
    )

    # =========================================================================
    # Alter settle_contributions: add reputation integration columns
    # =========================================================================

    op.add_column(
        'settle_contributions',
        sa.Column('contributor_reputation_score', sa.Numeric(), nullable=True, server_default=sa.text("'0.0'")),
    )

    op.add_column(
        'settle_contributions',
        sa.Column('anomaly_flags', postgresql.JSONB(), nullable=True, server_default=sa.text("'[]'::jsonb")),
    )

    op.add_column(
        'settle_contributions',
        sa.Column('submission_quality_weight', sa.Numeric(), nullable=True, server_default=sa.text("'1.0'")),
    )

    # Index for reputation-weighted queries
    op.create_index(
        'idx_settle_contributions_reputation',
        'settle_contributions',
        ['contributor_reputation_score'],
    )

    # =========================================================================
    # Comments
    # =========================================================================

    op.create_table_comment(
        'settle_contribution_reputation',
        'Per-attorney reputation scores for contribution weighting. '
        'Scores affect estimate calculation and submission review requirements.'
    )

    op.create_table_comment(
        'settle_anomaly_flags',
        'Anomaly detection flags for individual contributions. '
        'Used for admin review and automated reputation scoring.'
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_settle_contributions_reputation', table_name='settle_contributions')
    op.drop_index('idx_anomaly_flags_unresolved', table_name='settle_anomaly_flags')
    op.drop_index('idx_anomaly_flags_severity', table_name='settle_anomaly_flags')
    op.drop_index('idx_anomaly_flags_contribution', table_name='settle_anomaly_flags')
    op.drop_index('idx_reputation_score', table_name='settle_contribution_reputation')
    op.drop_index('idx_reputation_tier', table_name='settle_contribution_reputation')
    op.drop_index('idx_reputation_user_id', table_name='settle_contribution_reputation')

    # Drop constraints
    op.drop_constraint('valid_anomaly_severity', 'settle_anomaly_flags')
    op.drop_constraint('valid_reputation_submissions', 'settle_contribution_reputation')
    op.drop_constraint('valid_reputation_tier', 'settle_contribution_reputation')
    op.drop_constraint('valid_reputation_score', 'settle_contribution_reputation')

    # Drop columns
    op.drop_column('settle_contributions', 'submission_quality_weight')
    op.drop_column('settle_contributions', 'anomaly_flags')
    op.drop_column('settle_contributions', 'contributor_reputation_score')

    # Drop tables
    op.drop_table('settle_anomaly_flags')
    op.drop_table('settle_contribution_reputation')
