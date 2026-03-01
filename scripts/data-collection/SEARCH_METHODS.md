# Court Search Methods - How to Search Without Case Numbers

## 🎯 The Challenge

Both court systems require specific information to search:
- **Miami-Dade**: Needs Case Code + Year + Sequence Number
- **Los Angeles**: Has multiple search options but may require case numbers or names

## 📋 Solution: Alternative Search Methods

### Miami-Dade County, FL

**Current Issue:**
- The `/cjis/` page requires specific case numbers (Case Code + Year + Sequence)
- We don't have case numbers to search with
- This is the CRIMINAL search - we need CIVIL search

**What We Need to Find:**

1. **Civil Case Search URL:**
   - The `/cjis/` is for criminal cases
   - Need to find: Civil case search page
   - Look for: "Civil" in navigation menu
   - Alternative URL might be: `/civil/` or `/casesearch/` or similar

2. **Search by Case Type (if available):**
   - Some systems allow searching by case type
   - Look for: "Personal Injury" or "Motor Vehicle" filters
   - May allow date range searches

3. **Alternative: Use Case Number Patterns:**
   - If we can find case number patterns for personal injury
   - Example: Case Code "CA" for Civil, year 2023, then search sequences
   - This would require trial and error

**Steps to Find Civil Search:**

1. Visit: https://www2.miamidadeclerk.gov/
2. Look for navigation menu
3. Find "Civil" section (not "Criminal")
4. Look for case search functionality
5. Check if it allows:
   - Search by case type
   - Search by date range
   - Browse recent cases
   - Advanced search options

### Los Angeles County, CA

**Current Page:** https://www.lacourt.ca.gov/pages/lp/access-a-case

**Available Options:**

1. **"Find Case Information"** - Requires case number
   - ❌ Not useful - we don't have case numbers

2. **"Search For Case by Name"** - Requires person's name
   - ❌ Not useful - violates privacy, we can't use names

3. **"Search Court Calendars"** - Can search by date range
   - ✅ **POTENTIALLY USEFUL** - May show cases by date
   - Can filter by case type or court location
   - May show case numbers we can then look up

4. **"Access Court Documents"** - Requires case number
   - ❌ Not useful initially

**Recommended Approach for LA:**

1. **Use "Search Court Calendars":**
   - Click on "Search Court Calendars" card
   - Enter date range (e.g., last 6 months)
   - Filter by case type if available
   - This may show case numbers and case types
   - Then use those case numbers to get details

2. **Alternative: Browse Recent Filings:**
   - Some courts have "Recent Filings" or "New Cases" sections
   - May show case numbers without requiring search

## 🔍 Updated Collection Strategy

### Strategy 1: Calendar-Based Search (Los Angeles)

1. Use "Search Court Calendars" with date ranges
2. Extract case numbers from calendar results
3. Use case numbers to get case details
4. Filter for personal injury cases
5. Extract settlement information if available

### Strategy 2: Find Civil Search (Miami-Dade)

1. Navigate to Civil section (not Criminal)
2. Look for search options that don't require specific case numbers
3. May need to:
   - Browse recent cases
   - Search by case type
   - Use date range filters

### Strategy 3: Manual Collection (Recommended Initially)

1. **For Los Angeles:**
   - Use "Search Court Calendars"
   - Browse by date range
   - Manually identify personal injury cases
   - Collect case numbers and details

2. **For Miami-Dade:**
   - Find Civil case search
   - Browse or search by case type
   - Manually collect cases

3. **Structure Data:**
   - Use `manual-collection-template.json`
   - Include source URLs
   - Save as `manually_collected_cases.json`

## 🛠️ Script Updates Needed

Once we understand the search methods, update:

1. **`collect-court-records.py`:**
   - Add calendar search method for LA
   - Add case type search for Miami (once found)
   - Handle case number extraction from calendars
   - Then fetch case details using case numbers

2. **Search Flow:**
   ```
   Step 1: Search Calendar/Recent Cases
   Step 2: Extract Case Numbers
   Step 3: Filter for Personal Injury
   Step 4: Fetch Case Details
   Step 5: Extract Settlement Data
   Step 6: Anonymize and Store
   ```

## 📝 Next Steps

1. **For Los Angeles:**
   - Click "Search Court Calendars"
   - Test date range search
   - See what information is available
   - Note the URL and form structure

2. **For Miami-Dade:**
   - Find Civil case search page
   - Test search options
   - See if case type or date range search is available
   - Note the URL and form structure

3. **Update Scripts:**
   - Once search methods are understood
   - Update collection script
   - Test with small sample

---

**Current Status**: Need to explore actual search functionality on both sites to determine the best collection method.

