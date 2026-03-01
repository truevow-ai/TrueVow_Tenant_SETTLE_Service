# Public Court Records Access - Miami & Los Angeles

## Research Summary

### Miami-Dade County, Florida

**Primary Sources:**
1. **Miami-Dade Clerk of Courts** - Online Case Search
   - URL: https://www2.miamidadeclerk.gov/cjis/ (Note: Correct URL is .gov not .com)
   - Access: Public, free
   - **IMPORTANT**: The /cjis/ path is for CRIMINAL cases. We need CIVIL case search for personal injury.
   - Need to find: Civil case search URL/path
   - Data Available: Case numbers, case types, filing dates, case status, judgments
   - Limitations: Settlement amounts may not be publicly disclosed in all cases

2. **Florida Courts E-Filing Portal**
   - URL: https://www.myflcourtaccess.com/
   - Access: Public records search
   - Data Available: Case information, docket entries, final judgments

3. **Florida State Courts System**
   - URL: https://www.flcourts.org/
   - Access: Public case search
   - Data Available: Appellate court decisions with settlement information

**Data Collection Strategy:**
- Focus on personal injury cases (Motor Vehicle, Slip & Fall, etc.)
- Extract case type, jurisdiction, filing date
- Look for final judgments or settlement orders
- Anonymize all data (no names, addresses, SSNs)

### Los Angeles County, California

**Primary Sources:**
1. **LA County Superior Court - Case Search**
   - URL: https://www.lacourt.org/ (Note: /casesummary/ui/ path may not exist - need to find correct civil case search)
   - Access: Public, free
   - Data Available: Case information, case types, filing dates, case status
   - Limitations: Settlement amounts often confidential
   - **Note**: The /casesummary/ui/ path returns 404. Need to find correct civil case search URL.

2. **California Courts Online**
   - URL: https://www.courts.ca.gov/
   - Access: Public case search
   - Data Available: Case filings, judgments, appellate decisions

3. **PACER (Federal Cases)**
   - URL: https://pacer.uscourts.gov/
   - Access: Requires account, minimal fees
   - Data Available: Federal court records, some settlement information

**Data Collection Strategy:**
- Focus on personal injury cases in state courts
- Extract case type, jurisdiction, dates
- Look for public judgments (settlement amounts may be redacted)
- Anonymize all data

### Important Legal Considerations

1. **Public Records Laws:**
   - Both Florida and California have strong public records laws
   - Court filings are generally public records
   - Settlement amounts may be confidential in some cases

2. **Data Privacy:**
   - Must remove all PHI/PII (names, addresses, SSNs, dates of birth)
   - Only aggregate/anonymized data should be stored
   - Comply with HIPAA if medical information is involved

3. **Terms of Service:**
   - Check each website's Terms of Service
   - Some may prohibit automated scraping
   - May require manual data entry or API access

4. **Rate Limiting:**
   - Respect website rate limits
   - Use delays between requests
   - Consider using official APIs if available

### Recommended Approach

1. **Manual Data Collection (Initial):**
   - Start with manual collection of sample cases
   - Verify data structure and availability
   - Test anonymization process

2. **Semi-Automated Collection:**
   - Use browser automation (Playwright/Selenium) with delays
   - Implement proper error handling
   - Respect robots.txt and rate limits

3. **API Access (If Available):**
   - Check for official court APIs
   - May require registration or fees
   - More reliable and compliant

4. **Third-Party Services:**
   - Consider legal data providers (LexisNexis, Westlaw)
   - May have aggregated settlement databases
   - Cost-effective for bulk data

### Data Fields to Extract (Anonymized)

- Case Type (e.g., "Motor Vehicle Accident", "Slip and Fall")
- Jurisdiction (e.g., "Miami-Dade County, FL", "Los Angeles County, CA")
- Filing Date (year only, no specific dates)
- Case Status (e.g., "Settled", "Judgment")
- Settlement Range (if publicly available, bucketed)
- Injury Type (if mentioned in public records, generic categories only)
- Medical Bills Range (if available, bucketed)
- Outcome Type (Settlement, Jury Verdict, etc.)

### Anonymization Requirements

- ❌ NO names (plaintiff, defendant, attorneys)
- ❌ NO addresses
- ❌ NO dates of birth
- ❌ NO Social Security Numbers
- ❌ NO specific dates (only year)
- ❌ NO case numbers (can be identifying)
- ✅ Only generic categories and bucketed amounts
- ✅ Only aggregate data

