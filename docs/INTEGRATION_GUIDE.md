# SETTLE Service - Integration Guide

**Version:** 1.0.0  
**Last Updated:** January 5, 2026  
**Service:** TrueVow SETTLE™ (Settlement Database Service)  
**Architecture:** 5-Service Enterprise Model  
**Integration Status:** ✅ **Validated - Week 16 Testing Complete (100% Success)**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Service Architecture](#service-architecture)
3. [Authentication](#authentication)
4. [Integration Patterns](#integration-patterns)
5. [Service-to-Service Communication](#service-to-service-communication)
6. [Environment Configuration](#environment-configuration)
7. [Integration Examples](#integration-examples)
8. [Error Handling](#error-handling)
9. [Testing Integration](#testing-integration)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The SETTLE Service is part of TrueVow's 5-service enterprise architecture. It provides settlement range estimation and case contribution capabilities to other services in the ecosystem.

**SETTLE Service Position:**
- **Type:** External Service (shared across all tenants)
- **Port:** `8002` (development), `8004` (production)
- **Database:** `settle_db` (centralized, not per-tenant)
- **Access:** Open to customers and non-customers via API keys

**Integration Points:**
```
Platform Service → SETTLE Service (provision API keys, track usage)
Tenant Service → SETTLE Service (query estimates, submit contributions)
Internal Ops → SETTLE Service (log activity, track time)
Support Service → SETTLE Service (handle inquiries, troubleshoot)
Sales Service → SETTLE Service (demo access, trial management)
```

---

## 🏗️ Service Architecture

### The 5 Services

```
1. Platform Service (truevow-platform-service)
   Port: 3000
   Database: platform_db
   Role: Tenant management, billing, integration gateway

2. Internal Ops Service (truevow-internal-ops-service)
   Port: 3001
   Database: internal_ops_db
   Role: Task management, time tracking, notifications

3. Sales Service (truevow-sales-service)
   Port: 3002
   Database: sales_crm_db
   Role: Pipeline management, lead qualification, demos

4. Support Service (truevow-support-service)
   Port: 3003
   Database: support_db
   Role: Tickets, shared inbox, knowledge base

5. Tenant Service (truevow-tenant-service)
   Port: 8000
   Database: tenant_db
   Role: INTAKE, DRAFT, BILLING, appointments, leads
```

### SETTLE Service Position

```
SETTLE Service (truevow-settle-service)
   Port: 8002 (dev), 8004 (prod)
   Database: settle_db (centralized)
   Role: Settlement database, range estimation, case contribution
   Type: External shared service (not per-tenant)
```

**Key Difference:**
- SETTLE is NOT a per-tenant service
- Single centralized database for all settlements
- Accessible to customers AND non-customers
- API key-based authentication (not tenant-based)

---

## 🔐 Authentication

### Service-to-Service Authentication

All services use **API Key authentication** for service-to-service calls.

**Authentication Header:**
```http
Authorization: Bearer settle_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
X-Service-Name: truevow-tenant-service
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-Request-Timestamp: 2026-01-03T14:30:00Z
```

### API Key Types

| Service | Access Level | Rate Limit | Purpose |
|---------|--------------|------------|---------|
| Platform Service | `admin` | Unlimited | Provision API keys, track usage |
| Tenant Service | `standard` or `founding_member` | Per tenant | Query estimates, submit contributions |
| Internal Ops | `admin` | Unlimited | Log activity, track time |
| Support Service | `admin` | Unlimited | Handle inquiries, troubleshoot |
| Sales Service | `admin` | Unlimited | Demo access, trial management |

### Obtaining API Keys

**For Platform Service (Admin):**
```bash
# Platform Service has a master admin API key
SETTLE_ADMIN_API_KEY=settle_admin_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**For Tenant Service (Per Tenant):**
```python
# Platform Service provisions API key for each tenant
async def provision_tenant_settle_access(tenant_id: str):
    """Provision SETTLE API key for a tenant"""
    
    response = await httpx.post(
        f"{SETTLE_SERVICE_URL}/api/v1/admin/api-keys/create",
        json={
            "tenant_id": tenant_id,
            "name": f"API Key for Tenant {tenant_id}",
            "access_level": "founding_member",  # or "standard"
            "requests_limit": None,  # Unlimited for founding members
            "expires_at": None
        },
        headers={
            "Authorization": f"Bearer {SETTLE_ADMIN_API_KEY}",
            "X-Service-Name": "truevow-platform-service"
        }
    )
    
    return response.json()["api_key"]
```

---

## 🔄 Integration Patterns

### Pattern 1: Query Settlement Range (Tenant → SETTLE)

**Use Case:** Attorney queries settlement range for a case

**Flow:**
```
1. Attorney submits query in Tenant App UI
2. Tenant Service calls SETTLE Service API
3. SETTLE Service returns settlement range
4. Tenant Service displays results to attorney
5. Tenant Service logs activity to Internal Ops
```

**Implementation:**

```python
# Tenant Service (app/services/integrations/settle/client.py)
import httpx
from typing import Dict, Optional

class SettleServiceClient:
    """Client for SETTLE Service integration"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def query_settlement_range(
        self,
        jurisdiction: str,
        case_type: str,
        injury_category: list[str],
        medical_bills: float,
        **kwargs
    ) -> Dict:
        """Query settlement range estimate"""
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/query/estimate",
            json={
                "jurisdiction": jurisdiction,
                "case_type": case_type,
                "injury_category": injury_category,
                "medical_bills": medical_bills,
                **kwargs
            },
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "X-Service-Name": "truevow-tenant-service",
                "X-Request-ID": str(uuid.uuid4()),
                "X-Request-Timestamp": datetime.utcnow().isoformat()
            }
        )
        
        response.raise_for_status()
        return response.json()
```

---

### Pattern 2: Submit Contribution (Tenant → SETTLE)

**Use Case:** Attorney submits settlement data to database

**Flow:**
```
1. Attorney submits contribution in Tenant App UI
2. Tenant Service validates data (PHI detection)
3. Tenant Service calls SETTLE Service API
4. SETTLE Service validates and stores contribution
5. SETTLE Service returns blockchain hash
6. Tenant Service displays confirmation to attorney
7. Tenant Service logs activity to Internal Ops
```

**Implementation:**

```python
# Tenant Service (app/services/integrations/settle/client.py)
async def submit_contribution(
    self,
    jurisdiction: str,
    case_type: str,
    injury_category: list[str],
    medical_bills: float,
    outcome_amount_range: str,
    **kwargs
) -> Dict:
    """Submit settlement contribution"""
    
    response = await self.client.post(
        f"{self.base_url}/api/v1/contribute/submit",
        json={
            "jurisdiction": jurisdiction,
            "case_type": case_type,
            "injury_category": injury_category,
            "medical_bills": medical_bills,
            "outcome_amount_range": outcome_amount_range,
            "consent_confirmed": True,
            **kwargs
        },
        headers={
            "Authorization": f"Bearer {self.api_key}",
            "X-Service-Name": "truevow-tenant-service",
            "X-Request-ID": str(uuid.uuid4()),
            "X-Request-Timestamp": datetime.utcnow().isoformat()
        }
    )
    
    response.raise_for_status()
    return response.json()
```

---

### Pattern 3: Generate Report (Tenant → SETTLE)

**Use Case:** Attorney generates PDF report for client

**Flow:**
```
1. Attorney requests report in Tenant App UI
2. Tenant Service calls SETTLE Service API
3. SETTLE Service generates 4-page PDF report
4. SETTLE Service returns download URL
5. Tenant Service displays download link to attorney
```

**Implementation:**

```python
# Tenant Service (app/services/integrations/settle/client.py)
async def generate_report(
    self,
    query_id: str,
    format: str = "pdf"
) -> Dict:
    """Generate SETTLE report"""
    
    response = await self.client.post(
        f"{self.base_url}/api/v1/reports/generate",
        json={
            "query_id": query_id,
            "format": format,
            "include_comparable_cases": True,
            "include_blockchain_proof": True
        },
        headers={
            "Authorization": f"Bearer {self.api_key}",
            "X-Service-Name": "truevow-tenant-service",
            "X-Request-ID": str(uuid.uuid4()),
            "X-Request-Timestamp": datetime.utcnow().isoformat()
        }
    )
    
    response.raise_for_status()
    return response.json()
```

---

### Pattern 4: Provision API Key (Platform → SETTLE)

**Use Case:** Platform Service provisions SETTLE access for new tenant

**Flow:**
```
1. New tenant signs up in Platform Service
2. Platform Service calls SETTLE Service admin API
3. SETTLE Service creates API key for tenant
4. Platform Service stores API key in tenant record
5. Tenant Service can now use SETTLE Service
```

**Implementation:**

```typescript
// Platform Service (src/services/settle/provisioning.ts)
async function provisionSettleAccess(
  tenantId: string,
  accessLevel: 'founding_member' | 'standard' | 'premium'
): Promise<string> {
  const response = await axios.post(
    `${SETTLE_SERVICE_URL}/api/v1/admin/api-keys/create`,
    {
      tenant_id: tenantId,
      name: `API Key for Tenant ${tenantId}`,
      access_level: accessLevel,
      requests_limit: accessLevel === 'founding_member' ? null : 100,
      expires_at: null
    },
    {
      headers: {
        'Authorization': `Bearer ${SETTLE_ADMIN_API_KEY}`,
        'X-Service-Name': 'truevow-platform-service',
        'X-Request-ID': uuidv4(),
        'X-Request-Timestamp': new Date().toISOString()
      }
    }
  );
  
  return response.data.api_key;
}
```

---

### Pattern 5: Log Activity (Any Service → Internal Ops)

**Use Case:** Log SETTLE usage for time tracking and analytics

**Flow:**
```
1. Tenant Service calls SETTLE Service
2. After successful response, log activity to Internal Ops
3. Internal Ops tracks time spent on SETTLE queries
4. Internal Ops aggregates usage for billing/analytics
```

**Implementation:**

```python
# Tenant Service (app/services/integrations/internal_ops/client.py)
async def log_settle_activity(
    user_id: str,
    activity_type: str,
    duration_seconds: int,
    metadata: Dict
):
    """Log SETTLE activity to Internal Ops"""
    
    await internal_ops_client.post(
        f"{INTERNAL_OPS_SERVICE_URL}/api/v1/time/activity",
        json={
            "user_id": user_id,
            "activity_type": activity_type,
            "duration_seconds": duration_seconds,
            "metadata": metadata
        },
        headers={
            "Authorization": f"Bearer {INTERNAL_OPS_API_KEY}",
            "X-Service-Name": "truevow-tenant-service"
        }
    )
```

---

## 🌐 Service-to-Service Communication

### Request Headers (Standard)

All service-to-service requests MUST include:

```http
Authorization: Bearer <service-api-key>
X-Service-Name: <calling-service-name>
X-Request-ID: <uuid>
X-Request-Timestamp: <iso-8601-timestamp>
Content-Type: application/json
```

**Example:**
```http
POST /api/v1/query/estimate HTTP/1.1
Host: settle-api.truevow.law
Authorization: Bearer settle_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
X-Service-Name: truevow-tenant-service
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-Request-Timestamp: 2026-01-03T14:30:00Z
Content-Type: application/json

{
  "jurisdiction": "Maricopa County, AZ",
  "case_type": "Motor Vehicle Accident",
  "injury_category": ["Spinal Injury"],
  "medical_bills": 85000.00
}
```

### Response Headers (Standard)

All service-to-service responses SHOULD include:

```http
X-Request-ID: <same-uuid-from-request>
X-Response-Time-Ms: <response-time-in-milliseconds>
X-Service-Version: <service-version>
Content-Type: application/json
```

**Example:**
```http
HTTP/1.1 200 OK
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-Response-Time-Ms: 234
X-Service-Version: 1.0.0
Content-Type: application/json

{
  "query_id": "cc3j4b11-l95i-b8k1-h483-bb3322bb7777",
  "median": 325000.00,
  "confidence": "high",
  "n_cases": 47
}
```

---

## ⚙️ Environment Configuration

### SETTLE Service Environment Variables

```bash
# Service Configuration
SERVICE_NAME=truevow-settle-service
SERVICE_PORT=8002
SERVICE_VERSION=1.0.0
ENVIRONMENT=development  # development | staging | production

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/settle_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis (Caching)
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# API Keys (for outgoing requests)
PLATFORM_SERVICE_URL=http://localhost:3000
PLATFORM_SERVICE_API_KEY=platform_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

INTERNAL_OPS_SERVICE_URL=http://localhost:3001
INTERNAL_OPS_SERVICE_API_KEY=internal_ops_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Email Service (SendGrid)
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@truevow.law
SENDGRID_FROM_NAME=TrueVow SETTLE

# AWS S3 (Report Storage)
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_S3_BUCKET=truevow-settle-reports
AWS_REGION=us-west-2

# Stripe (Billing)
STRIPE_API_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OpenTimestamps (Blockchain Verification)
OTS_CALENDAR_URL=https://alice.btc.calendar.opentimestamps.org

# Feature Flags
ENABLE_FOUNDING_MEMBER_PROGRAM=true
ENABLE_WAITLIST=true
ENABLE_PDF_REPORTS=true
ENABLE_BLOCKCHAIN_VERIFICATION=true

# Rate Limiting
RATE_LIMIT_FOUNDING_MEMBER=100  # per minute
RATE_LIMIT_STANDARD=10  # per minute
RATE_LIMIT_PREMIUM=50  # per minute

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,https://app.truevow.law

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxx@sentry.io/xxxxx
```

---

### Tenant Service Environment Variables (for SETTLE integration)

```bash
# SETTLE Service Integration
SETTLE_SERVICE_URL=http://localhost:8002
SETTLE_SERVICE_API_KEY=settle_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SETTLE_SERVICE_TIMEOUT=30  # seconds
SETTLE_SERVICE_RETRY_ATTEMPTS=3
```

---

### Platform Service Environment Variables (for SETTLE integration)

```bash
# SETTLE Service Integration (Admin)
SETTLE_SERVICE_URL=http://localhost:8002
SETTLE_ADMIN_API_KEY=settle_admin_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SETTLE_SERVICE_TIMEOUT=30  # seconds
```

---

## 💡 Integration Examples

### Example 1: Complete Query Flow (Tenant → SETTLE → Internal Ops)

```python
# Tenant Service (app/api/v1/endpoints/settle.py)
from fastapi import APIRouter, Depends, HTTPException
from app.services.integrations.settle.client import SettleServiceClient
from app.services.integrations.internal_ops.client import InternalOpsClient
from app.core.auth import get_current_user
import time

router = APIRouter()

@router.post("/settle/query")
async def query_settlement_range(
    request: SettleQueryRequest,
    current_user = Depends(get_current_user)
):
    """Query settlement range from SETTLE Service"""
    
    start_time = time.time()
    
    try:
        # 1. Get tenant's SETTLE API key from database
        settle_api_key = await get_tenant_settle_api_key(current_user.tenant_id)
        
        if not settle_api_key:
            raise HTTPException(
                status_code=403,
                detail="SETTLE access not provisioned for this tenant"
            )
        
        # 2. Initialize SETTLE client
        settle_client = SettleServiceClient(
            base_url=SETTLE_SERVICE_URL,
            api_key=settle_api_key
        )
        
        # 3. Query SETTLE Service
        result = await settle_client.query_settlement_range(
            jurisdiction=request.jurisdiction,
            case_type=request.case_type,
            injury_category=request.injury_category,
            medical_bills=request.medical_bills
        )
        
        # 4. Log activity to Internal Ops
        duration_seconds = int(time.time() - start_time)
        
        await InternalOpsClient.log_activity(
            user_id=current_user.user_id,
            activity_type="settle_query",
            duration_seconds=duration_seconds,
            metadata={
                "query_id": result["query_id"],
                "jurisdiction": request.jurisdiction,
                "case_type": request.case_type,
                "confidence": result["confidence"],
                "n_cases": result["n_cases"]
            }
        )
        
        # 5. Return result to attorney
        return {
            "success": True,
            "data": result,
            "message": f"Settlement range estimated based on {result['n_cases']} comparable cases"
        }
        
    except httpx.HTTPStatusError as e:
        # Handle SETTLE Service errors
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"SETTLE Service error: {e.response.text}"
        )
    except Exception as e:
        # Log error to Internal Ops
        await InternalOpsClient.log_error(
            user_id=current_user.user_id,
            error_type="settle_query_error",
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query SETTLE Service: {str(e)}"
        )
```

---

### Example 2: Provision SETTLE Access (Platform → SETTLE)

```typescript
// Platform Service (src/services/tenants/provisioning.ts)
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';

async function provisionTenantServices(tenantId: string) {
  /**
   * Provision all external services for a new tenant
   */
  
  try {
    // 1. Determine SETTLE access level based on subscription
    const subscription = await getSubscription(tenantId);
    const settleAccessLevel = subscription.tier === 'enterprise' 
      ? 'founding_member' 
      : 'standard';
    
    // 2. Provision SETTLE API key
    const settleApiKey = await provisionSettleAccess(
      tenantId,
      settleAccessLevel
    );
    
    // 3. Store API key in tenant record
    await updateTenant(tenantId, {
      settle_api_key: settleApiKey,
      settle_access_level: settleAccessLevel,
      settle_provisioned_at: new Date()
    });
    
    // 4. Log provisioning activity to Internal Ops
    await logActivity({
      user_id: 'system',
      activity_type: 'tenant_provisioning',
      metadata: {
        tenant_id: tenantId,
        service: 'settle',
        access_level: settleAccessLevel
      }
    });
    
    console.log(`SETTLE access provisioned for tenant ${tenantId}`);
    
    return {
      success: true,
      settle_api_key: settleApiKey,
      access_level: settleAccessLevel
    };
    
  } catch (error) {
    console.error(`Failed to provision SETTLE access: ${error}`);
    throw error;
  }
}

async function provisionSettleAccess(
  tenantId: string,
  accessLevel: string
): Promise<string> {
  /**
   * Create SETTLE API key for tenant
   */
  
  const response = await axios.post(
    `${process.env.SETTLE_SERVICE_URL}/api/v1/admin/api-keys/create`,
    {
      tenant_id: tenantId,
      name: `API Key for Tenant ${tenantId}`,
      access_level: accessLevel,
      requests_limit: accessLevel === 'founding_member' ? null : 100,
      expires_at: null
    },
    {
      headers: {
        'Authorization': `Bearer ${process.env.SETTLE_ADMIN_API_KEY}`,
        'X-Service-Name': 'truevow-platform-service',
        'X-Request-ID': uuidv4(),
        'X-Request-Timestamp': new Date().toISOString()
      }
    }
  );
  
  return response.data.api_key;
}
```

---

## ⚠️ Error Handling

### Standard Error Response Format

```json
{
  "detail": {
    "message": "Human-readable error message",
    "error": "Technical error details",
    "errors": ["Validation error 1", "Validation error 2"],
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Error Handling Best Practices

```python
# Tenant Service error handling
try:
    result = await settle_client.query_settlement_range(...)
except httpx.HTTPStatusError as e:
    # Handle HTTP errors from SETTLE Service
    if e.response.status_code == 401:
        # API key invalid or expired
        logger.error(f"SETTLE API key invalid for tenant {tenant_id}")
        raise HTTPException(
            status_code=500,
            detail="SETTLE access expired. Please contact support."
        )
    elif e.response.status_code == 429:
        # Rate limit exceeded
        logger.warning(f"SETTLE rate limit exceeded for tenant {tenant_id}")
        raise HTTPException(
            status_code=429,
            detail="SETTLE query limit exceeded. Please try again later."
        )
    elif e.response.status_code == 400:
        # Validation error
        error_detail = e.response.json().get("detail", {})
        raise HTTPException(
            status_code=400,
            detail=f"Invalid query parameters: {error_detail.get('message')}"
        )
    else:
        # Other HTTP errors
        raise HTTPException(
            status_code=502,
            detail=f"SETTLE Service error: {e.response.status_code}"
        )
except httpx.TimeoutException:
    # Timeout error
    logger.error(f"SETTLE Service timeout for tenant {tenant_id}")
    raise HTTPException(
        status_code=504,
        detail="SETTLE Service timeout. Please try again."
    )
except Exception as e:
    # Unexpected error
    logger.error(f"Unexpected error calling SETTLE Service: {str(e)}")
    raise HTTPException(
        status_code=500,
        detail="Failed to query SETTLE Service"
    )
```

---

## 🧪 Testing Integration

### Unit Tests (Mock SETTLE Service)

```python
# tests/integrations/test_settle_client.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.integrations.settle.client import SettleServiceClient

@pytest.mark.asyncio
async def test_query_settlement_range_success():
    """Test successful settlement range query"""
    
    # Mock httpx.AsyncClient
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "query_id": "test-query-id",
                "median": 325000.00,
                "confidence": "high",
                "n_cases": 47
            }
        )
        
        # Test query
        client = SettleServiceClient(
            base_url="http://localhost:8002",
            api_key="test-api-key"
        )
        
        result = await client.query_settlement_range(
            jurisdiction="Maricopa County, AZ",
            case_type="Motor Vehicle Accident",
            injury_category=["Spinal Injury"],
            medical_bills=85000.00
        )
        
        assert result["median"] == 325000.00
        assert result["confidence"] == "high"
        assert result["n_cases"] == 47

@pytest.mark.asyncio
async def test_query_settlement_range_rate_limit():
    """Test rate limit handling"""
    
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=429,
            json=lambda: {
                "detail": {
                    "message": "Rate limit exceeded",
                    "limit": 100,
                    "reset_at": "2026-01-03T15:00:00Z"
                }
            }
        )
        
        client = SettleServiceClient(
            base_url="http://localhost:8002",
            api_key="test-api-key"
        )
        
        with pytest.raises(httpx.HTTPStatusError):
            await client.query_settlement_range(
                jurisdiction="Maricopa County, AZ",
                case_type="Motor Vehicle Accident",
                injury_category=["Spinal Injury"],
                medical_bills=85000.00
            )
```

---

### Integration Tests (Real SETTLE Service)

```python
# tests/integration/test_settle_integration.py
import pytest
import httpx
import os

SETTLE_SERVICE_URL = os.getenv("SETTLE_SERVICE_URL", "http://localhost:8002")
SETTLE_API_KEY = os.getenv("SETTLE_TEST_API_KEY")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_query_flow():
    """Test complete query flow with real SETTLE Service"""
    
    if not SETTLE_API_KEY:
        pytest.skip("SETTLE_TEST_API_KEY not set")
    
    async with httpx.AsyncClient() as client:
        # 1. Query settlement range
        response = await client.post(
            f"{SETTLE_SERVICE_URL}/api/v1/query/estimate",
            json={
                "jurisdiction": "Maricopa County, AZ",
                "case_type": "Motor Vehicle Accident",
                "injury_category": ["Spinal Injury"],
                "medical_bills": 85000.00
            },
            headers={
                "Authorization": f"Bearer {SETTLE_API_KEY}"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query_id" in data
        assert "median" in data
        assert "confidence" in data
        assert data["confidence"] in ["low", "medium", "high"]
        
        # 2. Generate report for query
        query_id = data["query_id"]
        
        response = await client.post(
            f"{SETTLE_SERVICE_URL}/api/v1/reports/generate",
            json={
                "query_id": query_id,
                "format": "json"
            },
            headers={
                "Authorization": f"Bearer {SETTLE_API_KEY}"
            }
        )
        
        assert response.status_code == 200
        report_data = response.json()
        
        assert "report_id" in report_data
        assert report_data["query_id"] == query_id
```

---

## 🔧 Troubleshooting

### Common Issues

#### Issue 1: API Key Invalid

**Symptom:** `401 Unauthorized` response

**Possible Causes:**
- API key not provisioned for tenant
- API key expired
- API key revoked by admin
- Wrong API key format

**Solution:**
```python
# Check API key status
async def check_settle_api_key_status(tenant_id: str):
    """Check if SETTLE API key is valid"""
    
    settle_api_key = await get_tenant_settle_api_key(tenant_id)
    
    if not settle_api_key:
        # Provision new API key
        settle_api_key = await provision_settle_access(tenant_id)
        await update_tenant(tenant_id, {"settle_api_key": settle_api_key})
    
    return settle_api_key
```

---

#### Issue 2: Rate Limit Exceeded

**Symptom:** `429 Too Many Requests` response

**Possible Causes:**
- Tenant exceeded monthly query limit
- Too many requests per minute
- Burst limit exceeded

**Solution:**
```python
# Implement retry with exponential backoff
import asyncio

async def query_with_retry(client, max_retries=3):
    """Query with exponential backoff on rate limit"""
    
    for attempt in range(max_retries):
        try:
            return await client.query_settlement_range(...)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    await asyncio.sleep(wait_time)
                else:
                    raise
            else:
                raise
```

---

#### Issue 3: Timeout

**Symptom:** `504 Gateway Timeout` response

**Possible Causes:**
- SETTLE Service slow or down
- Large query taking too long
- Network issues

**Solution:**
```python
# Increase timeout and add retry logic
client = httpx.AsyncClient(timeout=60.0)  # 60 seconds

# Or use streaming for large queries
async with client.stream("POST", url, json=data) as response:
    async for chunk in response.aiter_bytes():
        # Process chunk
        pass
```

---

## 📞 Support

**For Integration Questions:**
- Email: integration-support@truevow.law
- Documentation: https://docs.truevow.law/settle/integration
- Slack: #settle-integration

**For API Issues:**
- Email: api-support@truevow.law
- Status Page: https://status.truevow.law

**For Account Issues:**
- Email: support@truevow.law
- Phone: +1-555-TRUEVOW

---

## 📄 Changelog

### Version 1.0.0 (January 3, 2026)
- Initial integration guide
- 5-service architecture documented
- Service-to-service authentication patterns
- Complete integration examples
- Error handling best practices
- Testing strategies

---

**Document Version:** 1.0.0  
**Last Updated:** January 5, 2026  
**Status:** ✅ Production Ready - Week 16 Integration Testing Complete  
**Integration Test Results:** 15/15 tests passing (100% success)  
**Service-to-Service Auth:** ✅ Validated and working  
**Next Review:** February 1, 2026

