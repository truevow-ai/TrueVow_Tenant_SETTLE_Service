# SETTLE Service - Database Schemas

## 📁 **Files in This Directory**

### **1. settle_supabase.sql** ⭐ **USE THIS ONE**

**Status:** ✅ Production-Ready, Supabase-Specific  
**Last Updated:** December 7, 2025

**What it includes:**
- ✅ 6 tables with `settle_` prefix
- ✅ References central `users` table (no duplicate contacts)
- ✅ Row-Level Security (RLS) policies
- ✅ Performance indexes
- ✅ Database constraints
- ✅ Views for analytics
- ✅ Auto-update triggers

**Tables Created:**
1. `settle_contributions` - Anonymous settlement data
2. `settle_api_keys` - API key management
3. `settle_founding_members` - 2,100 member program
4. `settle_queries` - Query tracking
5. `settle_reports` - Generated reports
6. `settle_waitlist` - Pre-launch waitlist

**Use this for:**
- Production Supabase setup
- Actual deployment
- Integration with TrueVow platform

**Setup Guide:** `../SUPABASE_SETUP_GUIDE.md`

---

### **2. settle.sql** 📚 **REFERENCE ONLY**

**Status:** ⚠️ Deprecated - Generic Reference  
**Last Updated:** December 7, 2025

**What it is:**
- Generic SQL schema without platform-specific features
- NO table prefixes
- NO RLS policies
- NO integration with central tables

**Use this for:**
- Understanding table structure
- Documentation reference
- Non-Supabase deployments (manual adaptation required)

**⚠️ DO NOT use for production Supabase setup**

---

## 🚀 **Quick Start**

### **To Set Up SETTLE in Supabase:**

1. **Use the correct file:**
   ```
   database/schemas/settle_supabase.sql
   ```

2. **Follow the setup guide:**
   ```
   database/SUPABASE_SETUP_GUIDE.md
   ```

3. **Steps:**
   - Create Supabase project
   - Run `settle_supabase.sql` in SQL Editor
   - Verify 6 tables created with `settle_` prefix
   - Configure `.env` with credentials
   - Test connection

---

## 🔑 **Key Differences**

| Feature | settle.sql | settle_supabase.sql |
|---------|-----------|---------------------|
| Table Prefix | ❌ None | ✅ `settle_` |
| RLS Policies | ❌ No | ✅ Yes |
| Central Users Ref | ❌ No | ✅ Yes |
| Constraints | ⚠️ Basic | ✅ Full |
| Indexes | ⚠️ Basic | ✅ Optimized |
| Views | ❌ No | ✅ 3 views |
| Triggers | ❌ No | ✅ Auto-update |
| Comments | ⚠️ Some | ✅ Complete |
| Production Ready | ❌ No | ✅ Yes |

---

## ✅ **What Was Fixed (December 7, 2025)**

### **Issues Identified:**
1. ❌ No actual Supabase tables created (just documentation)
2. ❌ Schema had duplicate contacts table
3. ❌ No table prefixes for namespace separation
4. ❌ No integration with central platform tables

### **Solutions Implemented:**
1. ✅ Created `settle_supabase.sql` with actual Supabase schema
2. ✅ Removed contacts table, references central `users` table
3. ✅ All tables now have `settle_` prefix
4. ✅ Added `contributor_user_id` references to `users.user_id`
5. ✅ Added RLS policies for security
6. ✅ Added comprehensive indexes
7. ✅ Added validation constraints
8. ✅ Added analytics views

---

## 📊 **Table Relationships**

### **SETTLE → Central Platform:**

```
settle_contributions.contributor_user_id → users.user_id (SaaS Admin)
settle_api_keys.user_id → users.user_id (SaaS Admin)
settle_founding_members.user_id → users.user_id (SaaS Admin)
```

**Note:** These are logical relationships (not enforced foreign keys) to allow cross-database flexibility.

---

## 📝 **Migration Notes**

### **If you used the old settle.sql:**

**Problem:** Tables created without `settle_` prefix

**Solution:** Drop and recreate

```sql
-- Drop old tables (if they exist)
DROP TABLE IF EXISTS case_bank_entries CASCADE;
DROP TABLE IF EXISTS web_settle_waitlist CASCADE;
DROP TABLE IF EXISTS contributions CASCADE;

-- Run new schema
-- Use settle_supabase.sql
```

### **If you need to migrate data:**

```sql
-- Example: Copy data from old to new table
INSERT INTO settle_contributions (
    jurisdiction,
    case_type,
    injury_category,
    -- ... other fields
)
SELECT 
    jurisdiction,
    case_type,
    injury_category,
    -- ... other fields
FROM old_table_name;
```

---

## 🔒 **Security Features**

### **In settle_supabase.sql:**

1. **Row-Level Security (RLS)**
   - Enabled on `settle_api_keys`
   - Enabled on `settle_founding_members`
   - Service role has full access
   - Users can only read their own data

2. **Constraints**
   - Email validation
   - Enum checks (status, access_level, etc.)
   - Range validation (medical_bills, confidence_score)
   - Positive number checks

3. **Indexes**
   - Performance indexes on all query columns
   - Composite indexes for common patterns
   - GIN indexes on array columns

---

## 📚 **Additional Resources**

- **Setup Guide:** `../SUPABASE_SETUP_GUIDE.md`
- **Implementation Guide:** `../../IMPLEMENTATION_COMPLETE.md`
- **Encryption Guide:** `../../docs/security/ENCRYPTION_IMPLEMENTATION.md`
- **System Documentation:** Part 7, Section 7.14-7.16

---

## 📞 **Questions?**

- **Which file to use?** → `settle_supabase.sql`
- **Where's the setup guide?** → `../SUPABASE_SETUP_GUIDE.md`
- **How to reference users table?** → Use `contributor_user_id` field
- **Need to migrate?** → See Migration Notes above

---

**Last Updated:** December 7, 2025  
**Status:** Production-Ready ✅

