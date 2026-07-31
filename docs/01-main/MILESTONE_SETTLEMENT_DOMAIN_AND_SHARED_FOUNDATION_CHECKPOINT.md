# MILESTONE: Settlement Domain + Shared Foundation + Contract Normalization

**Checkpoint Date:** 2026-07-29
**Session Agent:** opencode (deepseek-v4-pro)
**Status:** COMPLETE (82 tests passing, lint clean)

## Deliverables

### 1. Settlement Domain Models (ENT-081 through ENT-106)
- 17 Pydantic models covering the full resolution lifecycle
- 30 REST endpoints under `/settle/` prefix
- 18 DB tables for settlement workflow data
- Authority gate enforcing AUTH-014 through AUTH-020

### 2. Shared Foundation Services (9 services)
- TenantCore: identity, roles, isolation (INV-001)
- AuthorityGate: AUTH-001 through AUTH-020, 27 registered actions
- PolicyRegistry: jurisdiction profiles, firm policies, immutable snapshots
- ConsentLedger: append-only, 7-state lifecycle (INV-012)
- DocumentService: versioned with SHA-256, signature evidence packages
- CommunicationService: multi-channel, delivery evidence
- WorkflowRuntime: deterministic transitions, overdue escalation
- AuditEventStore: EventEnvelope v1.0.1, 18 required fields
- IntegrationHub: 12 integration types

### 3. Contract Corrections
- EventEnvelope frozen at Literal["1.0.1"]
- MatterActivationEvidenceManifest: all 9 evidence refs mandatory
- WebhookSigner aligned to SaaS Admin TypeScript byte-for-byte
- Global vs tenant data separation (TenantJurisdictionActivation)

### 4. Golden Fixtures
- Deterministic EventEnvelope for cross-repository validation
- Deterministic HMAC computation matching SaaS Admin
- Frozen contract versions registry

## Test Results
- 36 settlement domain tests: PASS
- 23 shared foundation tests: PASS
- 9 golden fixture tests: PASS
- 14 existing tests: PASS
- Lint: CLEAN (ruff, 0 errors)

## Files Created
```
app/models/settlement.py
app/models/activation.py
app/services/settlement/__init__.py
app/services/settlement/authority_gate.py
app/services/settlement/audit.py
app/services/settlement/demand.py
app/services/settlement/negotiation.py
app/services/settlement/decision.py
app/services/settlement/agreement.py
app/services/settlement/lien.py
app/services/settlement/financial.py
app/services/settlement/closure.py
app/api/v1/endpoints/settlement.py
app/shared/__init__.py
app/shared/models.py
app/shared/tenant_core.py
app/shared/authority_gate.py
app/shared/policy_registry.py
app/shared/consent_ledger.py
app/shared/document_service.py
app/shared/communication_service.py
app/shared/workflow_runtime.py
app/shared/audit_store.py
app/shared/integration_hub.py
app/shared/contracts.py
alembic/versions/a1b2c3d4e5f6_add_settlement_workflow_tables.py
alembic/versions/b2c3d4e5f6a7_add_shared_foundation_tables.py
tests/test_settlement_domain.py
tests/test_shared_foundation.py
tests/test_golden_fixtures.py
```

## Files Modified
```
app/api/v1/router.py — added settlement router
app/core/service_auth.py — HMAC webhook signing (WebhookSigner, WebhookVerifier)
env.template — TRUEVOW_WEBHOOK_* env vars
docs/01-main/IMPLEMENTATION_PROGRESS.md — updated session summary
```

## Architecture Decisions

1. **Three-layer authority gate**: authority check → state transition validation → invariant validation
2. **Fail-closed default**: authority gate default is fail_closed
3. **Colon delimiter for HMAC**: matches SaaS Admin TypeScript exactly (`timestamp:method:path:body_hash`)
4. **URL path only**: no host, no query string in signing path
5. **Global vs tenant separation**: GLOBAL_REFERENCE_TYPES (11) vs TENANT_OWNED_TYPES (25) constants
6. **Product extensions prohibited at EventEnvelope root**: extend only through payload

## Next Actions
- RETAINER product build can proceed against stable SETTLE contracts
- INTAKE and RETAINER agents should import shared contracts from SaaS Admin
- Migrate any remaining Bearer auth to HMAC webhook signing
