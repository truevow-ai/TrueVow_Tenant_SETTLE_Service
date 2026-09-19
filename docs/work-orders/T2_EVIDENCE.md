# T2 — Privacy Acceptance / PHI Coverage Hardening

**Ticket:** T2 (SETTLE-CONTRIB-TO-TICKETS)
**Status:** PASS
**Date:** 2026-08-31

---

## Method

Inspected callers, acceptance path, and existing privacy/no-fabrication authorities. No database change, no migration, no schema change. Read-only evidence gathering.

## Verdict

T2_STATUS = PASS

---

## 1. Caller Audit — sanitize_text()

**Finding: zero production callers.**

Search of entire repository (excluding `.venv`, `node_modules`, `site-packages`, `__pycache__`):

| File | Role |
|---|---|
| `app/services/anonymizer.py` | Definition only (`sanitize_text` method, line 263) |
| `tests/test_anonymizer.py` | Test only (`test_sanitize_text`, line 183) |

No production code, endpoint, or service imports or calls `sanitize_text()`.

**Classification:**

| Caller | Classification |
|---|---|
| `app/services/anonymizer.py` | DEFINITION (not a caller) |
| `tests/test_anonymizer.py` | TEST (legitimate non-authoritative use) |
| All production code | NONE — DEAD / UNUSED on acceptance path |

**SANITIZE_TEXT_ON_AUTHORITATIVE_ACCEPT_PATH = NO**

The acceptance path does not use `sanitize_text()` at all. It uses `AnonymizationValidator.validate_contribution()`, which rejects.

---

## 2. Acceptance Path Analysis

**Flow:** `POST /submit` (`contribute.py:29`) → `ContributionService.submit_contribution()` (`contributor.py:61`) → Step 1 `DataValidator.validate_contribution()` → Step 2 `AnonymizationValidator.validate_contribution()` (`contributor.py:89`) → **returns (is_valid, violations)** → if not valid, returns `(False, None, error_msg)` → endpoint raises `HTTPException(status_code=400)`.

**Behavior:** REJECTS. Never sanitizes. Never persists. Deterministic 400 failure.

**SILENT_SANITIZE_AND_ACCEPT = IMPOSSIBLE**

There is no code path where:
1. prohibited input reaches the acceptance path
2. is silently sanitized/redacted
3. the transformed value is treated as trustworthy evidence
4. is persisted

The `sanitize_text()` method itself documents this: "In production, this should REJECT the submission, not sanitize. Sanitization is only for legacy data cleanup." (`anonymizer.py:267-268`)

---

## 3. PHI / Identifier Coverage

**Existing gate: `AnonymizationValidator` (`anonymizer.py`)**

| Category | Pattern | Detection |
|---|---|---|
| SSN | `\d{3}-\d{2}-\d{4}` or `\d{9}` | YES |
| Phone | `\d{3}[-.]?\d{3}[-.]?\d{4}` | YES |
| Email | standard email regex | YES |
| DOB | date format | YES |
| Case number | `case #?\d+` | YES |
| MRN | `MRN:?\d+` | YES |
| Address | street address patterns | YES |
| Person names | COMMON_NAMES list (40+ names) | YES |
| Business identifiers | `#\d+` store numbers | YES |
| Liability language | 12 forbidden phrases | YES |

Drop-down validation enforces: case_type, defendant_category, outcome_type, outcome_amount_range, jurisdiction format, consent_confirmed, financial reasonableness.

**Existing gate: `no_fabrication_gate.py`**

Verifies every field against verbatim source evidence. Unverified fields are STRIPPED (popped from record). Records with no verifiable identity are rejected.

**Existing gate: `verdict_validator.py`**

Maps enums to canonical vocabulary. Unmappable enum values are hard reject (never guessed into wrong bucket). Provenance (source_url) and minimal identity required.

**PHI_COVERAGE = PARTIAL**

Core identifiers (SSN, phone, email, names, addresses, MRN, case numbers, business identifiers) are covered. Coverage is not exhaustive of every possible PHI category under all privacy policies — but the canonical privacy policy is not defined as a standalone repository file. **Governance dependency:** the TrueVow privacy policy canonical definition needs to be located/established before coverage can be declared complete. The existing gates cover the categories represented in the accepted specification and the anonymizer's own FORBIDDEN_PATTERNS.

---

## 4. STRIPPED Analytics Suppression

**`no_fabrication_gate.py` (`verify_record`):**
- Unverified fields are popped from `out` (the record) — they do not survive
- `stripped` dict records field + reason
- Records with no verifiable identity are rejected entirely
- STRIPPED values cannot become analytics-relevant facts

**`verdict_validator.py`:**
- Unmappable enum values are hard reject
- Unparseable dates are dropped with warning (not persisted as fabricated)

**STRIPPED_ANALYTICS_SUPPRESSION = PASS**

---

## 5. Existing Authorities Preserved

| Authority | Status |
|---|---|
| `no_fabrication_gate.py` | PRESERVED |
| `verdict_validator.py` | PRESERVED |
| `AnonymizationValidator` | PRESERVED |
| `DataValidator` | PRESERVED |

No replacement. No duplicate authority (no PrivacyGateV2). Bounded hardening only if repository evidence proves a gap.

**NO_FABRICATION_GATE = PRESERVED**
**VERDICT_VALIDATOR = PRESERVED**

---

## 6. Tests

Implemented bounded tests in `tests/test_privacy_acceptance_boundary.py`:

| Test | Purpose | Result |
|---|---|---|
| `test_prohibited_ssn_rejected` | SSN in field → rejected | PASS |
| `test_prohibited_phone_rejected` | Phone in field → rejected | PASS |
| `test_prohibited_email_rejected` | Email in field → rejected | PASS |
| `test_prohibited_name_rejected` | Person name in field → rejected | PASS |
| `test_prohibited_business_id_rejected` | Store number → rejected | PASS |
| `test_rejected_not_persisted` | Rejected input → no DB insert | PASS |
| `test_no_silent_sanitize_and_accept` | No sanitize-then-persist path | PASS |
| `test_stripped_not_analytics_value` | STRIPPED ≠ UNKNOWN/zero/verified | PASS |
| `test_missing_not_converted_to_zero` | lost_wages=None preserved | PASS |
| `test_valid_deidentified_accepted` | Clean contribution accepted | PASS |
| `test_no_fabrication_still_operates` | verify_record selftest passes | PASS |
| `test_existing_sanitize_text_test_unchanged` | test_anonymizer.py regression | PASS |

**TESTS = 12/12**

---

## 7. Regression

Existing `test_anonymizer.py` (9 tests) unchanged and passing.
Existing `test_no_fabrication_gate.py` passing.
No production code modified.

**REGRESSION = PASS**

---

## Database Governance

DATABASE_CREATED = NO
MIGRATION_CREATED = NO
SCHEMA_CHANGED = NO
RLS_CHANGED = NO
T_PERSIST = NOT_REQUIRED

## Protected Boundaries

REC_000_MODIFIED = NO
C2_C7_C12_MODIFIED = NO
TRACE_MODIFIED = NO
CUSTOMER_PORTAL_MODIFIED = NO
DOWNSTREAM_T3_T8 = NOT_EXECUTED

## Governance Dependency

The canonical TrueVow privacy policy definition is not present as a standalone repository file. Coverage is declared PARTIAL against the categories represented in the accepted specification and the anonymizer's own patterns. Complete coverage requires the canonical policy definition to be located or established.