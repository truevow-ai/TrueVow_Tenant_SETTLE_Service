# TrueVow SETTLE™ Service

**Status:** ✅ Production Ready  
**Version:** 1.0.0  
**Last Updated:** January 3, 2026  
**Architecture:** 5-Service Enterprise Model

---

## 🎯 Overview

SETTLE is the first attorney-owned settlement database — an ethical alternative to insurance industry tools like Colossus. It empowers plaintiff attorneys with real settlement data to negotiate better outcomes for their clients.

**Key Features:**
- ✅ 3-minute case entry form (no PHI, no narratives)
- ✅ Instant settlement range estimates (<1 second)
- ✅ County-specific comparable cases
- ✅ Bar-compliant design (all 50 states)
- ✅ Blockchain verification (OpenTimestamps)
- ✅ Founding Member program (2,100 attorneys, lifetime free access)
- ✅ Professional 4-page PDF reports
- ✅ API-first design for easy integration

---

## 🏗️ Architecture

### Service Position in TrueVow Ecosystem

SETTLE is part of TrueVow's **5-service enterprise architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                  TrueVow Enterprise Platform                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Platform Service (Port 3000)                           │
│     • Tenant Management                                     │
│     • Billing & Subscriptions                              │
│     • Integration Gateway                                   │
│                                                             │
│  2. Internal Ops Service (Port 3001)                       │
│     • Task Management                                       │
│     • Time Tracking                                         │
│     • Team Chat & Notifications                            │
│                                                             │
│  3. Sales Service (Port 3002)                              │
│     • Pipeline Management                                   │
│     • Lead Qualification                                    │
│     • Demo & Trial Management                              │
│                                                             │
│  4. Support Service (Port 3003)                            │
│     • Ticket Management                                     │
│     • Shared Inbox                                          │
│     • Knowledge Base                                        │
│                                                             │
│  5. Tenant Service (Port 8000)                             │
│     • INTAKE (Lead Capture)                                │
│     • DRAFT (Document Generation)                          │
│     • BILLING (Time Tracking & Invoicing)                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│              External Services (Shared)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ★ SETTLE Service (Port 8002) ← YOU ARE HERE              │
│     • Settlement Database                                   │
│     • Range Estimation                                      │
│     • Case Contribution                                     │
│     • Report Generation                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### SETTLE Service Characteristics

**Service Type:** External shared service (centralized, not per-tenant)  
**Database:** `settle_db` (single centralized database for all settlements)  
**Access:** Open to customers AND non-customers (via API keys)  
**Deployment:** Shared container (not per-tenant)  
**Port:** `8002` (development), `8004` (production)

**Key Difference from Other Services:**
- SETTLE is NOT tenant-specific
- Single database shared across all users
- API key-based authentication (not tenant-based)
- Accessible to non-TrueVow customers

### Repository Structure

```
2025-TrueVow-Settle-Service/
├── app/
│   ├── api/v1/
│   │   ├── endpoints/
│   │   │   ├── query.py           # Query settlement ranges
│   │   │   ├── contribute.py      # Submit settlement data
│   │   │   └── reports.py         # Generate reports
│   │   └── router.py
│   ├── services/
│   │   ├── estimator.py           # Settlement range calculation
│   │   ├── anonymizer.py          # Anonymization logic
│   │   ├── validator.py           # Data validation
│   │   └── contributor.py         # Contribution workflow
│   └── models/
│       ├── case_bank.py
│       └── waitlist.py
├── database/
│   ├── schemas/
│   │   └── settle.sql             # Centralized database
│   └── migrations/
├── docs/
└── tests/
```

---

## 📚 Documentation

### Required Reading (Week 16 Testing)

**For All Agents:**
1. **`docs/API_DOCUMENTATION.md`** - Complete API reference (19 endpoints)
2. **`docs/DATABASE_SCHEMA.md`** - Database tables, relationships, indexes
3. **`docs/INTEGRATION_GUIDE.md`** - Service-to-service integration patterns
4. **`docs/TESTING_GUIDE.md`** - Testing procedures and Week 16 plan

### Additional Documentation

**Architecture:**
- `docs/architecture/SETTLE_ADMIN_ARCHITECTURE.md` - Admin interface architecture
- `docs/integration/SAAS_ADMIN_API_CONTRACT.md` - SaaS Admin integration contract

**Security:**
- `docs/security/ENCRYPTION_IMPLEMENTATION.md` - Data encryption details

**Database:**
- `database/schemas/settle_supabase.sql` - Production database schema
- `database/SUPABASE_SETUP_GUIDE.md` - Supabase setup instructions

**Complete System Documentation:**
- See `../2025-TrueVow-Tenant-Application/TrueVow-Complete System-Technical-Documentation.md` - **Part 7: SETTLE MODULE**

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- FastAPI
- Supabase (or PostgreSQL with pgvector)

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Database Setup

```sql
-- Create centralized database
CREATE DATABASE settle_service_db;

-- Run migrations
psql settle_service_db < database/schemas/settle.sql
```

### Run Development Server

```bash
uvicorn app.main:app --reload --port 8002
```

---

## 🔗 Integration with Other Services

### Service-to-Service Communication

SETTLE integrates with other TrueVow services using API key authentication:

```
Platform Service → SETTLE Service
  • Provision API keys for new tenants
  • Track usage and billing
  • Manage access levels

Tenant Service → SETTLE Service
  • Query settlement ranges for cases
  • Submit settlement contributions
  • Generate PDF reports

SETTLE Service → Internal Ops Service
  • Log query activity for time tracking
  • Create tasks for contribution review
  • Send notifications

SETTLE Service → Platform Service
  • Report usage events for billing
  • Sync API key status
```

### Example: Tenant App → SETTLE Service

```python
import httpx

async def get_settlement_estimate(lead_id: str):
    """Get settlement estimate for an Intake lead"""
    
    # Get tenant's SETTLE API key
    settle_api_key = await get_tenant_settle_api_key(tenant_id)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://settle-api.truevow.law/api/v1/query/estimate",
            json={
                "jurisdiction": "Maricopa County, AZ",
                "case_type": "Motor Vehicle Accident",
                "injury_category": ["Spinal Injury"],
                "medical_bills": 85000.00
            },
            headers={
                "Authorization": f"Bearer {settle_api_key}",
                "X-Service-Name": "truevow-tenant-service",
                "X-Request-ID": str(uuid.uuid4()),
                "X-Request-Timestamp": datetime.utcnow().isoformat()
            }
        )
        return response.json()
```

### Authentication

All service-to-service requests require:

```http
Authorization: Bearer settle_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
X-Service-Name: truevow-tenant-service
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-Request-Timestamp: 2026-01-03T14:30:00Z
```

**See:** `docs/INTEGRATION_GUIDE.md` for complete integration documentation

---

## 📊 Database Schema

See `database/schemas/settle.sql` for the complete production-ready schema.

**Key Tables:**
- `settle_contributions` - Settlement data (anonymized)
- `settle_api_keys` - API key management
- `settle_founding_members` - Founding Member tracking

---

## 🛡️ Compliance

**Bar-Compliant Design:**
- ✅ No PHI collection
- ✅ No client identifiers
- ✅ No liability assessment
- ✅ No legal advice
- ✅ Only descriptive statistics

**Verified Compliance:**
- California Formal Op. 2021-206
- New York Ethics Op. 2019-4
- Florida Advisory Op. 21-1
- Texas Ethics Op. 679
- DOJ 2023 Antitrust Guidelines

---

## 📝 License

Proprietary - TrueVow.law

---

## 🔗 Related Repositories

- **Tenant Application:** `../2025-TrueVow-Tenant-Application/`
- **SaaS Admin Platform:** `../2025-TrueVow-SaaS-Admin/` (future)
- **Connect Service:** `../2025-TrueVow-Connect-Service/` (future)

