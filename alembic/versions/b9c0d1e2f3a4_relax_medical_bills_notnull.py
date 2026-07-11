"""relax settle_contributions.medical_bills NOT NULL

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-07-11 02:45:00.000000

No-fabrication (AGENTS.md RULE 0): a contribution / bridged verdict must not be
forced to carry a medical_bills value we cannot verify. Many verified verdicts
do not state medical specials; fabricating a number (or a misleading 0) to
satisfy a NOT NULL constraint is forbidden. Make the column nullable so honest
"not recorded" is representable. The estimator uses exact_outcome_amount for
percentiles and only averages medical_bills over rows that HAVE it.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b9c0d1e2f3a4'
down_revision: Union[str, None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('settle_contributions', 'medical_bills', nullable=True)


def downgrade() -> None:
    # Re-imposing NOT NULL would require backfilling; leave nullable on downgrade
    # to avoid failing on legitimately-null rows.
    pass
