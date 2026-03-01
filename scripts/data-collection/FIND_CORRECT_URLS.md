# Finding Correct Court URLs for Data Collection

## 🎯 Goal

Find the correct URLs for searching **CIVIL/PERSONAL INJURY** cases (not criminal) in:
- Miami-Dade County, FL
- Los Angeles County, CA

## 📋 Step-by-Step Guide

### Miami-Dade County, FL

**Current URL (Criminal):** https://www2.miamidadeclerk.gov/cjis/

**Steps to Find Civil Case Search:**

1. Visit: https://www2.miamidadeclerk.gov/
2. Look for navigation menu items like:
   - "Civil"
   - "Civil Cases"
   - "Case Search"
   - "Online Services"
3. Click through to find civil case search
4. Note the URL path (e.g., `/civil/`, `/casesearch/`, etc.)
5. Test the search functionality

**What to Look For:**
- Search by case number
- Search by party name (we won't use this - privacy)
- Search by case type
- Filter by date range
- View case details

### Los Angeles County, CA

**Current URL (404):** https://www.lacourt.org/casesummary/ui/

**Steps to Find Correct URL:**

1. Visit: https://www.lacourt.org/
2. Look for:
   - "Case Search"
   - "Online Services"
   - "Case Information"
   - "Public Access"
3. Find civil case search functionality
4. Note the correct URL path
5. Test the search functionality

**What to Look For:**
- Case search interface
- Civil case search (not criminal)
- Case type filters
- Date range filters

## 🔍 What We Need

For each jurisdiction, we need:

1. **Base URL** - The main court website
2. **Search URL** - The URL for searching cases
3. **Search Form Selectors** - HTML elements for:
   - Case type dropdown/input
   - Date range inputs
   - Search button
4. **Results Page Selectors** - HTML elements for:
   - Case list/table
   - Case details links
   - Pagination (if any)

## 📝 Once URLs Are Found

1. **Update Documentation:**
   - `court-records-research.md`
   - `CORRECTED_URLS.md`
   - `COLLECTION_INSTRUCTIONS.md`

2. **Update Collection Script:**
   - `collect-court-records.py`
   - Add correct URLs
   - Add correct selectors

3. **Test Collection:**
   - Run with small sample (5-10 cases)
   - Verify data structure
   - Verify source URLs work

## 🚀 Quick Test

Once you find the URLs, test them:

1. Open the URL in browser
2. Try searching for "Personal Injury" or "Motor Vehicle" cases
3. See if results appear
4. Check if settlement amounts are visible (may be redacted)
5. Note the URL structure for case detail pages

## 💡 Tips

- **Look for "Civil" not "Criminal"** - We need civil cases
- **Check for "Public Access"** - Some courts have separate public vs. registered access
- **Note URL patterns** - Case detail URLs often follow patterns like `/case/12345` or `/casesummary?id=12345`
- **Check robots.txt** - Some courts may restrict automated access

---

**Next Step**: Visit both court websites and find the correct civil case search URLs.

