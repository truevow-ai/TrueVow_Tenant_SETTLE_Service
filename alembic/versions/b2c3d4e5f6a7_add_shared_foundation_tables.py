"""add shared foundation tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-29 11:00:00.000000

Shared foundation tables used by all five TrueVow products:
  - tenants, offices, user_accounts, role_assignments
  - persons, organizations, party_roles, contact_points, relationships
  - matters
  - jurisdiction_profiles, firm_policies, authority_records, configuration_versions
  - consent_records
  - document_versions, signature_evidences
  - communications, notifications
  - work_items
  - audit_events (ontology Event Envelope compliant)
  - integration_connections
  - service_level_policies, calendar_events
  - legal_holds, data_retention_policies
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENT-001: Tenants
    op.create_table(
        'tenants',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('jurisdiction', sa.String(10), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('settings', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-002: Offices
    op.create_table(
        'offices',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('address', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-003: User Accounts
    op.create_table(
        'user_accounts',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('external_auth_id', sa.String(255), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_users_tenant_email', 'tenant_id', 'email'),
    )

    # ENT-004: Role Assignments
    op.create_table(
        'role_assignments',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.UUID(), nullable=False, index=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('office_id', sa.UUID(), nullable=True),
        sa.Column('matter_id', sa.UUID(), nullable=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('granted_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_roles_user_tenant', 'user_id', 'tenant_id', 'is_active'),
    )

    # ENT-011: Persons
    op.create_table(
        'persons',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('middle_name', sa.String(100), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('ssn_last_four', sa.String(4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-012: Organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('org_type', sa.String(50), nullable=True),
        sa.Column('tax_id', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-013: Party Roles
    op.create_table(
        'party_roles',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('person_id', sa.UUID(), nullable=True),
        sa.Column('organization_id', sa.UUID(), nullable=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('matter_id', sa.UUID(), nullable=True, index=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-014: Contact Points
    op.create_table(
        'contact_points',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('person_id', sa.UUID(), nullable=True, index=True),
        sa.Column('organization_id', sa.UUID(), nullable=True),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('value', sa.String(255), nullable=False),
        sa.Column('is_primary', sa.Boolean(), default=False),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-015: Relationships
    op.create_table(
        'relationships',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('from_party_role_id', sa.UUID(), nullable=False),
        sa.Column('to_party_role_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.String(50), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-041: Matters
    op.create_table(
        'matters',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('office_id', sa.UUID(), nullable=True),
        sa.Column('client_party_role_id', sa.UUID(), nullable=False),
        sa.Column('responsible_attorney_id', sa.UUID(), nullable=False),
        sa.Column('matter_number', sa.String(50), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('practice_area', sa.String(100), nullable=True),
        sa.Column('lifecycle_state', sa.String(40), nullable=False, default='activation_pending'),
        sa.Column('jurisdiction', sa.String(10), nullable=True),
        sa.Column('incident_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_matters_attorney', 'responsible_attorney_id', 'lifecycle_state'),
    )

    # ENT-005: Jurisdiction Profiles
    op.create_table(
        'jurisdiction_profiles',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('jurisdiction', sa.String(10), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('applicable_ethics_rules', postgresql.JSONB(), default=[]),
        sa.Column('agreement_requirements', postgresql.JSONB(), default={}),
        sa.Column('required_disclosures', postgresql.JSONB(), default=[]),
        sa.Column('signature_requirements', postgresql.JSONB(), default={}),
        sa.Column('advertising_restrictions', sa.Text(), nullable=True),
        sa.Column('retention_requirements', postgresql.JSONB(), nullable=True),
        sa.Column('unsupported_features', postgresql.JSONB(), default=[]),
        sa.Column('counsel_approval_status', sa.String(20), default='pending'),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by', sa.UUID(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_jurisdiction_active', 'jurisdiction', 'is_active'),
    )

    # ENT-006: Firm Policies
    op.create_table(
        'firm_policies',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('policy_name', sa.String(255), nullable=False),
        sa.Column('policy_type', sa.String(100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('config', postgresql.JSONB(), default={}),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by', sa.UUID(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_policies_tenant_type', 'tenant_id', 'policy_type', 'is_active'),
    )

    # ENT-007: Authority Records
    op.create_table(
        'authority_records',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('actor_id', sa.UUID(), nullable=False),
        sa.Column('actor_type', sa.String(50), nullable=False),
        sa.Column('matter_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('authority_class', sa.String(20), nullable=False),
        sa.Column('granted_by', sa.UUID(), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence', postgresql.JSONB(), default={}),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-008: Configuration Versions
    op.create_table(
        'configuration_versions',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('config_type', sa.String(100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(128), nullable=False),
        sa.Column('config_data', postgresql.JSONB(), default={}),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-024: Consent Records
    op.create_table(
        'consent_records',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('person_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=True),
        sa.Column('consent_type', sa.String(50), nullable=False),
        sa.Column('state', sa.String(20), nullable=False, default='not_requested'),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('declined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by_id', sa.UUID(), nullable=True),
        sa.Column('disclosure_text', sa.Text(), nullable=True),
        sa.Column('channel', sa.String(20), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('evidence', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Index('idx_consent_person_type', 'person_id', 'consent_type'),
    )

    # ENT-115: Document Versions
    op.create_table(
        'document_versions',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=True, index=True),
        sa.Column('document_type', sa.String(100), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('content_hash', sa.String(128), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('byte_size', sa.Integer(), nullable=True),
        sa.Column('storage_path', sa.String(500), nullable=True),
        sa.Column('state', sa.String(30), nullable=False, default='draft'),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('classification', sa.String(30), nullable=True),
        sa.Column('lineage_id', sa.UUID(), nullable=True),
        sa.Column('generated_from_template_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by_id', sa.UUID(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-038: Signature Evidences
    op.create_table(
        'signature_evidences',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('document_version_id', sa.UUID(), nullable=False, index=True),
        sa.Column('signer_id', sa.UUID(), nullable=False),
        sa.Column('signer_role', sa.String(50), nullable=False),
        sa.Column('signature_type', sa.String(20), nullable=False),
        sa.Column('esign_consent_id', sa.UUID(), nullable=True),
        sa.Column('authentication_method', sa.String(50), nullable=True),
        sa.Column('authentication_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('signature_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('device_info', postgresql.JSONB(), nullable=True),
        sa.Column('document_hash_at_signing', sa.String(128), nullable=False),
        sa.Column('intent_confirmed', sa.Boolean(), default=False),
        sa.Column('evidence_package', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-022: Communications
    op.create_table(
        'communications',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=True, index=True),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('sender_id', sa.UUID(), nullable=True),
        sa.Column('recipient_id', sa.UUID(), nullable=True),
        sa.Column('recipient_address', sa.String(255), nullable=True),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('template_id', sa.UUID(), nullable=True),
        sa.Column('consent_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replied_to_id', sa.UUID(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('delivery_evidence', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-112: Notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True, index=True),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False, default='portal'),
        sa.Column('event_type', sa.String(100), nullable=True),
        sa.Column('event_id', sa.UUID(), nullable=True),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('action_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-107: Work Items
    op.create_table(
        'work_items',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=True, index=True),
        sa.Column('work_type', sa.String(100), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('state', sa.String(30), nullable=False, default='created'),
        sa.Column('priority', sa.String(20), default='medium'),
        sa.Column('assigned_to', sa.UUID(), nullable=True, index=True),
        sa.Column('assigned_queue', sa.String(100), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_by', sa.UUID(), nullable=True),
        sa.Column('blocked_reason', sa.Text(), nullable=True),
        sa.Column('policy_id', sa.UUID(), nullable=True),
        sa.Column('sla_policy_id', sa.UUID(), nullable=True),
        sa.Column('parent_work_item_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Audit Events (ontology Event Envelope compliant)
    op.create_table(
        'audit_events',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('aggregate_type', sa.String(50), nullable=True),
        sa.Column('aggregate_id', sa.UUID(), nullable=True),
        sa.Column('aggregate_version', sa.Integer(), nullable=True),
        sa.Column('actor_type', sa.String(50), nullable=True),
        sa.Column('actor_id', sa.UUID(), nullable=True),
        sa.Column('authority_class', sa.String(20), nullable=True),
        sa.Column('authority_record_id', sa.UUID(), nullable=True),
        sa.Column('policy_version_id', sa.UUID(), nullable=True),
        sa.Column('correlation_id', sa.UUID(), nullable=True),
        sa.Column('causation_id', sa.UUID(), nullable=True),
        sa.Column('prior_state', sa.String(50), nullable=True),
        sa.Column('resulting_state', sa.String(50), nullable=True),
        sa.Column('payload', postgresql.JSONB(), default={}),
        sa.Column('sensitivity_class', sa.String(20), default='internal'),
        sa.Column('schema_version', sa.String(10), default='1.0'),
        sa.Index('idx_audit_tenant_time', 'tenant_id', 'occurred_at'),
        sa.Index('idx_audit_aggregate', 'aggregate_type', 'aggregate_id'),
        sa.Index('idx_audit_event_type', 'event_type'),
        sa.Index('idx_audit_correlation', 'correlation_id'),
    )

    # ENT-009: Integration Connections
    op.create_table(
        'integration_connections',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('integration_type', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('config', postgresql.JSONB(), default={}),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_status', sa.String(20), nullable=True),
        sa.Column('last_sync_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-110: Service Level Policies
    op.create_table(
        'service_level_policies',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(20), nullable=True),
        sa.Column('target_response_minutes', sa.Integer(), nullable=True),
        sa.Column('target_completion_minutes', sa.Integer(), nullable=True),
        sa.Column('business_hours_only', sa.Boolean(), default=True),
        sa.Column('escalation_rules', postgresql.JSONB(), default={}),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-119: Legal Holds
    op.create_table(
        'legal_holds',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=True),
        sa.Column('hold_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scope', postgresql.JSONB(), default={}),
        sa.Column('authorized_by', sa.UUID(), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('release_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # ENT-010: Data Retention Policies
    op.create_table(
        'data_retention_policies',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('policy_name', sa.String(255), nullable=False),
        sa.Column('data_class', sa.String(100), nullable=False),
        sa.Column('retention_days', sa.Integer(), nullable=False),
        sa.Column('archival_days', sa.Integer(), nullable=True),
        sa.Column('applies_to', postgresql.JSONB(), default=[]),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Calendar Events (ENT-111)
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(), nullable=False, index=True),
        sa.Column('matter_id', sa.UUID(), nullable=True, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timezone', sa.String(50), default='America/Los_Angeles'),
        sa.Column('all_day', sa.Boolean(), default=False),
        sa.Column('location', sa.String(500), nullable=True),
        sa.Column('participants', postgresql.JSONB(), default=[]),
        sa.Column('recurrence_rule', sa.String(200), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('source_event_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('calendar_events', if_exists=True)
    op.drop_table('data_retention_policies', if_exists=True)
    op.drop_table('legal_holds', if_exists=True)
    op.drop_table('service_level_policies', if_exists=True)
    op.drop_table('integration_connections', if_exists=True)
    op.drop_table('audit_events', if_exists=True)
    op.drop_table('work_items', if_exists=True)
    op.drop_table('notifications', if_exists=True)
    op.drop_table('communications', if_exists=True)
    op.drop_table('signature_evidences', if_exists=True)
    op.drop_table('document_versions', if_exists=True)
    op.drop_table('consent_records', if_exists=True)
    op.drop_table('configuration_versions', if_exists=True)
    op.drop_table('authority_records', if_exists=True)
    op.drop_table('firm_policies', if_exists=True)
    op.drop_table('jurisdiction_profiles', if_exists=True)
    op.drop_table('matters', if_exists=True)
    op.drop_table('relationships', if_exists=True)
    op.drop_table('contact_points', if_exists=True)
    op.drop_table('party_roles', if_exists=True)
    op.drop_table('organizations', if_exists=True)
    op.drop_table('persons', if_exists=True)
    op.drop_table('role_assignments', if_exists=True)
    op.drop_table('user_accounts', if_exists=True)
    op.drop_table('offices', if_exists=True)
    op.drop_table('tenants', if_exists=True)
