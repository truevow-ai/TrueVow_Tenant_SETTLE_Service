# Casemine.com Scraper Guide

## Overview

This scraper extracts real legal case data from Casemine.com for populating the SETTLE database. It searches for cases using keywords, extracts detailed information, and saves it in a format ready for verification and database seeding.

## Features

- ✅ Searches Casemine.com with customizable keywords
- ✅ Extracts case details (jurisdiction, case type, injuries, outcomes)
- ✅ Focuses on latest cases first
- ✅ Maps data to SETTLE database schema
- ✅ Preserves source URLs for verification
- ✅ Handles rate limiting and errors gracefully

## Quick Start

### Option 1: PowerShell Script (Recommended)

```powershell
# Basic usage (default search terms)
.\run-casemine-scraper.ps1

# Custom search terms
.\run-casemine-scraper.ps1 -SearchTerms "car accident", "motor vehicle" -MaxCases 30

# With jurisdiction filter
.\run-casemine-scraper.ps1 -SearchTerms "personal injury" -Jurisdiction "Miami-Dade" -MaxCases 20

# Show browser (for debugging)
.\run-casemine-scraper.ps1 -ShowBrowser
```

### Option 2: Direct Python

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run scraper
python scrape-casemine.py --search "car accident" "personal injury" --max-cases 50

# With jurisdiction filter
python scrape-casemine.py --search "slip and fall" --jurisdiction "Los Angeles" --max-cases 30
```

## Search Terms

Recommended search terms for SETTLE database:

### Personal Injury Cases
- `"car accident"`
- `"motor vehicle accident"`
- `"personal injury settlement"`
- `"slip and fall"`
- `"premises liability"`
- `"wrongful death"`

### Case Types
- `"medical malpractice"`
- `"product liability"`
- `"workplace injury"`

### Combined Searches
- `"car accident settlement"`
- `"personal injury verdict"`
- `"injury case outcome"`

## Output

The scraper creates `casemine_cases.json` with the following structure:

```json
[
  {
    "source_url": "https://www.casemine.com/judgments/...",
    "case_name": "SMITH v. JONES",
    "jurisdiction": "Miami-Dade County, FL",
    "court": "Supreme Court of Florida",
    "case_date": "June 18, 2004",
    "case_type": "Motor Vehicle Accident",
    "injury_category": ["Spinal Injury", "Fracture"],
    "primary_diagnosis": null,
    "treatment_type": ["Surgery", "Physical Therapy"],
    "duration_of_treatment": null,
    "imaging_findings": ["Fracture", "Herniated Disc"],
    "medical_bills": 50000.0,
    "lost_wages": null,
    "policy_limits": null,
    "defendant_category": "Individual",
    "outcome_type": "Settlement",
    "outcome_amount_range": "$50k-$100k",
    "citation": "254 P.3d 1054",
    "collected_at": "2025-01-XX...",
    "collector_notes": "Scraped from Casemine.com",
    "verification_status": "pending"
  }
]
```

## Data Mapping

The scraper automatically maps Casemine data to SETTLE schema:

| Casemine Field | SETTLE Field | Notes |
|---------------|--------------|-------|
| Court/Jurisdiction | `jurisdiction` | Extracted from case text |
| Case Type | `case_type` | Inferred from content |
| Injuries Mentioned | `injury_category[]` | Array of injury types |
| Treatment Mentioned | `treatment_type[]` | Array of treatments |
| Settlement/Verdict Amount | `outcome_amount_range` | Bucketed into ranges |
| Medical Costs | `medical_bills` | Extracted if mentioned |
| Defendant Type | `defendant_category` | Inferred from text |

## Verification Workflow

1. **Collect Cases**
   ```bash
   python scrape-casemine.py --search "car accident" --max-cases 50
   ```

2. **Review Collected Data**
   - Open `casemine_cases.json`
   - Verify source URLs are accessible
   - Check that extracted data matches source

3. **Prepare for Seeding**
   ```bash
   python prepare-for-seeding.py casemine_cases.json verified_cases.json
   ```

4. **Seed Database**
   ```bash
   python seed-via-supabase-client.py verified_cases.json
   ```

## Important Notes

### Data Quality
- The scraper extracts information from case text, which may be incomplete
- Some fields may be `null` if not mentioned in the case
- Always verify extracted data against source URLs

### Rate Limiting
- The scraper includes 2-second delays between requests
- Casemine.com may have rate limits - adjust if needed
- Use `--headless false` to monitor browser activity

### Latest Cases First
- The scraper attempts to sort by "Recent" when available
- If sorting fails, it collects cases in order found
- Focus on recent cases for better data quality

### Jurisdiction Filtering
- Use `--jurisdiction` to filter by location
- Examples: "Miami-Dade", "Los Angeles", "California"
- Filtering happens at search level, not extraction level

## Troubleshooting

### No Cases Found
- Check search terms are valid
- Try broader search terms
- Verify Casemine.com is accessible
- Check browser console for errors (use `--headless false`)

### Incomplete Data
- Some cases may not have all fields
- This is normal - fields are optional in SETTLE schema
- Review source URLs to verify accuracy

### Timeout Errors
- Increase timeout values in script if needed
- Check internet connection
- Casemine.com may be slow - be patient

### Browser Issues
- Run `playwright install chromium` to ensure browser is installed
- Try `--headless false` to see what's happening
- Check Playwright version: `playwright --version`

## Example Commands

```bash
# Collect 30 car accident cases from Miami
python scrape-casemine.py --search "car accident" --jurisdiction "Miami-Dade" --max-cases 30

# Collect personal injury settlements
python scrape-casemine.py --search "personal injury settlement" --max-cases 50

# Collect slip and fall cases from Los Angeles
python scrape-casemine.py --search "slip and fall" --jurisdiction "Los Angeles" --max-cases 25

# Multiple search terms
python scrape-casemine.py --search "car accident" "motor vehicle" "auto accident" --max-cases 50
```

## Next Steps

After collecting cases:

1. **Verify Data**: Review `casemine_cases.json` and check source URLs
2. **Prepare**: Run `prepare-for-seeding.py` to format for database
3. **Seed**: Run `seed-via-supabase-client.py` to populate database
4. **Test**: Use SETTLE reporting function to test with real data

---

**Remember**: Only real, verifiable cases should be inserted into the database. Always verify source URLs and extracted data before seeding.

