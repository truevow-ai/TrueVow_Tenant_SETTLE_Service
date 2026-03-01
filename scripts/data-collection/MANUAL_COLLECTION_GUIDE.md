# Manual Collection Guide - Real Cases Only

**Purpose:** Collect REAL personal injury settlement cases from verifiable sources

---

## ✅ Allowed Sources

### 1. **Legal News Websites**
- **Law.com** - Search for "personal injury settlement"
- **ABA Journal** - Case studies and settlement news
- **Legal Newsline** - Personal injury news
- **Law360** - Settlement reports

### 2. **Law Firm Blogs**
- Many law firms publish case studies on their blogs
- Look for "case results" or "settlement" pages
- Example: Search "personal injury settlement [law firm name]"

### 3. **Court Record Websites** (When Accessible)
- Miami-Dade Clerk: https://www.miamidadeclerk.gov/clerk/civil/caseSearch.page
- Los Angeles Courts: https://www.lacourt.ca.gov/pages/lp/access-a-case
- **Note:** These often require case numbers

### 4. **Legal Publications**
- State bar journals
- Legal magazines
- Case study publications

---

## 📋 Collection Process

### Step 1: Find a Real Case Article

**Search Terms:**
- "personal injury settlement Miami"
- "car accident settlement Los Angeles"
- "slip and fall case settlement Florida"
- "personal injury verdict California"

**What to Look For:**
- ✅ Actual settlement amounts mentioned
- ✅ Case type (MVA, Slip & Fall, etc.)
- ✅ Jurisdiction (Miami-Dade, Los Angeles, etc.)
- ✅ Injury types mentioned
- ✅ Source URL you can verify

### Step 2: Use Collection Helper

```bash
python manual-collection-helper.py
```

This will guide you through:
- Entering source URL
- Extracting case information
- Saving to file

### Step 3: Verify Information

**Before saving, verify:**
- ✅ Source URL is real and accessible
- ✅ Settlement amount matches article
- ✅ Case type is accurate
- ✅ Jurisdiction is correct
- ✅ Injury information is from the article

### Step 4: Prepare for Database

```bash
python prepare-for-seeding.py manually_collected_cases.json verified_cases.json
```

### Step 5: Seed Database

```bash
python seed-via-supabase-client.py verified_cases.json
```

---

## 📝 What Information to Collect

### **Required:**
- Source URL (article link)
- Jurisdiction (Miami-Dade County, FL or Los Angeles County, CA)
- Case Type (Motor Vehicle Accident, Slip and Fall, etc.)
- Settlement Range ($0-$50k, $50k-$100k, etc.)

### **Recommended:**
- Injury Categories (Spinal Injury, TBI, Fracture, etc.)
- Medical Bills (if mentioned)
- Treatment Type (Surgery, Physical Therapy, etc.)
- Defendant Category (Business, Individual, Unknown)

### **Optional:**
- Primary Diagnosis
- Duration of Treatment
- Imaging Findings
- Lost Wages
- Policy Limits

---

## 🔍 Example Sources

### **Miami-Dade Cases:**
1. Search: "Miami personal injury settlement" on Google News
2. Check: Local news sites (Miami Herald, etc.)
3. Look: Florida legal blogs discussing cases

### **Los Angeles Cases:**
1. Search: "Los Angeles personal injury settlement" on Google News
2. Check: Local news sites (LA Times, etc.)
3. Look: California legal blogs discussing cases

### **General Sources:**
- Google News: "personal injury settlement [jurisdiction]"
- Legal news aggregators
- Law firm case results pages
- Legal publications

---

## ⚠️ Important Rules

### **DO:**
- ✅ Only collect from real, verifiable sources
- ✅ Preserve source URLs for verification
- ✅ Extract accurate information from articles
- ✅ Verify settlement amounts match source

### **DON'T:**
- ❌ Make up or estimate information
- ❌ Use placeholder data
- ❌ Collect from unverified sources
- ❌ Guess settlement amounts

---

## 📊 Quality Checklist

Before inserting into database, verify:

- [ ] Source URL is real and accessible
- [ ] Settlement amount matches source
- [ ] Case type is accurate
- [ ] Jurisdiction is correct
- [ ] Injury information is from source
- [ ] No synthetic or estimated data
- [ ] All required fields are filled
- [ ] Information is verifiable

---

## 🚀 Quick Start

1. **Find an article** about a real settlement case
2. **Run collection helper:**
   ```bash
   python manual-collection-helper.py
   ```
3. **Enter information** from the article
4. **Verify** the information is accurate
5. **Save** and repeat for more cases
6. **Prepare and seed** database when ready

---

## 📁 Files Created

- `manually_collected_cases.json` - Your collected cases
- `verified_cases.json` - Database-ready format (after preparation)
- Verification reports for each case

---

**Remember:** Quality over quantity. Better to have 5 verified real cases than 50 unverified ones!

