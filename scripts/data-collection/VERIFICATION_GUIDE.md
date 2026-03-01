# Data Verification Guide

## Overview

This guide explains how to manually verify that collected court records data is **authentic** and **not synthetic**.

## ⚠️ Why Verification is Critical

- **Data Integrity**: Ensure SETTLE database contains real, accurate settlement data
- **Trust**: Users must trust that estimates are based on real cases
- **Compliance**: Verify data comes from legitimate public sources
- **Quality**: Reject any synthetic or fabricated data

## 📋 Verification Process

### Step 1: Review Verification Report

After data collection, a `verification_report.json` file is generated with:
- Source URLs to original court records
- Case references for tracking
- Collection metadata
- Verification status fields (to be filled)

### Step 2: Verify Each Case

For each case in the report:

1. **Open Source URL**
   - Click the `source_url` link
   - Verify it goes to a real court website
   - Confirm the case exists in the court's system

2. **Check Case Details**
   - Verify case type matches
   - Verify jurisdiction matches
   - Verify filing year matches
   - Check if settlement amount is visible (may be redacted)

3. **Verify Settlement Data**
   - If settlement amount is public, verify it matches the bucketed range
   - If not public, verify case status indicates settlement occurred
   - Check that outcome type (Settlement/Judgment) is correct

4. **Check Anonymization**
   - Verify NO names are present
   - Verify NO addresses are present
   - Verify NO SSNs or other PHI/PII
   - Verify only generic categories and bucketed amounts

### Step 3: Mark Verification Status

For each case, mark one of:

- **✅ Verified**: Data is authentic and from real court records
- **⚠️ Needs Review**: Uncertain, requires additional verification
- **❌ Rejected**: Data is not authentic or cannot be verified

### Step 4: Export Verified Cases

Only verified cases should be seeded to the database.

## 🛠️ Using the Verification Tool

### Interactive Verification

```bash
python verify-collected-data.py --file verification_report.json
```

This will:
1. Show each case one by one
2. Open source URLs in browser (optional)
3. Allow you to mark verification status
4. Save verification results

### View Summary Only

```bash
python verify-collected-data.py --file verification_report.json --summary
```

### Export Verified Cases

```bash
python verify-collected-data.py --file verification_report.json --export-verified verified_cases.json
```

This creates a file with only verified cases, ready for database seeding.

## 📊 Verification Checklist

For each case, verify:

- [ ] Source URL links to real court website
- [ ] Case exists in court's system
- [ ] Case type matches collected data
- [ ] Jurisdiction matches collected data
- [ ] Filing year matches (if available)
- [ ] Settlement amount/range is reasonable (if visible)
- [ ] No PHI/PII in collected data
- [ ] Data is properly anonymized
- [ ] Case reference is valid

## 🔍 What to Look For

### ✅ Authentic Data Indicators

- Source URL goes to official court website
- Case number format matches court's system
- Case details match public records
- Settlement amounts are reasonable for case type
- Data is properly anonymized

### ❌ Red Flags (Reject These)

- Source URL doesn't work or goes to wrong site
- Case doesn't exist in court system
- Settlement amounts seem fabricated
- Data contains identifying information
- Case reference doesn't match court format
- Multiple cases with identical data

## 📝 Verification Report Structure

```json
{
  "collection_date": "2026-01-04T12:00:00",
  "total_cases": 50,
  "cases": [
    {
      "case_number": 1,
      "jurisdiction": "Miami-Dade County, FL",
      "case_type": "Motor Vehicle Accident",
      "source_url": "https://www2.miami-dadeclerk.com/cjis/...",
      "case_reference": "MD-2023-00123",
      "verification_status": "pending",
      "verification_notes": "",
      "verified_by": "",
      "verification_date": ""
    }
  ]
}
```

## 🎯 Verification Workflow

1. **Collect Data** → `collected_cases.json` + `verification_report.json`
2. **Review Report** → Check source URLs and case references
3. **Verify Cases** → Use interactive tool or manual review
4. **Export Verified** → `verified_cases.json` (only verified cases)
5. **Seed Database** → Use verified cases only

## ⚠️ Important Notes

1. **Source URLs are for verification only** - Do NOT store in production database
2. **Case references are anonymized** - Original case numbers are not stored
3. **Only verified cases** should be seeded to database
4. **Rejected cases** should be removed from collection
5. **Needs Review cases** should be investigated further

## 🔒 Security & Privacy

- Source URLs may contain case numbers - these are for verification only
- Do NOT store source URLs in production database
- Do NOT store case references in production database
- Only anonymized data goes to production

## 📞 Questions?

If you encounter:
- **Unverifiable cases**: Mark as "needs_review" or "rejected"
- **Broken source URLs**: Mark as "rejected"
- **Suspicious data**: Mark as "rejected" and investigate
- **Missing information**: Mark as "needs_review"

---

**Remember**: Only seed verified, authentic data to the SETTLE database!

