# Cross-Service Workflows

<cite>
**Referenced Files in This Document**
- [app/main.py](file://app/main.py)
- [app/core/service_registry.py](file://app/core/service_registry.py)
- [app/api/v1/router.py](file://app/api/v1/router.py)
- [app/api/v1/endpoints/query.py](file://app/api/v1/endpoints/query.py)
- [app/api/v1/endpoints/contribute.py](file://app/api/v1/endpoints/contribute.py)
- [app/api/v1/endpoints/reports.py](file://app/api/v1/endpoints/reports.py)
- [app/api/v1/endpoints/mdm_webhook.py](file://app/api/v1/endpoints/mdm_webhook.py)
- [app/services/billing_event_service.py](file://app/services/billing_event_service.py)
- [app/services/integrations/internal_ops/client.py](file://app/services/integrations/internal_ops/client.py)
- [app/services/integrations/platform/client.py](file://app/services/integrations/platform/client.py)
- [app/core/event_emitter.py](file://app/core/event_emitter.py)
- [app/core/auth.py](file://app/core/auth.py)
- [app/models/case_bank.py](file://app/models/case_bank.py)
- [docs/INTEGRATION_GUIDE.md](file://docs/INTEGRATION_GUIDE.md)
- [docs/architecture/SETTLE_ADMIN_ARCHITECTURE.md](file://docs/architecture/SETTLE_ADMIN_ARCHITECTURE.md)
- [tests/integration/week_16_integration_tests.py](file://tests/integration/week_16_integration_tests.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document explains the end-to-end workflows spanning multiple TrueVow services and their integration patterns. It focuses on:
- Tenant onboarding workflows and service activation
- Cross-service data flows among SETTLE, Internal Ops, Platform, and SaaS Admin
- Integration contracts between SETTLE, Internal Ops, and Platform services
- Workflow diagrams showing service interactions, data transformations, and error propagation
- Coordination mechanisms, state management, and audit trail requirements
- Monitoring, debugging techniques, and failure recovery strategies for distributed operations

## Project Structure
The SETTLE service is a FastAPI application that exposes public and authenticated endpoints, integrates with Internal Ops and Platform services, and emits behavioral events to SaaS Admin. It registers itself with the Service Registry and participates in event-driven workflows.

```mermaid
graph TB
subgraph "SETTLE Service"
MAIN["app/main.py"]
ROUTER["app/api/v1/router.py"]
QRY["app/api/v1/endpoints/query.py"]
CONTRIB["app/api/v1/endpoints/contribute.py"]
REP["app/api/v1/endpoints/reports.py"]
MDM["app/api/v1/endpoints/mdm_webhook.py"]
AUTH["app/core/auth.py"]
EVT["app/core/event_emitter.py"]
BILL["app/services/billing_event_service.py"]
IO["app/services/integrations/internal_ops/client.py"]
PLAT["app/services/integrations/platform/client.py"]
end
MAIN --> ROUTER
ROUTER --> QRY
ROUTER --> CONTRIB
ROUTER --> REP
ROUTER --> MDM
QRY --> AUTH
CONTRIB --> AUTH
REP --> AUTH
QRY --> EVT
CONTRIB --> EVT
REP --> EVT
QRY --> BILL
CONTRIB --> BILL
REP --> BILL
QRY --> IO
CONTRIB --> IO
QRY --> PLAT
CONTRIB --> PLAT
```

**Diagram sources**
- [app/main.py:102-135](file://app/main.py#L102-L135)
- [app/api/v1/router.py:5-25](file://app/api/v1/router.py#L5-L25)
- [app/api/v1/endpoints/query.py:20-98](file://app/api/v1/endpoints/query.py#L20-L98)
- [app/api/v1/endpoints/contribute.py:51-125](file://app/api/v1/endpoints/contribute.py#L51-L125)
- [app/api/v1/endpoints/reports.py:23-188](file://app/api/v1/endpoints/reports.py#L23-L188)
- [app/api/v1/endpoints/mdm_webhook.py:73-114](file://app/api/v1/endpoints/mdm_webhook.py#L73-L114)
- [app/core/auth.py:34-90](file://app/core/auth.py#L34-L90)
- [app/core/event_emitter.py:56-88](file://app/core/event_emitter.py#L56-L88)
- [app/services/billing_event_service.py:72-119](file://app/services/billing_event_service.py#L72-L119)
- [app/services/integrations/internal_ops/client.py:34-84](file://app/services/integrations/internal_ops/client.py#L34-L84)
- [app/services/integrations/platform/client.py:34-84](file://app/services/integrations/platform/client.py#L34-L84)

**Section sources**
- [app/main.py:102-135](file://app/main.py#L102-L135)
- [app/api/v1/router.py:5-25](file://app/api/v1/router.py#L5-L25)

## Core Components
- Service Registry and Heartbeat: SETTLE registers with the registry, publishes modules and integrations, and maintains a heartbeat.
- Authentication: Dual-mode authentication supporting API keys and Clerk JWT, with audit logging.
- Behavioral Event Emission: Fire-and-forget emission of feature-level events to SaaS Admin.
- Billing Event Service: Tracks billable actions and persists them for downstream processing.
- Integration Clients: Internal Ops client for activity logging, tasks, notifications, and error logging; Platform client for usage reporting and API key synchronization.
- Endpoints: Query estimation, contribution submission, report generation, and MDM webhook handlers.

**Section sources**
- [app/core/service_registry.py:64-207](file://app/core/service_registry.py#L64-L207)
- [app/core/auth.py:34-90](file://app/core/auth.py#L34-L90)
- [app/core/event_emitter.py:56-88](file://app/core/event_emitter.py#L56-L88)
- [app/services/billing_event_service.py:72-119](file://app/services/billing_event_service.py#L72-L119)
- [app/services/integrations/internal_ops/client.py:34-84](file://app/services/integrations/internal_ops/client.py#L34-L84)
- [app/services/integrations/platform/client.py:34-84](file://app/services/integrations/platform/client.py#L34-L84)
- [app/api/v1/endpoints/query.py:20-98](file://app/api/v1/endpoints/query.py#L20-L98)
- [app/api/v1/endpoints/contribute.py:51-125](file://app/api/v1/endpoints/contribute.py#L51-L125)
- [app/api/v1/endpoints/reports.py:23-188](file://app/api/v1/endpoints/reports.py#L23-L188)
- [app/api/v1/endpoints/mdm_webhook.py:73-114](file://app/api/v1/endpoints/mdm_webhook.py#L73-L114)

## Architecture Overview
SETTLE operates as a shared service with centralized settlement data. It integrates with:
- Internal Ops for activity logging, task creation, notifications, and error logging
- Platform for usage reporting and API key synchronization
- SaaS Admin via behavioral events and MDM webhooks for lifecycle events

```mermaid
graph TB
CLIENT["Client / Tenant Service"]
SETTLE["SETTLE Service"]
INTERNAL_OPS["Internal Ops Service"]
PLATFORM["Platform Service"]
SAAS_ADMIN["SaaS Admin"]
CLIENT --> SETTLE
SETTLE --> INTERNAL_OPS
SETTLE --> PLATFORM
SETTLE --> SAAS_ADMIN
```

**Diagram sources**
- [app/services/integrations/internal_ops/client.py:30-32](file://app/services/integrations/internal_ops/client.py#L30-L32)
- [app/services/integrations/platform/client.py:30-32](file://app/services/integrations/platform/client.py#L30-L32)
- [app/core/event_emitter.py:50-55](file://app/core/event_emitter.py#L50-L55)
- [app/api/v1/endpoints/mdm_webhook.py:73-89](file://app/api/v1/endpoints/mdm_webhook.py#L73-L89)

## Detailed Component Analysis

### Service Registration and Heartbeat
SETTLE registers with the Service Registry during startup, publishes module capabilities, and registers integration contracts. A background heartbeat task keeps the service alive in the registry.

```mermaid
sequenceDiagram
participant Boot as "SETTLE Startup"
participant Registry as "Service Registry"
participant HB as "HeartbeatTask"
Boot->>Registry : "POST /api/v1/registry (ServiceConfig)"
Registry-->>Boot : "Registration result"
Boot->>Registry : "POST /api/v1/registry/modules (Modules)"
Boot->>Registry : "POST /api/v1/integrations (Contracts)"
Boot->>HB : "Start heartbeat loop"
HB->>Registry : "POST /api/v1/registry/heartbeat"
```

**Diagram sources**
- [app/main.py:60-90](file://app/main.py#L60-L90)
- [app/core/service_registry.py:64-82](file://app/core/service_registry.py#L64-L82)
- [app/core/service_registry.py:113-147](file://app/core/service_registry.py#L113-L147)
- [app/core/service_registry.py:178-207](file://app/core/service_registry.py#L178-L207)
- [app/core/service_registry.py:216-243](file://app/core/service_registry.py#L216-L243)

**Section sources**
- [app/main.py:60-90](file://app/main.py#L60-L90)
- [app/core/service_registry.py:248-333](file://app/core/service_registry.py#L248-L333)

### Authentication and Audit Trail
SETTLE supports dual authentication modes and logs all auth events to an audit table for compliance.

```mermaid
flowchart TD
Start(["Incoming Request"]) --> CheckAuth["Extract Authorization/X-API-Key"]
CheckAuth --> Mode{"API Key or JWT?"}
Mode --> |API Key| VerifyKey["Verify API Key (hash lookup)"]
Mode --> |JWT| VerifyJWT["Verify Clerk JWT + Scope/Roles"]
VerifyKey --> KeyOK{"Valid?"}
VerifyJWT --> JWTOk{"Valid?"}
KeyOK --> |Yes| LogAuth["Log auth_success to audit"]
JWTOk --> |Yes| LogAuth
KeyOK --> |No| AuthFail["HTTP 401/403"]
JWTOk --> |No| AuthFail
LogAuth --> Continue["Proceed to endpoint"]
```

**Diagram sources**
- [app/core/auth.py:34-90](file://app/core/auth.py#L34-L90)
- [app/core/auth.py:392-484](file://app/core/auth.py#L392-L484)
- [app/core/auth.py:487-729](file://app/core/auth.py#L487-L729)

**Section sources**
- [app/core/auth.py:34-90](file://app/core/auth.py#L34-L90)
- [app/core/auth.py:392-484](file://app/core/auth.py#L392-L484)
- [app/core/auth.py:487-729](file://app/core/auth.py#L487-L729)

### Settlement Query Workflow
A tenant or client runs a settlement query, which triggers billing and behavioral events.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Query as "Query Endpoint"
participant Validator as "DataValidator"
participant Estimator as "SettlementEstimator"
participant DB as "Database"
participant Billing as "BillingEventService"
participant Events as "SettleEventEmitter"
participant InternalOps as "InternalOpsServiceClient"
participant Platform as "PlatformServiceClient"
Client->>Query : "POST /api/v1/query/estimate"
Query->>Validator : "Validate EstimateRequest"
Validator-->>Query : "Validation result"
Query->>DB : "Open transaction/connection"
Query->>Estimator : "estimate_settlement_range"
Estimator->>DB : "Query comparable cases"
DB-->>Estimator : "Results"
Estimator-->>Query : "EstimateResponse"
Query->>Billing : "emit_settlement_query_run"
Query->>Events : "emit settlement_query_run"
Query->>InternalOps : "log_activity (non-critical)"
Query->>Platform : "report_usage (non-critical)"
Query-->>Client : "EstimateResponse"
```

**Diagram sources**
- [app/api/v1/endpoints/query.py:20-98](file://app/api/v1/endpoints/query.py#L20-L98)
- [app/services/billing_event_service.py:271-285](file://app/services/billing_event_service.py#L271-L285)
- [app/core/event_emitter.py:56-88](file://app/core/event_emitter.py#L56-L88)
- [app/services/integrations/internal_ops/client.py:34-84](file://app/services/integrations/internal_ops/client.py#L34-L84)
- [app/services/integrations/platform/client.py:34-84](file://app/services/integrations/platform/client.py#L34-L84)

**Section sources**
- [app/api/v1/endpoints/query.py:20-98](file://app/api/v1/endpoints/query.py#L20-L98)
- [app/services/billing_event_service.py:271-285](file://app/services/billing_event_service.py#L271-L285)
- [app/core/event_emitter.py:56-88](file://app/core/event_emitter.py#L56-L88)
- [app/services/integrations/internal_ops/client.py:34-84](file://app/services/integrations/internal_ops/client.py#L34-L84)
- [app/services/integrations/platform/client.py:34-84](file://app/services/integrations/platform/client.py#L34-L84)

### Contribution Submission Workflow
Contributions are validated, anonymized, hashed, stored, and trigger behavioral and billing events. A fire-and-forget reward call may be made to another service.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Contribute as "Contribute Endpoint"
participant Contributor as "ContributionService"
participant DB as "Database"
participant Billing as "BillingEventService"
participant Events as "SettleEventEmitter"
participant InternalOps as "InternalOpsServiceClient"
participant Platform as "PlatformServiceClient"
Client->>Contribute : "POST /api/v1/contribute/submit"
Contribute->>Contributor : "submit_contribution"
Contributor->>DB : "Insert contribution (status=pending)"
DB-->>Contributor : "Success"
Contribute->>Billing : "emit_contribution_submitted"
Contribute->>Events : "emit contribution_submitted"
Contribute->>InternalOps : "log_activity (non-critical)"
Contribute->>Platform : "report_usage (non-critical)"
Contribute-->>Client : "ContributionResponse"
```

**Diagram sources**
- [app/api/v1/endpoints/contribute.py:51-125](file://app/api/v1/endpoints/contribute.py#L51-L125)
- [app/services/billing_event_service.py:305-316](file://app/services/billing_event_service.py#L305-L316)
- [app/core/event_emitter.py:56-88](file://app/core/event_emitter.py#L56-L88)
- [app/services/integrations/internal_ops/client.py:34-84](file://app/services/integrations/internal_ops/client.py#L34-L84)
- [app/services/integrations/platform/client.py:34-84](file://app/services/integrations/platform/client.py#L34-L84)

**Section sources**
- [app/api/v1/endpoints/contribute.py:51-125](file://app/api/v1/endpoints/contribute.py#L51-L125)
- [app/services/billing_event_service.py:305-316](file://app/services/billing_event_service.py#L305-L316)
- [app/core/event_emitter.py:56-88](file://app/core/event_emitter.py#L56-L88)
- [app/services/integrations/internal_ops/client.py:34-84](file://app/services/integrations/internal_ops/client.py#L34-L84)
- [app/services/integrations/platform/client.py:34-84](file://app/services/integrations/platform/client.py#L34-L84)

### Report Generation Workflow
Reports require a prior query; the endpoint retrieves query data, generates a blockchain hash, and emits events.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Reports as "Reports Endpoint"
participant DB as "Database"
participant Contributor as "ContributionService"
participant Billing as "BillingEventService"
participant Events as "SettleEventEmitter"
Client->>Reports : "POST /api/v1/reports/generate (query_id or estimate_id)"
Reports->>DB : "Retrieve query data (if exists)"
DB-->>Reports : "Query data or empty"
Reports->>Contributor : "_generate_blockchain_hash"
Reports->>Billing : "emit_report_generated"
Reports->>Events : "emit report_generated"
Reports-->>Client : "ReportResponse"
```

**Diagram sources**
- [app/api/v1/endpoints/reports.py:23-188](file://app/api/v1/endpoints/reports.py#L23-L188)
- [app/services/billing_event_service.py:288-302](file://app/services/billing_event_service.py#L288-L302)
- [app/core/event_emitter.py:56-88](file://app/core/event_emitter.py#L56-L88)

**Section sources**
- [app/api/v1/endpoints/reports.py:23-188](file://app/api/v1/endpoints/reports.py#L23-L188)
- [app/services/billing_event_service.py:288-302](file://app/services/billing_event_service.py#L288-L302)
- [app/core/event_emitter.py:56-88](file://app/core/event_emitter.py#L56-L88)

### MDM Webhook Workflow
SETTLE receives lifecycle events from MDM, updates snapshots, emits billing events, and records internal events.

```mermaid
sequenceDiagram
participant MDM as "MDM (SaaS Admin)"
participant Webhook as "MDM Webhook Endpoint"
participant DB as "Database"
participant Billing as "BillingEventService"
MDM->>Webhook : "POST /api/v1/events/mdm (case.created/updated/settled)"
Webhook->>DB : "Upsert settle_case_snapshots"
Webhook->>Billing : "emit_settle_case_open (on created)"
Webhook->>DB : "Insert settle_events"
Webhook-->>MDM : "Status response"
```

**Diagram sources**
- [app/api/v1/endpoints/mdm_webhook.py:73-114](file://app/api/v1/endpoints/mdm_webhook.py#L73-L114)
- [app/api/v1/endpoints/mdm_webhook.py:116-183](file://app/api/v1/endpoints/mdm_webhook.py#L116-L183)
- [app/api/v1/endpoints/mdm_webhook.py:186-249](file://app/api/v1/endpoints/mdm_webhook.py#L186-L249)
- [app/api/v1/endpoints/mdm_webhook.py:252-292](file://app/api/v1/endpoints/mdm_webhook.py#L252-L292)
- [app/services/billing_event_service.py:260-268](file://app/services/billing_event_service.py#L260-L268)

**Section sources**
- [app/api/v1/endpoints/mdm_webhook.py:73-114](file://app/api/v1/endpoints/mdm_webhook.py#L73-L114)
- [app/api/v1/endpoints/mdm_webhook.py:116-183](file://app/api/v1/endpoints/mdm_webhook.py#L116-L183)
- [app/api/v1/endpoints/mdm_webhook.py:186-249](file://app/api/v1/endpoints/mdm_webhook.py#L186-L249)
- [app/api/v1/endpoints/mdm_webhook.py:252-292](file://app/api/v1/endpoints/mdm_webhook.py#L252-L292)
- [app/services/billing_event_service.py:260-268](file://app/services/billing_event_service.py#L260-L268)

### Integration Contracts: SETTLE ↔ Internal Ops
- Purpose: Activity logging, task creation, notifications, error logging
- Non-critical failures: All calls return success/failure without raising exceptions
- Typical payloads include user_id, activity_type, task metadata, notification details, and error context

**Section sources**
- [app/services/integrations/internal_ops/client.py:34-84](file://app/services/integrations/internal_ops/client.py#L34-L84)
- [app/services/integrations/internal_ops/client.py:86-142](file://app/services/integrations/internal_ops/client.py#L86-L142)
- [app/services/integrations/internal_ops/client.py:144-198](file://app/services/integrations/internal_ops/client.py#L144-L198)
- [app/services/integrations/internal_ops/client.py:200-238](file://app/services/integrations/internal_ops/client.py#L200-L238)

### Integration Contracts: SETTLE ↔ Platform
- Purpose: Usage reporting for billing and API key status synchronization
- Non-critical failures: Usage reporting and sync return success/failure without raising exceptions

**Section sources**
- [app/services/integrations/platform/client.py:34-84](file://app/services/integrations/platform/client.py#L34-L84)
- [app/services/integrations/platform/client.py:86-122](file://app/services/integrations/platform/client.py#L86-L122)
- [app/services/integrations/platform/client.py:124-140](file://app/services/integrations/platform/client.py#L124-L140)

### Data Models and Validation
- EstimateRequest and EstimateResponse define the query interface and response structure
- ContributionRequest and ContributionResponse define contribution interface and response structure
- Validation enforces jurisdiction format, outcome ranges, and ethical compliance

**Section sources**
- [app/models/case_bank.py:69-139](file://app/models/case_bank.py#L69-L139)
- [app/models/case_bank.py:141-203](file://app/models/case_bank.py#L141-L203)

### Tenant Onboarding and Service Activation
- Founding Member creation involves approvals in SaaS Admin and API key generation in SETTLE
- API keys are stored with hashes and linked to user records
- Access levels determine permissions for contributions and administrative endpoints

**Section sources**
- [docs/architecture/SETTLE_ADMIN_ARCHITECTURE.md:430-515](file://docs/architecture/SETTLE_ADMIN_ARCHITECTURE.md#L430-L515)
- [docs/INTEGRATION_GUIDE.md:331-361](file://docs/INTEGRATION_GUIDE.md#L331-L361)

## Dependency Analysis
SETTLE depends on:
- Core modules for authentication, event emission, and service registry
- Integration clients for Internal Ops and Platform
- Billing event service for metering
- Database access for persistence
- Pydantic models for request/response validation

```mermaid
graph TB
QRY["query.py"] --> AUTH["auth.py"]
QRY --> EVT["event_emitter.py"]
QRY --> BILL["billing_event_service.py"]
QRY --> IO["internal_ops/client.py"]
QRY --> PLAT["platform/client.py"]
CONTRIB["contribute.py"] --> AUTH
CONTRIB --> EVT
CONTRIB --> BILL
CONTRIB --> IO
CONTRIB --> PLAT
REP["reports.py"] --> AUTH
REP --> EVT
REP --> BILL
MDM["mdm_webhook.py"] --> BILL
```

**Diagram sources**
- [app/api/v1/endpoints/query.py:9-14](file://app/api/v1/endpoints/query.py#L9-L14)
- [app/api/v1/endpoints/contribute.py:9-13](file://app/api/v1/endpoints/contribute.py#L9-L13)
- [app/api/v1/endpoints/reports.py:11-17](file://app/api/v1/endpoints/reports.py#L11-L17)
- [app/api/v1/endpoints/mdm_webhook.py:19-21](file://app/api/v1/endpoints/mdm_webhook.py#L19-L21)

**Section sources**
- [app/api/v1/endpoints/query.py:9-14](file://app/api/v1/endpoints/query.py#L9-L14)
- [app/api/v1/endpoints/contribute.py:9-13](file://app/api/v1/endpoints/contribute.py#L9-L13)
- [app/api/v1/endpoints/reports.py:11-17](file://app/api/v1/endpoints/reports.py#L11-L17)
- [app/api/v1/endpoints/mdm_webhook.py:19-21](file://app/api/v1/endpoints/mdm_webhook.py#L19-L21)

## Performance Considerations
- Response targets: Sub-second p95 for queries; under 2 seconds for report generation
- Asynchronous operations: Heartbeat, event emission, and integration calls are non-blocking
- Background tasks: API key last_used_at updates occur asynchronously
- Caching and indexing: Database queries leverage indexed fields for comparable cases

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
- Authentication failures: Check audit logs for auth_success/auth_failure entries and verify API key/JWT validity
- Integration failures: Internal Ops and Platform calls are non-critical; inspect logs for error messages and retry policies
- Billing events: Verify pending events and status transitions; reconcile with downstream systems
- Webhook handling: Validate MDM API key, parse JSON correctly, and confirm snapshot updates and event recording
- Monitoring: Use heartbeat, request IDs, and Sentry for distributed tracing

**Section sources**
- [app/core/auth.py:34-90](file://app/core/auth.py#L34-L90)
- [app/services/integrations/internal_ops/client.py:81-84](file://app/services/integrations/internal_ops/client.py#L81-L84)
- [app/services/integrations/platform/client.py:82-84](file://app/services/integrations/platform/client.py#L82-L84)
- [app/services/billing_event_service.py:120-143](file://app/services/billing_event_service.py#L120-L143)
- [app/api/v1/endpoints/mdm_webhook.py:86-95](file://app/api/v1/endpoints/mdm_webhook.py#L86-L95)

## Conclusion
SETTLE orchestrates settlement intelligence workflows across services with robust authentication, non-critical integration calls, and comprehensive eventing. Its integration contracts with Internal Ops and Platform enable seamless operational insights and billing alignment, while MDM webhooks maintain accurate case snapshots. The documented workflows, diagrams, and troubleshooting steps provide a blueprint for reliable, observable, and recoverable distributed operations.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Appendix A: Behavioral Events Emitted by SETTLE
- settlement_query_run
- report_generated
- contribution_submitted

**Section sources**
- [app/core/event_emitter.py:36-41](file://app/core/event_emitter.py#L36-L41)

### Appendix B: Billable Actions and Billing Events
- settle_case_open
- settlement_query_run
- report_generated
- contribution_submitted

**Section sources**
- [app/services/billing_event_service.py:31-36](file://app/services/billing_event_service.py#L31-L36)

### Appendix C: Integration Tests Coverage
- Service-to-service communication checks
- Settlement query workflow validation
- Contribution workflow validation
- Report generation workflow validation

**Section sources**
- [tests/integration/week_16_integration_tests.py:713-749](file://tests/integration/week_16_integration_tests.py#L713-L749)
- [tests/integration/week_16_integration_tests.py:246-280](file://tests/integration/week_16_integration_tests.py#L246-L280)