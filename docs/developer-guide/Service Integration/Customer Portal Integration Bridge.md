# Customer Portal Integration Bridge

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [app/main.py](file://app/main.py)
- [app/api/v1/router.py](file://app/api/v1/router.py)
- [app/api/v1/endpoints/query.py](file://app/api/v1/endpoints/query.py)
- [app/api/v1/endpoints/reports.py](file://app/api/v1/endpoints/reports.py)
- [app/api/v1/endpoints/contribute.py](file://app/api/v1/endpoints/contribute.py)
- [app/core/config.py](file://app/core/config.py)
- [app/core/service_auth.py](file://app/core/service_auth.py)
- [app/services/integrations/internal_ops/client.py](file://app/services/integrations/internal_ops/client.py)
- [app/services/integrations/platform/client.py](file://app/services/integrations/platform/client.py)
- [app/models/case_bank.py](file://app/models/case_bank.py)
- [docs/INTEGRATION_GUIDE.md](file://docs/INTEGRATION_GUIDE.md)
- [docs/API_DOCUMENTATION.md](file://docs/API_DOCUMENTATION.md)
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

## Introduction
This document describes the Customer Portal Integration Bridge for the TrueVow SETTLE Service, focusing on how external customer portals and tenant applications integrate with the centralized settlement intelligence service. The bridge enables secure, authenticated access to settlement range estimation, contribution submission, and report generation while maintaining strict compliance with ethical and privacy standards.

The SETTLE Service operates as a shared, centralized service (not tenant-specific) and exposes both public endpoints (e.g., waitlist and stats) and authenticated endpoints for query, contribution, and reporting. Integration with other TrueVow services follows a standardized service-to-service authentication pattern using API keys and mandatory request headers.

## Project Structure
The integration bridge spans several key areas:
- Application entry point and routing
- API endpoints for query, contribution, and reports
- Service configuration and authentication
- Integration clients for Internal Ops and Platform services
- Data models for request/response validation

```mermaid
graph TB
subgraph "SETTLE Service"
Main["app/main.py<br/>FastAPI app, CORS, routes"]
Router["app/api/v1/router.py<br/>Route registration"]
Query["app/api/v1/endpoints/query.py<br/>/api/v1/query/estimate"]
Reports["app/api/v1/endpoints/reports.py<br/>/api/v1/reports/generate"]
Contribute["app/api/v1/endpoints/contribute.py<br/>/api/v1/contribute/submit"]
Config["app/core/config.py<br/>Settings and service URLs"]
Auth["app/core/service_auth.py<br/>Service authentication"]
CaseBank["app/models/case_bank.py<br/>Pydantic models"]
end
subgraph "Integration Clients"
InternalOps["app/services/integrations/internal_ops/client.py<br/>Internal Ops client"]
Platform["app/services/integrations/platform/client.py<br/>Platform client"]
end
Main --> Router
Router --> Query
Router --> Reports
Router --> Contribute
Query --> Auth
Reports --> Auth
Contribute --> Auth
Query --> CaseBank
Reports --> CaseBank
Auth --> Config
InternalOps --> Config
Platform --> Config
```

**Diagram sources**
- [app/main.py:1-87](file://app/main.py#L1-L87)
- [app/api/v1/router.py:1-22](file://app/api/v1/router.py#L1-L22)
- [app/api/v1/endpoints/query.py:1-153](file://app/api/v1/endpoints/query.py#L1-L153)
- [app/api/v1/endpoints/reports.py:1-248](file://app/api/v1/endpoints/reports.py#L1-L248)
- [app/api/v1/endpoints/contribute.py:1-112](file://app/api/v1/endpoints/contribute.py#L1-L112)
- [app/core/config.py:1-363](file://app/core/config.py#L1-L363)
- [app/core/service_auth.py:1-376](file://app/core/service_auth.py#L1-L376)
- [app/models/case_bank.py:1-347](file://app/models/case_bank.py#L1-L347)
- [app/services/integrations/internal_ops/client.py:1-244](file://app/services/integrations/internal_ops/client.py#L1-L244)
- [app/services/integrations/platform/client.py:1-145](file://app/services/integrations/platform/client.py#L1-L145)

**Section sources**
- [README.md:1-297](file://README.md#L1-L297)
- [app/main.py:1-87](file://app/main.py#L1-L87)
- [app/api/v1/router.py:1-22](file://app/api/v1/router.py#L1-L22)

## Core Components
- FastAPI Application: Initializes logging, Sentry monitoring (conditional), CORS, and registers API routers.
- API Router: Organizes public, authenticated, and admin endpoints under /api/v1.
- Endpoints:
  - Query: Settlement range estimation with validation and pilot-mode user handling.
  - Reports: Report generation with blockchain hashing and optional JSON summary.
  - Contribute: Contribution submission with compliance validation and future database integration.
- Authentication: Service-to-service authentication enforcing API keys, service names, and request IDs.
- Integration Clients:
  - Internal Ops Client: Logs activity, creates tasks, sends notifications, and logs errors.
  - Platform Client: Consumes reports for billing and retrieves tenant information.

**Section sources**
- [app/main.py:1-87](file://app/main.py#L1-L87)
- [app/api/v1/router.py:1-22](file://app/api/v1/router.py#L1-L22)
- [app/api/v1/endpoints/query.py:1-153](file://app/api/v1/endpoints/query.py#L1-L153)
- [app/api/v1/endpoints/reports.py:1-248](file://app/api/v1/endpoints/reports.py#L1-L248)
- [app/api/v1/endpoints/contribute.py:1-112](file://app/api/v1/endpoints/contribute.py#L1-L112)
- [app/core/service_auth.py:1-376](file://app/core/service_auth.py#L1-L376)
- [app/services/integrations/internal_ops/client.py:1-244](file://app/services/integrations/internal_ops/client.py#L1-L244)
- [app/services/integrations/platform/client.py:1-145](file://app/services/integrations/platform/client.py#L1-L145)

## Architecture Overview
The Customer Portal Integration Bridge leverages a five-service enterprise architecture. The SETTLE Service acts as a centralized shared service, accessible to both TrueVow customers and non-customers via API keys. It communicates with other services using standardized headers and API keys.

```mermaid
graph TB
subgraph "TrueVow Enterprise Platform"
PlatformSvc["Platform Service<br/>Tenant mgmt, billing, integration gateway"]
InternalOpsSvc["Internal Ops Service<br/>Task mgmt, time tracking, notifications"]
SalesSvc["Sales Service<br/>Pipeline, demos"]
SupportSvc["Support Service<br/>Tickets, inbox"]
TenantSvc["Tenant Service<br/>INTAKE, DRAFT, BILLING"]
SETTLE["SETTLE Service<br/>Settlement DB, range estimation, reporting"]
end
TenantSvc --> SETTLE
PlatformSvc --> SETTLE
SETTLE --> InternalOpsSvc
SETTLE -.-> SalesSvc
SETTLE -.-> SupportSvc
```

**Diagram sources**
- [README.md:26-92](file://README.md#L26-L92)
- [docs/INTEGRATION_GUIDE.md:47-93](file://docs/INTEGRATION_GUIDE.md#L47-L93)

## Detailed Component Analysis

### Query Estimation Workflow
The query endpoint estimates settlement ranges using comparable cases, with validation, pilot-mode user handling, and optional forwarding of end-user identity via a special header when using API key authentication.

```mermaid
sequenceDiagram
participant Portal as "Customer Portal"
participant Tenant as "Tenant Service"
participant SETTLE as "SETTLE Service"
participant DB as "Database"
Portal->>Tenant : "Submit case details"
Tenant->>SETTLE : "POST /api/v1/query/estimate<br/>Authorization, X-Service-Name, X-Request-ID"
SETTLE->>SETTLE : "Validate request"
SETTLE->>DB : "Fetch comparable cases"
DB-->>SETTLE : "Matching cases"
SETTLE->>SETTLE : "Compute percentiles/multiplier"
SETTLE-->>Tenant : "EstimateResponse"
Tenant-->>Portal : "Display settlement range"
```

**Diagram sources**
- [app/api/v1/endpoints/query.py:20-132](file://app/api/v1/endpoints/query.py#L20-L132)
- [docs/INTEGRATION_GUIDE.md:154-214](file://docs/INTEGRATION_GUIDE.md#L154-L214)

**Section sources**
- [app/api/v1/endpoints/query.py:1-153](file://app/api/v1/endpoints/query.py#L1-L153)
- [docs/INTEGRATION_GUIDE.md:154-214](file://docs/INTEGRATION_GUIDE.md#L154-L214)

### Report Generation Workflow
The reports endpoint generates a 4-page professional report, optionally returning a JSON summary. It retrieves prior query data and constructs a blockchain hash for verification.

```mermaid
sequenceDiagram
participant Portal as "Customer Portal"
participant Tenant as "Tenant Service"
participant SETTLE as "SETTLE Service"
Portal->>Tenant : "Request report"
Tenant->>SETTLE : "POST /api/v1/reports/generate<br/>query_id/format"
SETTLE->>SETTLE : "Retrieve estimate data"
SETTLE->>SETTLE : "Generate blockchain hash"
SETTLE-->>Tenant : "ReportResponse (URL/JSON)"
Tenant-->>Portal : "Provide download link"
```

**Diagram sources**
- [app/api/v1/endpoints/reports.py:22-177](file://app/api/v1/endpoints/reports.py#L22-L177)
- [docs/INTEGRATION_GUIDE.md:272-314](file://docs/INTEGRATION_GUIDE.md#L272-L314)

**Section sources**
- [app/api/v1/endpoints/reports.py:1-248](file://app/api/v1/endpoints/reports.py#L1-L248)
- [docs/INTEGRATION_GUIDE.md:272-314](file://docs/INTEGRATION_GUIDE.md#L272-L314)

### Contribution Submission Workflow
The contribution endpoint validates submissions against strict ethical guidelines and prepares blockchain receipts for auditability.

```mermaid
flowchart TD
Start(["Contribution Request"]) --> Validate["Validate fields and compliance"]
Validate --> Valid{"Valid?"}
Valid --> |No| ReturnError["Return 400 with errors"]
Valid --> |Yes| Hash["Generate blockchain hash"]
Hash --> Store["Store contribution (status=pending)"]
Store --> Notify["Notify Internal Ops (optional)"]
Notify --> ReturnSuccess["Return confirmation"]
ReturnError --> End(["End"])
ReturnSuccess --> End
```

**Diagram sources**
- [app/api/v1/endpoints/contribute.py:16-82](file://app/api/v1/endpoints/contribute.py#L16-L82)
- [docs/INTEGRATION_GUIDE.md:217-268](file://docs/INTEGRATION_GUIDE.md#L217-L268)

**Section sources**
- [app/api/v1/endpoints/contribute.py:1-112](file://app/api/v1/endpoints/contribute.py#L1-L112)
- [docs/INTEGRATION_GUIDE.md:217-268](file://docs/INTEGRATION_GUIDE.md#L217-L268)

### Service Authentication and Integration
Service-to-service authentication requires standardized headers and API keys. The configuration module centralizes service URLs and timeouts, enabling consistent client initialization.

```mermaid
classDiagram
class ServiceAuth {
+__call__(authorization, x_service_name, x_request_id, x_request_timestamp) Dict
+AUTHENTICATED_SERVICES : List[str]
}
class ServiceClient {
+get(endpoint, **kwargs) Dict
+post(endpoint, json, **kwargs) Dict
+close() void
-_get_headers() Dict
}
class Settings {
+SERVICE_NAME : str
+SERVICE_PORT : int
+PLATFORM_SERVICE_URL : str
+INTERNAL_OPS_SERVICE_URL : str
+INTERNAL_OPS_TIMEOUT : int
+platform_service_api_key : Optional[str]
}
ServiceAuth --> Settings : "reads service URLs"
ServiceClient --> Settings : "uses service URLs and timeouts"
```

**Diagram sources**
- [app/core/service_auth.py:20-180](file://app/core/service_auth.py#L20-L180)
- [app/core/service_auth.py:183-321](file://app/core/service_auth.py#L183-L321)
- [app/core/config.py:266-331](file://app/core/config.py#L266-L331)

**Section sources**
- [app/core/service_auth.py:1-376](file://app/core/service_auth.py#L1-L376)
- [app/core/config.py:1-363](file://app/core/config.py#L1-L363)

### Integration Clients
- Internal Ops Client: Provides methods to log activity, create tasks, send notifications, and log errors. Non-critical failures are handled gracefully.
- Platform Client: Integrates with the Platform Service for billing consumption and tenant information retrieval.

```mermaid
classDiagram
class InternalOpsServiceClient {
+log_activity(user_id, activity_type, duration_seconds, metadata) Dict
+create_task(task_title, assigned_to, task_type, description, priority, due_date, metadata) Dict
+send_notification(user_id, notification_type, title, message, priority, metadata) Dict
+log_error(user_id, error_type, error_message, metadata) Dict
+close() void
}
class PlatformServiceClient {
+consume_report(tenant_id, case_id, report_id) Dict
+get_tenant_info(tenant_id) Optional[Dict]
+close() void
}
InternalOpsServiceClient --> ServiceClient : "uses"
PlatformServiceClient --> ServiceClient : "uses"
```

**Diagram sources**
- [app/services/integrations/internal_ops/client.py:19-244](file://app/services/integrations/internal_ops/client.py#L19-L244)
- [app/services/integrations/platform/client.py:39-145](file://app/services/integrations/platform/client.py#L39-L145)
- [app/core/service_auth.py:327-375](file://app/core/service_auth.py#L327-L375)

**Section sources**
- [app/services/integrations/internal_ops/client.py:1-244](file://app/services/integrations/internal_ops/client.py#L1-L244)
- [app/services/integrations/platform/client.py:1-145](file://app/services/integrations/platform/client.py#L1-L145)
- [app/core/service_auth.py:327-375](file://app/core/service_auth.py#L327-L375)

## Dependency Analysis
The integration bridge depends on:
- FastAPI for routing and request handling
- Pydantic models for request/response validation
- Service authentication for secure inter-service communication
- Configuration module for service URLs and timeouts
- Integration clients for downstream services

```mermaid
graph TB
QueryEP["query.py"] --> AuthDep["service_auth.py"]
ReportsEP["reports.py"] --> AuthDep
ContributeEP["contribute.py"] --> AuthDep
AuthDep --> ConfigMod["config.py"]
InternalOpsClient["internal_ops/client.py"] --> AuthDep
PlatformClient["platform/client.py"] --> AuthDep
QueryEP --> CaseBank["case_bank.py"]
ReportsEP --> CaseBank
```

**Diagram sources**
- [app/api/v1/endpoints/query.py:1-153](file://app/api/v1/endpoints/query.py#L1-L153)
- [app/api/v1/endpoints/reports.py:1-248](file://app/api/v1/endpoints/reports.py#L1-L248)
- [app/api/v1/endpoints/contribute.py:1-112](file://app/api/v1/endpoints/contribute.py#L1-L112)
- [app/core/service_auth.py:1-376](file://app/core/service_auth.py#L1-L376)
- [app/core/config.py:1-363](file://app/core/config.py#L1-L363)
- [app/models/case_bank.py:1-347](file://app/models/case_bank.py#L1-L347)
- [app/services/integrations/internal_ops/client.py:1-244](file://app/services/integrations/internal_ops/client.py#L1-L244)
- [app/services/integrations/platform/client.py:1-145](file://app/services/integrations/platform/client.py#L1-L145)

**Section sources**
- [app/api/v1/endpoints/query.py:1-153](file://app/api/v1/endpoints/query.py#L1-L153)
- [app/api/v1/endpoints/reports.py:1-248](file://app/api/v1/endpoints/reports.py#L1-L248)
- [app/api/v1/endpoints/contribute.py:1-112](file://app/api/v1/endpoints/contribute.py#L1-L112)
- [app/core/service_auth.py:1-376](file://app/core/service_auth.py#L1-L376)
- [app/core/config.py:1-363](file://app/core/config.py#L1-L363)
- [app/models/case_bank.py:1-347](file://app/models/case_bank.py#L1-L347)
- [app/services/integrations/internal_ops/client.py:1-244](file://app/services/integrations/internal_ops/client.py#L1-L244)
- [app/services/integrations/platform/client.py:1-145](file://app/services/integrations/platform/client.py#L1-L145)

## Performance Considerations
- Response time targets: Query endpoint aims for sub-second response times; reports generation targets under two seconds.
- Rate limiting: Configurable per access level (founding members, standard, premium).
- Caching: Redis configuration supports caching for improved performance.
- Timeouts: Service clients enforce timeouts for downstream calls.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common integration issues and resolutions:
- Authentication failures: Ensure Authorization header contains a valid API key, and X-Service-Name and X-Request-ID are present.
- Rate limit exceeded: Monitor access levels and reduce request frequency accordingly.
- Service timeouts: Increase timeouts or retry with exponential backoff.
- Validation errors: Review request payloads against documented schemas and validation rules.

**Section sources**
- [docs/INTEGRATION_GUIDE.md:738-800](file://docs/INTEGRATION_GUIDE.md#L738-L800)
- [docs/API_DOCUMENTATION.md:47-71](file://docs/API_DOCUMENTATION.md#L47-L71)

## Conclusion
The Customer Portal Integration Bridge provides a robust, secure pathway for customer portals and tenant applications to leverage the SETTLE Service’s settlement intelligence capabilities. By adhering to standardized authentication, request/response formats, and integration patterns, systems can reliably estimate settlement ranges, submit contributions, and generate verifiable reports while maintaining compliance and performance standards.