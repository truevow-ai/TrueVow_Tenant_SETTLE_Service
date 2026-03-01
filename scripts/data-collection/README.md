# Court Records Data Collection & Database Seeding

## Overview

This system collects publicly available court records from Miami-Dade County, FL and Los Angeles County, CA, anonymizes all data to remove PHI/PII, and seeds the SETTLE database with initial settlement data.

## ⚠️ Important Legal & Compliance Notes

1. **Public Records Only**: Only collects publicly available court records
2. **Anonymization Required**: All PHI/PII is removed before storage
3. **Rate Limiting**: Respects website rate limits and Terms of Service
4. **Compliance**: Follows HIPAA and bar compliance requirements
5. **No Identifying Information**: No names, addresses, SSNs, or specific dates stored

## Setup

### 1. Install Dependencies

```bash
pip install playwright asyncpg python-dotenv aiohttp
playwright install chromium
```

### 2. Configure Environment

Create `.env` file:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/settle_db
```

### 3. Research Court Websites

Before running, you need to:
1. Visit the court websites manually
2. Identify the correct selectors for case search
3. Verify data availability
4. Check Terms of Service

**Miami-Dade County:**
- URL: https://www2.miami-dadeclerk.com/cjis/
- Manual research needed to identify selectors

**Los Angeles County:**
- URL: https://www.lacourt.org/casesummary/ui/
- Manual research needed to identify selectors

## Usage

### Step 1: Collect Court Records

```bash
cd scripts/data-collection
python collect-court-records.py
```

This will:
- Search for personal injury cases
- Extract anonymized data
- Export to `collected_cases.json` and `collected_cases.sql`

### Step 2: Review Collected Data

```bash
# Review the JSON file
cat collected_cases.json

# Verify anonymization
# Ensure no PHI/PII is present
```

### Step 3: Seed Database

```bash
python seed-database.py --file collected_cases.json --verify
```

This will:
- Insert cases into `settle_contributions` table
- Verify the seeding
- Show statistics

## Data Collection Strategy

### Manual Collection (Recommended for Initial)

1. **Start Small**: Collect 10-20 sample cases manually
2. **Verify Structure**: Ensure data matches SETTLE schema
3. **Test Anonymization**: Verify no PHI/PII leaks through
4. **Scale Up**: Once verified, increase collection volume

### Semi-Automated Collection

1. **Browser Automation**: Use Playwright to automate searches
2. **Rate Limiting**: Add delays between requests (2-5 seconds)
3. **Error Handling**: Handle timeouts, network errors gracefully
4. **Respect ToS**: Check and comply with Terms of Service

### Alternative: Third-Party Data Sources

Consider using:
- **LexisNexis**: Legal research database
- **Westlaw**: Legal research database
- **Court Data APIs**: If available from courts
- **Legal Data Providers**: Specialized settlement databases

## Data Anonymization Process

### What Gets Removed:
- ❌ Names (plaintiff, defendant, attorneys)
- ❌ Addresses
- ❌ Social Security Numbers
- ❌ Dates of birth
- ❌ Specific dates (only year kept)
- ❌ Case numbers (can be identifying)
- ❌ Any other identifying information

### What Gets Kept (Anonymized):
- ✅ Case type (generic categories)
- ✅ Jurisdiction (county/state only)
- ✅ Filing year (year only, no specific date)
- ✅ Settlement range (bucketed amounts)
- ✅ Injury category (generic categories)
- ✅ Outcome type (Settlement, Judgment, etc.)

## Example Data Structure

```json
{
  "jurisdiction": "Miami-Dade County, FL",
  "case_type": "Motor Vehicle Accident",
  "injury_category": ["Spinal Injury", "Soft Tissue Injury"],
  "medical_bills": 0.0,
  "defendant_category": "Unknown",
  "outcome_type": "Settlement",
  "outcome_amount_range": "$50k-$100k",
  "filing_year": 2023
}
```

## Verification Checklist

Before seeding database, verify:

- [ ] No names in data
- [ ] No addresses in data
- [ ] No SSNs in data
- [ ] No specific dates (only years)
- [ ] All amounts are bucketed
- [ ] All categories are generic
- [ ] Data matches SETTLE schema
- [ ] Consent confirmed for all records
- [ ] Status set to 'approved' (public records)

## Troubleshooting

### No Cases Collected

1. **Check Website Access**: Verify websites are accessible
2. **Update Selectors**: Court websites may have changed
3. **Check Rate Limits**: May be blocked, add longer delays
4. **Verify Search Terms**: Ensure correct case type search

### Database Connection Errors

1. **Check DATABASE_URL**: Verify connection string
2. **Check Database Status**: Ensure PostgreSQL is running
3. **Check Permissions**: Verify database user has INSERT permissions

### Anonymization Issues

1. **Review Data**: Manually check collected data
2. **Update Filters**: Add more aggressive anonymization
3. **Remove Suspicious Records**: Delete any with potential PHI/PII

## Next Steps

1. **Manual Collection**: Start with 20-50 cases manually
2. **Verify Process**: Test anonymization and seeding
3. **Scale Up**: Once verified, increase collection volume
4. **Monitor**: Regularly check for data quality issues
5. **Update**: Keep selectors updated as websites change

## Legal Disclaimer

This tool is for collecting publicly available court records only. Users are responsible for:
- Complying with all applicable laws
- Respecting website Terms of Service
- Ensuring proper data anonymization
- Maintaining bar compliance
- Following HIPAA requirements (if applicable)

