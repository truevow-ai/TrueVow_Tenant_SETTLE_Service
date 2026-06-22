# E2E Integration Testing Guide

## Overview

This guide covers end-to-end integration testing between the SETTLE backend and customer portal.

## Prerequisites

- Docker Desktop installed
- Python 3.13+ installed
- Node.js 18+ installed
- Supabase project (local or cloud)

## Local Deployment

### 1. Start Supabase (local)

```bash
# Using Supabase CLI
supabase start
# Or use the cloud Supabase project URL/key
```

### 2. Configure Environment Variables

**SETTLE-Service** (`.env`):
```
SETTLE_SUPABASE_URL=http://localhost:54321
SETTLE_SUPABASE_KEY=your-service-role-key
SETTLE_ADMIN_API_KEY=test-admin-key
SETTLE_ALLOWED_ORIGINS=http://localhost:3000
```

**Customer Portal** (`.env.local`):
```
NEXT_PUBLIC_SETTLE_API_URL=http://localhost:8002
SETTLE_API_KEY=test-admin-key
```

### 3. Start SETTLE Backend

```bash
cd TrueVow_Tenant_SETTLE-Service
uvicorn app.main:app --reload --port 8002
```

### 4. Start Customer Portal

```bash
cd Truevow_Tenant_Customer_Portal_Service
npm install
npm run dev
```

### 5. Run E2E Tests

```bash
cd Truevow_Tenant_Customer_Portal_Service
npx playwright install
npx playwright test
```

## Test Scenarios

### Scenario 1: Full Settlement Analysis Flow
1. User navigates to `/dashboard/settle/query`
2. User fills in jurisdiction, case type, injury, medical bills
3. User clicks "Get Estimate"
4. Verify estimate response displays:
   - Percentile ranges (P25, Median, P75, P95)
   - Confidence Score (0-100 with factor breakdown)
   - Multiplier method (if available)
   - Overdemand cliff warning (if applicable)
   - Outcome distribution (if available)

### Scenario 2: Advanced Filters
1. User navigates to `/dashboard/settle/query`
2. User expands "Advanced Filters"
3. User sets outcome type, date range, medical bills range
4. User clicks "Get Estimate"
5. Verify filters are passed to backend

### Scenario 3: Carrier Patterns
1. User navigates to `/dashboard/settle/carrier-patterns`
2. Verify page loads with data table
3. Verify filters work (jurisdiction, case type)
4. Verify total cases count displays

### Scenario 4: Confidence Score Display
1. User views estimate on analysis page
2. Verify confidence score displays with:
   - Overall score + label badge
   - 7 factor breakdown with progress bars
   - Warnings section (if any)

### Scenario 5: API Integration
1. Backend returns estimate with all new fields
2. Portal correctly parses and displays all fields
3. No type errors in browser console

## Docker Compose (Optional)

See `docker-compose.e2e.yml` for full local stack.

```bash
docker-compose -f docker-compose.e2e.yml up -d
```

## Troubleshooting

| Issue | Solution |
|---|---|
| Backend not starting | Check Supabase connection, verify `.env` |
| Portal 500 errors | Check `NEXT_PUBLIC_SETTLE_API_URL` |
| CORS errors | Verify `SETTLE_ALLOWED_ORIGINS` includes portal URL |
| Playwright tests fail | Ensure both services are running on correct ports |
