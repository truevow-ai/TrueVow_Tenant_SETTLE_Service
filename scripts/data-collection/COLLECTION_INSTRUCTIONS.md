# Data Collection Instructions

## 🚀 Quick Start

### Step 1: Manual Collection (Start Here)

1. **Open the template:**
   - File: `manual-collection-template.json`
   - This shows the data structure needed

2. **Visit Court Websites:**
   - **Miami-Dade County, FL:**
     - Base URL: https://www2.miamidadeclerk.gov/
     - ⚠️ Note: /cjis/ is for CRIMINAL cases - need to find CIVIL case search
     - Look for: "Civil" or "Civil Cases" section in navigation
     - Search for: Personal Injury cases
     - Look for: Settled cases with public settlement amounts
   
   - **Los Angeles County, CA:**
     - Base URL: https://www.lacourt.org/
     - ⚠️ Note: /casesummary/ui/ returns 404 - need to find correct path
     - Look for: "Case Search" or "Online Services" section
     - Search for: Personal Injury cases
     - Look for: Settled cases with public settlement amounts
   
   **See FIND_CORRECT_URLS.md for detailed instructions on finding the correct URLs.**

3. **Collect Case Data:**
   - For each case, collect:
     - Case type (Motor Vehicle Accident, Slip and Fall, etc.)
     - Jurisdiction (Miami-Dade County, FL or Los Angeles County, CA)
     - Settlement amount (if public) - will be bucketed
     - Filing year (year only, no specific date)
     - **Source URL** (link to the court record - for verification)
     - Case reference (anonymized, e.g., MD-2023-00123)

4. **Create Collection File:**
   - Copy `manual-collection-template.json`
   - Fill in with collected cases
   - Save as `manually_collected_cases.json`

### Step 2: Create Verification Report

```bash
python create-verification-from-manual.py manually_collected_cases.json
```

This creates `verification_report.json` with all cases ready for verification.

### Step 3: Verify Data

```bash
python verify-collected-data.py --file verification_report.json
```

This interactive tool will:
- Show each case with source URL
- Let you open URLs in browser
- Mark verification status
- Save verification results

### Step 4: Export Verified Cases

```bash
python verify-collected-data.py --file verification_report.json --export-verified verified_cases.json
```

This creates a file with only verified cases.

### Step 5: Seed Database

```bash
python seed-database.py --file verified_cases.json --verify
```

Only verified, authentic cases are seeded to the database.

---

## 📋 Data Collection Template

Each case should have:

```json
{
  "jurisdiction": "Miami-Dade County, FL",
  "case_type": "Motor Vehicle Accident",
  "injury_category": ["Spinal Injury"],
  "medical_bills": 45000.0,
  "defendant_category": "Unknown",
  "outcome_type": "Settlement",
  "outcome_amount_range": "$50k-$100k",
  "filing_year": 2023,
  "source_url": "https://www2.miami-dadeclerk.com/cjis/...",
  "case_reference": "MD-2023-00123",
  "collection_date": "2026-01-04T12:00:00",
  "collector_notes": "Settlement found in public judgment"
}
```

---

## ⚠️ Important Notes

1. **Source URLs are required** - For verification only, not stored in DB
2. **Only collect publicly available data**
3. **Anonymize all data** - No names, addresses, SSNs
4. **Bucket settlement amounts** - Use ranges: $0-$50k, $50k-$100k, etc.
5. **Year only** - No specific dates, only filing year

---

## 🎯 Start Collecting Now

1. Open `manual-collection-template.json`
2. Visit court websites
3. Collect 5-10 sample cases
4. Save as `manually_collected_cases.json`
5. Run: `python create-verification-from-manual.py manually_collected_cases.json`

---

**Ready to collect!** Start with 5-10 cases to test the process, then scale up.

