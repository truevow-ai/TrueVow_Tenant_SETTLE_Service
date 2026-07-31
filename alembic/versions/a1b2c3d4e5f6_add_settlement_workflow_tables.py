"""add settlement workflow tables

Revision ID: a1b2c3d4e5f6
Revises: ffd820027e8c
Create Date: 2026-07-29 10:00:00.000000

Settlement domain tables per TrueVow Plaintiff Law Firm Operations Ontology v1.0:
  - settle_demand_packages         (ENT-081)
  - settle_demand_drafts           (ENT-082)
  - settle_demand_transmissions    (ENT-092)
  - settle_negotiation_rounds      (ENT-093)
  - settle_offers                  (ENT-094)
  - settle_counteroffers           (ENT-095)
  - settle_settlement_decisions    (ENT-096)
  - settle_attorney_recommendations
  - settle_settlement_agreements   (ENT-097)
  - settle_releases                (ENT-098)
  - settle_settlement_payments     (ENT-099)
  - settle_liens                   (ENT-100)
  - settle_settlement_allocations  (ENT-102)
  - settle_trust_ledger            (ENT-103)
  - settle_closing_statements      (ENT-104)
  - settle_disbursements           (ENT-105)
  - settle_matter_closures         (ENT-106)
  - settle_settlement_audit_events (Audit log)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ffd820027e8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENT-081: Demand Packages
    op.create_table(
        'settle_demand_packages',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('claim_ids', postgresql.JSONB(), default=list),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('state', sa.String(30), nullable=False, default='assembling'),
        sa.Column('document_hash', sa.String(128), nullable=True),
        sa.Column('authorized_by', sa.UUID(), nullable=True),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by_id', sa.UUID(), nullable=True),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('withdrawn_by', sa.UUID(), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('withdrawn_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-082: Demand Drafts
    op.create_table(
        'settle_demand_drafts',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('package_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content_hash', sa.String(128), nullable=True),
        sa.Column('generated_by', sa.String(50), nullable=True),
        sa.Column('is_ai_generated', sa.Boolean(), nullable=False, default=False),
        sa.Column('state', sa.String(30), nullable=False, default='drafting'),
        sa.Column('attorney_reviewer_id', sa.UUID(), nullable=True),
        sa.Column('attorney_notes', sa.Text(), nullable=True),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-092: Demand Transmissions
    op.create_table(
        'settle_demand_transmissions',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('package_id', sa.UUID(), nullable=False),
        sa.Column('package_version', sa.Integer(), nullable=False),
        sa.Column('recipient', sa.String(255), nullable=False),
        sa.Column('recipient_contact_id', sa.UUID(), nullable=True),
        sa.Column('method', sa.String(20), nullable=False, default='email'),
        sa.Column('status', sa.String(30), nullable=False, default='pending'),
        sa.Column('transmission_notes', sa.Text(), nullable=True),
        sa.Column('transmitted_by', sa.UUID(), nullable=True),
        sa.Column('transmitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_evidence', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-093: Negotiation Rounds
    op.create_table(
        'settle_negotiation_rounds',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('claim_ids', postgresql.JSONB(), default=list),
        sa.Column('round_number', sa.Integer(), nullable=False, default=1),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-094: Offers
    op.create_table(
        'settle_offers',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('negotiation_round_id', sa.UUID(), nullable=False),
        sa.Column('claim_ids', postgresql.JSONB(), default=list),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('source_contact_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('is_global', sa.Boolean(), nullable=False, default=False),
        sa.Column('terms_summary', sa.Text(), nullable=True),
        sa.Column('expiration_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(40), nullable=False, default='offer_received'),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('client_notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('authorized_by', sa.UUID(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_offers_matter_status', 'matter_id', 'status'),
        sa.Index('idx_offers_round', 'negotiation_round_id'),
    )

    # ENT-095: Counteroffers
    op.create_table(
        'settle_counteroffers',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('negotiation_round_id', sa.UUID(), nullable=False),
        sa.Column('responds_to_offer_id', sa.UUID(), nullable=False),
        sa.Column('claim_ids', postgresql.JSONB(), default=list),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('is_global', sa.Boolean(), nullable=False, default=False),
        sa.Column('terms_summary', sa.Text(), nullable=True),
        sa.Column('expiration_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('authorized_by_client', sa.Boolean(), nullable=False, default=False),
        sa.Column('client_authorization_id', sa.UUID(), nullable=True),
        sa.Column('authorized_by_attorney', sa.UUID(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, default='draft'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-096: Settlement Decisions
    op.create_table(
        'settle_settlement_decisions',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('offer_id', sa.UUID(), nullable=False),
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('decided_by', sa.UUID(), nullable=False),
        sa.Column('representative_authority_id', sa.UUID(), nullable=True),
        sa.Column('attorney_recommendation_id', sa.UUID(), nullable=True),
        sa.Column('attorney_advised_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('informed_consent_confirmed', sa.Boolean(), nullable=False, default=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('counter_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('counter_terms', sa.Text(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_decisions_offer', 'offer_id'),
    )

    # Attorney Recommendations
    op.create_table(
        'settle_attorney_recommendations',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('offer_id', sa.UUID(), nullable=False),
        sa.Column('recommended_action', sa.String(20), nullable=False),
        sa.Column('recommended_counter_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('analysis_summary', sa.Text(), nullable=True),
        sa.Column('considerations', postgresql.JSONB(), default=list),
        sa.Column('ai_supported', sa.Boolean(), nullable=False, default=False),
        sa.Column('ai_analysis_reference', sa.String(255), nullable=True),
        sa.Column('recommended_by', sa.UUID(), nullable=False),
        sa.Column('recommended_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-097: Settlement Agreements
    op.create_table(
        'settle_settlement_agreements',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('settlement_decision_id', sa.UUID(), nullable=False),
        sa.Column('claim_ids', postgresql.JSONB(), default=list),
        sa.Column('document_hash', sa.String(128), nullable=True),
        sa.Column('document_version', sa.Integer(), nullable=False, default=1),
        sa.Column('status', sa.String(30), nullable=False, default='draft'),
        sa.Column('agreement_date', sa.Date(), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('gross_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('is_confidential', sa.Boolean(), nullable=False, default=False),
        sa.Column('attorney_approved_by', sa.UUID(), nullable=True),
        sa.Column('attorney_approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('client_signed_by', sa.UUID(), nullable=True),
        sa.Column('client_signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_signed_by', sa.UUID(), nullable=True),
        sa.Column('firm_signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fully_executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-098: Releases
    op.create_table(
        'settle_releases',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('settlement_agreement_id', sa.UUID(), nullable=False),
        sa.Column('document_hash', sa.String(128), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('status', sa.String(30), nullable=False, default='draft'),
        sa.Column('attorney_reviewed_by', sa.UUID(), nullable=True),
        sa.Column('attorney_reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_to_client_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('client_signed_by', sa.UUID(), nullable=True),
        sa.Column('client_signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('release_scope', sa.Text(), nullable=True),
        sa.Column('is_mutual', sa.Boolean(), nullable=False, default=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-099: Settlement Payments
    op.create_table(
        'settle_settlement_payments',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('settlement_agreement_id', sa.UUID(), nullable=False),
        sa.Column('payer', sa.String(255), nullable=False),
        sa.Column('payer_contact_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('reference_number', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, default='pending'),
        sa.Column('expected_date', sa.Date(), nullable=True),
        sa.Column('received_date', sa.Date(), nullable=True),
        sa.Column('cleared_date', sa.Date(), nullable=True),
        sa.Column('deposited_to_trust', sa.Boolean(), nullable=False, default=False),
        sa.Column('trust_ledger_entry_id', sa.UUID(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-100: Liens
    op.create_table(
        'settle_liens',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('claimant', sa.String(255), nullable=False),
        sa.Column('claimant_type', sa.String(50), nullable=False),
        sa.Column('claim_basis', sa.Text(), nullable=True),
        sa.Column('asserted_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('verified_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, default='asserted'),
        sa.Column('asserted_date', sa.Date(), nullable=True),
        sa.Column('documents_received', sa.Boolean(), nullable=False, default=False),
        sa.Column('documents_requested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by', sa.UUID(), nullable=True),
        sa.Column('disputed_reason', sa.Text(), nullable=True),
        sa.Column('negotiated_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('resolution_date', sa.Date(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_liens_matter_status', 'matter_id', 'status'),
    )

    # ENT-102: Settlement Allocations
    op.create_table(
        'settle_settlement_allocations',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('settlement_agreement_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('gross_proceeds', sa.Numeric(15, 2), nullable=False),
        sa.Column('attorney_fees', sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column('attorney_fee_pct', sa.Numeric(6, 3), nullable=True),
        sa.Column('costs_advanced', sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column('lien_payments', sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column('other_deductions', sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column('client_net', sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column('reconciliation_status', sa.String(20), nullable=False, default='unbalanced'),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),
        sa.Column('approved_by_attorney', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('client_acknowledged', sa.Boolean(), nullable=False, default=False),
        sa.Column('client_acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-103: Trust Ledger
    op.create_table(
        'settle_trust_ledger',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('settlement_payment_id', sa.UUID(), nullable=True),
        sa.Column('disbursement_id', sa.UUID(), nullable=True),
        sa.Column('entry_type', sa.String(30), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('running_balance', sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reference_number', sa.String(100), nullable=True),
        sa.Column('posted_by', sa.UUID(), nullable=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reconciled', sa.Boolean(), nullable=False, default=False),
        sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-104: Closing Statements
    op.create_table(
        'settle_closing_statements',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('settlement_agreement_id', sa.UUID(), nullable=False),
        sa.Column('allocation_id', sa.UUID(), nullable=False),
        sa.Column('document_hash', sa.String(128), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('gross_recovery', sa.Numeric(15, 2), nullable=False),
        sa.Column('total_deductions', sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column('net_to_client', sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column('line_items', postgresql.JSONB(), default=list),
        sa.Column('approved_by_attorney', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('client_acknowledged', sa.Boolean(), nullable=False, default=False),
        sa.Column('client_acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_evidence', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-105: Disbursements
    op.create_table(
        'settle_disbursements',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('allocation_id', sa.UUID(), nullable=False),
        sa.Column('payee', sa.String(255), nullable=False),
        sa.Column('payee_type', sa.String(30), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, default='pending'),
        sa.Column('authorized_by', sa.UUID(), nullable=True),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trust_ledger_entry_id', sa.UUID(), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('reference_number', sa.String(100), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_by', sa.UUID(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('reversed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reversed_by', sa.UUID(), nullable=True),
        sa.Column('reversal_reason', sa.Text(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-106: Matter Closures
    op.create_table(
        'settle_matter_closures',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('state', sa.String(20), nullable=False, default='active'),
        sa.Column('closure_type', sa.String(30), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by', sa.UUID(), nullable=True),
        sa.Column('closure_authorized_by', sa.UUID(), nullable=True),
        sa.Column('unresolved_items', postgresql.JSONB(), default=list),
        sa.Column('reopened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reopened_by', sa.UUID(), nullable=True),
        sa.Column('reopen_reason', sa.Text(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Settlement Audit Events
    op.create_table(
        'settle_settlement_audit_events',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=False, index=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=True),
        sa.Column('actor_type', sa.String(50), nullable=True),
        sa.Column('authority_source', sa.String(30), nullable=True),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('prior_state', sa.String(50), nullable=True),
        sa.Column('resulting_state', sa.String(50), nullable=True),
        sa.Column('details', postgresql.JSONB(), default={}),
        sa.Column('policy_version', sa.String(50), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_settlement_audit_matter', 'matter_id', 'occurred_at'),
        sa.Index('idx_settlement_audit_entity', 'entity_type', 'entity_id'),
        sa.Index('idx_settlement_audit_type', 'event_type'),
    )


def downgrade() -> None:
    op.drop_table('settle_settlement_audit_events', if_exists=True)
    op.drop_table('settle_matter_closures', if_exists=True)
    op.drop_table('settle_disbursements', if_exists=True)
    op.drop_table('settle_closing_statements', if_exists=True)
    op.drop_table('settle_trust_ledger', if_exists=True)
    op.drop_table('settle_settlement_allocations', if_exists=True)
    op.drop_table('settle_liens', if_exists=True)
    op.drop_table('settle_settlement_payments', if_exists=True)
    op.drop_table('settle_releases', if_exists=True)
    op.drop_table('settle_settlement_agreements', if_exists=True)
    op.drop_table('settle_attorney_recommendations', if_exists=True)
    op.drop_table('settle_settlement_decisions', if_exists=True)
    op.drop_table('settle_counteroffers', if_exists=True)
    op.drop_table('settle_offers', if_exists=True)
    op.drop_table('settle_negotiation_rounds', if_exists=True)
    op.drop_table('settle_demand_transmissions', if_exists=True)
    op.drop_table('settle_demand_drafts', if_exists=True)
    op.drop_table('settle_demand_packages', if_exists=True)
