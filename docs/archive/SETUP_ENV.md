# 🔧 Environment Configuration Setup

## ✅ **REQUIRED: Create `.env.local` File**

Create a file named `.env.local` in the root of your project with these **required** credentials:

---

## 📋 **MINIMUM REQUIRED CONFIGURATION**

```bash
# ============================================================================
# REQUIRED: SUPABASE CREDENTIALS
# ============================================================================
# Get from: https://supabase.com/dashboard → settle-production → Settings → API

SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-anon-key-here
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-service-role-key-here

# ============================================================================
# REQUIRED: SECURITY KEYS
# ============================================================================
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"

SECRET_KEY=your-secret-key-here
API_KEY_SALT=your-api-key-salt-here

# ============================================================================
# DEVELOPMENT SETTINGS
# ============================================================================
USE_MOCK_DATA=False
DEBUG=True
ENVIRONMENT=development
```

---

## 🔑 **HOW TO GET SUPABASE CREDENTIALS**

### **Step 1: Go to Supabase Dashboard**
https://supabase.com/dashboard

### **Step 2: Select Your Project**
Click on: `settle-production`

### **Step 3: Get API Credentials**
1. Click **Settings** (gear icon at bottom left)
2. Click **API** (in left sidebar)
3. Copy these values:

```
Project URL          → SUPABASE_URL
anon / public key    → SUPABASE_KEY
service_role key     → SUPABASE_SERVICE_KEY (click "Reveal" button)
```

**Screenshot of where to find them:**
```
Settings → API
├── Project URL: https://xxxxxxxxxxxxx.supabase.co
├── API Keys
│   ├── anon (public):     eyJhbG... (safe to use in browser)
│   └── service_role:      eyJhbG... (keep secret, full access)
```

---

## 🔐 **HOW TO GENERATE SECURITY KEYS**

### **Option 1: Using Python** (Recommended)

```bash
# Generate SECRET_KEY
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate API_KEY_SALT
python -c "import secrets; print('API_KEY_SALT=' + secrets.token_urlsafe(32))"
```

**Copy the output and paste into your `.env.local` file.**

### **Option 2: Using OpenSSL**

```bash
# Generate SECRET_KEY
openssl rand -base64 32

# Generate API_KEY_SALT
openssl rand -base64 32
```

### **Option 3: Online Generator**
https://generate-secret.vercel.app/32

---

## 📁 **COMPLETE `.env.local` EXAMPLE**

Here's a complete working example (replace with your actual values):

```bash
# ============================================================================
# SUPABASE CREDENTIALS
# ============================================================================
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYxNjIxMjQyNiwiZXhwIjoxOTMxNzg4NDI2fQ.abc123...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoic2VydmljZV9yb2xlIiwiaWF0IjoxNjE2MjEyNDI2LCJleHAiOjE5MzE3ODg0MjZ9.xyz789...

# ============================================================================
# SECURITY KEYS
# ============================================================================
SECRET_KEY=KjH8mN_vQp2rL9sX4tY6uZ0aB1cD3eF5gH7iJ9kL0mN2oP4qR6sT8uV0wX2yZ4aB
API_KEY_SALT=M6nO8pQ0rR2sT4uV6wX8yZ0aB2cD4eF6gH8iJ0kL2mN4oP6qR8sT0uV2wX4yZ6aB

# ============================================================================
# DEVELOPMENT SETTINGS
# ============================================================================
USE_MOCK_DATA=False
DEBUG=True
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8002

# ============================================================================
# OPTIONAL: ADMIN KEY
# ============================================================================
ADMIN_API_KEY=settle_admin_dev_key_12345

# ============================================================================
# OPTIONAL: FEATURE FLAGS
# ============================================================================
FEATURE_PDF_GENERATION=True
FEATURE_BLOCKCHAIN_VERIFICATION=True
FEATURE_AUTO_APPROVAL=False

# ============================================================================
# OPTIONAL: CORS
# ============================================================================
CORS_ORIGINS=http://localhost:3000,http://localhost:8002
```

---

## ✅ **VERIFY YOUR SETUP**

After creating `.env.local`, verify it works:

### **Step 1: Install Dependencies**
```bash
pip install python-dotenv supabase
```

### **Step 2: Test Connection**
```bash
python scripts/test_supabase_connection.py
```

**Expected Output:**
```
============================================================
🧪 SETTLE Service - Supabase Connection Test
============================================================
✅ Supabase client created
   URL: https://xxxxxxxxxxxxx.supabase.co

📊 Testing tables...
------------------------------------------------------------
✅ settle_contributions              0 rows
✅ settle_api_keys                   1 rows (sample admin key)
✅ settle_founding_members           0 rows
✅ settle_queries                    0 rows
✅ settle_reports                    0 rows
✅ settle_waitlist                   0 rows

✅ ALL TESTS PASSED
```

---

## 🚨 **TROUBLESHOOTING**

### **Error: "Missing Supabase credentials"**
- Make sure `.env.local` file exists in project root
- Check that `SUPABASE_URL` and `SUPABASE_KEY` are set
- Verify no typos in variable names

### **Error: "Invalid API key"**
- Copy the entire key including `eyJhbG...` prefix
- Don't add quotes around the key
- Make sure you copied the correct key (anon vs service_role)

### **Error: "Connection refused"**
- Check that `SUPABASE_URL` is correct
- Verify Supabase project is active (not paused)
- Check your internet connection

### **Error: "Permission denied"**
- Make sure you're using `SUPABASE_SERVICE_KEY` (not just `SUPABASE_KEY`)
- Service role key has full database access
- Anon key has limited access (good for frontend, not backend)

---

## 📝 **QUICK CHECKLIST**

- [ ] Created `.env.local` file in project root
- [ ] Added `SUPABASE_URL` from Supabase dashboard
- [ ] Added `SUPABASE_KEY` (anon key)
- [ ] Added `SUPABASE_SERVICE_KEY` (service_role key)
- [ ] Generated `SECRET_KEY` using Python/OpenSSL
- [ ] Generated `API_KEY_SALT` using Python/OpenSSL
- [ ] Set `USE_MOCK_DATA=False`
- [ ] Ran `python scripts/test_supabase_connection.py`
- [ ] Saw "ALL TESTS PASSED" ✅

---

## 🎯 **NEXT STEPS**

Once your `.env.local` is configured:

1. **Start the SETTLE service:**
   ```bash
   uvicorn app.main:app --reload --port 8002
   ```

2. **Visit API docs:**
   http://localhost:8002/docs

3. **Test the API:**
   - Try the health check: `GET /health`
   - Check founding member stats: `GET /api/v1/stats/founding-members`

---

## 🔒 **SECURITY NOTES**

⚠️ **IMPORTANT:**
- **NEVER** commit `.env.local` to git
- **NEVER** share your `SUPABASE_SERVICE_KEY` publicly
- **NEVER** use development keys in production
- Keep your `.env.local` file private

The `.env.local` file is already in `.gitignore` to prevent accidental commits.

---

## 📚 **ADDITIONAL RESOURCES**

- **Supabase Docs:** https://supabase.com/docs
- **Environment Variables:** https://pydantic-docs.helpmanual.io/usage/settings/
- **Security Best Practices:** https://supabase.com/docs/guides/api/securing-your-api

---

**Need help?** Check `database/SUPABASE_SETUP_GUIDE.md` for more details.

