# Browser Exploration Findings

**Date:** January 6, 2026  
**Status:** ✅ **URLs and Search Methods Identified**

---

## 🎯 Key Findings

### Miami-Dade County, FL

**Civil Case Search URL Found:**
- ✅ **URL:** https://www.miamidadeclerk.gov/clerk/civil/caseSearch.page
- ✅ **Navigation Path:** Home → CIVIL, FAMILY COURT & MARRIAGE → Search for Cases

**Search Method:**
- The page appears to require case number search
- Need to explore if there are alternative search methods (date range, case type, etc.)
- May require registration/login for advanced search

**Next Steps:**
1. Navigate to: https://www.miamidadeclerk.gov/clerk/civil/caseSearch.page
2. Check for:
   - Date range search options
   - Case type filters
   - Browse recent cases option
   - Advanced search features

### Los Angeles County, CA

**Access-a-Case Page:**
- ✅ **URL:** https://www.lacourt.ca.gov/pages/lp/access-a-case
- ✅ **Multiple Search Options Available**

**Available Search Methods:**

1. **"Find Case Information"**
   - Requires: Case number
   - ❌ Not useful without case numbers

2. **"Search For Case by Name"**
   - Requires: Person's name
   - ❌ Privacy violation - cannot use

3. **"Search Court Calendars"** ⭐ **POTENTIALLY USEFUL**
   - Can search by: Date range
   - May show: Case numbers, case types, hearing dates
   - ✅ **RECOMMENDED APPROACH**

4. **"Access Court Documents"**
   - Requires: Case number
   - ❌ Not useful initially

**Recommended Approach for LA:**
1. Use "Search Court Calendars"
2. Enter date range (e.g., last 6 months)
3. Filter by case type if available
4. Extract case numbers from calendar results
5. Use case numbers to get case details

---

## 📋 Updated Collection Strategy

### Strategy 1: Calendar-Based Collection (Los Angeles)

**Steps:**
1. Navigate to: https://www.lacourt.ca.gov/pages/lp/access-a-case
2. Click: "Search Court Calendars"
3. Enter: Date range (e.g., January 2023 - December 2023)
4. Review: Calendar results
5. Extract: Case numbers and case types
6. Filter: Personal injury cases
7. Fetch: Case details using case numbers
8. Extract: Settlement information (if available)

### Strategy 2: Case Number Pattern Search (Miami-Dade)

**Steps:**
1. Navigate to: https://www.miamidadeclerk.gov/clerk/civil/caseSearch.page
2. Research: Common case codes for personal injury
   - May be: "CA" (Civil), "PI" (Personal Injury), etc.
3. Try: Different case code + year combinations
4. Extract: Case numbers from results
5. Fetch: Case details
6. Extract: Settlement information

**Alternative for Miami:**
- Check if there's a "Browse Recent Cases" option
- Check if there's a date range search
- Check if registration provides additional search options

---

## 🔍 What We Still Need to Determine

### Miami-Dade:
- [ ] Does the search page allow date range search?
- [ ] Are there case type filters?
- [ ] What are the case codes for personal injury?
- [ ] Is there a "browse recent cases" option?
- [ ] Does registration unlock additional search methods?

### Los Angeles:
- [ ] What does "Search Court Calendars" actually show?
- [ ] Can we filter by case type in calendar search?
- [ ] What information is available in calendar results?
- [ ] How to get case details from case numbers?

---

## 🛠️ Next Steps

### Immediate Actions:

1. **Test Los Angeles Calendar Search:**
   - Manually click "Search Court Calendars"
   - Test date range search
   - See what results are returned
   - Note the URL and form structure

2. **Test Miami-Dade Civil Search:**
   - Navigate to civil search page
   - Check all available search options
   - Test if date range or case type search is available
   - Note the form structure

3. **Update Collection Scripts:**
   - Once search methods are confirmed
   - Update `collect-court-records.py` with actual selectors
   - Test with small sample

### Recommended Approach:

**Start with Manual Collection:**
1. Use calendar search in LA to find case numbers
2. Use case numbers to get case details
3. Collect 5-10 sample cases manually
4. Verify the data structure
5. Then automate the process

---

## 📝 URLs Confirmed

### Miami-Dade County:
- **Main Page:** https://www.miamidadeclerk.gov/clerk/home.page
- **Civil Search:** https://www.miamidadeclerk.gov/clerk/civil/caseSearch.page

### Los Angeles County:
- **Access-a-Case:** https://www.lacourt.ca.gov/pages/lp/access-a-case
- **Calendar Search:** (Need to click through to get actual URL)

---

**Status:** ✅ **URLs Found - Need to Test Actual Search Functionality**

