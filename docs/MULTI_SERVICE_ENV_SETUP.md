# 🏗️ Multi-Service Environment Configuration

**For Managing Multiple TrueVow Services in One `.env.local` File**

---

## 🎯 **WHY USE PREFIXES?**

When running multiple TrueVow services (SETTLE, SaaS Admin, Sales CRM, etc.) from a single codebase or shared configuration, using **prefixed environment variables** prevents conflicts and confusion.

**Example Problem Without Prefixes:**
```bash
# ❌ CONFUSING - Which database is this for?
SUPABASE_URL=https://abc123.supabase.co
SUPABASE_KEY=eyJhbG...

# Is this for SETTLE? SaaS Admin? Sales CRM? 🤷
```

**Solution With Prefixes:**
```bash
# ✅ CLEAR - Each service has its own credentials
SETTLE_SUPABASE_URL=https://settle-prod.supabase.co
SETTLE_SUPABASE_ANON_KEY=eyJhbG...

SAAS_ADMIN_SUPABASE_URL=https://admin-prod.supabase.co
SAAS_ADMIN_SUPABASE_ANON_KEY=eyJhbG...

SALES_CRM_SUPABASE_URL=https://crm-prod.supabase.co
SALES_CRM_SUPABASE_ANON_KEY=eyJhbG...
```

---

## ✅ **SETTLE SERVICE NOW SUPPORTS PREFIXES!**

The SETTLE service has been updated to support **both** naming conventions:

### **Option 1: Prefixed (Recommended for Multi-Service Setup)**
```bash
SETTLE_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SETTLE_SUPABASE_ANON_KEY=eyJhbG...
SETTLE_SUPABASE_SERVICE_KEY=eyJhbG...
SETTLE_SECRET_KEY=your-secret-key
SETTLE_API_KEY_SALT=your-api-key-salt
```

### **Option 2: Unprefixed (For Standalone SETTLE Service)**
```bash
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbG...
SUPABASE_SERVICE_KEY=eyJhbG...
SECRET_KEY=your-secret-key
API_KEY_SALT=your-api-key-salt
```

**The service checks for prefixed names first, then falls back to unprefixed.**

---

## 📋 **COMPLETE MULTI-SERVICE `.env.local` TEMPLATE**

Here's an example showing all TrueVow services in one file:

```bash
# ============================================================================
# TrueVow Platform - Unified Environment Configuration
# ============================================================================

# ============================================================================
# SETTLE SERVICE (Settlement Intelligence)
# ============================================================================
SETTLE_SUPABASE_URL=https://settle-production.supabase.co
SETTLE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SETTLE_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SETTLE_SECRET_KEY=KjH8mN_vQp2rL9sX4tY6uZ0aB1cD3eF5gH7iJ9kL0mN2oP4qR6sT8uV0wX2yZ4aB
SETTLE_API_KEY_SALT=M6nO8pQ0rR2sT4uV6wX8yZ0aB2cD4eF6gH8iJ0kL2mN4oP6qR8sT0uV2wX4yZ6aB
SETTLE_USE_MOCK_DATA=False
SETTLE_DEBUG=True
SETTLE_PORT=8002

# ============================================================================
# SAAS ADMIN SERVICE (Tenant Management)
# ============================================================================
SAAS_ADMIN_SUPABASE_URL=https://saas-admin-production.supabase.co
SAAS_ADMIN_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SAAS_ADMIN_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SAAS_ADMIN_SECRET_KEY=different-secret-key-for-admin
SAAS_ADMIN_CLERK_SECRET_KEY=sk_test_...
SAAS_ADMIN_PORT=8001

# ============================================================================
# SALES CRM SERVICE (Sales Management)
# ============================================================================
SALES_CRM_SUPABASE_URL=https://sales-crm-production.supabase.co
SALES_CRM_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SALES_CRM_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SALES_CRM_SECRET_KEY=different-secret-key-for-crm
SALES_CRM_PORT=8003

# ============================================================================
# TENANT SERVICE (Intake Application)
# ============================================================================
TENANT_DATABASE_URL=postgresql://user:pass@localhost:5432/intake_db
TENANT_SECRET_KEY=different-secret-key-for-tenant
TENANT_PORT=8000

# ============================================================================
# SHARED SERVICES (Used by Multiple Services)
# ============================================================================
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
SENDGRID_API_KEY=SG.xxx...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# ============================================================================
# DEVELOPMENT SETTINGS
# ============================================================================
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO
```

---

## 🔧 **HOW THE SETTLE SERVICE READS PREFIXED VARS**

The `app/core/config.py` now has smart fallback logic:

```python
class Settings(BaseSettings):
    # Prefixed variables (for multi-service setup)
    SETTLE_SUPABASE_URL: Optional[str] = None
    SETTLE_SUPABASE_ANON_KEY: Optional[str] = None
    SETTLE_SUPABASE_SERVICE_KEY: Optional[str] = None
    
    # Unprefixed variables (backwards compatibility)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    
    @property
    def supabase_url(self) -> Optional[str]:
        """Prefers SETTLE_ prefix, falls back to unprefixed"""
        return self.SETTLE_SUPABASE_URL or self.SUPABASE_URL
    
    @property
    def supabase_key(self) -> Optional[str]:
        """Prefers SETTLE_ prefix, falls back to unprefixed"""
        return self.SETTLE_SUPABASE_ANON_KEY or self.SUPABASE_KEY
    
    @property
    def supabase_service_key(self) -> Optional[str]:
        """Prefers SETTLE_ prefix, falls back to unprefixed"""
        return self.SETTLE_SUPABASE_SERVICE_KEY or self.SUPABASE_SERVICE_KEY
```

**Priority:**
1. Checks `SETTLE_SUPABASE_URL` first ✅
2. Falls back to `SUPABASE_URL` if not found
3. Returns `None` if neither exists

---

## 📝 **YOUR SETTLE `.env.local` FILE (PREFIXED VERSION)**

Based on what you already have, here's your complete SETTLE configuration:

```bash
# ============================================================================
# SETTLE SERVICE CONFIGURATION (Prefixed for Multi-Service Setup)
# ============================================================================

# Database Name (optional, for reference only)
SETTLE_DATABASE_NAME=TrueVow-SETTLE-App

# Supabase Credentials (from Supabase Dashboard → settle-production)
SETTLE_SUPABASE_URL=https://sdxyynwzfmonfkensswo.supabase.co
SETTLE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNkeHl5bnd6Zm1vbmZrZW5zc3dvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI0NTgzMjUsImV4cCI6MjA3ODAzNDMyNX0.FH3abraN1A1jF9coX0OUBRTlt84Xl1JvGQAwLESc4s4
SETTLE_SUPABASE_SERVICE_KEY=your-service-role-key-here-from-supabase

# Security Keys (generate with: python scripts/generate_env_keys.py)
SETTLE_SECRET_KEY=your-generated-secret-key-here
SETTLE_API_KEY_SALT=your-generated-api-key-salt-here

# Application Settings
SETTLE_USE_MOCK_DATA=False
SETTLE_DEBUG=True
SETTLE_ENVIRONMENT=development
SETTLE_PORT=8002

# Optional: Admin API Key
SETTLE_ADMIN_API_KEY=settle_admin_dev_key_12345

# Optional: Feature Flags
SETTLE_FEATURE_PDF_GENERATION=True
SETTLE_FEATURE_BLOCKCHAIN_VERIFICATION=True
SETTLE_FEATURE_AUTO_APPROVAL=False
```

---

## ⚠️ **YOU STILL NEED TO ADD:**

### **1. Service Role Key**
```bash
SETTLE_SUPABASE_SERVICE_KEY=eyJhbG...
```

**Where to get it:**
1. Go to: https://supabase.com/dashboard
2. Click: `settle-production` (or your project name)
3. Click: **Settings** → **API**
4. Find: **service_role** key
5. Click: **"Reveal"** button
6. Copy the entire key (starts with `eyJhbG...`)

### **2. Security Keys**
```bash
SETTLE_SECRET_KEY=...
SETTLE_API_KEY_SALT=...
```

**Generate them:**
```bash
python scripts/generate_env_keys.py
```

Then copy the output into your `.env.local` file.

---

## ✅ **COMPLETE WORKING EXAMPLE FOR YOUR SETUP**

Here's what your **complete** `.env.local` should look like (fill in the missing values):

```bash
# SETTLE Service Configuration
SETTLE_DATABASE_NAME=TrueVow-SETTLE-App

# Supabase (you already have these)
SETTLE_SUPABASE_URL=https://sdxyynwzfmonvkensswo.supabase.co
SETTLE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNkeHl5bnd6Zm1vbmZrZW5zc3dvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI0NTgzMjUsImV4cCI6MjA3ODAzNDMyNX0.FH3abraN1A1jF9coX0OUBRTlt84Xl1JvGQAwLESc4s4

# TODO: Add these two (get from Supabase + generate script)
SETTLE_SUPABASE_SERVICE_KEY=
SETTLE_SECRET_KEY=
SETTLE_API_KEY_SALT=

# Settings
SETTLE_USE_MOCK_DATA=False
SETTLE_DEBUG=True
SETTLE_PORT=8002
```

---

## 🧪 **TEST YOUR PREFIXED CONFIGURATION**

```bash
# Test Supabase connection (now supports prefixed vars)
python scripts/test_supabase_connection.py
```

**Expected output:**
```
✅ Supabase client created
   URL: https://sdxyynwzfmonvkensswo.supabase.co

📊 Testing tables...
✅ settle_contributions              0 rows
✅ settle_api_keys                   1 rows
✅ settle_founding_members           0 rows
✅ settle_queries                    0 rows
✅ settle_reports                    0 rows
✅ settle_waitlist                   0 rows

✅ ALL TESTS PASSED
```

---

## 📊 **VARIABLE NAMING CONVENTION ACROSS SERVICES**

| Service | Prefix | Example Variables |
|---------|--------|-------------------|
| **SETTLE** | `SETTLE_` | `SETTLE_SUPABASE_URL`, `SETTLE_SECRET_KEY` |
| **SaaS Admin** | `SAAS_ADMIN_` | `SAAS_ADMIN_SUPABASE_URL`, `SAAS_ADMIN_CLERK_SECRET_KEY` |
| **Sales CRM** | `SALES_CRM_` | `SALES_CRM_SUPABASE_URL`, `SALES_CRM_SECRET_KEY` |
| **Tenant App** | `TENANT_` | `TENANT_DATABASE_URL`, `TENANT_SECRET_KEY` |
| **Shared** | (none) | `STRIPE_API_KEY`, `SENDGRID_API_KEY`, `SLACK_WEBHOOK_URL` |

---

## 🎯 **BENEFITS OF THIS APPROACH**

### ✅ **Clear Separation**
```bash
# Easy to see which service uses what
SETTLE_SUPABASE_URL=...          # For SETTLE
SAAS_ADMIN_SUPABASE_URL=...      # For SaaS Admin
SALES_CRM_SUPABASE_URL=...       # For Sales CRM
```

### ✅ **No Conflicts**
```bash
# Each service can have different databases
SETTLE_SUPABASE_URL=https://settle-prod.supabase.co
SAAS_ADMIN_SUPABASE_URL=https://admin-prod.supabase.co

# Each service can have different secrets
SETTLE_SECRET_KEY=abc123...
SAAS_ADMIN_SECRET_KEY=xyz789...
```

### ✅ **Easy to Share**
```bash
# Can share common .env.local across services
# Or keep separate files:
.env.local.settle
.env.local.saas-admin
.env.local.sales-crm
```

### ✅ **Backwards Compatible**
```bash
# SETTLE still works with unprefixed vars if you run it standalone
SUPABASE_URL=...  # Works!
SETTLE_SUPABASE_URL=...  # Also works! (takes priority)
```

---

## 📚 **QUICK REFERENCE**

### **Minimum Required for SETTLE Service:**

```bash
SETTLE_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SETTLE_SUPABASE_ANON_KEY=eyJhbG...
SETTLE_SUPABASE_SERVICE_KEY=eyJhbG...
SETTLE_SECRET_KEY=xxx...
SETTLE_API_KEY_SALT=xxx...
SETTLE_USE_MOCK_DATA=False
```

### **To Generate Security Keys:**
```bash
python scripts/generate_env_keys.py
```

### **To Get Supabase Service Key:**
```
Supabase Dashboard → settle-production → Settings → API → service_role (Reveal)
```

### **To Test Configuration:**
```bash
python scripts/test_supabase_connection.py
```

---

## 🎉 **YOU'RE ON THE RIGHT TRACK!**

Using prefixes like `SETTLE_`, `SAAS_ADMIN_`, `SALES_CRM_` is **best practice** for managing multiple services. The SETTLE service now fully supports this approach!

**Next Steps:**
1. ✅ Keep your `SETTLE_SUPABASE_URL` and `SETTLE_SUPABASE_ANON_KEY` (you already have these)
2. ⬜ Add `SETTLE_SUPABASE_SERVICE_KEY` (get from Supabase dashboard)
3. ⬜ Generate and add `SETTLE_SECRET_KEY` and `SETTLE_API_KEY_SALT`
4. ⬜ Test with `python scripts/test_supabase_connection.py`
5. ⬜ Start service with `uvicorn app.main:app --reload --port 8002`

---

**This approach will scale perfectly as you add more TrueVow services!** 🚀

