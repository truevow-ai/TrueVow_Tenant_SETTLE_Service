# 🚀 SETTLE Service - Supabase Setup Guide

**Last Updated:** December 7, 2025  
**Status:** Production-Ready  
**Tables:** 6 tables with `settle_` prefix

---

## ✅ **WHAT WAS FIXED**

### **Issues Corrected:**
1. ❌ **OLD:** No actual Supabase tables created (just documentation)
2. ❌ **OLD:** Schema had duplicate contacts table
3. ✅ **NEW:** Created `settle_supabase.sql` with actual Supabase schema
4. ✅ **NEW:** References central `users` table (no duplicate contacts)
5. ✅ **NEW:** All tables use `settle_` prefix

### **Key Changes:**
- **Removed:** No contacts table in SETTLE (references central `users` table)
- **Added:** `contributor_user_id` field references `users.user_id` from SaaS Admin
- **Added:** All tables prefixed with `settle_`
- **Added:** Row-Level Security (RLS) policies
- **Added:** Database constraints and validation
- **Added:** Performance indexes

---

## 📋 **TABLES CREATED (All with `settle_` prefix)**

1. **settle_contributions** - Anonymous settlement data (main table)
2. **settle_api_keys** - API key management
3. **settle_founding_members** - 2,100 member program
4. **settle_queries** - Query tracking & analytics
5. **settle_reports** - Generated reports
6. **settle_waitlist** - Pre-launch waitlist

**Views:**
- `settle_approved_contributions`
- `settle_founding_member_stats`
- `settle_api_usage_by_level`

---

## 🗄️ **STEP-BY-STEP SUPABASE SETUP**

### **Step 1: Create Supabase Project** (2 minutes)

1. Go to https://supabase.com/dashboard
2. Click **"New Project"**
3. Fill in:
   - **Name:** `settle-production`
   - **Database Password:** Generate strong password (save it!)
   - **Region:** Choose closest to your users (e.g., `US West (Oregon)`)
4. Click **"Create new project"**
5. Wait ~2 minutes for provisioning

✅ **Checkpoint:** Project created, dashboard visible

---

### **Step 2: Run the Schema** (1 minute)

1. In Supabase Dashboard, go to **SQL Editor** (left sidebar)
2. Click **"New Query"**
3. Copy entire contents of `database/schemas/settle_supabase.sql`
4. Paste into SQL Editor
5. Click **"Run"** (or press F5)

**Expected Output:**
```
Success. No rows returned.

NOTICE:  
NOTICE:  ============================================================================
NOTICE:  SETTLE Service Schema Created Successfully!
NOTICE:  ============================================================================
NOTICE:  Tables Created:
NOTICE:    1. settle_contributions (with indexes)
NOTICE:    2. settle_api_keys (with RLS)
NOTICE:    3. settle_founding_members (with RLS)
NOTICE:    4. settle_queries
NOTICE:    5. settle_reports
NOTICE:    6. settle_waitlist
```

✅ **Checkpoint:** 6 tables created successfully

---

### **Step 3: Verify Tables Created** (1 minute)

In SQL Editor, run:

```sql
-- List all tables with settle_ prefix
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename LIKE 'settle_%'
ORDER BY tablename;
```

**Expected Output:**
```
settle_api_keys
settle_contributions
settle_founding_members
settle_queries
settle_reports
settle_waitlist
```

✅ **Checkpoint:** All 6 tables listed

---

### **Step 4: Get Database Credentials** (1 minute)

1. Go to **Settings → Database** (left sidebar)
2. Scroll to **Connection string**
3. Copy these values:

```env
# Save these for your .env file:

SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Also available:
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
```

✅ **Checkpoint:** Credentials copied

---

### **Step 5: Configure SETTLE Service** (2 minutes)

1. Navigate to SETTLE service directory:
```bash
cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\2025-TrueVow-Settle-Service
```

2. Create `.env` file:
```bash
# .env

# Supabase Connection
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-key-here

# Disable mock data (use real database)
USE_MOCK_DATA=False

# Security (generate these!)
SECRET_KEY=your-generated-secret-key
API_KEY_SALT=your-generated-salt

# Application
APP_NAME="TrueVow SETTLE Service"
ENVIRONMENT=production
DEBUG=False
```

3. Generate secure keys:
```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate API_KEY_SALT
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

✅ **Checkpoint:** `.env` file created with real credentials

---

### **Step 6: Test Connection** (2 minutes)

**Install Supabase client:**
```bash
pip install supabase
```

**Test script:**
```python
# test_supabase.py

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(url, key)

# Test query
try:
    response = supabase.table('settle_contributions').select("count", count='exact').execute()
    print(f"✅ Connection successful!")
    print(f"   Table: settle_contributions")
    print(f"   Count: {response.count} rows")
except Exception as e:
    print(f"❌ Connection failed: {str(e)}")
```

**Run test:**
```bash
python test_supabase.py
```

**Expected Output:**
```
✅ Connection successful!
   Table: settle_contributions
   Count: 0 rows
```

✅ **Checkpoint:** Database connection works

---

### **Step 7: Start SETTLE Service** (1 minute)

```bash
# Install dependencies (if not already)
pip install -r requirements.txt

# Start service
uvicorn app.main:app --reload --port 8002
```

**Test API:**
```bash
# Health check
curl http://localhost:8002/health

# Query endpoint (will use real database)
curl -X POST http://localhost:8002/api/v1/query/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "injury_type": "Spinal Injury",
    "state": "AZ",
    "county": "Maricopa",
    "medical_bills": 50000
  }'
```

✅ **Checkpoint:** Service running with real Supabase database

---

## 📊 **VERIFY SETUP**

### **Check Table Structure:**

```sql
-- In Supabase SQL Editor:

-- 1. Check table structure
SELECT 
    table_name, 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_name = 'settle_contributions'
ORDER BY ordinal_position;

-- 2. Check indexes
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'settle_contributions';

-- 3. Check views
SELECT * FROM settle_founding_member_stats;

-- 4. Check RLS policies
SELECT 
    schemaname, 
    tablename, 
    policyname, 
    permissive, 
    roles, 
    cmd 
FROM pg_policies 
WHERE tablename LIKE 'settle_%';
```

---

## 🔑 **RELATIONSHIP TO CENTRAL TABLES**

### **How SETTLE References Existing Tables:**

```sql
-- settle_contributions references users table
settle_contributions.contributor_user_id → users.user_id (SaaS Admin)

-- settle_api_keys references users table  
settle_api_keys.user_id → users.user_id (SaaS Admin)

-- settle_founding_members references users table
settle_founding_members.user_id → users.user_id (SaaS Admin)
```

**Note:** Foreign key constraints are NOT enforced to allow cross-database flexibility.
The relationship is logical, not enforced at database level.

---

## 📝 **SAMPLE QUERIES**

### **Insert Test Contribution:**

```sql
INSERT INTO settle_contributions (
    jurisdiction,
    case_type,
    injury_category,
    treatment_type,
    duration_of_treatment,
    medical_bills,
    defendant_category,
    outcome_type,
    outcome_amount_range,
    status
) VALUES (
    'Maricopa County, AZ',
    'Motor Vehicle Accident',
    ARRAY['Spinal Injury'],
    ARRAY['Physical Therapy', 'Surgery'],
    '6-12 months',
    50000.00,
    'Business',
    'Settlement',
    '$300k-$600k',
    'approved'
);
```

### **Query Approved Contributions:**

```sql
SELECT 
    jurisdiction,
    case_type,
    injury_category,
    medical_bills,
    outcome_amount_range,
    contributed_at
FROM settle_approved_contributions
WHERE jurisdiction LIKE '%Maricopa%'
ORDER BY contributed_at DESC
LIMIT 10;
```

### **Check Founding Member Stats:**

```sql
SELECT * FROM settle_founding_member_stats;
```

---

## 🚨 **TROUBLESHOOTING**

### **Issue: "relation settle_contributions does not exist"**

**Solution:**
```sql
-- Check if tables exist
SELECT tablename FROM pg_tables WHERE tablename LIKE 'settle_%';

-- If empty, re-run the schema file
-- Go to SQL Editor → paste settle_supabase.sql → Run
```

### **Issue: "permission denied for table settle_contributions"**

**Solution:**
```sql
-- Grant permissions
GRANT ALL ON settle_contributions TO anon, authenticated, service_role;
GRANT ALL ON settle_api_keys TO anon, authenticated, service_role;
GRANT ALL ON settle_founding_members TO anon, authenticated, service_role;
GRANT ALL ON settle_queries TO anon, authenticated, service_role;
GRANT ALL ON settle_reports TO anon, authenticated, service_role;
GRANT ALL ON settle_waitlist TO anon, authenticated, service_role;
```

### **Issue: "SUPABASE_URL not found"**

**Solution:**
```bash
# Make sure .env file exists in project root
ls .env

# If not, create it with credentials from Step 4
```

---

## ✅ **SETUP COMPLETE CHECKLIST**

- [ ] Supabase project created
- [ ] Schema executed (6 tables with `settle_` prefix)
- [ ] Tables verified in SQL Editor
- [ ] Credentials copied to `.env` file
- [ ] Connection tested successfully
- [ ] SETTLE service starts without errors
- [ ] API endpoints respond correctly
- [ ] No duplicate contacts table (references central `users`)

---

## 📚 **NEXT STEPS**

1. **Seed Test Data:** Run `python scripts/seed_test_data.py`
2. **Generate API Keys:** Run `python scripts/create_api_key.py`
3. **Deploy to Production:** Follow `START_SERVER.md` deployment guide
4. **Enable Encryption:** TLS 1.3 + AES-256-GCM (see `docs/security/ENCRYPTION_IMPLEMENTATION.md`)

---

## 📞 **NEED HELP?**

- **Supabase Docs:** https://supabase.com/docs
- **Schema File:** `database/schemas/settle_supabase.sql`
- **Implementation Guide:** `IMPLEMENTATION_COMPLETE.md`
- **Encryption Guide:** `docs/security/ENCRYPTION_IMPLEMENTATION.md`

---

**Setup Status:** ✅ **READY FOR PRODUCTION**

**All tables created with `settle_` prefix and proper relationships to central platform tables!**

