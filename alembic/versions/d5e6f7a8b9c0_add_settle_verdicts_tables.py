"""add settle_verdicts and settle_verdict_scrape_jobs tables

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-07-09 07:45:00.000000

Internal verdict research engine (ALM VerdictSearch competitor). NOT
customer-facing: stores case names, judge names, carrier names. Rows land as
review_status='pending' from the scraping pipeline and are promoted by human
review. Schema mirrors app/models/verdicts.py (VerdictRecord) and the columns
written by cds_cap_loader.map_candidate_to_verdict().
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'settle_verdicts',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Case identification (internal only)
        sa.Column('case_name', sa.String(500), nullable=True),
        sa.Column('case_number', sa.String(200), nullable=True),
        sa.Column('jurisdiction', sa.String(200), nullable=False),
        sa.Column('court', sa.String(300), nullable=True),
        sa.Column('judge_name', sa.String(300), nullable=True),

        # Case classification
        sa.Column('case_type', sa.String(100), nullable=False),
        sa.Column('injury_type', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('plaintiff_age_range', sa.String(20), nullable=True),
        sa.Column('liability_tier', sa.String(20), nullable=True),
        sa.Column('comparative_negligence_pct', sa.Numeric(5, 2), nullable=True),

        # Financial data (internal — exact amounts)
        sa.Column('medical_bills', sa.Numeric(15, 2), nullable=True),
        sa.Column('economic_damages', sa.Numeric(15, 2), nullable=True),
        sa.Column('non_economic_damages', sa.Numeric(15, 2), nullable=True),
        sa.Column('punitive_damages', sa.Numeric(15, 2), nullable=True),
        sa.Column('total_verdict', sa.Numeric(15, 2), nullable=True),
        sa.Column('settlement_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('policy_limit_indicator', sa.String(20), nullable=True),

        # Outcome
        sa.Column('outcome_type', sa.String(30), nullable=False),
        sa.Column('defendant_category', sa.String(100), nullable=True),
        sa.Column('defendant_industry', sa.String(50), nullable=True),
        sa.Column('insurance_carrier', sa.String(200), nullable=True),

        # Trial data
        sa.Column('expert_witnesses_plaintiff', sa.Integer(), nullable=True),
        sa.Column('expert_witnesses_defense', sa.Integer(), nullable=True),
        sa.Column('trial_duration_days', sa.Integer(), nullable=True),

        # Timing
        sa.Column('verdict_date', sa.Date(), nullable=True),
        sa.Column('filing_date', sa.Date(), nullable=True),
        sa.Column('resolution_date', sa.Date(), nullable=True),

        # Source & provenance
        sa.Column('source', sa.String(30), nullable=False, server_default='scraped'),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('source_notes', sa.Text(), nullable=True),

        # Data quality
        sa.Column('confidence_score', sa.Numeric(4, 3), nullable=False, server_default='0.5'),
        sa.Column('completeness_score', sa.Numeric(4, 3), nullable=False, server_default='0.0'),
        sa.Column('review_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),

        # Metadata
        sa.Column('scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Enum integrity at the DB level (defense in depth beyond the app gate).
        sa.CheckConstraint(
            "outcome_type IN ('verdict_plaintiff','verdict_defense','settlement','dismissed')",
            name='ck_settle_verdicts_outcome_type',
        ),
        sa.CheckConstraint(
            "liability_tier IS NULL OR liability_tier IN ('clear','contested','shared','unknown')",
            name='ck_settle_verdicts_liability_tier',
        ),
        sa.CheckConstraint(
            "plaintiff_age_range IS NULL OR plaintiff_age_range IN "
            "('under_18','18_30','31_45','46_60','61_75','75_plus')",
            name='ck_settle_verdicts_age_range',
        ),
        sa.CheckConstraint(
            "review_status IN ('pending','reviewed','verified','rejected')",
            name='ck_settle_verdicts_review_status',
        ),
        sa.CheckConstraint(
            "comparative_negligence_pct IS NULL OR "
            "(comparative_negligence_pct >= 0 AND comparative_negligence_pct <= 100)",
            name='ck_settle_verdicts_comp_neg_pct',
        ),
    )
    op.create_index('idx_settle_verdicts_jurisdiction', 'settle_verdicts', ['jurisdiction'])
    op.create_index('idx_settle_verdicts_case_type', 'settle_verdicts', ['case_type'])
    op.create_index('idx_settle_verdicts_outcome', 'settle_verdicts', ['outcome_type'])
    op.create_index('idx_settle_verdicts_review', 'settle_verdicts', ['review_status'])
    op.create_index('idx_settle_verdicts_verdict_date', 'settle_verdicts', ['verdict_date'])
    op.create_index('idx_settle_verdicts_carrier', 'settle_verdicts', ['insurance_carrier'])
    # Dedup guard: case_name + jurisdiction + verdict_date (matches the loader's
    # duplicate check).
    op.create_index(
        'idx_settle_verdicts_dedup', 'settle_verdicts',
        ['case_name', 'jurisdiction', 'verdict_date'],
    )

    op.create_table(
        'settle_verdict_scrape_jobs',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='running'),
        sa.Column('source_config', postgresql.JSONB(), nullable=True),
        sa.Column('records_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_inserted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running','completed','failed','partial')",
            name='ck_scrape_jobs_status',
        ),
    )
    op.create_index('idx_scrape_jobs_source', 'settle_verdict_scrape_jobs', ['source'])
    op.create_index('idx_scrape_jobs_status', 'settle_verdict_scrape_jobs', ['status'])


def downgrade() -> None:
    op.drop_table('settle_verdict_scrape_jobs')
    op.drop_table('settle_verdicts')
