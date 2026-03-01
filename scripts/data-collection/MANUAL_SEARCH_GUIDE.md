# Manual Search Guide - How to Search Without Case Numbers

## 🎯 The Problem

Both court systems seem to require specific case information:
- **Miami-Dade**: Needs Case Code + Year + Sequence Number
- **Los Angeles**: Multiple options but may require case numbers

## 📋 Manual Search Methods

### Los Angeles County - Using Calendar Search

**Step-by-Step:**

1. **Go to Access-a-Case Page:**
   - URL: https://www.lacourt.ca.gov/pages/lp/access-a-case

2. **Click "Search Court Calendars":**
   - This card allows searching by date range
   - May show case numbers and case types

3. **Enter Search Criteria:**
   - Date range (e.g., last 6 months)
   - Court location (if filter available)
   - Case type (if filter available)

4. **Review Results:**
   - Look for Personal Injury cases
   - Note case numbers
   - Check if settlement information is visible

5. **Get Case Details:**
   - Use case numbers to get full case information
   - Look for settlement amounts (may be redacted)

### Miami-Dade County - Finding Civil Search

**Step-by-Step:**

1. **Go to Main Clerk Page:**
   - URL: https://www2.miamidadeclerk.gov/

2. **Look for "Civil" Section:**
   - The `/cjis/` page is for CRIMINAL cases
   - Need to find CIVIL case search
   - Look in navigation menu for "Civil" or "Civil Cases"

3. **Explore Civil Search Options:**
   - May have different search methods
   - Could allow:
     - Search by case type
     - Browse recent cases
     - Date range search
     - Advanced search

4. **If Only Case Number Search Available:**
   - May need to use case number patterns
   - Example: Try common case codes for civil cases
   - Try different years and sequence ranges
   - This is time-consuming but may work

## 🔍 Alternative Approaches

### Approach 1: Use Case Number Patterns

**For Miami-Dade:**
- Research common case codes for personal injury
- Example: "CA" for Civil, "PI" for Personal Injury
- Try year 2023, then sequences 000001-999999
- Very time-consuming, may hit rate limits

### Approach 2: Browse Recent Filings

**Both Courts:**
- Some courts have "Recent Filings" sections
- May show new cases without requiring search
- Can browse and identify personal injury cases
- Extract case numbers from listings

### Approach 3: Use Third-Party Services

**Options:**
- LexisNexis CourtLink
- Westlaw Court Records
- CourtListener (free, limited)
- Justia (free case law)

### Approach 4: Manual Collection (Recommended)

**Best for Initial Collection:**

1. **Visit Court Websites Manually:**
   - Use calendar search (LA) or browse recent cases
   - Identify personal injury cases
   - Note case numbers

2. **Collect Case Details:**
   - Use case numbers to get full details
   - Extract settlement information
   - Note source URLs

3. **Structure Data:**
   - Use `manual-collection-template.json`
   - Fill in collected information
   - Include source URLs for verification

4. **Save Collection:**
   - Save as `manually_collected_cases.json`
   - Create verification report
   - Verify authenticity

## 🛠️ Using the Exploration Script

Run the exploration script to understand search methods:

```bash
python explore-search-methods.py
```

This will:
- Open browsers to both court sites
- Navigate to search pages
- Take screenshots
- Save HTML for analysis
- Help identify search form elements

## 📝 Collection Workflow

### For Los Angeles:

1. Go to: https://www.lacourt.ca.gov/pages/lp/access-a-case
2. Click: "Search Court Calendars"
3. Enter: Date range (e.g., last 6 months)
4. Review: Results for personal injury cases
5. Collect: Case numbers and details
6. Structure: Use template to organize data

### For Miami-Dade:

1. Go to: https://www2.miamidadeclerk.gov/
2. Find: "Civil" section (not Criminal)
3. Explore: Available search options
4. Collect: Cases using available method
5. Structure: Use template to organize data

## ✅ Next Steps

1. **Run Exploration Script:**
   ```bash
   python explore-search-methods.py
   ```

2. **Manually Test Search Methods:**
   - Try calendar search in LA
   - Find civil search in Miami
   - Note what works

3. **Update Collection Script:**
   - Once search methods are understood
   - Update `collect-court-records.py`
   - Test with small sample

4. **Start Manual Collection:**
   - Collect 5-10 sample cases
   - Verify the process
   - Then scale up

---

**Current Status**: Need to explore actual search functionality to determine best method.

