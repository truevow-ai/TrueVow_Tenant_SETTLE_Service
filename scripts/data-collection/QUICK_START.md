# Quick Start Guide - Court Records Data Collection

## 🚀 Quick Setup (5 minutes)

### Step 1: Install Dependencies

```bash
cd scripts/data-collection
pip install -r requirements.txt
playwright install chromium
```

### Step 2: Configure Database

Create `.env` file:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/settle_db
```

### Step 3: Manual Data Collection (Recommended First)

Since court websites require specific selectors, start with **manual collection**:

1. **Visit Court Websites:**
   - Miami-Dade: https://www2.miami-dadeclerk.com/cjis/
   - Los Angeles: https://www.lacourt.org/casesummary/ui/

2. **Search for Personal Injury Cases:**
   - Use case type filters
   - Look for settled cases
   - Note settlement amounts (if public)

3. **Create Sample Data File:**

Create `sample_cases.json`:
```json
[
  {
    "jurisdiction": "Miami-Dade County, FL",
    "case_type": "Motor Vehicle Accident",
    "injury_category": ["Spinal Injury"],
    "medical_bills": 45000.0,
    "defendant_category": "Unknown",
    "outcome_type": "Settlement",
    "outcome_amount_range": "$50k-$100k",
    "filing_year": 2023
  },
  {
    "jurisdiction": "Los Angeles County, CA",
    "case_type": "Slip and Fall",
    "injury_category": ["Soft Tissue Injury"],
    "medical_bills": 25000.0,
    "defendant_category": "Business",
    "outcome_type": "Settlement",
    "outcome_amount_range": "$50k-$100k",
    "filing_year": 2023
  }
]
```

### Step 4: Seed Database

```bash
python seed-database.py --file sample_cases.json --verify
```

## 📋 Next Steps

### Option A: Manual Collection (Safest)

1. Collect 20-50 cases manually from court websites
2. Create JSON file with anonymized data
3. Review data for any PHI/PII
4. Seed database
5. Verify results

### Option B: Automated Collection (After Manual Verification)

1. Update `collect-court-records.py` with actual website selectors
2. Test with small batch (10 cases)
3. Verify anonymization
4. Scale up gradually

### Option C: Third-Party Data (Recommended for Scale)

1. Research legal data providers (LexisNexis, Westlaw)
2. Purchase aggregated settlement databases
3. Import and anonymize
4. Seed database

## ✅ Verification Checklist

Before seeding, ensure:
- [ ] No names in data
- [ ] No addresses
- [ ] No SSNs
- [ ] No specific dates (only years)
- [ ] All amounts bucketed
- [ ] All categories generic
- [ ] Data matches SETTLE schema

## 🎯 Target Data Volume

- **Initial Seed:** 100-200 cases per jurisdiction
- **Ongoing:** 50-100 cases per month
- **Total Goal:** 1,000+ cases for meaningful statistics

## 📞 Need Help?

1. Check `README.md` for detailed documentation
2. Review `court-records-research.md` for website research
3. Test with sample data first
4. Start small, scale gradually

