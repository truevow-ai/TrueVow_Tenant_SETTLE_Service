# Field Addition Recommendation - Conservative Approach

## Core Principle
**Only add fields that are:**
1. **Essential** for accurate settlement range queries
2. **Reasonably available** to attorneys (not hard to find/remember)
3. **Non-sensitive** (won't discourage contributions)

## Current Query Parameters (What Attorneys Search By)
- `injury_type` → Maps to `injury_category` ✅
- `state` / `county` → Maps to `jurisdiction` ✅
- `medical_bills` → Maps to `medical_bills` ✅

**Conclusion: Current schema already supports all core search functionality.**

## Analysis of Suggested Additional Fields

### ❌ **DO NOT ADD** (Not Essential for Core Functionality)

1. **Settlement Date** - Not used in queries, only for temporal analysis (nice-to-have)
2. **Attorney Fees** - Sensitive information, attorneys may not want to share
3. **Settlement Structure** (lump sum vs. structured) - Doesn't affect range queries
4. **Mediation/Arbitration** - Process detail, not outcome detail
5. **Insurance Company** - Could be PHI, too sensitive

### ⚠️ **CONSIDER CAREFULLY** (Only if Data Shows They Significantly Impact Settlement Amounts)

1. **Comparative Negligence** - Could significantly affect settlement amount
   - **Question**: Do we have data showing this materially changes settlement ranges?
   - **Risk**: Adds friction to contribution form
   - **Recommendation**: **Wait** - Only add if analysis of collected data shows clear correlation

2. **Pre-existing Conditions** - Could affect settlement amount
   - **Question**: Do we have data showing this materially changes settlement ranges?
   - **Risk**: Adds friction, might be hard for attorneys to determine
   - **Recommendation**: **Wait** - Only add if analysis of collected data shows clear correlation

## Recommendation: **KEEP CURRENT SCHEMA AS-IS**

### Why?
1. ✅ All core query functionality is already supported
2. ✅ Current fields are easy for attorneys to provide
3. ✅ No friction that would discourage contributions
4. ✅ Can always add fields later if data analysis shows they're needed

### When to Revisit?
After collecting **substantial data** (500+ cases), analyze:
- Do cases with comparative negligence have significantly different settlement ranges?
- Do cases with pre-existing conditions have significantly different settlement ranges?
- Are attorneys asking for these filters in their queries?

**Only then** consider adding fields if:
- Data shows clear correlation with settlement amounts
- Attorneys are requesting these filters
- The value outweighs the friction

## Current Fields Are Sufficient For:
- ✅ Accurate settlement range queries
- ✅ Filtering by injury type, location, medical bills
- ✅ Providing percentile ranges (25th, median, 75th, 95th)
- ✅ Bar-compliant (zero PHI)

## Bottom Line
**Don't add fields until we have data proving they're essential.** The current schema is well-designed and sufficient for the core value proposition.
