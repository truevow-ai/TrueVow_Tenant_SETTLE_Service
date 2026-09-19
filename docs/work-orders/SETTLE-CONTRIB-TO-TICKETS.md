# SETTLE-CONTRIB-TO-TICKETS — External / Historical Settlement Contribution

**Status:** TO_TICKETS = COMPLETE
**Controlling specification:** SETTLE-CONTRIB-SPEC-001 (APPROVED / FROZEN)
**Controlling baseline:** SETTLE-REC-000 (REVIEW_BASELINE_FROZEN)
**Authorization:** /to-tickets = AUTHORIZED, /implement = NOT AUTHORIZED

---

## Dependency Model

```text
T1  Existing-model + persistence capability proof
        ↓
T2  Privacy acceptance / PHI coverage hardening
        ↓
T3  Provenance + evidence capability
        ↓
T4  Verification / partial verification / re-verification
        ↓
T5  Analytics eligibility enforcement
        ↓
T6  External/historical contribution intake path
        ↓
T7  SETTLE application/API capability
        ↓
T8  Integration + RLS + security + privacy + analytics regression proof
```

This is a dependency model, not permission to fabricate eight tickets. Merge/split only where repository evidence and implementation boundaries justify it.

---

## Gate Rule (MANDATORY)

**PERSISTENCE_CHANGE_REQUIRED = MAYBE_UNRESOLVED.**

T1 must produce evidence before any persistence-extension ticket may be unlocked. If T1 concludes existing SETTLE entities, relationships, and application logic can represent provenance, verification, and analytics-eligibility safely, create NO persistence-extension ticket. Only if T1 establishes genuine persistence insufficiency may the ticket plan conditionally unlock a separate smallest-possible persistence extension ticket.

Any eventual persistence change: uses existing SETTLE Supabase only; follows existing migration/governance conventions; includes rollback; preserves RLS and tenant isolation; includes database tests; creates no parallel database.

---

## T1 — Existing-Model + Persistence Capability Proof

| Field | Value |
|---|---|
| **Purpose** | Prove whether existing SETTLE entities, relationships, and application logic can represent provenance, verification, and analytics-eligibility for external/historical contributions without schema extension |
| **Governing spec sections** | SPEC-001 §8 (Reuse Matrix), §11.3a (Candidate Persistence Representations), §26 (Schema Reuse Proof Requirement) |
| **Existing authority / code to reuse** | `app/shared/contracts.py` (canonical contracts); existing SETTLE Supabase schema (settlement domain, case bank, contributions, offers/negotiations, liens/resolution); `_common/enrich.py`; `no_fabrication_gate.py`; `verdict_validator.py` |
| **Exact bounded scope** | Inspect existing SETTLE Supabase schema and application model. Determine whether `source_url`, `field_evidence` (value + snippet + source_url per field), `validated_field_count`, `validation_counts`, and analytics-eligibility flags can be represented via existing entities/columns/relationships/application state. Document findings. |
| **Prohibited scope** | No schema change. No migration. No new table, column, enum, constraint, RLS policy. No code implementation. No migration ticket created as an assumed requirement |
| **Dependencies** | None (T0 — first ticket) |
| **Acceptance criteria** | Written conclusion: (a) existing model can represent required capability — OR (b) existing model cannot represent required capability, with specific evidence of what is missing |
| **Tests** | Schema inspection report; evidence-of-insufficiency document if applicable |
| **Database impact** | NONE (inspection only) |
| **Ontology impact** | NONE |
| **Privacy / security impact** | NONE (inspection only) |
| **Rollback considerations** | N/A (no changes made) |
| **Evidence required for completion** | Documented conclusion with specific references to existing schema elements used or identified gaps |
| **Status** | BLOCKS all persistence-extension work. All downstream persistence tickets are CONDITIONAL and BLOCKED until T1 concludes |

**Conditional persistence gate:** If T1 concludes existing model CAN represent the capability → NO persistence-extension ticket is created. If T1 concludes existing model CANNOT represent the capability → unlock T-PERSIST (smallest-possible persistence extension) as a CONDITIONAL ticket.

---

## T2 — Privacy Acceptance / PHI Coverage Hardening

| Field | Value |
|---|---|
| **Purpose** | Ensure `sanitize_text()` and `no_fabrication_gate.py` satisfy the launch-critical privacy hardening requirement for external/historical contributions |
| **Governing spec sections** | SPEC-001 §5 (Privacy Acceptance Gate), §8.2 (`no_fabrication_gate.py` / `verdict_validator.py` disposition), §11.10 (Governance Blockers), §35 (Security Requirements) |
| **Existing authority / code to reuse** | `app/services/anonymizer.py` (`sanitize_text()`); `settle_data_scraping_factory/court_dockets_records/no_fabrication_gate.py` (`verify_record`); `settle_data_scraping_factory/court_dockets_records/verdict_validator.py` (`normalize_and_validate`) |
| **Exact bounded scope** | (a) Specify `sanitize_text()` disposition: existing utility may remain only outside prohibited acceptance semantics or behind explicit rejection/gating — silent sanitization of prohibited PHI must not be treated as trustworthy evidence. (b) Determine PHI-category coverage of `no_fabrication_gate.py` and `verdict_validator.py`: inspect source and tests to prove whether existing mechanisms already catch all required PHI categories for historical contributions, or document specific coverage gaps. |
| **Prohibited scope** | No code change to `sanitize_text()` in this ticket. No replacement of `no_fabrication_gate.py` or `verdict_validator.py`. No coverage-hardening implementation. No PHI persistence without verification. |
| **Dependencies** | T1 (persistence proof must conclude first to determine if provenance/verification fields exist in existing model) |
| **Acceptance criteria** | (a) `sanitize_text()` disposition documented: retained only outside prohibited acceptance semantics. (b) PHI-category coverage report: existing mechanisms proven complete OR specific gaps documented |
| **Tests** | Coverage analysis report; disposition document |
| **Database impact** | NONE |
| **Ontology impact** | NONE |
| **Privacy / security impact** | HIGH — directly addresses launch-critical privacy hardening |
| **Rollback considerations** | N/A (analysis/disposition only) |
| **Evidence required for completion** | `sanitize_text()` disposition document; PHI-category coverage analysis with evidence |
| **Status** | CONDITIONAL on T1 conclusion for persistence field availability |

---

## T3 — Provenance + Evidence Capability

| Field | Value |
|---|---|
| **Purpose** | Establish provenance and evidence capability for external/historical contributions: every analytics-relevant contributed fact must have sufficient governed provenance/evidence to establish its support and auditability |
| **Governing spec sections** | SPEC-001 §4 (Provenance & Evidence Model), §11.3a (Candidate Persistence Representations), §17 (Field Classification Reference), §23 (Field-Level Validation Tracking), §24 (Minimal Provenance Model) |
| **Existing authority / code to reuse** | `_common/enrich.py` (source snippet capture); `no_fabrication_gate.py` (verify_record); `verdict_validator.py` (normalize_and_validate); existing contribution records in SETTLE Supabase |
| **Exact bounded scope** | Define the provenance capability: what constitutes sufficient governed provenance/evidence for each analytics-relevant contributed fact. Define `field_evidence` structure (value + snippet + source_url per field). Define `validated_field_count` and `validation_counts` tracking. Classify each field per the taxonomy in §3 (VALUE_PROVENANCED, VALUE_VERIFIED, VALUE_ANALYTICS_ELIGIBLE, UNKNOWN, MISSING, NOT_APPLICABLE, STRIPPED). |
| **Prohibited scope** | No schema change unless T1 proves insufficiency. No persistence implementation. No fabrication of field values. No collapse of UNKNOWN/MISSING/NOT_APPLICABLE. No STRIPPED values treated as analytical. |
| **Dependencies** | T1 (persistence proof determines whether existing model can represent provenance fields), T2 (PHI coverage must be understood before provenance is trusted) |
| **Acceptance criteria** | Provenance capability specification: field classification taxonomy, `field_evidence` structure, `validated_field_count`/`validation_counts` definition, and evidence that every analytics-relevant contributed fact has a traceable `source_url` + verbatim snippet |
| **Tests** | Provenance capability specification; field classification table |
| **Database impact** | NONE unless T1 proves insufficiency (then CONDITIONAL) |
| **Ontology impact** | NONE |
| **Privacy / security impact** | MEDIUM — provenance fields may contain source URLs and snippets; must not persist unverifiable PHI |
| **Rollback considerations** | N/A (specification capability, not implementation) |
| **Evidence required for completion** | Provenance capability specification with field classification table |
| **Status** | CONDITIONAL on T1 conclusion for persistence field availability |

---

## T4 — Verification / Partial Verification / Re-verification

| Field | Value |
|---|---|
| **Purpose** | Establish verification capability: the system must distinguish sufficiently supported/verified facts from unsupported, partially verified, unknown, missing, and not-applicable facts according to existing canonical semantics |
| **Governing spec sections** | SPEC-001 §6 (Verification Lifecycle), §8.2 (`no_fabrication_gate.py` / `verdict_validator.py` disposition), §11.3 (Smallest Proven Extension — Verification Capability), §22 (Re-Verification Rule) |
| **Existing authority / code to reuse** | `no_fabrication_gate.py` (`verify_record`); `verdict_validator.py` (`normalize_and_validate`); existing verify → normalize → persist gate sequence from `cds_cap_loader.py` / `load_direct_supabase.py` |
| **Exact bounded scope** | Define the verification capability for historical contributions: gate sequence (verify_record → normalize_and_validate → enrichment → persistence). Define verification state tracking. Define re-verification trigger (gate changes, schema changes, new evidence sources). Define record preservation rule (rejected, purged, quarantined records preserved for later recovery). Define UNKNOWN/MISSING/NOT_APPLICABLE preservation and STRIPPED suppression. |
| **Prohibited scope** | No replacement of `no_fabrication_gate.py` or `verdict_validator.py`. No coverage-hardening implementation (that is T2). No bypass of existing gates. No fabrication of verification states. |
| **Dependencies** | T1 (persistence proof), T2 (PHI coverage), T3 (provenance capability) |
| **Acceptance criteria** | Verification capability specification: gate sequence definition, verification state model, re-verification trigger definition, record preservation rule, UNKNOWN/MISSING/NOT_APPLICABLE preservation rule, STRIPPED suppression rule |
| **Tests** | Verification capability specification; re-verification trigger definition |
| **Database impact** | NONE unless T1 proves insufficiency |
| **Ontology impact** | NONE |
| **Privacy / security impact** | MEDIUM — verification state affects which facts are trusted |
| **Rollback considerations** | N/A (specification capability, not implementation) |
| **Evidence required for completion** | Verification capability specification |
| **Status** | CONDITIONAL on T1 conclusion for persistence field availability |

---

## T5 — Analytics Eligibility Enforcement

| Field | Value |
|---|---|
| **Purpose** | Establish analytics eligibility capability: an enforceable mechanism must prevent ineligible records/facts from influencing Case Bank analytics |
| **Governing spec sections** | SPEC-001 §7 (Analytics Eligibility), §11.3 (Smallest Proven Extension — Analytics Eligibility), §25 (Analytics Eligibility Criteria) |
| **Existing authority / code to reuse** | Existing contribution records; existing analytics eligibility criteria; `no_fabrication_gate.py` (verified facts only); `verdict_validator.py` (normalized facts only) |
| **Exact bounded scope** | Define analytics eligibility criteria: VALUE_VERIFIED + VALUE_ANALYTICS_ELIGIBLE + `field_evidence` present for every field + `validated_field_count`/`validation_counts` present + no unverifiable fields persisted + no fabricated fields/default collapses/placeholder conversions. Define ineligible records: any with STRIPPED/UNKNOWN/MISSING/NOT_APPLICABLE fields that were collapsed, defaulted, or placeholder-converted. Define the enforcement mechanism. |
| **Prohibited scope** | No analytics inclusion of unverified records. No schema change unless T1 proves insufficiency. No default analytics inclusion. |
| **Dependencies** | T1 (persistence proof), T3 (provenance capability), T4 (verification capability) |
| **Acceptance criteria** | Analytics eligibility specification: eligibility criteria, enforcement mechanism, ineligible record definition |
| **Tests** | Analytics eligibility specification |
| **Database impact** | NONE unless T1 proves insufficiency |
| **Ontology impact** | NONE |
| **Privacy / security impact** | MEDIUM — analytics eligibility affects which records influence decisions |
| **Rollback considerations** | N/A (specification capability, not implementation) |
| **Evidence required for completion** | Analytics eligibility specification |
| **Status** | CONDITIONAL on T1 conclusion for persistence field availability |

---

## T6 — External / Historical Contribution Intake Path

| Field | Value |
|---|---|
| **Purpose** | Establish the designated backend intake path for cases with no prior TrueVow lifecycle, routed through the applicable existing verification/persistence gates |
| **Governing spec sections** | SPEC-001 §2 (Existing Contribution Architecture), §11.3 (Smallest Proven Extension — Intake Capability), §16 (Minimal Launch Architecture) |
| **Existing authority / code to reuse** | Existing verify-and-persist gate sequence; `cds_cap_loader.py` / `load_direct_supabase.py` as pattern references; `_common/enrich.py`; `no_fabrication_gate.py`; `verdict_validator.py` |
| **Exact bounded scope** | Define the intake path: a designated backend entry point for external/historical contributions with no prior INTAKE/TRACE/SETTLE lifecycle origin. The intake path must route through the existing verify-and-persist gate sequence (verify_record → normalize_and_validate → enrichment → persistence). No Customer Portal UI. No fake TRACE lifecycle. No TRACE domain duplication. |
| **Prohibited scope** | No Customer Portal UI. No TRACE handoff. No C2/C7/C12 work. No fake TRACE lifecycle. No new ontology IDs. No new canonical events/contracts. No implementation in this ticket (specification capability). |
| **Dependencies** | T1 (persistence proof), T2 (privacy hardening), T3 (provenance), T4 (verification), T5 (analytics eligibility) |
| **Acceptance criteria** | Intake path specification: designated backend entry point, gate sequence routing, no prior lifecycle requirement |
| **Tests** | Intake path specification |
| **Database impact** | NONE unless T1 proves insufficiency |
| **Ontology impact** | NONE |
| **Privacy / security impact** | HIGH — intake path is the entry point for external data |
| **Rollback considerations** | N/A (specification capability, not implementation) |
| **Evidence required for completion** | Intake path specification |
| **Status** | CONDITIONAL on T1 conclusion for persistence field availability |

---

## T7 — SETTLE Application / API Capability

| Field | Value |
|---|---|
| **Purpose** | Define the SETTLE application/API capability for external/historical contributions: backend-only; no Customer Portal UI |
| **Governing spec sections** | SPEC-001 §9 (Minimal Launch Contract — Proposed, NON-CANONICAL), §27 (Customer Portal Boundary), §28 (Cross-Service Contract Boundary) |
| **Existing authority / code to reuse** | `app/shared/contracts.py` (canonical contracts); `app/core/service_auth.py` — NOT used for this feature (OUT-OF-SCOPE per §8.2 correction); existing API patterns |
| **Exact bounded scope** | Define the application/API capability for historical contributions: backend-only endpoints or application logic. Do not create new canonical cross-service events or contracts. Do not modify C2/C7/C12. Do not touch webhook signing for this feature. |
| **Prohibited scope** | No Customer Portal UI. No new canonical cross-service events/contracts. No C2/C7/C12 modification. No webhook signing involvement. No TRACE handoff. |
| **Dependencies** | T1–T6 |
| **Acceptance criteria** | Application/API capability specification: backend-only scope, no new canonical contracts, no C2/C7/C12 involvement |
| **Tests** | Application/API capability specification |
| **Database impact** | NONE unless T1 proves insufficiency |
| **Ontology impact** | NONE |
| **Privacy / security impact** | MEDIUM — application layer handles verified data |
| **Rollback considerations** | N/A (specification capability, not implementation) |
| **Evidence required for completion** | Application/API capability specification |
| **Status** | CONDITIONAL on T1 conclusion for persistence field availability |

---

## T8 — Integration + RLS + Security + Privacy + Analytics Regression Proof

| Field | Value |
|---|---|
| **Purpose** | End-to-end proof that the integrated external/historical contribution path satisfies security, privacy, RLS/tenant isolation, and analytics regression requirements |
| **Governing spec sections** | SPEC-001 §5 (Privacy Acceptance Gate), §7 (Analytics Eligibility), §29 (Migration Tracking), §35 (Security Requirements), §10 (Launch Threat & Failure Analysis) |
| **Existing authority / code to reuse** | `tests/test_golden_fixtures.py` (17 golden webhook tests — do not modify); existing test command `python -m pytest tests/`; existing RLS/tenant isolation patterns |
| **Exact bounded scope** | Define integration test strategy: security tests, privacy tests, RLS/tenant isolation tests, analytics regression tests, re-verification tests. Specify test categories but do not implement them. Test command: `python -m pytest tests/` (existing convention). |
| **Prohibited scope** | No test implementation in this ticket (test strategy specified only). No modification of existing golden fixture tests. No production code changes. |
| **Dependencies** | T1–T7 |
| **Acceptance criteria** | Integration test strategy specification: test categories, acceptance criteria per category, regression proof requirements |
| **Tests** | Test strategy specification only |
| **Database impact** | NONE |
| **Ontology impact** | NONE |
| **Privacy / security impact** | HIGH — covers security, privacy, RLS |
| **Rollback considerations** | N/A (specification capability, not implementation) |
| **Evidence required for completion** | Integration test strategy specification |
| **Status** | FINAL ticket in dependency chain |

---

## Conditional Persistence Ticket (T-PERSIST) — BLOCKED until T1 proves necessity

| Field | Value |
|---|---|
| **Purpose** | Smallest-possible persistence extension if T1 proves existing model cannot represent provenance, verification, or analytics-eligibility capability |
| **Governing spec sections** | SPEC-001 §8.3 (Potential EXTEND areas), §26 (Schema Reuse Proof Requirement), §11.4 (Persistence Change Required = MAYBE) |
| **Existing authority / code to reuse** | Existing SETTLE Supabase schema; existing migration/governance conventions |
| **Exact bounded scope** | CONDITIONAL — only unlocked if T1 establishes genuine persistence insufficiency. Must prove existing entities/relationships/application logic cannot represent the required capability. Must include rollback, RLS/tenant isolation, database tests. No parallel database. |
| **Prohibited scope** | NO migration ticket as an assumed requirement. NO parallel database. NO schema change without T1 proof. NO implementation until authorized by /implement. |
| **Dependencies** | T1 (MUST prove insufficiency first) — BLOCKED until then |
| **Acceptance criteria** | T1 evidence of insufficiency; migration + rollback + RLS/tenant-isolation + tests plan |
| **Tests** | Migration plan including tests |
| **Database impact** | CONDITIONAL — only if T1 proves necessity |
| **Ontology impact** | NONE |
| **Privacy / security impact** | MEDIUM — persistence changes affect data integrity |
| **Rollback considerations** | Required (migration + rollback plan) |
| **Evidence required for completion** | T1 insufficiency evidence; migration plan; rollback plan; RLS/tenant-isolation plan; database tests |
| **Status** | CONDITIONAL and BLOCKED until T1 proves necessity |

---

## Protected Boundaries (DO NOT TOUCH)

- REC-000 = FROZEN — DO NOT MODIFY
- C2 (matter.activated) = PROTECTED
- C7 (resolution-update) = PROTECTED
- C12 (settle_events) = PROTECTED
- TRACE handoff = OUT OF SCOPE
- Customer Portal UI = OUT OF SCOPE (backend specification only)
- Webhook signing (`app/core/service_auth.py`) = OUT OF SCOPE for this contribution specification
- No new ontology IDs without separate governance
- No new canonical cross-service events/contracts without separate governance
- No fake TRACE lifecycle
- No duplication of TRACE evidence
- `tests/test_golden_fixtures.py` (17 golden webhook tests) = DO NOT MODIFY
- `app/shared/contracts.py` = DO NOT EDIT
- `app/models/activation.py` = DO NOT EDIT

---

## Implementation Principles

1. **Existing model first.** Before any schema extension, prove existing SETTLE entities/relationships/application logic cannot represent the required capability.
2. **No migration as assumed requirement.** T1 must establish necessity before any persistence-extension ticket may be unlocked.
3. **Capability before implementation.** Provenance, verification, analytics-eligibility, and intake are capability specifications first. Implementation comes after `/to-tickets` review and `/implement` authorization.
4. **No fabrication.** Every field entering the database must be verifiable — source_url + verbatim snippet. UNKNOWN/MISSING/NOT_APPLICABLE preserved. STRIPPED suppressed from analytical use.
5. **Smallest useful trustworthy record.** Prefer the smallest useful trustworthy record over the largest possible form.
6. **Reuse before extend.** REUSE-AS-IS first; EXTEND only after proof.
7. **Existing SETTLE Supabase only.** No parallel database.
8. **Migration/governance conventions.** Any eventual change includes rollback, RLS/tenant-isolation, and database tests.

---

## Ticket Summary

| Ticket | Status | Database Impact | Blocked By |
|---|---|---|---|
| T1 | READY | NONE (inspection only) | — |
| T2 | READY | NONE | T1 |
| T3 | READY | NONE | T1, T2 |
| T4 | READY | NONE | T1, T2, T3 |
| T5 | READY | NONE | T1, T3, T4 |
| T6 | READY | NONE | T1–T5 |
| T7 | READY | NONE | T1–T6 |
| T8 | READY | NONE | T1–T7 |
| T-PERSIST | CONDITIONAL / BLOCKED | CONDITIONAL | T1 (proof of insufficiency) |

---

## Terminal State

- SETTLE-CONTRIB-SPEC-001 = APPROVED_SPECIFICATION_BASELINE
- TO_TICKETS = COMPLETE
- IMPLEMENTATION = NOT AUTHORIZED
- PERSISTENCE_CHANGE_REQUIRED = MAYBE_UNRESOLVED
- DATABASE_CREATED = NO
- MIGRATION_CREATED = NO
- SCHEMA_CHANGED = NO
- REC_000_MODIFIED = NO
- C2_C7_C12_MODIFIED = NO
- AGENT_RESPONSE_LANGUAGE = ENGLISH
- GENERATED_ARTIFACT_LANGUAGE = ENGLISH
- STOP
