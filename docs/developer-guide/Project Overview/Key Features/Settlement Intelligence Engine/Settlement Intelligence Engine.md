# Settlement Intelligence Engine

<cite>
**Referenced Files in This Document**
- [settlement_calculator.py](file://app/services/settlement_calculator.py)
- [estimator.py](file://app/services/estimator.py)
- [similarity_engine.py](file://app/services/similarity_engine.py)
- [case_bank.py](file://app/models/case_bank.py)
- [query.py](file://app/api/v1/endpoints/query.py)
- [router.py](file://app/api/v1/router.py)
- [reports.py](file://app/api/v1/endpoints/reports.py)
- [pdf_generator.py](file://app/services/reports/pdf_generator.py)
- [validator.py](file://app/services/validator.py)
- [anonymizer.py](file://app/services/anonymizer.py)
- [billing_event_service.py](file://app/services/billing_event_service.py)
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
The Settlement Intelligence Engine provides percentile-based settlement range estimation using two complementary methodologies:
- Database-driven percentile calculation when sufficient comparable cases are available
- Multiplier fallback system for limited-data scenarios

The system integrates a deterministic similarity engine for comparable case discovery, a robust confidence scoring framework, and comprehensive reporting with blockchain verification. It supports both authenticated API access and compliance-focused data handling.

## Project Structure
The Settlement Intelligence Engine is organized around three primary layers:
- API Layer: FastAPI endpoints for estimation, reporting, and administrative functions
- Services Layer: Core algorithms for estimation, similarity matching, validation, and reporting
- Models Layer: Pydantic models defining request/response schemas and domain entities

```mermaid
graph TB
subgraph "API Layer"
Q[Query Endpoint]
R[Reports Endpoint]
RT[Router]
end
subgraph "Services Layer"
EST[SettlementEstimator]
SC[SettlementCalculator]
SE[SimilarityEngine]
VAL[DataValidator]
ANON[AnonymizationValidator]
PDF[PDFGenerator]
BE[BillingEventService]
end
subgraph "Models Layer"
REQ[EstimateRequest]
RES[EstimateResponse]
CC[ComparableCase]
SCModel[SettleContribution]
end
Q --> EST
R --> PDF
RT --> Q
RT --> R
EST --> SE
EST --> VAL
EST --> ANON
EST --> BE
SC --> SE
SC --> BE
EST --> REQ
EST --> RES
EST --> CC
EST --> SCModel
```

**Diagram sources**
- [router.py:1-26](file://app/api/v1/router.py#L1-L26)
- [query.py:1-119](file://app/api/v1/endpoints/query.py#L1-L119)
- [reports.py:1-259](file://app/api/v1/endpoints/reports.py#L1-L259)
- [estimator.py:25-443](file://app/services/estimator.py#L25-L443)
- [settlement_calculator.py:41-257](file://app/services/settlement_calculator.py#L41-L257)
- [similarity_engine.py:188-441](file://app/services/similarity_engine.py#L188-L441)
- [case_bank.py:69-139](file://app/models/case_bank.py#L69-L139)

**Section sources**
- [router.py:1-26](file://app/api/v1/router.py#L1-L26)
- [query.py:1-119](file://app/api/v1/endpoints/query.py#L1-L119)
- [reports.py:1-259](file://app/api/v1/endpoints/reports.py#L1-L259)

## Core Components
This section documents the primary algorithms and services that power the Settlement Intelligence Engine.

### Percentile-Based Settlement Range Estimator
The SettlementEstimator implements the dual-methodology approach:
- Database-driven percentile calculation for ≥15 cases using 25th, median, 75th, and 95th percentiles
- Multiplier fallback system for <15 cases using industry-standard multipliers
- Confidence scoring thresholds: high (≥30), medium (15-29), low (<15)

```mermaid
flowchart TD
Start([Estimate Request]) --> QueryCases["Query Comparable Cases"]
QueryCases --> CheckCases{"Case Count ≥ 15?"}
CheckCases --> |Yes| PercentileCalc["Calculate Percentiles<br/>25th, Median, 75th, 95th"]
CheckCases --> |No| MultiplierCalc["Apply Multiplier Fallback<br/>Medical Bills × Industry Multipliers"]
PercentileCalc --> MedicalAdjust["Adjust for Medical Bill Differences"]
MedicalAdjust --> Confidence["Assign Confidence Level<br/>High/Medium/Low"]
MultiplierCalc --> Confidence
Confidence --> RepresentativeCases["Select Representative Cases"]
RepresentativeCases --> Justification["Generate Range Justification"]
Justification --> Response([EstimateResponse])
```

**Diagram sources**
- [estimator.py:60-116](file://app/services/estimator.py#L60-L116)
- [estimator.py:148-210](file://app/services/estimator.py#L148-L210)
- [estimator.py:212-262](file://app/services/estimator.py#L212-L262)
- [estimator.py:291-343](file://app/services/estimator.py#L291-L343)
- [estimator.py:345-388](file://app/services/estimator.py#L345-L388)

### Deterministic Similarity Engine
The SimilarityEngine computes weighted similarity scores (0-100) between target cases and historical settlement records using structured legal signals:
- Incident type matching with relatedness matrix
- Injury category severity levels
- Jurisdiction scoring (exact county, same state, neighboring state)
- Medical specials band adjacency
- Liability strength and litigation stage matching

```mermaid
classDiagram
class SimilarityEngine {
+compute_similarity(target, record) SimilarityResult
+find_comparable_settlements(target, records) SimilarityResult[]
-_score_incident_type(target, record) int
-_score_injury_category(target, record) int
-_score_jurisdiction(target_state, target_county, record_state, record_county) int
-_score_medical_specials(target, record) int
-_score_liability_strength(target, record) int
-_score_litigation_stage(target, record) int
-_score_policy_limit(target, record) int
}
class SimilarityResult {
+string record_id
+int similarity_score
+string settlement_band
+Dict~string, int~ factors
}
class CaseSnapshot {
+string case_id
+string tenant_id
+string incident_type
+string injury_category
+string county
+string state
+Optional~string~ policy_limit_band
+Optional~string~ insurer
+string litigation_stage
+Optional~string~ medical_specials_band
+string liability_strength
}
class SettlementRecord {
+string record_id
+string state
+string county
+string incident_type
+string injury_category
+Optional~string~ medical_specials_band
+Optional~string~ policy_limit_band
+Optional~string~ insurer
+string litigation_stage
+string liability_strength
+string settlement_band
+string settlement_month
}
SimilarityEngine --> SimilarityResult : "creates"
SimilarityEngine --> CaseSnapshot : "matches against"
SimilarityEngine --> SettlementRecord : "scores against"
```

**Diagram sources**
- [similarity_engine.py:188-418](file://app/services/similarity_engine.py#L188-L418)
- [similarity_engine.py:75-115](file://app/services/similarity_engine.py#L75-L115)
- [similarity_engine.py:91-106](file://app/services/similarity_engine.py#L91-L106)

### Confidence Scoring System
The SettlementCalculator implements a weighted confidence scoring system:
- Sample size contribution (0-40 points)
- Jurisdiction match strength (0-30 points)
- Average similarity score (0-30 points)

Confidence labels: High (80+), Moderate (60+), Low (40+), Very Low (<40)

```mermaid
flowchart TD
Start([Comparable Results]) --> ExtractValues["Extract Settlement Values"]
ExtractValues --> Percentiles["Calculate Percentiles<br/>25th, Median, 75th"]
Percentiles --> Confidence["Calculate Confidence Score"]
Confidence --> SampleSize["Score Sample Size<br/>0-40"]
Confidence --> Jurisdiction["Score Jurisdiction<br/>0-30"]
Confidence --> Similarity["Score Average Similarity<br/>0-30"]
SampleSize --> Total["Total Score ≤ 100"]
Jurisdiction --> Total
Similarity --> Total
Total --> Label["Convert to Confidence Label"]
Label --> Response([SettlementRange])
```

**Diagram sources**
- [settlement_calculator.py:57-103](file://app/services/settlement_calculator.py#L57-L103)
- [settlement_calculator.py:117-191](file://app/services/settlement_calculator.py#L117-L191)

**Section sources**
- [estimator.py:25-50](file://app/services/estimator.py#L25-L50)
- [settlement_calculator.py:41-191](file://app/services/settlement_calculator.py#L41-L191)
- [similarity_engine.py:188-418](file://app/services/similarity_engine.py#L188-L418)

## Architecture Overview
The Settlement Intelligence Engine follows a layered architecture with clear separation of concerns:

```mermaid
graph TB
subgraph "External Clients"
API[Web Applications]
Mobile[Mobile Apps]
Admin[Admin Portal]
end
subgraph "API Gateway"
Auth[Authentication]
RateLimit[Rate Limiting]
end
subgraph "Intelligence Engine"
Query[Query Service]
Reports[Reports Service]
Billing[Billing Service]
end
subgraph "Data Layer"
DB[(PostgreSQL Database)]
Cache[(Redis Cache)]
Storage[(S3 Storage)]
end
API --> Auth
Mobile --> Auth
Admin --> Auth
Auth --> RateLimit
RateLimit --> Query
RateLimit --> Reports
RateLimit --> Billing
Query --> DB
Reports --> DB
Reports --> Storage
Billing --> DB
Query --> Cache
Reports --> Cache
```

**Diagram sources**
- [query.py:20-98](file://app/api/v1/endpoints/query.py#L20-L98)
- [reports.py:23-188](file://app/api/v1/endpoints/reports.py#L23-L188)
- [billing_event_service.py:62-169](file://app/services/billing_event_service.py#L62-L169)

### API Integration Patterns
The engine exposes RESTful endpoints with standardized request/response patterns:

```mermaid
sequenceDiagram
participant Client as "Client Application"
participant API as "FastAPI Router"
participant Query as "Query Endpoint"
participant Estimator as "SettlementEstimator"
participant Validator as "DataValidator"
participant DB as "Database"
participant Billing as "BillingService"
Client->>API : POST /api/v1/query/estimate
API->>Query : Route request
Query->>Validator : Validate request
Validator-->>Query : Validation result
Query->>Estimator : estimate_settlement_range(request)
Estimator->>DB : Query comparable cases
DB-->>Estimator : Comparable cases
Estimator->>Estimator : Calculate ranges
Estimator-->>Query : EstimateResponse
Query->>Billing : Emit settlement_query_run event
Billing-->>Query : Event acknowledged
Query-->>Client : EstimateResponse
```

**Diagram sources**
- [query.py:20-98](file://app/api/v1/endpoints/query.py#L20-L98)
- [estimator.py:60-116](file://app/services/estimator.py#L60-L116)
- [billing_event_service.py:271-285](file://app/services/billing_event_service.py#L271-L285)

**Section sources**
- [router.py:1-26](file://app/api/v1/router.py#L1-L26)
- [query.py:20-98](file://app/api/v1/endpoints/query.py#L20-L98)
- [reports.py:23-188](file://app/api/v1/endpoints/reports.py#L23-L188)

## Detailed Component Analysis

### Percentile-Based Calculation Algorithm
The percentile calculation uses numpy's percentile function to compute quartiles and quintiles from comparable case outcomes:

```mermaid
flowchart TD
Start([Comparable Cases]) --> Extract["Extract Outcome Amounts"]
Extract --> Validate{"Any Cases?"}
Validate --> |No| DefaultRanges["Default Ranges"]
Validate --> |Yes| CalcPercentiles["Calculate 25th, 50th, 75th, 95th Percentiles"]
CalcPercentiles --> MedicalAdjust{"Significant Medical Bill Difference?"}
MedicalAdjust --> |Yes| ApplyAdjustment["Apply Proportional Adjustment<br/>50% Weight"]
MedicalAdjust --> |No| SkipAdjustment["Skip Adjustment"]
ApplyAdjustment --> Confidence["Assign Confidence Level"]
SkipAdjustment --> Confidence
DefaultRanges --> Confidence
Confidence --> Response([Percentile Ranges])
```

**Diagram sources**
- [estimator.py:148-210](file://app/services/estimator.py#L148-L210)

#### Multiplier Fallback System
For limited-data scenarios (<15 cases), the engine applies industry-standard multipliers based on medical bill severity:

| Severity Level | Medical Bill Threshold | Multipliers |
|---------------|----------------------|-------------|
| Low | < $5,000 | Min: 1.5x, Typical: 2.0x, High: 3.0x |
| Medium | $5,000-$25,000 | Min: 2.0x, Typical: 3.5x, High: 5.0x |
| High | > $25,000 | Min: 3.0x, Typical: 5.0x, High: 8.0x |

#### Medical Bill Adjustment Mechanism
The system adjusts settlement ranges when current medical bills differ significantly from comparable cases:
- Ratio threshold: < 0.5 or > 2.0 indicates significant difference
- Partial adjustment applied (50% weight) to reduce impact bias

**Section sources**
- [estimator.py:148-210](file://app/services/estimator.py#L148-L210)
- [estimator.py:212-262](file://app/services/estimator.py#L212-L262)
- [estimator.py:179-193](file://app/services/estimator.py#L179-L193)

### Representative Case Selection Algorithm
The engine selects diverse, representative comparable cases for reporting:

```mermaid
flowchart TD
Start([Comparable Cases]) --> Sort["Sort by Outcome Range Ascending<br/>and Recency Descending"]
Sort --> Distribute{"Cases > Limit?"}
Distribute --> |No| SelectAll["Select All Cases"]
Distribute --> |Yes| EvenSpread["Select Evenly Distributed Cases<br/>Step = Length/Limit"]
EvenSpread --> Anonymize["Anonymize Case Data"]
SelectAll --> Anonymize
Anonymize --> Response([Representative Cases])
```

**Diagram sources**
- [estimator.py:291-343](file://app/services/estimator.py#L291-L343)

#### Jurisdiction Matching Criteria
The similarity engine implements hierarchical jurisdiction matching:
- Exact county match: 20 points
- Same state, different county: 12 points
- Neighboring state: 6 points
- Different region: 0 points

**Section sources**
- [estimator.py:291-343](file://app/services/estimator.py#L291-L343)
- [similarity_engine.py:294-313](file://app/services/similarity_engine.py#L294-L313)

### Confidence Scoring Implementation
The SettlementCalculator implements a weighted scoring system:

```mermaid
flowchart TD
Start([Comparable Results]) --> SampleSize["Score Sample Size<br/>0-40"]
Start --> Jurisdiction["Score Jurisdiction<br/>0-30"]
Start --> Similarity["Score Average Similarity<br/>0-30"]
SampleSize --> Total["Sum = 40 + 30 + 30 = 100"]
Jurisdiction --> Total
Similarity --> Total
Total --> Clamp["Clamp to 0-100"]
Clamp --> Label["Convert to Label<br/>High/Moderate/Low/Very Low"]
Label --> Response([Confidence Factors])
```

**Diagram sources**
- [settlement_calculator.py:117-191](file://app/services/settlement_calculator.py#L117-L191)

**Section sources**
- [settlement_calculator.py:117-191](file://app/services/settlement_calculator.py#L117-L191)

### Reporting and Compliance Features
The engine generates comprehensive reports with blockchain verification:

```mermaid
sequenceDiagram
participant Client as "Client"
participant Reports as "Reports Endpoint"
participant PDF as "PDF Generator"
participant Validator as "DataValidator"
participant Anonymizer as "AnonymizationValidator"
participant Storage as "Storage Service"
Client->>Reports : POST /api/v1/reports/generate
Reports->>Validator : Validate request
Validator-->>Reports : Validation result
Reports->>Anonymizer : Anonymize data
Anonymizer-->>Reports : Anonymized data
Reports->>PDF : Generate PDF report
PDF->>Storage : Store report
Storage-->>PDF : Storage confirmation
PDF-->>Reports : PDF bytes
Reports-->>Client : ReportResponse with blockchain hash
```

**Diagram sources**
- [reports.py:23-188](file://app/api/v1/endpoints/reports.py#L23-L188)
- [pdf_generator.py:41-86](file://app/services/reports/pdf_generator.py#L41-L86)

**Section sources**
- [reports.py:23-188](file://app/api/v1/endpoints/reports.py#L23-L188)
- [pdf_generator.py:41-86](file://app/services/reports/pdf_generator.py#L41-L86)

## Dependency Analysis
The Settlement Intelligence Engine exhibits clean dependency relationships with minimal coupling:

```mermaid
graph TB
subgraph "Core Dependencies"
PYD[Pydantic Models]
NUMPY[Numpy]
FASTAPI[FastAPI]
WEASY[WeasyPrint]
end
subgraph "Engine Components"
EST[SettlementEstimator]
SC[SettlementCalculator]
SE[SimilarityEngine]
VAL[DataValidator]
ANON[AnonymizationValidator]
PDF[PDFGenerator]
BE[BillingEventService]
end
PYD --> EST
PYD --> SC
PYD --> SE
PYD --> VAL
PYD --> ANON
PYD --> PDF
PYD --> BE
NUMPY --> EST
NUMPY --> SC
FASTAPI --> EST
FASTAPI --> SC
FASTAPI --> SE
FASTAPI --> VAL
FASTAPI --> ANON
FASTAPI --> PDF
FASTAPI --> BE
WEASY --> PDF
```

**Diagram sources**
- [estimator.py:10-22](file://app/services/estimator.py#L10-L22)
- [settlement_calculator.py:8-18](file://app/services/settlement_calculator.py#L8-L18)
- [similarity_engine.py:10-15](file://app/services/similarity_engine.py#L10-L15)
- [pdf_generator.py:32-39](file://app/services/reports/pdf_generator.py#L32-L39)

### Data Model Relationships
The system uses Pydantic models to define request/response schemas and domain entities:

```mermaid
erDiagram
ESTIMATE_REQUEST {
string jurisdiction
string case_type
array injury_category
float medical_bills
float medical_bills
string case_type
array injury_category
array treatment_type
string duration_of_treatment
array imaging_findings
float lost_wages
string policy_limits
string defendant_category
}
ESTIMATE_RESPONSE {
float percentile_25
float median
float percentile_75
float percentile_95
int n_cases
string confidence
array comparable_cases
string range_justification
uuid query_id
datetime queried_at
int response_time_ms
}
COMPARABLE_CASE {
string jurisdiction
string case_type
array injury_category
string primary_diagnosis
float medical_bills
string outcome_range
string outcome_type
datetime contributed_at
}
SETTLE_CONTRIBUTION {
uuid id
string jurisdiction
string case_type
array injury_category
string primary_diagnosis
array treatment_type
string duration_of_treatment
array imaging_findings
float medical_bills
float lost_wages
string policy_limits
string defendant_category
string outcome_type
string outcome_amount_range
datetime contributed_at
string blockchain_hash
bool consent_confirmed
uuid contributor_api_key_id
bool founding_member
datetime created_at
datetime updated_at
string status
string rejection_reason
bool is_outlier
float confidence_score
}
ESTIMATE_REQUEST ||--o{ COMPARABLE_CASE : "generates"
ESTIMATE_REQUEST ||--|| ESTIMATE_RESPONSE : "produces"
SETTLE_CONTRIBUTION ||--o{ COMPARABLE_CASE : "contains"
```

**Diagram sources**
- [case_bank.py:69-139](file://app/models/case_bank.py#L69-L139)
- [case_bank.py:15-63](file://app/models/case_bank.py#L15-L63)

**Section sources**
- [case_bank.py:69-139](file://app/models/case_bank.py#L69-L139)
- [case_bank.py:15-63](file://app/models/case_bank.py#L15-L63)

## Performance Considerations
The Settlement Intelligence Engine is optimized for low-latency responses:

### Response Time Targets
- Query endpoint: <1 second (p95)
- Report generation: <2 seconds (p95)
- PDF generation: Mock fallback available when WeasyPrint unavailable

### Scalability Patterns
- Database query expansion: progressive expansion from county → state → regional → national
- Similarity scoring: capped at 200 comparable cases per query
- Confidence scoring: O(n) complexity for sample size evaluation
- Memory usage: bounded by case collection limits

### Database Integration
The estimator currently uses mock data but includes database connectivity hooks for production deployment. The query endpoint demonstrates proper database connection patterns and error handling.

## Troubleshooting Guide

### Common Issues and Resolutions
1. **Insufficient Comparable Cases**
   - Symptom: Multiplier fallback activation
   - Resolution: Expand jurisdiction scope or increase data contribution

2. **Similarity Score Too Low**
   - Symptom: No comparable cases found
   - Resolution: Adjust injury categories or expand case type filters

3. **Validation Errors**
   - Symptom: Request rejected with validation errors
   - Resolution: Check jurisdiction format, required fields, and value ranges

4. **Report Generation Failures**
   - Symptom: PDF generation errors
   - Resolution: Install WeasyPrint dependency or use JSON format

### Error Handling Patterns
The system implements comprehensive error handling:
- HTTP 400 for validation failures
- HTTP 500 for internal server errors
- Detailed error messages with stack traces in debug mode
- Graceful degradation for missing dependencies

**Section sources**
- [query.py:100-107](file://app/api/v1/endpoints/query.py#L100-L107)
- [reports.py:190-197](file://app/api/v1/endpoints/reports.py#L190-L197)
- [pdf_generator.py:83-85](file://app/services/reports/pdf_generator.py#L83-L85)

## Conclusion
The Settlement Intelligence Engine provides a robust, compliant solution for percentile-based settlement range estimation. Its dual-methodology approach ensures reliable estimates across varying data availability scenarios, while comprehensive validation and anonymization maintain legal and ethical standards. The modular architecture supports easy integration, scalability, and future enhancements.

Key strengths include:
- Deterministic algorithms with transparent scoring
- Comprehensive compliance with legal and privacy requirements
- Flexible reporting with blockchain verification
- Scalable architecture supporting growth

## Appendices

### API Reference Summary
- **POST /api/v1/query/estimate**: Settlement range estimation with percentile calculation
- **POST /api/v1/reports/generate**: Report generation with blockchain verification
- **GET /api/v1/query/health**: Health check endpoint
- **GET /api/v1/reports/health**: Reports service health check

### Configuration Options
- Minimum sample size: 15 cases for percentile calculation
- Confidence thresholds: High (≥30), Medium (15-29), Low (<15)
- Similarity threshold: ≥60 for comparable case inclusion
- Maximum comparable cases: 200 per query

### Integration Guidelines
- Authentication: API Key or JWT tokens supported
- Rate limiting: Implemented at gateway level
- Monitoring: Built-in event emission for behavioral analytics
- Compliance: Zero PHI/PII data handling with blockchain verification