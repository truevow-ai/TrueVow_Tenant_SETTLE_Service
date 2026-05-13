"""add settlement verification and adjuster fields

Revision ID: ec7e4c7db3be
Revises: ffd820027e8c
Create Date: 2026-03-09 18:07:30.104897

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec7e4c7db3be'
down_revision: Union[str, None] = 'ffd820027e8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add verification_status enum and column
    op.execute("""
        CREATE TYPE verification_status AS ENUM ('pending', 'verified', 'rejected', 'flagged')
    """)
    
    op.add_column('settlement_records', 
        sa.Column('verification_status', sa.Enum('pending', 'verified', 'rejected', 'flagged', name='verification_status'), 
                  nullable=False, server_default='pending')
    )
    
    # Add case_id for MDM reference (one settlement per case)
    op.add_column('settlement_records',
        sa.Column('case_id', sa.String(36), nullable=True)
    )
    op.create_unique_constraint('uq_settlement_records_case_id', 'settlement_records', ['case_id'])
    
    # Add date fields for validation
    op.add_column('settlement_records',
        sa.Column('incident_date', sa.Date(), nullable=True)
    )
    op.add_column('settlement_records',
        sa.Column('settlement_date', sa.Date(), nullable=True)
    )
    
    # Add adjuster-level intelligence fields
    op.add_column('settlement_records',
        sa.Column('adjuster_name', sa.String(200), nullable=True)
    )
    op.add_column('settlement_records',
        sa.Column('adjuster_strategy', sa.Text(), nullable=True)
    )
    op.add_column('settlement_records',
        sa.Column('negotiation_days', sa.Integer(), nullable=True)
    )
    op.add_column('settlement_records',
        sa.Column('initial_offer', sa.Numeric(12, 2), nullable=True)
    )
    op.add_column('settlement_records',
        sa.Column('final_offer', sa.Numeric(12, 2), nullable=True)
    )
    op.add_column('settlement_records',
        sa.Column('offer_ratio', sa.Numeric(5, 2), nullable=True)
    )
    
    # Add indexes for verification workflow
    op.create_index('idx_settlement_records_verification_status', 'settlement_records', ['verification_status'])
    op.create_index('idx_settlement_records_case_id', 'settlement_records', ['case_id'])
    op.create_index('idx_settlement_records_adjuster', 'settlement_records', ['insurer', 'adjuster_name'])


def downgrade() -> None:
    op.drop_index('idx_settlement_records_adjuster', 'settlement_records')
    op.drop_index('idx_settlement_records_case_id', 'settlement_records')
    op.drop_index('idx_settlement_records_verification_status', 'settlement_records')
    
    op.drop_column('settlement_records', 'offer_ratio')
    op.drop_column('settlement_records', 'final_offer')
    op.drop_column('settlement_records', 'initial_offer')
    op.drop_column('settlement_records', 'negotiation_days')
    op.drop_column('settlement_records', 'adjuster_strategy')
    op.drop_column('settlement_records', 'adjuster_name')
    op.drop_column('settlement_records', 'settlement_date')
    op.drop_column('settlement_records', 'incident_date')
    op.drop_constraint('uq_settlement_records_case_id', 'settlement_records', type_='unique')
    op.drop_column('settlement_records', 'case_id')
    op.drop_column('settlement_records', 'verification_status')
    
    op.execute("DROP TYPE verification_status")
