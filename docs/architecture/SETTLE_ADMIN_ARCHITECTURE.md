# 🏗️ SETTLE Service - Administrative Architecture

**Last Updated:** December 7, 2025  
**Status:** Architecture Decision Document  
**Version:** 1.0

---

## 🎯 **YOUR QUESTIONS ANSWERED**

### **Q1: Where is the central `users` table?**

**Answer:** The `users` table is in the **SaaS Admin Platform** database.

**Location:**
```
Repository: 2025-TrueVow-Tenant-Application
File: operations/database/saas_admin_schema_FINAL.sql
Table: users (lines 154-208)
Database: saas_admin_db (shared across all tenants)
```

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(100) REFERENCES tenants(tenant_id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    role VARCHAR(50) NOT NULL,  -- 'super_admin', 'admin', 'attorney', etc.
    permissions JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(50) DEFAULT 'active',
    -- ... more fields
);
```

---

### **Q2: How does SETTLE get managed administratively?**

**Answer:** SETTLE is managed through the **SaaS Admin Platform** (System 2).

---

## 🏛️ **TRUEVOW SYSTEM ARCHITECTURE**

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRUEVOW PLATFORM ARCHITECTURE                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐
│  SYSTEM 1               │  │  SYSTEM 2               │  │  SYSTEM 3               │
│  Tenant Application     │  │  SaaS Admin Platform    │  │  SETTLE Service         │
│  (Per-Firm Containers)  │  │  (Shared Control Plane) │  │  (Shared Service)       │
│                         │  │                         │  │                         │
│  Database:              │  │  Database:              │  │  Database:              │
│  - intake_firm1         │  │  - saas_admin_db ⭐     │  │  - settle_db ⭐         │
│  - intake_firm2         │  │    ├── tenants          │  │    ├── settle_contributions │
│  - intake_firm3         │  │    ├── users ⭐         │  │    ├── settle_api_keys │
│  (Isolated per firm)    │  │    ├── pricing_tiers    │  │    ├── settle_founding_members │
│                         │  │    ├── subscriptions    │  │    └── settle_queries   │
│  Features:              │  │    └── billing          │  │                         │
│  - Intake calls         │  │                         │  │  Features:              │
│  - FSM workflow         │  │  Features:              │  │  - Settlement ranges    │
│  - Lead scoring         │  │  - Tenant management    │  │  - Contribution tracking│
│  - CRM sync             │  │  - User management ⭐   │  │  - Report generation    │
│                         │  │  - Billing & payments   │  │  - Founding Members     │
│                         │  │  - Analytics            │  │                         │
│                         │  │  - SETTLE admin ⭐      │  │  Managed By:            │
│                         │  │                         │  │  → SaaS Admin ⭐        │
└─────────┬───────────────┘  └──────────┬──────────────┘  └───────────┬─────────────┘
          │                             │                              │
          │                             │                              │
          └─────────────────────────────┴──────────────────────────────┘
                                        │
                              HTTP API Calls
```

**Key Insight:**
- **System 2 (SaaS Admin)** manages **System 3 (SETTLE)**
- The `users` table lives in **System 2 (SaaS Admin)**
- SETTLE references this `users` table for authentication/tracking

---

## 📊 **DATABASE ARCHITECTURE**

### **Three Separate Databases:**

```
┌────────────────────────────────────────────────────────────┐
│  DATABASE 1: Tenant Databases (Per-Firm Isolation)        │
├────────────────────────────────────────────────────────────┤
│  intake_oakwood_law                                        │
│    ├── leads                                               │
│    ├── contacts  ← Firm-specific contacts                  │
│    ├── intake_sessions                                     │
│    └── appointments                                        │
│                                                            │
│  intake_smith_firm                                         │
│    ├── leads                                               │
│    ├── contacts                                            │
│    └── ...                                                 │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  DATABASE 2: SaaS Admin (Shared Control Plane) ⭐         │
├────────────────────────────────────────────────────────────┤
│  saas_admin_db                                             │
│    ├── tenants          ← All law firms                    │
│    ├── users ⭐          ← ALL users (attorneys, staff)    │
│    ├── pricing_tiers    ← Subscription plans               │
│    ├── subscriptions    ← Active subscriptions             │
│    ├── billing          ← Invoices, payments               │
│    └── analytics        ← Cross-tenant metrics             │
│                                                            │
│  Location: operations/database/saas_admin_schema_FINAL.sql │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  DATABASE 3: SETTLE Service (Shared Settlement DB) ⭐      │
├────────────────────────────────────────────────────────────┤
│  settle_db                                                 │
│    ├── settle_contributions      ← Settlement data         │
│    ├── settle_api_keys           ← API access              │
│    ├── settle_founding_members   ← 2,100 members           │
│    ├── settle_queries            ← Query tracking          │
│    ├── settle_reports            ← Generated reports       │
│    └── settle_waitlist           ← Pre-launch waitlist     │
│                                                            │
│  References users.user_id from Database 2 ⭐              │
│  Location: database/schemas/settle_supabase.sql            │
└────────────────────────────────────────────────────────────┘
```

---

## 🔑 **HOW `users` TABLE CONNECTS TO SETTLE**

### **The Relationship:**

```sql
-- In Database 2 (SaaS Admin):
CREATE TABLE users (
    user_id UUID PRIMARY KEY,      ← SETTLE references this
    tenant_id VARCHAR(100),
    email VARCHAR(255),
    role VARCHAR(50),
    -- ... attorney/admin user info
);

-- In Database 3 (SETTLE):
CREATE TABLE settle_contributions (
    id UUID PRIMARY KEY,
    contributor_user_id UUID,      ← References users.user_id
    -- ... settlement data
);

CREATE TABLE settle_api_keys (
    id UUID PRIMARY KEY,
    user_id UUID,                  ← References users.user_id
    user_email TEXT,
    -- ... API key info
);

CREATE TABLE settle_founding_members (
    id UUID PRIMARY KEY,
    user_id UUID,                  ← References users.user_id
    email TEXT,
    -- ... member info
);
```

**Connection Flow:**
```
1. Attorney signs up → Record created in users table (Database 2)
2. Attorney becomes Founding Member → Record created in settle_founding_members (Database 3)
   - settle_founding_members.user_id = users.user_id (links the records)
3. Attorney contributes settlement → settle_contributions.contributor_user_id = users.user_id
```

---

## 🛠️ **HOW SETTLE GETS MANAGED ADMINISTRATIVELY**

### **Management Through SaaS Admin Platform**

SETTLE is managed by **TrueVow staff** through the **SaaS Admin Platform** (System 2).

---

## 🎛️ **SAAS ADMIN PLATFORM - SETTLE MANAGEMENT**

### **Admin Console Sections (Future)**

```
┌─────────────────────────────────────────────────────────┐
│  TrueVow SaaS Admin Platform                            │
│  URL: admin.truevow.law                                 │
└─────────────────────────────────────────────────────────┘

Navigation:
├── Dashboard
├── Tenants (Law Firms)
├── Users & Accounts
├── Billing & Subscriptions
├── Analytics
└── SETTLE Module ⭐ NEW
    ├── Contributions
    │   ├── Pending Review (358 items)
    │   ├── Approved (9,876 items)
    │   ├── Rejected (0 items)
    │   └── Flagged for Review (0 items)
    │
    ├── Founding Members
    │   ├── All Members (1,234 / 2,100)
    │   ├── Enrollment Requests (45 pending)
    │   ├── Member Stats (contributions, queries)
    │   └── Manage API Keys
    │
    ├── API Keys
    │   ├── All API Keys (1,567 total)
    │   ├── By Access Level
    │   │   ├── Founding Members (1,234)
    │   │   ├── Standard Users (300)
    │   │   ├── Premium Users (30)
    │   │   └── Admins (3)
    │   ├── Generate New Key
    │   └── Revoke Key
    │
    ├── Analytics & Reports
    │   ├── Database Growth (10,234 contributions)
    │   ├── Jurisdiction Coverage (342 counties)
    │   ├── Query Volume (1,234/day)
    │   ├── Report Generation (345/day)
    │   └── Revenue Tracking
    │
    └── Settings
        ├── Pricing Configuration
        ├── Compliance Settings
        └── Feature Flags
```

---

## 📋 **ADMINISTRATIVE WORKFLOWS**

### **1. Approve/Reject Contributions**

**UI Flow (SaaS Admin):**
```
1. Admin logs into admin.truevow.law
2. Navigates to SETTLE → Contributions → Pending Review
3. Sees list of pending contributions:
   
   ┌────────────────────────────────────────────────────────┐
   │  Contribution #12345                                   │
   │  Jurisdiction: Maricopa County, AZ                     │
   │  Case Type: Motor Vehicle Accident                     │
   │  Medical Bills: $52,000                                │
   │  Outcome: $300k-$600k                                  │
   │  Submitted: 2025-12-06 14:23                          │
   │                                                        │
   │  [ View Details ]  [ ✅ Approve ]  [ ❌ Reject ]       │
   └────────────────────────────────────────────────────────┘

4. Admin clicks "Approve"
5. System calls: POST /api/v1/admin/approve-contribution
6. Backend updates: settle_contributions.status = 'approved'
7. Contribution now appears in settlement range queries
```

**API Endpoint (to be built):**
```python
# app/api/v1/endpoints/admin.py

@router.post("/admin/approve-contribution")
async def approve_contribution(
    contribution_id: UUID,
    admin_user_id: UUID = Depends(get_admin_user)
):
    """
    Approve a pending contribution (admin only).
    
    Requires: admin or super_admin role from users table
    """
    # Update status
    await db.execute(
        "UPDATE settle_contributions SET status = 'approved' WHERE id = $1",
        contribution_id
    )
    
    return {"message": "Contribution approved", "contribution_id": contribution_id}
```

---

### **2. Manage Founding Members**

**UI Flow (SaaS Admin):**
```
1. Admin navigates to SETTLE → Founding Members
2. Sees enrollment request:
   
   ┌────────────────────────────────────────────────────────┐
   │  Founding Member Application #456                      │
   │  Name: John Smith                                      │
   │  Email: jsmith@smithlaw.com                           │
   │  Firm: Smith & Associates                              │
   │  Bar #: CA-123456                                      │
   │  State: California                                     │
   │  Applied: 2025-12-06                                  │
   │                                                        │
   │  [ Verify Bar # ]  [ ✅ Approve ]  [ ❌ Reject ]       │
   └────────────────────────────────────────────────────────┘

3. Admin verifies bar number (external lookup)
4. Admin clicks "Approve"
5. System:
   a. Creates user in users table (if not exists)
   b. Creates record in settle_founding_members
   c. Generates API key in settle_api_keys
   d. Emails attorney with API key
```

**API Endpoint:**
```python
@router.post("/admin/approve-founding-member")
async def approve_founding_member(
    application_id: UUID,
    admin_user_id: UUID = Depends(get_admin_user)
):
    """Approve Founding Member application"""
    
    # 1. Get application from settle_waitlist
    app = await get_waitlist_entry(application_id)
    
    # 2. Create user in users table (if not exists)
    user = await create_or_get_user(
        email=app.email,
        first_name=app.first_name,
        role='attorney',
        tenant_id=None  # Founding members not tied to specific tenant
    )
    
    # 3. Generate API key
    api_key, api_key_hash = generate_api_key()
    api_key_record = await create_api_key(
        user_id=user.user_id,
        access_level='founding_member',
        requests_limit=None  # Unlimited
    )
    
    # 4. Create founding member record
    await create_founding_member(
        user_id=user.user_id,
        email=app.email,
        law_firm_name=app.law_firm_name,
        state=app.state,
        api_key_id=api_key_record.id
    )
    
    # 5. Send welcome email with API key
    await send_founding_member_welcome_email(
        email=app.email,
        api_key=api_key
    )
    
    return {"message": "Founding Member approved", "user_id": user.user_id}
```

---

### **3. Monitor Database Growth**

**UI Flow (SaaS Admin):**
```
SETTLE → Analytics Dashboard

┌────────────────────────────────────────────────────────────────┐
│  SETTLE Database Statistics                                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  📊 Total Contributions: 10,234                                │
│      ✅ Approved: 9,876 (96.5%)                                │
│      ⏳ Pending: 358 (3.5%)                                    │
│      🚩 Flagged: 0 (0.0%)                                      │
│                                                                │
│  👥 Founding Members: 1,234 / 2,100 (58.8%)                    │
│      Active: 1,198 (97.1%)                                     │
│      Total Contributions: 5,432                                │
│                                                                │
│  🌍 Jurisdiction Coverage:                                     │
│      States: 38 / 50                                           │
│      Counties: 342                                             │
│                                                                │
│  📈 Daily Activity:                                            │
│      Queries: 1,234/day                                        │
│      Reports: 345/day                                          │
│      New Contributions: 42/day                                 │
│                                                                │
│  💰 Revenue (This Month):                                      │
│      Standard Reports: $16,905 (345 × $49)                     │
│      Premium Subscriptions: $5,970 (30 × $199)                 │
│      Total: $22,875/month                                      │
└────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ **WHERE EACH TABLE LIVES**

### **Database Location Map:**

| Table Name | Database | Managed By | Purpose |
|------------|----------|------------|---------|
| **users** ⭐ | saas_admin_db | SaaS Admin | ALL platform users (attorneys, staff, admins) |
| **tenants** | saas_admin_db | SaaS Admin | All law firms |
| **contacts** | intake_[firm] | Tenant App | Firm-specific leads/clients |
| **settle_contributions** | settle_db | SETTLE Service | Settlement data |
| **settle_api_keys** | settle_db | SaaS Admin | API access control |
| **settle_founding_members** | settle_db | SaaS Admin | Founding Member tracking |

---

## 🔗 **DATA FLOW: Creating a Founding Member**

### **Complete Flow Across Systems:**

```
STEP 1: Attorney Applies (Public Website)
┌────────────────────────────────────────┐
│  Website: settle.truevow.law/apply     │
│  Form: Name, Email, Firm, Bar #        │
│  Submit → API: POST /waitlist/join     │
└───────────────┬────────────────────────┘
                │
                ↓
        [settle_waitlist table]
        settle_db (SETTLE Service)


STEP 2: Admin Reviews Application (SaaS Admin)
┌────────────────────────────────────────┐
│  SaaS Admin: admin.truevow.law         │
│  Navigate: SETTLE → Pending Apps       │
│  Review: Verify bar number             │
│  Action: Click "Approve"               │
└───────────────┬────────────────────────┘
                │
                ↓
        Admin API Call:
        POST /api/v1/admin/approve-founding-member


STEP 3: Create User Record (SaaS Admin DB)
┌────────────────────────────────────────┐
│  Database: saas_admin_db               │
│  Table: users                          │
│  Action: INSERT or UPDATE              │
│  Result: user_id = uuid                │
└───────────────┬────────────────────────┘
                │
                ↓
        user_id: "abc-123-def-456"


STEP 4: Generate API Key (SETTLE DB)
┌────────────────────────────────────────┐
│  Database: settle_db                   │
│  Table: settle_api_keys                │
│  Action: INSERT                        │
│  Fields:                               │
│    - user_id: "abc-123-def-456" ⭐     │
│    - api_key_hash: "sha256..."         │
│    - access_level: "founding_member"   │
│    - requests_limit: NULL (unlimited)  │
└───────────────┬────────────────────────┘
                │
                ↓
        api_key: "settle_1234567890abcdef"


STEP 5: Create Founding Member Record (SETTLE DB)
┌────────────────────────────────────────┐
│  Database: settle_db                   │
│  Table: settle_founding_members        │
│  Action: INSERT                        │
│  Fields:                               │
│    - user_id: "abc-123-def-456" ⭐     │
│    - email: "jsmith@smithlaw.com"      │
│    - api_key_id: [from step 4]         │
│    - status: "active"                  │
└───────────────┬────────────────────────┘
                │
                ↓
        Founding Member Created!


STEP 6: Send Welcome Email
┌────────────────────────────────────────┐
│  Email Service                         │
│  To: jsmith@smithlaw.com               │
│  Subject: "Welcome to SETTLE™"         │
│  Body:                                 │
│    - Congratulations!                  │
│    - Your API Key: settle_123...       │
│    - Documentation link                │
│    - Integration guide                 │
└────────────────────────────────────────┘
```

---

## 👥 **WHO MANAGES WHAT**

### **SaaS Admin Platform Admins (TrueVow Staff)**

**Responsibilities:**
- ✅ Approve/reject settlement contributions
- ✅ Approve/reject Founding Member applications
- ✅ Generate and revoke API keys
- ✅ View analytics across all SETTLE activity
- ✅ Configure pricing ($49/report, etc.)
- ✅ Monitor database quality
- ✅ Flag outliers for review

**Access:**
- Platform: `admin.truevow.law`
- Database: Full access to both `saas_admin_db` and `settle_db`
- Role: `super_admin` or `admin` in users table

---

### **Attorneys (Founding Members & Standard Users)**

**Responsibilities:**
- ✅ Submit settlement contributions
- ✅ Query settlement ranges
- ✅ Generate reports
- ✅ View their own stats

**Access:**
- API: `settle.truevow.law/api/v1/*`
- Authentication: API key (Bearer token)
- Self-service: Can query/contribute but can't approve

---

## 🔐 **ADMINISTRATIVE API ENDPOINTS (To Be Built)**

### **Required for SaaS Admin Integration:**

```python
# app/api/v1/endpoints/admin.py

@router.get("/admin/contributions/pending")
async def get_pending_contributions(
    admin_user: User = Depends(require_admin)
):
    """Get all pending contributions for review"""
    # Query: SELECT * FROM settle_contributions WHERE status = 'pending'

@router.post("/admin/contributions/{id}/approve")
async def approve_contribution(
    id: UUID,
    admin_user: User = Depends(require_admin)
):
    """Approve a contribution"""
    # UPDATE settle_contributions SET status = 'approved' WHERE id = $1

@router.post("/admin/contributions/{id}/reject")
async def reject_contribution(
    id: UUID,
    reason: str,
    admin_user: User = Depends(require_admin)
):
    """Reject a contribution"""
    # UPDATE settle_contributions SET status = 'rejected', rejection_reason = $1

@router.get("/admin/founding-members")
async def get_founding_members(
    admin_user: User = Depends(require_admin)
):
    """Get all Founding Members"""
    # Query: SELECT * FROM settle_founding_members

@router.post("/admin/founding-members/enroll")
async def enroll_founding_member(
    application_id: UUID,
    admin_user: User = Depends(require_admin)
):
    """Enroll a new Founding Member"""
    # 1. Create user in users table (saas_admin_db)
    # 2. Generate API key
    # 3. Create founding member record
    # 4. Send welcome email

@router.get("/admin/analytics/dashboard")
async def get_settle_analytics(
    admin_user: User = Depends(require_admin)
):
    """Get SETTLE analytics dashboard data"""
    # Aggregate stats from all settle_ tables
```

---

## 🔄 **CROSS-DATABASE OPERATIONS**

### **Challenge: Two Separate Databases**

SETTLE Service (settle_db) needs to work with SaaS Admin (saas_admin_db):

**Solution:** HTTP API calls between services

```python
# In SaaS Admin Platform:
# When approving Founding Member, call SETTLE Service API

async def approve_founding_member_application(app_id: UUID):
    # 1. Create user in saas_admin_db.users (local DB)
    user = await create_user_in_saas_admin_db(
        email=app.email,
        role='attorney'
    )
    
    # 2. Call SETTLE Service API to create founding member
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://settle.truevow.law/api/v1/admin/founding-members/create",
            json={
                "user_id": str(user.user_id),
                "email": user.email,
                "law_firm_name": app.law_firm_name,
                "state": app.state
            },
            headers={"Authorization": f"Bearer {SETTLE_ADMIN_API_KEY}"}
        )
    
    return response.json()
```

---

## 📊 **ADMINISTRATIVE DASHBOARD MOCKUP**

### **SETTLE Admin View (Inside SaaS Admin Platform)**

```
┌───────────────────────────────────────────────────────────────┐
│  SETTLE Administration                                         │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  📊 Quick Stats                                               │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐   │
│  │ Total Cases │ Pending     │ Founding    │ Revenue/Mo  │   │
│  │ 10,234      │ 358         │ 1,234/2,100 │ $22,875     │   │
│  └─────────────┴─────────────┴─────────────┴─────────────┘   │
│                                                               │
│  🚨 Requires Attention                                        │
│  • 358 contributions pending review                           │
│  • 45 Founding Member applications waiting                    │
│  • 12 flagged for manual review (outliers)                    │
│                                                               │
│  📋 Recent Activity                                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 14:23  New contribution (Maricopa County, AZ)          │ │
│  │ 14:15  Founding Member approved (jsmith@smithlaw.com)  │ │
│  │ 13:52  Report generated ($49 revenue)                  │ │
│  │ 13:45  Query: Los Angeles, CA - Spinal Injury          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  [View Pending Contributions]  [Manage Founding Members]     │
│  [View Analytics]              [Configure Settings]          │
└───────────────────────────────────────────────────────────────┘
```

---

## 🔑 **AUTHENTICATION & AUTHORIZATION**

### **Who Can Access What:**

| User Type | Access To | Permissions |
|-----------|-----------|-------------|
| **Super Admin** | SaaS Admin + SETTLE | Full access (approve, reject, configure) |
| **Admin** | SaaS Admin + SETTLE | Approve/reject, view analytics |
| **Founding Member** | SETTLE API only | Query, contribute, generate reports (unlimited) |
| **Standard User** | SETTLE API only | Query, contribute, generate reports (paid) |
| **Anonymous** | Public website only | Join waitlist only |

### **Authorization Flow:**

```python
# In SETTLE Service:

def require_admin(api_key: str = Depends(get_api_key)):
    """Require admin access level"""
    
    # 1. Get API key info
    key_info = await get_api_key_info(api_key)
    
    # 2. Check access level
    if key_info['access_level'] not in ['admin', 'super_admin']:
        raise HTTPException(403, "Admin access required")
    
    # 3. Verify user exists in saas_admin_db.users
    # (Optional: Can query via API or shared DB connection)
    user = await verify_user_in_saas_admin(key_info['user_id'])
    
    return user
```

---

## 🏗️ **RECOMMENDED ARCHITECTURE**

### **Option A: Separate Supabase Projects (Simpler)** ⭐

```
Project 1: saas-admin-truevow
  Database: saas_admin_db
  Tables:
    - tenants
    - users ⭐
    - pricing_tiers
    - subscriptions
    - billing

Project 2: settle-production  
  Database: settle_db
  Tables:
    - settle_contributions
    - settle_api_keys (stores user_id as TEXT or UUID)
    - settle_founding_members
    - settle_queries
    - settle_reports
```

**Connection:**
- No direct foreign keys (different databases)
- Use `user_id` as logical reference
- API calls for cross-database operations

**Advantages:**
- ✅ Easier to set up (2 independent projects)
- ✅ No cross-database query complexity
- ✅ Better isolation
- ✅ Can use different Supabase regions if needed

---

### **Option B: Single Supabase Project with Schemas**

```
Project: truevow-platform
  Schema 1: public (or saas_admin)
    - tenants
    - users ⭐
    - pricing_tiers
    
  Schema 2: settle
    - settle_contributions
    - settle_api_keys
    - settle_founding_members
```

**Advantages:**
- ✅ True foreign key constraints
- ✅ Single connection string
- ✅ Easier cross-database queries

**Disadvantages:**
- ⚠️ Less isolation
- ⚠️ Harder to scale independently

---

## 📝 **IMPLEMENTATION PLAN**

### **Phase 1: Set Up SETTLE Database (This Week)** ✅

```bash
# 1. Create Supabase project for SETTLE
# Project name: settle-production

# 2. Run schema
# SQL Editor → Paste settle_supabase.sql → Run

# 3. Verify tables
python scripts/test_supabase_connection.py

# 4. Configure SETTLE service
# .env → SUPABASE_URL, SUPABASE_KEY

# 5. Test API
uvicorn app.main:app --reload
```

**Status:** ✅ Ready to execute now

---

### **Phase 2: Build Admin Endpoints (Week 2)**

Create admin endpoints in SETTLE service:

```python
# app/api/v1/endpoints/admin.py (NEW FILE)

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

router = APIRouter()

@router.get("/admin/contributions/pending")
async def get_pending_contributions(admin=Depends(require_admin)):
    """Get pending contributions for review"""
    pass

@router.post("/admin/contributions/{id}/approve")
async def approve_contribution(id: UUID, admin=Depends(require_admin)):
    """Approve contribution"""
    pass

@router.post("/admin/founding-members/enroll")
async def enroll_founding_member(data: dict, admin=Depends(require_admin)):
    """Enroll Founding Member"""
    pass

@router.get("/admin/analytics/dashboard")
async def get_dashboard_analytics(admin=Depends(require_admin)):
    """Get analytics for admin dashboard"""
    pass
```

**Status:** 📋 To be built

---

### **Phase 3: Build SaaS Admin UI (Week 3-4)**

Create SETTLE admin section in SaaS Admin platform:

```
Repository: 2025-TrueVow-SaaS-Admin (future)
Path: app/admin/settle/
Files:
  - contributions/page.tsx      (Review pending contributions)
  - founding-members/page.tsx   (Manage Founding Members)
  - analytics/page.tsx           (View SETTLE analytics)
  - settings/page.tsx            (Configure SETTLE settings)
```

**Status:** 📋 Future work

---

## ✅ **SUMMARY**

### **Q1: Where is the `users` table?**

**Location:**
```
Repository: 2025-TrueVow-Tenant-Application
File: operations/database/saas_admin_schema_FINAL.sql
Table: users (lines 154-208)
Database: saas_admin_db
Purpose: Central table for ALL platform users (attorneys, admins, staff)
```

**SETTLE references this table via:**
- `settle_contributions.contributor_user_id`
- `settle_api_keys.user_id`
- `settle_founding_members.user_id`

---

### **Q2: How does SETTLE get managed administratively?**

**Answer:** Through the **SaaS Admin Platform** (System 2)

**Management Functions:**
1. ✅ **Approve/reject contributions** (via admin UI)
2. ✅ **Manage Founding Members** (enroll, track stats)
3. ✅ **Generate/revoke API keys** (access control)
4. ✅ **View analytics** (database growth, revenue)
5. ✅ **Configure pricing** ($49/report, etc.)
6. ✅ **Monitor quality** (flag outliers)

**Access:** TrueVow staff only (super_admin or admin role)

---

## 🚀 **YOUR IMMEDIATE NEXT STEP**

**Create the Supabase database right now:**

1. Go to https://supabase.com/dashboard
2. Create project: `settle-production`
3. Open SQL Editor
4. Copy and run: `database/schemas/settle_supabase.sql`
5. Run test: `python scripts/test_supabase_connection.py`

**That's it!** The database will be live and ready to use. ✅

Want me to create the admin endpoints (Phase 2) next?
