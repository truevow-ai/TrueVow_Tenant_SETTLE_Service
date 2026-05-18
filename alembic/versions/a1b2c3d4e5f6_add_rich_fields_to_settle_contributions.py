"""add_rich_fields_to_settle_contributions

Revision ID: a1b2c3d4e5f6
Revises: ed2900358f69
Create Date: 2026-05-17

Adds 12 new columns to settle_contributions for richer settlement intelligence:

Tier 1 (high impact on estimate quality):
  - insurance_carrier: TEXT — carrier name for negotiation leverage
  - comparative_negligence_pct: NUMERIC — affects settlement math
  - exact_outcome_amount: NUMERIC — precision alongside bucketed range
  - is_verdict: BOOLEAN — verdict vs settlement distinction
  - date_of_verdict: TIMESTAMPTZ — staleness + inflation adjustment

Tier 2 (useful for filtering/display):
  - court_level: TEXT — federal vs circuit vs district
  - injury_severity: TEXT — soft_tissue/surgical/catastrophic
  - policy_limit_amount: NUMERIC — cap signal
  - source_type: TEXT — firm_submission vs scraped_verdict vs news_report

Tier 3 (nice-to-have):
  - trial_duration_days: INTEGER — case complexity signal
  - appeal_filed: BOOLEAN — post-verdict signal
  - appeal_outcome: TEXT — affirmed/reversed/settled

Also adds indexes on high-query fields for admin UI performance.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ed2900358f69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Tier 1 — High impact on estimate quality
    # =========================================================================

    op.add_column(
        'settle_contributions',
        sa.Column('insurance_carrier', sa.Text(), nullable=True),
    )

    op.add_column(
        'settle_contributions',
        sa.Column('comparative_negligence_pct', sa.Numeric(), nullable=True),
    )

    op.add_column(
        'settle_contributions',
        sa.Column('exact_outcome_amount', sa.Numeric(), nullable=True),
    )

    op.add_column(
        'settle_contributions',
        sa.Column('is_verdict', sa.Boolean(), nullable=True),
    )

    op.add_column(
        'settle_contributions',
        sa.Column('date_of_verdict', sa.DateTime(timezone=True), nullable=True),
    )

    # =========================================================================
    # Tier 2 — Useful for filtering/display
    # =========================================================================

    op.add_column(
        'settle_contributions',
        sa.Column('court_level', sa.Text(), nullable=True),
    )

    op.add_column(
        'settle_contributions',
        sa.Column('injury_severity', sa.Text(), nullable=True),
    )

    op.add_column(
        'settle_contributions',
        sa.Column('policy_limit_amount', sa.Numeric(), nullable=True),
    )

    op.add_column(
        'settle_contributions',
        sa.Column('source_type', sa.Text(), nullable=True),
    )

    # =========================================================================
    # Tier 3 — Nice-to-have
    # =========================================================================

    op.add_column(
        'settle_contributions',
        sa.Column('trial_duration_days', sa.Integer(), nullable=True),
    )

    op.add_column(
        'settle_contributions',
        sa.Column('appeal_filed', sa.Boolean(), nullable=True),
    )

    op.add_column(
        'settle_contributions',
        sa.Column('appeal_outcome', sa.Text(), nullable=True),
    )

    # =========================================================================
    # Indexes for admin UI and estimator queries
    # =========================================================================

    op.create_index(
        'idx_settle_contributions_insurance_carrier',
        'settle_contributions',
        ['insurance_carrier'],
    )

    op.create_index(
        'idx_settle_contributions_source_type',
        'settle_contributions',
        ['source_type'],
    )

    op.create_index(
        'idx_settle_contributions_injury_severity',
        'settle_contributions',
        ['injury_severity'],
    )

    op.create_index(
        'idx_settle_contributions_is_verdict',
        'settle_contributions',
        ['is_verdict'],
    )

    op.create_index(
        'idx_settle_contributions_date_of_verdict',
        'settle_contributions',
        ['date_of_verdict'],
    )

    # Add constraint for source_type valid values
    op.create_check_constraint(
        'valid_source_type',
        'settle_contributions',
        "source_type IS NULL OR source_type IN ('firm_submission', 'scraped_verdict', 'news_report', 'court_docket', 'settlement_survey')"
    )

    # Add constraint for court_level valid values
    op.create_check_constraint(
        'valid_court_level',
        'settle_contributions',
        "court_level IS NULL OR court_level IN ('circuit', 'federal_district', 'federal_appellate', 'state_appellate', 'arbitration', 'mediation')"
    )

    # Add constraint for injury_severity valid values
    op.create_check_constraint(
        'valid_injury_severity',
        'settle_contributions',
        "injury_severity IS NULL OR injury_severity IN ('soft_tissue', 'fracture', 'surgical', 'catastrophic', 'fatal')"
    )

    # Add constraint for appeal_outcome valid values
    op.create_check_constraint(
        'valid_appeal_outcome',
        'settle_contributions',
        "appeal_outcome IS NULL OR appeal_outcome IN ('affirmed', 'reversed', 'remanded', 'settled', 'dismissed', 'pending')"
    )

    # Add constraint for comparative_negligence_pct range
    op.create_check_constraint(
        'valid_comparative_negligence_pct',
        'settle_contributions',
        "comparative_negligence_pct IS NULL OR (comparative_negligence_pct >= 0 AND comparative_negligence_pct <= 100)"
    )

    # Add constraint for exact_outcome_amount range
    op.create_check_constraint(
        'valid_exact_outcome_amount',
        'settle_contributions',
        "exact_outcome_amount IS NULL OR (exact_outcome_amount >= 0 AND exact_outcome_amount <= 100000000)"
    )

    # Add constraint for policy_limit_amount range
    op.create_check_constraint(
        'valid_policy_limit_amount',
        'settle_contributions',
        "policy_limit_amount IS NULL OR (policy_limit_amount >= 0 AND policy_limit_amount <= 100000000)"
    )

    # Add constraint for trial_duration_days range
    op.create_check_constraint(
        'valid_trial_duration_days',
        'settle_contributions',
        "trial_duration_days IS NULL OR (trial_duration_days >= 0 AND trial_duration_days <= 3650)"
    )


def downgrade() -> None:
    # Drop constraints
    op.drop_constraint('valid_trial_duration_days', 'settle_contributions')
    op.drop_constraint('valid_policy_limit_amount', 'settle_contributions')
    op.drop_constraint('valid_exact_outcome_amount', 'settle_contributions')
    op.drop_constraint('valid_comparative_negligence_pct', 'settle_contributions')
    op.drop_constraint('valid_appeal_outcome', 'settle_contributions')
    op.drop_constraint('valid_injury_severity', 'settle_contributions')
    op.drop_constraint('valid_court_level', 'settle_contributions')
    op.drop_constraint('valid_source_type', 'settle_contributions')

    # Drop indexes
    op.drop_index('idx_settle_contributions_date_of_verdict', table_name='settle_contributions')
    op.drop_index('idx_settle_contributions_is_verdict', table_name='settle_contributions')
    op.drop_index('idx_settle_contributions_injury_severity', table_name='settle_contributions')
    op.drop_index('idx_settle_contributions_source_type', table_name='settle_contributions')
    op.drop_index('idx_settle_contributions_insurance_carrier', table_name='settle_contributions')

    # Drop columns
    op.drop_column('settle_contributions', 'appeal_outcome')
    op.drop_column('settle_contributions', 'appeal_filed')
    op.drop_column('settle_contributions', 'trial_duration_days')
    op.drop_column('settle_contributions', 'source_type')
    op.drop_column('settle_contributions', 'policy_limit_amount')
    op.drop_column('settle_contributions', 'injury_severity')
    op.drop_column('settle_contributions', 'court_level')
    op.drop_column('settle_contributions', 'date_of_verdict')
    op.drop_column('settle_contributions', 'is_verdict')
    op.drop_column('settle_contributions', 'exact_outcome_amount')
    op.drop_column('settle_contributions', 'comparative_negligence_pct')
    op.drop_column('settle_contributions', 'insurance_carrier')
