# 500 Settlement Cases Extraction - Status Report

## Overview
Extracting all 500 case URLs from Casemine search results (filtered for "settlement" cases) and processing only settlement cases for the SETTLE database.

## Current Process

### Step 1: URL Extraction (In Progress)
- Scrolling through all 500 case listings on the search results page
- Extracting all case/judgment URLs
- Saving to `all_500_case_urls.txt`

### Step 2: Settlement Filtering & Extraction (Pending)
- Processing each URL with settlement-only filter
- Skipping verdict-only cases (no settlement mentioned)
- Extracting case details for settlement cases only
- Saving to `settlement_cases_500.json`

### Step 3: Data Review & Field Suggestions (Pending)
- Review extracted data
- Identify any additional fields that should be captured
- Suggest database schema updates if needed

## Current Database Schema Fields

Based on `settle_contributions` table, we're capturing:

### Step 1: Venue & Case Type
- `jurisdiction` (e.g., "Maricopa County, AZ")
- `case_type` (e.g., "Motor Vehicle Accident")

### Step 2: Injury & Treatment
- `injury_category` (array: ["Spinal Injury", "TBI"])
- `primary_diagnosis` (optional, ICD-10 category)
- `treatment_type` (array: ["Surgery", "PT"])
- `duration_of_treatment` (optional: "<3 months", etc.)
- `imaging_findings` (array: ["Fracture", "Herniated Disc"])

### Step 3: Financial
- `medical_bills` (numeric, required)
- `lost_wages` (numeric, optional)
- `policy_limits` (optional: "$15k/$30k", etc.)

### Step 4: Liability Context
- `defendant_category` ("Individual", "Business", "Government", "Unknown")

### Step 5: Outcome
- `outcome_type` (must be "Settlement" for our use case)
- `outcome_amount_range` (bucketed: "$0-$50k", "$50k-$100k", etc.)

### Metadata
- `source_url` (where we scraped from)
- `collected_at` (timestamp)
- `collector_notes` (notes about collection)
- `verification_status` (pending/verified/rejected)

## Potential Additional Fields to Consider

After reviewing the extracted cases, we may want to add:

1. **Case Date/Year** - When did the case occur? (already captured as `case_date` in scraper)
2. **Court Name** - Which specific court? (already captured as `court` in scraper)
3. **Case Citation** - Official case citation (already captured as `citation` in scraper)
4. **Settlement Date** - When was the settlement reached? (not currently captured)
5. **Attorney Fees** - Were attorney fees included in settlement? (not currently captured)
6. **Pre-existing Conditions** - Were there pre-existing conditions? (not currently captured)
7. **Comparative Negligence** - Was there comparative negligence? (not currently captured)
8. **Insurance Company** - Which insurance company was involved? (not currently captured - might be PHI)
9. **Settlement Structure** - Lump sum vs. structured settlement? (not currently captured)
10. **Mediation/Arbitration** - Was mediation or arbitration used? (not currently captured)

## Notes

- The scraper is configured to **skip non-settlement cases** automatically
- Rate limiting: 15-25 seconds between cases, 30-50 seconds every 5 cases
- CAPTCHA handling: Attempts extraction even if CAPTCHA is detected
- All cases must have `outcome_type = "Settlement"` to be useful for range queries

## Next Steps

1. ✅ Extract all 500 URLs (in progress)
2. ⏳ Process URLs with settlement filter
3. ⏳ Review extracted data
4. ⏳ Suggest additional fields if needed
5. ⏳ Prepare for database seeding
