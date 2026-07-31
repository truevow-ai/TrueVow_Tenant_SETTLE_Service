"""
TrueVow Shared Foundation — Ontology Registry v1.0

The stable operating concepts that exist whether or not a particular TrueVow
feature exists. Product features are implementations of the ontology; they are
not permitted to redefine it.

Shared capabilities (used by all five products):
  - Tenant and identity core
  - Universal Authority Gate (AUTH-001 through AUTH-020)
  - Policy Registry (jurisdiction profiles, firm policies)
  - Consent Ledger (append-only, versioned consent records)
  - Document Service (version, hash, sign, deliver)
  - Communication Service (email, SMS, reminders, delivery evidence)
  - Workflow Runtime (deterministic states, timers, approvals, escalations)
  - Audit Event Store (ontology-compliant event envelope)
  - Integration Hub (calendars, CRM, signatures, accounting, exports)
"""

from .models import (
    AuthorityClass,
    Tenant,
    Office,
    UserAccount,
    RoleAssignment,
    Person,
    Organization,
    PartyRole,
    ContactPoint,
    Relationship,
    Matter,
    JurisdictionProfile,
    TenantJurisdictionActivation,
    FirmPolicy,
    AuthorityRecord,
    ConfigurationVersion,
    ConsentRecord,
    ConsentType,
    ConsentState,
    DocumentVersion,
    DocumentState,
    SignatureEvidence,
    Communication,
    CommunicationChannel,
    CommunicationStatus,
    WorkItem,
    WorkItemState,
    AuditEvent,
    EventEnvelope,
    IntegrationConnection,
    IntegrationType,
    Notification,
    BusinessEvent,
    CalendarEvent,
    ServiceLevelPolicy,
    LegalHold,
    DataRetentionPolicy,
    TransitionContract,
    GLOBAL_REFERENCE_TYPES,
    TENANT_OWNED_TYPES,
)

__all__ = [
    "AuthorityClass",
    "Tenant", "Office", "UserAccount", "RoleAssignment",
    "Person", "Organization", "PartyRole", "ContactPoint", "Relationship",
    "Matter",
    "JurisdictionProfile", "TenantJurisdictionActivation",
    "FirmPolicy", "AuthorityRecord", "ConfigurationVersion",
    "ConsentRecord", "ConsentType", "ConsentState",
    "DocumentVersion", "DocumentState", "SignatureEvidence",
    "Communication", "CommunicationChannel", "CommunicationStatus",
    "WorkItem", "WorkItemState",
    "AuditEvent", "EventEnvelope",
    "IntegrationConnection", "IntegrationType",
    "Notification", "BusinessEvent", "CalendarEvent",
    "ServiceLevelPolicy", "LegalHold", "DataRetentionPolicy",
    "TransitionContract",
    "GLOBAL_REFERENCE_TYPES", "TENANT_OWNED_TYPES",
]
