# TrueVow Settle™ Service

**Status:** 🚧 In Development  
**Version:** 1.0.0  
**Last Updated:** December 5, 2025

---

## 🎯 Overview

SETTLE is the first attorney-owned settlement database — an ethical alternative to insurance industry tools like Colossus. It empowers plaintiff attorneys with real settlement data to negotiate better outcomes for their clients.

**Key Features:**
- ✅ 3-minute case entry form (no PHI, no narratives)
- ✅ Instant settlement range estimates (<1 second)
- ✅ County-specific comparable cases
- ✅ Bar-compliant design (all 50 states)
- ✅ Blockchain verification (OpenTimestamps)
- ✅ Founding Member program (2,100 attorneys)

---

## 🏗️ Architecture

**Service Type:** Centralized shared service (not per-tenant)  
**Database:** Single centralized database for all settlements  
**Access:** Open to customers and non-customers (via API keys)  
**Deployment:** Shared container (not per-tenant)

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

**Complete System Documentation:**
- See `../2025-TrueVow-Tenant-Application/TrueVow-Complete System-Technical-Documentation.md` - **Part 7: SETTLE MODULE**

**Architecture Documentation:**
- See `../2025-TrueVow-Tenant-Application/docs/architecture/SETTLE_CONNECT_ARCHITECTURE_REVISED.md`

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

## 🔗 Integration

### Tenant App → Settle Service

```python
import httpx

async def get_settlement_estimate(lead_id: str):
    """Get settlement estimate for an Intake lead"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://settle.truevow.law/api/v1/query/estimate",
            json={
                "injury_type": "spinal_injury",
                "state": "AZ",
                "county": "Maricopa",
                "medical_bills": 68420
            },
            headers={"Authorization": f"Bearer {settle_api_key}"}
        )
        return response.json()
```

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

