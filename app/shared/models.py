"""
TrueVow Shared Foundation Models — Ontology Registry v1.0

All canonical types use stable IDs. Business events use past-tense dot notation.
Commands are imperative and are not events.

This file provides the data models for all 9 shared foundation services that
every TrueVow product uses. Product-specific models extend from these shared types.

TENANCY CLASSIFICATION (Correction 4 — v1.0.1):

GLOBAL PLATFORM REFERENCES (never carry tenant_id):
  AuthorityClass enum, ActorRole enum, ConsentType, ConsentState,
  DocumentState, WorkItemState, CommunicationChannel, CommunicationStatus,
  IntegrationType, TransitionContract, JurisdictionProfile,
  EventEnvelope (tenant_id is the event scope, not the model's tenant)

TENANT-OWNED BUSINESS RECORDS (always carry tenant_id):
  Tenant, Office, UserAccount, RoleAssignment, Person, Organization,
  PartyRole, ContactPoint, Relationship, Matter, FirmPolicy,
  AuthorityRecord, ConfigurationVersion, ConsentRecord, DocumentVersion,
  SignatureEvidence, Communication, Notification, WorkItem, CalendarEvent,
  ServiceLevelPolicy, AuditEvent, IntegrationConnection, LegalHold,
  DataRetentionPolicy

Global canonical registries remain immutable platform reference data.
Tenant overrides are stored separately, never modifying the canonical record.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date as date_type
from uuid import UUID
from enum import Enum


# ============================================================================
# CORE ENUMS & TYPES
# ============================================================================

class AuthorityClass(str, Enum):
    SYS_ADMIN = "SYS-ADMIN"
    FIRM_POLICY = "FIRM-POLICY"
    STAFF_AUTH = "STAFF-AUTH"
    ATTY_AUTH = "ATTY-AUTH"
    CLIENT_AUTH = "CLIENT-AUTH"
    PROHIBITED = "PROHIBITED"


class ActorRole(str, Enum):
    PROSPECTIVE_CLIENT = "prospective_client"
    CLIENT = "client"
    MINOR_CLIENT = "minor_client"
    GUARDIAN = "guardian"
    REFERRAL_SOURCE = "referral_source"
    INTAKE_COORDINATOR = "intake_coordinator"
    LEGAL_ASSISTANT = "legal_assistant"
    CASE_MANAGER = "case_manager"
    PARALEGAL = "paralegal"
    RESPONSIBLE_ATTORNEY = "responsible_attorney"
    SUPERVISING_ATTORNEY = "supervising_attorney"
    MANAGING_ATTORNEY = "managing_attorney"
    LITIGATION_ATTORNEY = "litigation_attorney"
    SETTLEMENT_AUTHORITY_HOLDER = "settlement_authority_holder"
    TRUST_ACCOUNTING = "trust_accounting"
    FIRM_ADMINISTRATOR = "firm_administrator"
    COMPLIANCE_REVIEWER = "compliance_reviewer"
    HEALTHCARE_PROVIDER = "healthcare_provider"
    RECORDS_CUSTODIAN = "records_custodian"
    INSURER = "insurer"
    CLAIMS_ADJUSTER = "claims_adjuster"
    ADVERSE_PARTY = "adverse_party"
    DEFENSE_COUNSEL = "defense_counsel"
    LIENHOLDER = "lienholder"
    COURT = "court"
    EXPERT = "expert"
    VENDOR = "vendor"
    PLATFORM = "platform"
    AI_ASSISTANCE = "ai_assistance"
    OPERATIONS = "operations"


ConsentType = Literal[
    "communication", "recording", "electronic_delivery",
    "electronic_signature", "disclosure_acknowledgment",
    "data_sharing", "sms", "email",
]

ConsentState = Literal[
    "not_requested", "requested", "granted",
    "declined", "revoked", "expired", "superseded",
]

DocumentState = Literal[
    "draft", "in_review", "approved", "executed",
    "filed_or_sent", "superseded", "void", "archived",
]

WorkItemState = Literal[
    "created", "assigned", "in_progress", "blocked",
    "awaiting_external", "review_required", "completed",
    "waived", "cancelled",
]

CommunicationChannel = Literal["email", "sms", "voice", "portal", "mail", "fax"]

CommunicationStatus = Literal[
    "draft", "queued", "sent", "delivered",
    "failed", "bounced", "opened", "replied",
]

IntegrationType = Literal[
    "calendar", "crm", "case_management", "esignature",
    "accounting", "trust_accounting", "document_storage",
    "email", "sms", "voice", "export", "import",
]


# ============================================================================
# IDENTITY, TENANCY & GOVERNANCE — ENT-001 through ENT-010
# ============================================================================

class Tenant(BaseModel):
    """ENT-001: A law firm customer security and data boundary."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    slug: str
    jurisdiction: Optional[str] = None
    is_active: bool = True
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class Office(BaseModel):
    """ENT-002: Operational location or business unit within a tenant."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    name: str
    address: Optional[Dict[str, Any]] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class UserAccount(BaseModel):
    """ENT-003: Authenticated human identity with tenant membership."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    email: str
    display_name: str
    is_active: bool = True
    external_auth_id: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class RoleAssignment(BaseModel):
    """ENT-004: Time-bounded grant of permissions and responsibilities."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    tenant_id: UUID
    office_id: Optional[UUID] = None
    matter_id: Optional[UUID] = None
    role: ActorRole
    is_active: bool = True
    effective_from: datetime
    effective_to: Optional[datetime] = None
    granted_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# PEOPLE, PARTIES & RELATIONSHIPS — ENT-011 through ENT-018
# ============================================================================

class Person(BaseModel):
    """ENT-011: Canonical natural-person identity independent of role."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    date_of_birth: Optional[date_type] = None
    ssn_last_four: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class Organization(BaseModel):
    """ENT-012: Canonical legal or operational organization identity."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    name: str
    org_type: Optional[str] = None
    tax_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PartyRole(BaseModel):
    """ENT-013: Context-specific role of a Person or Organization."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    person_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    role: ActorRole
    matter_id: Optional[UUID] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ContactPoint(BaseModel):
    """ENT-014: Email, phone, postal address, or channel endpoint with verification status."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    person_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    channel: CommunicationChannel
    value: str
    is_primary: bool = False
    is_verified: bool = False
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class Relationship(BaseModel):
    """ENT-015: Typed connection between parties."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    from_party_role_id: UUID
    to_party_role_id: UUID
    relationship_type: str
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    evidence: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# MATTER — ENT-041
# ============================================================================

class Matter(BaseModel):
    """ENT-041: Canonical represented legal engagement with lifecycle and scope."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    office_id: Optional[UUID] = None
    client_party_role_id: UUID
    responsible_attorney_id: UUID
    matter_number: Optional[str] = None
    title: Optional[str] = None
    practice_area: Optional[str] = None
    lifecycle_state: Literal[
        "activation_pending", "active_prelitigation", "demand_preparation",
        "negotiation", "litigation", "resolution_pending",
        "disbursement_pending", "closed", "reopened",
    ] = "activation_pending"
    jurisdiction: Optional[str] = None
    incident_date: Optional[date_type] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# COMPLIANCE CONTROL PLANE — ENT-005 through ENT-008
# ============================================================================

class JurisdictionProfile(BaseModel):
    """ENT-005: Versioned package of rules, constraints, and supported workflows."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    jurisdiction: str
    version: int = 1
    effective_date: date_type
    applicable_ethics_rules: List[str] = Field(default_factory=list)
    agreement_requirements: Dict[str, Any] = Field(default_factory=dict)
    required_disclosures: List[str] = Field(default_factory=list)
    signature_requirements: Dict[str, Any] = Field(default_factory=dict)
    advertising_restrictions: Optional[str] = None
    retention_requirements: Optional[Dict[str, Any]] = None
    unsupported_features: List[str] = Field(default_factory=list)
    counsel_approval_status: Literal["pending", "approved", "rejected"] = "pending"
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    superseded_by: Optional[UUID] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class TenantJurisdictionActivation(BaseModel):
    """Tenant-scoped activation of a global JurisdictionProfile.

    A tenant never activates or modifies the global profile itself.
    This record captures which jurisdiction profile version the firm has
    adopted, when it was activated, and the firm's jurisdiction-specific
    configuration overrides.

    Global JurisdictionProfile: No tenant_id, immutable platform reference.
    TenantJurisdictionActivation: Has tenant_id, references approved profile.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    jurisdiction_profile_version_id: UUID
    jurisdiction: str
    activated_at: datetime
    activated_by: Optional[UUID] = None
    effective_date: date_type
    status: Literal["pending", "active", "suspended", "withdrawn"] = "active"
    firm_config_overrides: Dict[str, Any] = Field(default_factory=dict)
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FirmPolicy(BaseModel):
    """ENT-006: Tenant-approved rule governing administrative execution."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    policy_name: str
    policy_type: str
    version: int = 1
    effective_date: date_type
    config: Dict[str, Any] = Field(default_factory=dict)
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    superseded_by: Optional[UUID] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class AuthorityRecord(BaseModel):
    """ENT-007: Evidence that a named actor may approve a defined action."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    actor_id: UUID
    actor_type: ActorRole
    matter_id: Optional[UUID] = None
    action: str
    authority_class: AuthorityClass
    granted_by: Optional[UUID] = None
    effective_from: datetime
    effective_to: Optional[datetime] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class ConfigurationVersion(BaseModel):
    """ENT-008: Immutable snapshot of operational configuration."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    config_type: str
    version: int
    content_hash: str
    config_data: Dict[str, Any] = Field(default_factory=dict)
    captured_at: datetime
    created_at: datetime


# ============================================================================
# CONSENT LEDGER — ENT-024
# ============================================================================

class ConsentRecord(BaseModel):
    """ENT-024: Versioned, attributable grant or revocation of permission.

    INV-012: Consent history is append-only. Grants, refusals, revocations,
    expirations, and supersessions are immutable events.
    """
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    person_id: UUID
    matter_id: Optional[UUID] = None
    consent_type: ConsentType
    state: ConsentState = "not_requested"
    version: int = 1
    requested_at: Optional[datetime] = None
    granted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    superseded_by_id: Optional[UUID] = None
    disclosure_text: Optional[str] = None
    channel: Optional[CommunicationChannel] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


# ============================================================================
# DOCUMENT SERVICE — ENT-115
# ============================================================================

class DocumentVersion(BaseModel):
    """ENT-115: Immutable binary/text version and metadata.

    INV-006: Every sent, filed, or executed document references an immutable
    Document Version and hash.
    """
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    matter_id: Optional[UUID] = None
    document_type: str
    title: str
    version: int = 1
    content_hash: Optional[str] = None
    mime_type: Optional[str] = None
    byte_size: Optional[int] = None
    storage_path: Optional[str] = None
    state: DocumentState = "draft"
    source: Optional[str] = None
    classification: Optional[str] = None
    lineage_id: Optional[UUID] = None
    generated_from_template_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    superseded_by_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class SignatureEvidence(BaseModel):
    """ENT-038: Immutable evidence supporting a signature."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    document_version_id: UUID
    signer_id: UUID
    signer_role: ActorRole
    signature_type: Literal["electronic", "wet", "digital"]
    esign_consent_id: Optional[UUID] = None
    authentication_method: Optional[str] = None
    authentication_timestamp: Optional[datetime] = None
    signature_timestamp: datetime
    ip_address: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None
    document_hash_at_signing: str
    intent_confirmed: bool = False
    evidence_package: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


# ============================================================================
# COMMUNICATION SERVICE — ENT-022
# ============================================================================

class Communication(BaseModel):
    """ENT-022: Message, call, voicemail, email, SMS, or portal interaction."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    matter_id: Optional[UUID] = None
    channel: CommunicationChannel
    direction: Literal["outbound", "inbound"]
    sender_id: Optional[UUID] = None
    recipient_id: Optional[UUID] = None
    recipient_address: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    template_id: Optional[UUID] = None
    consent_id: Optional[UUID] = None
    status: CommunicationStatus = "draft"
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_to_id: Optional[UUID] = None
    error_message: Optional[str] = None
    delivery_evidence: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class Notification(BaseModel):
    """ENT-112: System-generated or user-triggered communication about an event.

    Does not replace authoritative event state.
    """
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    matter_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    notification_type: str
    title: str
    body: str
    channel: CommunicationChannel = "portal"
    event_type: Optional[str] = None
    event_id: Optional[UUID] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    action_url: Optional[str] = None
    created_at: datetime


# ============================================================================
# WORKFLOW RUNTIME — ENT-107 through ENT-110
# ============================================================================

class WorkItem(BaseModel):
    """ENT-107: Actionable unit of work with owner, due date, policy, and state."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    matter_id: Optional[UUID] = None
    work_type: str
    title: str
    description: Optional[str] = None
    state: WorkItemState = "created"
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    assigned_to: Optional[UUID] = None
    assigned_queue: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[UUID] = None
    blocked_reason: Optional[str] = None
    policy_id: Optional[UUID] = None
    sla_policy_id: Optional[UUID] = None
    parent_work_item_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class CalendarEvent(BaseModel):
    """ENT-111: Scheduled appointment, deadline, hearing, task, or reminder."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    matter_id: Optional[UUID] = None
    title: str
    event_type: str
    start_at: datetime
    end_at: Optional[datetime] = None
    timezone: str = "America/Los_Angeles"
    all_day: bool = False
    location: Optional[str] = None
    participants: List[UUID] = Field(default_factory=list)
    recurrence_rule: Optional[str] = None
    source: Optional[str] = None
    source_event_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ServiceLevelPolicy(BaseModel):
    """ENT-110: Target response or completion time and escalation rules."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    name: str
    entity_type: str
    priority: Optional[str] = None
    target_response_minutes: Optional[int] = None
    target_completion_minutes: Optional[int] = None
    business_hours_only: bool = True
    escalation_rules: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


# ============================================================================
# AUDIT EVENT STORE — ENT-113, Event Envelope
# ============================================================================

class AuditEvent(BaseModel):
    """ENT-113: Immutable record of an actor, action, object, authority, and result.

    Separate from diagnostic logs (INV-015).
    """
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    aggregate_type: Optional[str] = None
    aggregate_id: Optional[UUID] = None
    aggregate_version: Optional[int] = None
    actor_type: Optional[ActorRole] = None
    actor_id: Optional[UUID] = None
    authority_class: Optional[AuthorityClass] = None
    authority_record_id: Optional[UUID] = None
    policy_version_id: Optional[UUID] = None
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    prior_state: Optional[str] = None
    resulting_state: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    sensitivity_class: Literal["public", "internal", "confidential", "restricted"] = "internal"
    schema_version: Literal["1.0.1"] = "1.0.1"


class EventEnvelope(BaseModel):
    """Ontology-compliant event envelope v1.0.1 — single machine-readable source of truth.

    REQUIRED (18 fields):
      event_id, event_type, occurred_at, recorded_at, tenant_id
      aggregate_type, aggregate_id, aggregate_version
      actor_type, actor_id, authority_class, authority_record_id
      policy_version_id, correlation_id, causation_id
      payload, sensitivity_class, schema_version

    Rules: append_only, idempotent_by_event_id, tenant_scoped,
           schema_versioned, no_secrets_in_payload, product_extensions_prohibited.

    Product-specific fields MUST NOT be added at envelope root.
    Extend only through the payload object.
    """
    event_id: UUID
    event_type: str
    occurred_at: datetime
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: UUID
    aggregate_type: str
    aggregate_id: UUID
    aggregate_version: int
    actor_type: ActorRole
    actor_id: UUID
    authority_class: AuthorityClass
    authority_record_id: UUID
    policy_version_id: UUID
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    sensitivity_class: Literal["public", "internal", "confidential", "restricted"] = "internal"
    schema_version: Literal["1.0.1"] = "1.0.1"


class TransitionContract(BaseModel):
    """Ontology transition contract.

    Required fields: transition_id, aggregate_type, from_states, to_state,
    command, required_authority, required_evidence, guards, event_type, failure_mode.
    Default failure mode: fail_closed.
    """
    transition_id: UUID
    aggregate_type: str
    from_states: List[str]
    to_state: str
    command: str
    required_authority: AuthorityClass
    required_evidence: List[str] = Field(default_factory=list)
    guards: List[str] = Field(default_factory=list)
    event_type: str
    failure_mode: Literal["fail_closed", "fail_open"] = "fail_closed"


class BusinessEvent(BaseModel):
    """ENT-114: Domain fact stating that something meaningful occurred.

    Drives projections and state transitions.
    """
    id: UUID
    tenant_id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    occurred_at: datetime
    payload: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# INTEGRATION HUB — ENT-009
# ============================================================================

class IntegrationConnection(BaseModel):
    """ENT-009: Tenant-scoped authorization to an external system."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    name: str
    integration_type: IntegrationType
    provider: str
    config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[Literal["success", "failed", "in_progress"]] = None
    last_sync_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# LEGAL HOLD & RETENTION — ENT-010, ENT-119
# ============================================================================

class LegalHold(BaseModel):
    """ENT-119: Instruction suspending normal deletion for defined data.

    INV-014: Legal hold prevents deletion regardless of ordinary retention schedule.
    """
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    matter_id: Optional[UUID] = None
    hold_name: str
    description: Optional[str] = None
    scope: Dict[str, Any] = Field(default_factory=dict)
    authorized_by: UUID
    effective_date: date_type
    release_date: Optional[date_type] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class DataRetentionPolicy(BaseModel):
    """ENT-010: Rules governing preservation, archival, deletion, and legal hold."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    policy_name: str
    data_class: str
    retention_days: int
    archival_days: Optional[int] = None
    applies_to: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


# ============================================================================
# TENANCY CLASSIFICATION (Correction 4 — v1.0.1)
# ============================================================================

GLOBAL_REFERENCE_TYPES: tuple = (
    "AuthorityClass",
    "ActorRole",
    "ConsentType",
    "ConsentState",
    "DocumentState",
    "WorkItemState",
    "CommunicationChannel",
    "CommunicationStatus",
    "IntegrationType",
    "TransitionContract",
    "JurisdictionProfile",
)

TENANT_OWNED_TYPES: tuple = (
    "Tenant",
    "Office",
    "UserAccount",
    "RoleAssignment",
    "Person",
    "Organization",
    "PartyRole",
    "ContactPoint",
    "Relationship",
    "Matter",
    "FirmPolicy",
    "AuthorityRecord",
    "ConfigurationVersion",
    "ConsentRecord",
    "DocumentVersion",
    "SignatureEvidence",
    "Communication",
    "Notification",
    "WorkItem",
    "CalendarEvent",
    "ServiceLevelPolicy",
    "AuditEvent",
    "IntegrationConnection",
    "LegalHold",
    "DataRetentionPolicy",
)
