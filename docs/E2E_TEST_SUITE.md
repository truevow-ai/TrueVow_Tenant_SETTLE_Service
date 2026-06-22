# E2E Integration Testing Suite

## Overview

End-to-end tests verifying the full integration between SETTLE backend and customer portal.

## Test Scenarios Covered

| # | Scenario | Backend Feature | Frontend Feature |
|---|---|---|---|
| 1 | Full settlement analysis flow | Estimate API | Analysis page display |
| 2 | Confidence score display | Confidence Score service | Analysis + Query pages |
| 3 | Multiplier method display | Multiplier Model Layer | Analysis page comparison |
| 4 | Overdemand cliff warning | Overdemand Cliff Detection | Amber warning banner |
| 5 | Outcome distribution display | Outcome Distribution service | Historical outcome table |
| 6 | Advanced filters | Advanced filter fields | Query page filter controls |
| 7 | Carrier patterns page | Carrier Patterns API | Carrier patterns page |
| 8 | API proxy routing | All SETTLE endpoints | Next.js API routes |

## Setup

### 1. Start SETTLE Backend

```bash
cd TrueVow_Tenant_SETTLE-Service
uvicorn app.main:app --reload --port 8002
```

### 2. Start Customer Portal

```bash
cd Truevow_Tenant_Customer_Portal_Service
npm run dev
```

### 3. Run E2E Tests

```bash
cd Truevow_Tenant_Customer_Portal_Service
npx playwright test e2e/settle-integration.spec.ts
```

## Test Results

| Test | Status | Notes |
|---|---|---|
| Full settlement analysis | ⏳ Pending | Requires live services |
| Confidence score display | ⏳ Pending | Requires live services |
| Multiplier method display | ⏳ Pending | Requires live services |
| Overdemand cliff warning | ⏳ Pending | Requires live services |
| Outcome distribution display | ⏳ Pending | Requires live services |
| Advanced filters | ⏳ Pending | Requires live services |
| Carrier patterns page | ⏳ Pending | Requires live services |
| API proxy routing | ⏳ Pending | Requires live services |

## Notes

- Tests require both SETTLE backend and customer portal to be running
- Use mock API keys for testing
- Supabase must have seed data for meaningful results
- Tests are designed to run against local development environment
