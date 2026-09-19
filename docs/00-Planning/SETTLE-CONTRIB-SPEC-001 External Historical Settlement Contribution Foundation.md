# SETTLE-CONTRIB-SPEC-001 — External / Historical Settlement Contribution Foundation

**Status:** REVIEW_REQUIRED
**Phase:** Specification only. Implementation authorization: NONE.
**Controlling baseline:** SETTLE-REC-000 (frozen at REVIEW_BASELINE, `.tmp/SETTLE-REC-000_EVIDENCE_PACK.md`).
**Authoritative contract location:** `app/shared/contracts.py` (CONTRACT_VERSIONS, golden fixtures).
**Repository convention:** Planning artifacts live under `docs/00-Planning/`.

---

## Section 1 — Authority & Baseline

1. **Controlling objective:** Produce the smallest evidence-backed, launch-safe backend specification for EXTERNAL / HISTORICAL settlement contributions to SETTLE. Stop at a frozen specification. Implementation authorization: NONE.
2. **Controlling exit decision:** "Can the existing SETTLE architecture safely support verified historical / external settlement contributions as-is?" If NO, the answer must be: "What is the smallest proven extension required for launch?"
3. **REC-000 is FROZEN.** No append, no reopen, no broad reconciliation. Only amend if new repository evidence proves an existing REC statement factually incorrect; record separately and identify the exact statement affected.
4. **Scope boundary — IN:** backend specification for contributions from cases that never existed in INTAKE, TRACE, or SETTLE matter development. Contributions that are purely external / historical and may have no prior TrueVow lifecycle origin.
5. **Scope boundary — OUT:** Customer Portal UI, C2 (matter.activated), C7 (resolution-update), C12 (settle_events), TRACE handoff, matter.activated events, trace.settlement_context_ready events, ontology registry edits, new canonical cross-service events or contracts, any implementation, any migration, any schema change, any new database.
6. **Three persistent rules (AGENTS.md):**
   - RULE 1 — Agent output language: ALL human-readable communication MUST be English (applies to agent response AND artifacts).
   - RULE 2 — Do not rename/mutate mislabelled planning files (the two DOCX-with-.md-extension files must stay as-is; renaming is a separate repository-hygiene ticket).
   - RULE 3 — Existing SETTLE Supabase only. Reuse before adding. No parallel database.
7. **Launch status:** External / Historical Settlement Contribution = LAUNCH REQUIRED (recorded in REC-000 governance correction). Not a future nice-to-have.
8. **No-fabrication prime directive (RULE 0):** Every field entering the database MUST be verifiable — it must trace to a source_url AND appear verbatim in a stored evidence snippet. Numbers by digits, strings by substring, ages by in-range number in snippet, enums by justifying keyword, dates by their parts, lists element-by-element. If unverifiable, STRIP. Never guess, infer, manufacture defaults, convert missing to zero, fabricate evidence, fabricate verification states, fabricate TRACE provenance. Zero eligible records beats contaminated analytics.
9. **Verification gates (per REC-000):**
   - `no_fabrication_gate.py` (`verify_record`) — universal evidence gate. Run FIRST.
   - `verdict_validator.py` (`normalize_and_validate`) — enum/format/bounds gate. Run SECOND.
   - Both loaders (`cds_cap_loader.py`, `load_direct_supabase.py`) run BOTH gates before any insert.
10. **Agent status declarations (mandatory at end of this packet):**
    - AGENT_RESPONSE_LANGUAGE = ENGLISH
    - GENERATED_ARTIFACT_LANGUAGE = ENGLISH
    - REC_000_MODIFIED = NO
    - DATABASE_CREATED = NO
    - MIGRATION_CREATED = NO
    - SCHEMA_CHANGED = NO
    - DOWNSTREAM_IMPLEMENTATION = NOT AUTHORIZED
    - SETTLE-CONTRIB-SPEC-001 = REVIEW_REQUIRED
    - STOP

## Section 2 — Existing Contribution Architecture (As-Is)

2.1 **Inbound contribution path (existing):** Contributions arrive via `settle_data_scraping_factory/court_dockets_records/` loaders (`cds_cap_loader.py`, `load_direct_supabase.py`). Each record passes through `no_fabrication_gate.py` (verify_record) then `verdict_validator.py` (normalize_and_validate) before any DB insert.
2.2 **Evidence capture:** `_common/enrich.py` captures a source snippet for EVERY field it extracts. Fields must have `source_url` + verbatim snippet.
2.3 **Persistence (existing):** SETTLE Supabase database — existing settlement domain, existing case bank, existing contributions, existing offers/negotiations, existing liens/resolution. No new tables, columns, enums, constraints, RLS policies, or databases proposed in this specification.
2.4 **Readback / query (existing):** Existing API query patterns return verified fields. No new query endpoints proposed in this specification.
2.5 **External / cross-service signaling (existing):** Webhook signing/verification via `app/core/service_auth.py` (`WebhookSigner`, `WebhookVerifier`). Canonical paths: `POST /settle/webhooks/matter-activated` (receives from TRACE), `POST /settle/webhooks/resolution-update` (notifies COMMAND). None of these are touched in this specification.
2.6 **Anonymization / privacy (existing):** `app/services/anonymizer.py` — `sanitize_text()`. Launch-critical privacy hardening (see Section 5).
2.7 **Existing contribution lifecycle (as-is):** Ingest → verify → normalize → persist → enrich → query → (optional) external signal. Historical contributions must follow the SAME verify-and-persist gate, even though they have no prior INTAKE/TRACE/SETTLE lifecycle origin.
2.8 **Gap determination:** The existing architecture has a verify-and-persist gate, enrichment with source snippets, a no-fabrication gate, and anonymization. What it does NOT have is a designated intake path for cases that arrive fully formed from external/historical sources with no prior lifecycle provenance. The existing path assumes a scraping/loader origin. This is a pipeline-origin gap, not necessarily a schema gap.

## Section 3 — Historical Contribution Field Matrix

For each field that may enter a historical contribution record, classify it:

3.1 **Classification taxonomy (per REC-000 no-fabrication rule):**
   - `VALUE_PROVIDED` — source supplies the exact value (digits, substring, keyword, date part, list element). Verifiable. May persist.
   - `VALUE_PROVENANCED` — source supplies the value AND a traceable `source_url` + verbatim snippet. Higher trust; preferred.
   - `VALUE_VERIFIED` — passed through `no_fabrication_gate.py` (verify_record) AND `verdict_validator.py` (normalize_and_validate). Highest trust; required for DB insert.
   - `VALUE_ANALYTICS_ELIGIBLE` — verified AND meets analytics-eligibility criteria (Section 7).
   - `UNKNOWN` — source does not supply the field and no inference is permitted. Must NOT collapse to default, zero, or empty.
   - `MISSING` — source supplies the field but the value is absent/null/empty. Must NOT collapse to default, zero, or empty.
   - `NOT_APPLICABLE` — the field category does not apply to this case type. Must NOT collapse to default, zero, or empty.
   - `STRIPPED` — unverifiable; must NOT persist.
3.2 **Field categories to classify (per judicial-contribution domain):** case identifiers, parties, attorneys, courts, judges, case types, injury types, dates (incident, filing, decision, statute of limitations), damages (economic / non-economic / punitive), medical bills, lost wages, insurance carriers, settlements, verdicts, liens, offers, negotiations, contributions, contributions amounts, contribution dates, contribution sources, contribution provenance, verification status, verification evidence, analytics eligibility flags.
3.3 **Mapping rule for each category:**
   - If the source supplies the exact value with a traceable `source_url` + verbatim snippet → `VALUE_PROVENANCED`.
   - If it passes both gates → `VALUE_VERIFIED`.
   - If analytics-eligibility criteria (Section 7) are also met → `VALUE_ANALYTICS_ELIGIBLE`.
   - If the source does NOT supply the field → `UNKNOWN`, `MISSING`, or `NOT_APPLICABLE` as appropriate. Never collapse.
   - If the value cannot be verified → `STRIPPED`. Never persist.
3.4 **Explicit prohibition:** No fallback buckets (e.g., no default `personal_injury_general` case_type when the real one is unknown). No splitting a total in half. No default enum when the real one is unknown. No converting missing to zero. No converting UNKNOWN to a placeholder.
3.5 **Record size preference:** Prefer the smallest useful trustworthy record over the largest possible form. A smaller, fully-verifiable record beats a large contaminated one. Zero records is preferable to one fabricated field.
3.6 **Per-field evidence tracking:** Persist `validated_field_count`, `validation_counts`, and `field_evidence` (value + snippet + source_url per field) so any row is auditable field-by-field, word-by-word, number-by-number.

## Section 4 — Provenance & Evidence Model

4.1 **Core principle:** Every field that enters the database MUST be verifiable. Verifiable = traces to a `source_url` AND appears verbatim in a stored evidence snippet.
4.2 **Evidence snippet requirements:**
   - Numbers: by their digits.
   - Strings: by substring.
   - Ages: by an in-range number in the snippet.
   - Enums: by a justifying keyword.
   - Dates: by their parts.
   - Lists: element-by-element.
4.3 **`source_url` requirements:** Must be present for every persisted field. Must be traceable to the external/historical source document.
4.4 **`field_evidence` structure (per field):** `{ value: <verbatim>, snippet: <source snippet>, source_url: <traceable URL> }`. Persist alongside the record.
4.5 **Verification tracking:** Persist `validated_field_count` and `validation_counts` per record so any row is auditable field-by-field.
4.6 **Provenance chain for historical contributions:** External/historical source → field extraction with verbatim snippet + source_url → `no_fabrication_gate.py` (verify_record) → `verdict_validator.py` (normalize_and_validate) → persist with `field_evidence` + `validated_field_count` + `validation_counts`. Same gate sequence as existing loaders. No bypass.
4.7 **No TRACE provenance fabrication:** Historical contributions may have no TRACE origin. Do NOT fabricate `trace.settlement_context_ready`, `matter.activated`, or any TRACE event. Do NOT fabricate medical chronology, raw PHI, evidence documents, treatment records, or liability/coverage evidence source-of-truth in SETTLE.
4.8 **Enrichment consistency:** `_common/enrich.py` must capture a source snippet for every field it extracts — including historical contribution fields. Same enrichment standard as existing loaders.

## Section 5 — Privacy Acceptance Gate (`sanitize_text()` Disposition)

5.1 **Current state:** `app/services/anonymizer.py` contains `sanitize_text()`. It redacts/masks PHI in text fields.
5.2 **Launch-critical designation (REC-000 governance correction):** `sanitize_text()` is flagged **EXTEND / LAUNCH-CRITICAL PRIVACY HARDENING**. Silently redacting PHI must not become an acceptance shortcut.
5.3 **Disposition (specification only):**
   - Do NOT delete `sanitize_text()`. Do NOT change its code in this specification.
   - Specify that `sanitize_text()` must eventually be evaluated for one or more of the following dispositions:
     - `QUARANTINE` — restrict to display/logging only; never an acceptance-path dependency.
     - `WRAP` — wrap with explicit rejection validation that rejects input that relies solely on sanitized output for a decision.
     - `REMOVE_FROM_ACCEPTANCE` — remove from acceptance paths entirely; only permitted in non-decision contexts.
   - The launch-safe default is: `sanitize_text()` output must NOT be the sole basis for any persistence, verification, or analytics-eligibility decision.
5.4 **No PHI persistence without verification:** Any PHI field (medical chronology, treatment records, raw PHI, liability/coverage evidence) that cannot be verified must be STRIPPED per RULE 0. Do not persist unverifiable PHI.
5.5 **TRACE data non-duplication:** SETTLE must NOT copy TRACE's medical chronology, raw PHI, evidence documents, treatment records, liability evidence, etc. into its database simply because the Customer Portal needs to display something. Canonical SETTLE information stays in SETTLE's existing Supabase database.

## Section 6 — Verification Lifecycle (Historical Contributions)

6.1 **Lifecycle phases:**
   1. **Ingestion** — external/historical source document arrives. No prior INTAKE/TRACE/SETTLE lifecycle required.
   2. **Field extraction** — extract fields with verbatim snippet + `source_url`.
   3. **Evidence gate** — `no_fabrication_gate.py` (`verify_record`) runs FIRST.
   4. **Normalization gate** — `verdict_validator.py` (`normalize_and_validate`) runs SECOND.
   5. **Enrichment** — `_common/enrich.py` captures source snippet for every extracted field.
   6. **Privacy gate** — `sanitize_text()` applied per Section 5; sanitized output must not be sole decision basis.
   7. **Persistence** — persist only `VALUE_VERIFIED` fields with `field_evidence` + `validated_field_count` + `validation_counts`. Strip `STRIPPED`. Preserve `UNKNOWN`/`MISSING`/`NOT_APPLICABLE`.
   8. **Readback** — existing query patterns return verified fields.
   9. **Re-verification** — mandatory whenever the gate changes; rejected, purged, and quarantined records are preserved for later recovery.
6.2 **No bypass:** Every new source pipeline (historical contributions included) MUST route through both gates before touching the DB. Never add an insert path that bypasses them.
6.3 **Re-verification trigger:** Gate changes, schema changes, or new evidence sources require re-verification of already-loaded data.
6.4 **Record preservation:** Rejected, purged, and quarantined records are preserved (never destroyed) so they can be re-verified against their sources later and recovered if they legitimately pass.

## Section 7 — Analytics Eligibility

7.1 **Core principle:** Zero eligible records is preferable to contaminated analytics. Do not grow the record count to please stakeholders. A smaller, fully-verifiable database beats a large contaminated one, always.
7.2 **Eligibility criteria (must be met for analytics):**
   - `VALUE_VERIFIED` — passed both gates.
   - `VALUE_ANALYTICS_ELIGIBLE` — meets additional analytics-eligibility criteria.
   - `field_evidence` present for every field — auditable field-by-field.
   - `validated_field_count` and `validation_counts` present — auditable per record.
   - No unverifiable fields persisted.
   - No fabricated fields, no default collapses, no placeholder conversions.
7.3 **Explicit exclusion:** Records with any `STRIPPED`, `UNKNOWN`, `MISSING`, or `NOT_APPLICABLE` fields that were collapsed, defaulted, or placeholder-converted must NOT be analytics-eligible.
7.4 **Analytics boundary:** SETTLE analytics eligibility is backend-only. The Customer Portal owns attorney-facing UI and its own eligibility presentation. SETTLE specifies backend capability only.
7.5 **No duplicate TRACE data:** SETTLE must NOT copy TRACE's medical chronology, raw PHI, evidence documents, treatment records, liability evidence, etc. into its database for analytics. Canonical SETTLE information stays in SETTLE's existing Supabase database.

## Section 8 — Existing Supabase Reuse Matrix

8.1 **Governing rule (RULE 3):** All SETTLE database changes go through the EXISTING SETTLE Supabase database and its existing migration/governance system. Before creating any table or column, PROVE that the existing SETTLE schema/model cannot represent the requirement.
8.2 **Reuse matrix (REUSE-AS-IS unless proven otherwise):**

| Capability | Disposition | Evidence / Notes |
|---|---|---|
| Settlement domain | REUSE-AS-IS | Existing settlement domain in SETTLE Supabase |
| Case bank | REUSE-AS-IS | Existing case bank in SETTLE Supabase |
| Contributions | REUSE-AS-IS / EXTEND | Existing contributions; may need provenance extension (see 8.3) |
| Offers / Negotiations | REUSE-AS-IS | Existing offers/negotiations |
| Liens / Resolution | REUSE-AS-IS | Existing liens/resolution |
| Webhook signing/verification | OUT-OF-SCOPE / NOT REQUIRED FOR CURRENT SPEC — do not include `app/core/service_auth.py` in the minimal historical-contribution architecture merely because it exists | No direct evidence that Customer Portal→SETTLE contribution path requires this mechanism. Service_auth.py is entangled with C2/Trace scaffolding. Classify as OUT-OF-SCOPE unless concrete evidence establishes relevance. Do not invent a webhook/event contract. Do not modify C2/C7. |
| `sanitize_text()` | EXTEND / LAUNCH-CRITICAL PRIVACY HARDENING — existing utility may remain only outside prohibited acceptance semantics or behind explicit rejection/gating | Do NOT imply current behavior is reusable as-is for historical contribution acceptance. Silent sanitization of prohibited PHI on an acceptance path must not be treated as trustworthy evidence. |
| `no_fabrication_gate.py` | EXTEND pending PHI-category coverage proof — existing mechanism may be retained only if tests/source inspection prove complete required launch coverage | Current PHI/category coverage is PARTIAL. REUSE-AS-IS only if evidence proves completeness. Do not replace the mechanism. |
| `verdict_validator.py` | EXTEND pending PHI-category coverage proof — existing mechanism may be retained only if tests/source inspection prove complete required launch coverage | Current PHI/category coverage is PARTIAL. REUSE-AS-IS only if evidence proves completeness. Do not replace the mechanism. |
| `_common/enrich.py` | REUSE-AS-IS | Existing enrichment; must capture snippet for every field |
| `cds_cap_loader.py` | REUSE-AS-IS | Existing loader; gate sequence applies |
| `load_direct_supabase.py` | REUSE-AS-IS | Existing loader; gate sequence applies |
| Evidence pack artifacts | REUSE-AS-IS | `.tmp/SETTLE-REC-000_EVIDENCE_PACK.md` |
| Contract artifacts (`app/shared/contracts.py`, `app/models/activation.py`) | REUSE-AS-IS | Frozen contracts; do not edit |

8.3 **Potential EXTEND areas (proposed only, NON-CANONICAL; requires proof that existing schema cannot represent):**
   - Contribution provenance fields — may need `source_url`, `field_evidence`, `validated_field_count`, `validation_counts` columns/attributes on contribution records. PROVE existing schema cannot represent before adding.
   - Historical contribution source reference — may need a reference to the external/historical source document. PROVE existing schema cannot represent before adding.
   - Verification status tracking — may need verification-state fields per record. PROVE existing schema cannot represent before adding.
   - Analytics eligibility flags — may need flags per record. PROVE existing schema cannot represent before adding.
8.4 **Explicit prohibition — no parallel database:** Do NOT create `settle_old_database`, `settle_v3_database`, `historical_contributions_database`, `analytics_database`, or any other parallel data plane.
8.5 **Explicit prohibition — no schema change without proof:** Do NOT add any table, column, enum, constraint, RLS policy, or migration unless the existing SETTLE schema/model is proven unable to represent the requirement.
8.6 **Explicit prohibition — no duplicate TRACE data:** SETTLE must NOT copy TRACE's medical chronology, raw PHI, evidence documents, treatment records, liability evidence, etc. into its database simply because the Customer Portal needs to display something.

## Section 9 — Minimal Launch Contract (Proposed, NON-CANONICAL)

9.1 **Status:** Proposed only. NON-CANONICAL. Must NOT be treated as committed contracts.
9.2 **Purpose:** Define the smallest possible contract surface for verified historical contributions so that /to-tickets can convert it into implementation tickets.
9.3 **Proposed contract elements (all subject to /to-tickets and existing contract governance):**
   - Historical contribution intake endpoint (backend-only; no Customer Portal UI).
   - Verify-and-persist gate sequence (same as existing loaders): `no_fabrication_gate.py` → `verdict_validator.py` → enrichment → persistence.
   - `field_evidence` persistence per field (value + snippet + source_url).
   - `validated_field_count` and `validation_counts` persistence per record.
   - `UNKNOWN`/`MISSING`/`NOT_APPLICABLE` preservation (no collapse).
   - `STRIPPED` suppression (do not persist).
   - `sanitize_text()` disposition (Section 5).
   - Analytics eligibility criteria (Section 7).
9.4 **Non-canonical disclaimer:** This section is a PROPOSED contract for /to-tickets triage. It is NOT a canonical contract. Canonical contracts live in `app/shared/contracts.py` and are governed by the existing contract versioning system. Do not add, edit, or remove canonical contracts based on this section.
9.5 **Migration tracking:** Auth source logged on every verification. Legacy bearer auth deprecated after 2026-09-01. Dual auth (HMAC OR legacy) during migration window.

## Section 10 — Launch Threat & Failure Analysis

10 scenarios, each classified as MITIGATED / PARTIAL / UNRESOLVED:

10.1 **Scenario 1 — Fabricated case type default.** Threat: default `personal_injury_general` when the real one is unknown. Mitigation: RULE 0 prohibition + `verdict_validator.py` enum gate. Classification: MITIGATED.
10.2 **Scenario 2 — Missing amount collapsed to zero.** Threat: `lost_wages=UNKNOWN` collapsed to `$0`. Mitigation: RULE 0 + `UNKNOWN` preservation rule. Classification: MITIGATED.
10.3 **Scenario 3 — Unverifiable PHI persisted.** Threat: unverifiable medical chronology persisted to DB. Mitigation: `no_fabrication_gate.py` + STRIPPED rule + `sanitize_text()`. Classification: PARTIAL (requires proof that gate catches all PHI categories).
10.4 **Scenario 4 — TRACE provenance fabricated.** Threat: fake `trace.settlement_context_ready` event invented for historical case. Mitigation: explicit prohibition + no TRACE event fabrication rule. Classification: MITIGATED.
10.5 **Scenario 5 — Parallel database created.** Threat: new `historical_contributions_database` spun up. Mitigation: RULE 3 + explicit prohibition. Classification: MITIGATED.
10.6 **Scenario 6 — Schema change without proof.** Threat: new columns added to support historical contributions without proving existing schema insufficient. Mitigation: RULE 3 + reuse-first + proof requirement. Classification: MITIGATED.
10.7 **Scenario 7 — `sanitize_text()` becomes acceptance-path dependency.** Threat: sanitized output used as sole basis for persistence/verification decision. Mitigation: Section 5 disposition + explicit prohibition. Classification: PARTIAL (requires implementation of disposition).
10.8 **Scenario 8 — Analytics contaminated by unverified records.** Threat: unverified records included in analytics. Mitigation: Section 7 eligibility criteria + zero-record-preference. Classification: MITIGATED.
10.9 **Scenario 9 — Customer Portal built for historical contributions.** Threat: frontend built before backend spec is frozen. Mitigation: explicit scope boundary (backend-only). Classification: MITIGATED.
10.10 **Scenario 10 — C2/C7/C12 touched.** Threat: matter.activated or resolution-update or settle_events modified. Mitigation: explicit scope boundary + frozen contracts. Classification: MITIGATED.
10.11 **Scenario 11 — Record count grown to please stakeholders.** Threat: inflated record count with fabricated fields. Mitigation: RULE 0 + zero-record-preference + verification gates. Classification: MITIGATED.
10.12 **Scenario 12 — Default enum when real one is unknown.** Threat: fallback enum bucket used. Mitigation: RULE 0 + explicit prohibition. Classification: MITIGATED.
10.13 **Scenario 13 — Splitting a total in half.** Threat: damage total divided arbitrarily. Mitigation: RULE 0 + explicit prohibition. Classification: MITIGATED.
10.14 **Scenario 14 — Converting missing to empty string.** Threat: `MISSING` → `""` or `null` collapse. Mitigation: RULE 0 + `UNKNOWN`/`MISSING`/`NOT_APPLICABLE` preservation. Classification: MITIGATED.
10.15 **Scenario 15 — Re-verification skipped after gate change.** Threat: already-loaded data not re-verified when gate changes. Mitigation: Section 6 re-verification trigger + record preservation rule. Classification: PARTIAL (requires implementation of re-verification workflow).

**Overall classification:** 13 MITIGATED, 2 PARTIAL, 0 UNRESOLVED. The 2 PARTIAL scenarios (3 and 7) require implementation of the proposed dispositions before launch-safe operation is confirmed.

## Section 11 — Final Specification Decision

11.1 **Controlling exit decision:** "Can the existing SETTLE architecture safely support verified historical / external settlement contributions as-is?"
11.2 **Answer:** NO — not fully as-is, but the gap is a pipeline-origin gap, not necessarily a schema gap. The existing architecture has verify-and-persist gates, enrichment, anonymization, and no-fabrication checks. What is missing is a designated intake path for external/historical cases with no prior INTAKE/TRACE/SETTLE lifecycle origin, plus provenance/verification/analytics-eligibility extensions to the contribution model.
11.3 **Smallest proven extension required for launch (CAPABILITY level):**
    The existing schema has not yet been proven insufficient. The proven
    requirements are capability-level, not physical-field declarations:

    A. EXTERNAL/HISTORICAL INTAKE CAPABILITY
       A designated backend path for cases with no prior TrueVow lifecycle,
       routed through the applicable existing verification/persistence gates.

    B. PROVENANCE CAPABILITY
       Every analytics-relevant contributed fact must have sufficient governed
       provenance/evidence to establish its support and auditability.

    C. VERIFICATION CAPABILITY
       The system must distinguish sufficiently supported/verified facts from
       unsupported, partially verified, unknown, missing, and not-applicable
       facts according to existing canonical semantics.

    D. ANALYTICS-ELIGIBILITY CAPABILITY
       An enforceable mechanism must prevent ineligible records/facts from
       influencing Case Bank analytics.

    E. PRIVACY ACCEPTANCE HARDENING
       Prohibited sensitive input must be rejected or explicitly gated rather
       than silently transformed and accepted as trustworthy evidence.

    F. SEMANTIC PRESERVATION
       Preserve UNKNOWN / MISSING / NOT_APPLICABLE and suppress STRIPPED from
       analytical use.

11.3a **Candidate Persistence Representations — NON-CANONICAL / NOT PROVEN NECESSARY:**
    The following physical representations are candidate solutions, not proven
    requirements. They may proceed to implementation design only if /to-tickets
    evidence proves the existing model cannot represent the required capability
    safely:
    - source_url
    - field_evidence
    - validated_field_count
    - validation_counts
    - analytics eligibility flags
11.4 **Persistence change required:** MAYBE — only if the existing SETTLE schema/model is proven unable to represent the provenance/verification/analytics fields. REUSE-AS-IS first; EXTEND only after proof.
11.5 **Privacy hardening required:** YES — `sanitize_text()` disposition (Section 5).
11.6 **Verification extension required:** YES — verify-and-persist gate sequence extended to historical contribution intake path (Section 6).
11.7 **Provenance extension required:** YES — `field_evidence`, `source_url`, `validated_field_count`, `validation_counts` per record (Section 4; PROVE existing schema cannot represent first).
11.8 **Customer Portal follow-on required:** YES — the Customer Portal owns attorney-facing UI for historical contributions. Backend specification only in this packet. Portal follow-on is a separate, later work package.
11.9 **TRACE-STL-001 dependency:** Historical contributions may have no TRACE origin. Do NOT fabricate TRACE events. TRACE handoff is OUT OF SCOPE. If TRACE integration is later needed, it is a separate work package.
11.10 **Governance blockers:**
    - `sanitize_text()` disposition not yet implemented (Section 5 — PARTIAL).
    - Re-verification workflow not yet implemented (Section 6 — PARTIAL).
    - Existing schema provenance/verification fields not yet proven to be insufficient (Section 8.3 — requires proof).
    - `no_fabrication_gate.py` and `verdict_validator.py` must catch all PHI categories (Scenario 3 — PARTIAL).
11.11 **Ready for /to-tickets:** NO — this is a specification packet. /to-tickets authorization comes after the specification is reviewed and approved.
11.12 **Final declarations:**
    - AGENT_RESPONSE_LANGUAGE = ENGLISH
    - GENERATED_ARTIFACT_LANGUAGE = ENGLISH
    - REC_000_MODIFIED = NO
    - DATABASE_CREATED = NO
    - MIGRATION_CREATED = NO
    - SCHEMA_CHANGED = NO
    - DOWNSTREAM_IMPLEMENTATION = NOT AUTHORIZED
    - SETTLE-CONTRIB-SPEC-001 = REVIEW_REQUIRED
    - STOP

## Section 12 — Shed Design Directions (Explicit Non-Work)

These are design directions to explicitly SOW/SHED for this work package. They are NOT in scope and must not be implemented.

12.1 **SHED — Customer Portal UI:** The Customer Portal owns attorney-facing UI for historical contributions. This is a frontend/product work package, not a backend specification.
12.2 **SHED — TRACE handoff:** `matter.activated`, `trace.settlement_context_ready`, and any TRACE integration are out of scope. If needed, they are a separate work package.
12.3 **SHED — C2/C7/C12 work:** `POST /settle/webhooks/matter-activated`, `POST /settle/webhooks/resolution-update`, and `settle_events` table are frozen contracts / reserved. No work on them in this package.
12.4 **SHED — Ontology registry edits:** Do not create new ENT IDs. Do not edit the canonical ontology registry. Do not freeze new cross-service events or contracts.
12.5 **SHED — Parallel database:** No `settle_old_database`, `settle_v3_database`, `historical_contributions_database`, `analytics_database`, or any parallel data plane.
12.6 **SHED — Schema changes without proof:** No new tables, columns, enums, constraints, RLS policies, or migrations unless the existing SETTLE schema is proven insufficient.
12.7 **SHED — Default buckets and placeholder conversions:** No default `personal_injury_general` case_type, no splitting totals, no converting missing to zero, no converting UNKNOWN to placeholder.
12.8 **SHED — Analytics without eligibility:** No analytics-eligible records unless they meet ALL criteria in Section 7.
12.9 **SHED — Fabrication of any kind:** No guessing, inferring, manufacturing defaults, converting missing to zero, fabricating evidence, fabrication of verification states, fabrication of TRACE provenance.

## Section 13 — Test Strategy (Specify Only; Do Not Implement)

13.1 **Test type:** Specification-level tests only. No implementation tests in this work package.
13.2 **Existing test coverage to preserve:** `tests/test_golden_fixtures.py` (17 webhook tests). Do not modify.
13.3 **Proposed test categories (for /to-tickets):**
    - Gate sequence tests: verify `no_fabrication_gate.py` → `verdict_validator.py` → enrichment → persistence sequence runs for historical contribution intake.
    - Provenance tests: verify `field_evidence` (value + snippet + source_url) persisted per field.
    - Verification tracking tests: verify `validated_field_count` and `validation_counts` persisted per record.
    - Collapse prevention tests: verify `UNKNOWN`/`MISSING`/`NOT_APPLICABLE` are preserved, not collapsed to default/zero/empty.
    - Strip tests: verify unverifiable fields are STRIPPED, not persisted.
    - PHI strip tests: verify unverifiable PHI is stripped per RULE 0.
    - Analytics eligibility tests: verify only verified + analytics-eligible records qualify.
    - Re-verification tests: verify re-verification triggers on gate changes.
    - `sanitize_text()` disposition tests: verify sanitized output is not sole basis for any decision.
    - Schema reuse tests: verify existing schema can represent provenance fields before EXTEND is proposed.
13.4 **Test command (existing convention):** `python -m pytest tests/` (Python, pytest + SQLAlchemy). Do not implement these tests in this specification.

## Section 14 — Implementation Frontier (Explicit Non-Work)

14.1 **This specification packet authorizes NONE of the following:**
    - Any implementation code.
    - Any migration.
    - Any schema change.
    - Any new database.
    - Any Customer Portal UI.
    - Any TRACE handoff.
    - Any C2/C7/C12 work.
    - Any ontology registry edit.
    - Any new canonical cross-service event or contract.
    - Any test implementation (test strategy is specified only; see Section 13).
14.2 **What this specification authorizes:** A frozen specification document for `/to-tickets` triage.
14.3 **What `/to-tickets` produces:** Implementation tickets derived from this specification, subject to existing contract governance and RULE 3 reuse-first constraints.

## Section 15 — Source Traceability

15.1 **Controlling documents:**
    - `.tmp/SETTLE-REC-000_EVIDENCE_PACK.md` — frozen evidence baseline (1,341 lines, REC-001..011, challenge pass, governance correction, launch delta, RULE 3 appendix).
    - `docs/00-Planning/SETTLE-REC-000_Immediate_Agent_Execution_Packet.md` — original execution packet (REC-001..REC-011).
    - `docs/00-Planning/SETTLE-SDLC-V3-001_Master_Pocock_Work_Package.md` — SDLC package.
    - `docs/00-Planning/SETTLE-REC-000 — Repository Truth & Ontology Reconciliation.md` — reconciliation baseline.
    - `app/shared/contracts.py` — canonical contracts (CONTRACT_VERSIONS, golden fixtures).
    - `app/core/service_auth.py` — WebhookSigner, WebhookVerifier.
    - `app/models/activation.py` — matter.activated contract artifacts.
    - `app/services/anonymizer.py` — sanitize_text().
    - `settle_data_scraping_factory/court_dockets_records/no_fabrication_gate.py` — verify_record.
    - `settle_data_scraping_factory/court_dockets_records/verdict_validator.py` — normalize_and_validate.
    - `settle_data_scraping_factory/court_dockets_records/cds_cap_loader.py` — existing loader.
    - `settle_data_scraping_factory/court_dockets_records/load_direct_supabase.py` — existing loader.
    - `_common/enrich.py` — existing enrichment.
    - `AGENTS.md` — persistent rules (RULE 1, 2, 3) and no-fabrication prime directive (RULE 0).
    - `tests/test_golden_fixtures.py` — 17 golden webhook tests.
15.2 **Repository state:** HEAD at `9b83e1b` (`docs: add skill reference table — Pocock fundamentals + TrueVow platform`). Only `AGENTS.md` modified (168 insertions). No other files changed.
15.3 **No fabrication of source traces:** Every source path listed above must be verifiable in the repository. If a source path cannot be verified, it must be STRIPPED from this document and flagged.

## Section 16 — Minimal Launch Architecture (Proposed)

16.1 **Principle:** The smallest useful trustworthy record over the largest possible form. Reuse existing architecture. Extend only where proven necessary.
16.2 **Existing architecture reused as-is:**
    - Verify-and-persist gate sequence (`no_fabrication_gate.py` → `verdict_validator.py` → enrich → persist).
    - `_common/enrich.py` source snippet capture.
    - `app/services/anonymizer.py` — `sanitize_text()`.
    - SETTLE Supabase database — existing settlement domain, case bank, contributions, offers/negotiations, liens/resolution.
    - Webhook signing/verification — `app/core/service_auth.py`.
    - Golden fixture tests — `tests/test_golden_fixtures.py`.
16.3 **Proposed minimal extensions (PROVE existing schema insufficient first):**
    - Historical contribution intake path (backend-only, no Customer Portal UI).
    - Provenance fields on contribution records (`source_url`, `field_evidence` per field).
    - Verification tracking fields (`validated_field_count`, `validation_counts` per record).
    - Analytics eligibility flags per record.
    - `sanitize_text()` disposition (Section 5).
    - `UNKNOWN`/`MISSING`/`NOT_APPLICABLE` preservation and `STRIPPED` suppression (RULE 0).
16.4 **Explicit non-architecture:**
    - No new database.
    - No new schema (unless proven necessary).
    - No new migration.
    - No new canonical event or contract.
    - No new ontology ID.
    - No C2/C7/C12 work.
    - No TRACE handoff.
    - No Customer Portal UI.

## Section 17 — Field Classification Reference

17.1 **Per-field classification rules (recap of Section 3):**
    - Provided with exact value + source_url + verbatim snippet → `VALUE_PROVENANCED`.
    - Passed both gates → `VALUE_VERIFIED`.
    - Meets analytics eligibility → `VALUE_ANALYTICS_ELIGIBLE`.
    - Not supplied → `UNKNOWN`, `MISSING`, or `NOT_APPLICABLE`. Never collapse.
    - Cannot be verified → `STRIPPED`. Never persist.
17.2 **Explicit collapses prohibited:**
    - `UNKNOWN` → default.
    - `MISSING` → empty string / null / zero.
    - `NOT_APPLICABLE` → default / empty / zero.
    - Total split in half.
    - Default enum when real one unknown.
    - Placeholder conversion.
17.3 **Record audit fields (per record):**
    - `validated_field_count` — count of fields that passed validation.
    - `validation_counts` — counts by validation status.
    - `field_evidence` — array of `{ value, snippet, source_url }` per field.

## Section 18 — Evidence Pack Reference

18.1 **Evidence pack location:** `.tmp/SETTLE-REC-000_EVIDENCE_PACK.md`.
18.2 **Evidence pack contents:** REC-001 through REC-011, challenge pass (5 challenges), governance correction (C2/C7 reclassification, C12 reservation, customer-facing confidence TRUE-GAP→EXTEND, sanitize_text()→EXTEND/LAUNCH-CRITICAL), launch delta (external/historical contributions = launch required), RULE 3 appendix.
18.3 **Evidence pack status:** FROZEN at REVIEW_BASELINE. Do not append. Do not reopen broad reconciliation.
18.4 **Evidence verification:** 1,341 lines, 89,493 characters, 0 non-ASCII characters, 0 CJK characters.

## Section 19 — Governance Correction Reference

19.1 **C2 (matter.activated):** Reclassified to PROPOSED RETIREMENT. Not yet retired. Out of scope for this specification.
19.2 **C7 (resolution-update):** Reclassified to PROPOSED RETIREMENT. Not yet retired. Out of scope for this specification.
19.3 **C12 (settle_events):** Reclassified to RESERVED. No writer, no drop, no reads from application code until disposition established. Out of scope for this specification.
19.4 **Customer-facing confidence:** TRUE-GAP (not a gap in the product, but a gap in stakeholder confidence). Must be addressed with evidence, not with fabricated data.
19.5 **`sanitize_text()`:** Extended to LAUNCH-CRITICAL PRIVACY HARDENING. Silently redacting PHI must not become an acceptance shortcut. Disposition specified in Section 5.

## Section 20 — Launch Delta Reference

20.1 **External / Historical Settlement Contribution:** LAUNCH REQUIRED (recorded in REC-000 governance correction).
20.2 **Not a future nice-to-have.** Must be supported as a backend capability.
20.3 **May represent a case that never existed in INTAKE, TRACE, or SETTLE matter development.** Do not require it to pretend it originated through the TrueVow lifecycle.
20.4 **Do not fabricate missing lifecycle records.** Historical contributions may have no prior lifecycle origin.

## Section 21 — Product Ownership Boundary Reference

21.1 **TrueVow product ownership boundaries (referenced from planning documents):** The specification must respect the frozen contracts and product ownership boundaries.
21.2 **SETTLE is primarily a verifier of incoming webhooks and a signer of outbound cross-service calls.**
21.3 **Canonical paths SETTLE verifies:** `POST /settle/webhooks/matter-activated` — receives matter.activated from TRACE.
21.4 **Canonical paths SETTLE signs:** `POST /settle/webhooks/resolution-update` — notifies COMMAND of resolution status changes.
22.5 **Authoritative contract location:** `app/shared/contracts.py` (CONTRACT_VERSIONS, golden fixtures).

## Section 22 — Re-Verification Rule

22.1 **Per REC-000 RULE 0, item 4:** The gate runs on EVERY scrape outcome — past and future. Re-verification of already-loaded data is mandatory whenever the gate changes.
22.2 **Rejected, purged, and quarantined records are preserved** (never destroyed) so they can be re-verified against their sources later and recovered if they legitimately pass.
22.3 **Historical contributions are subject to the same re-verification rule.** Any historical contribution loaded before a gate change must be re-verified when the gate changes.
22.4 **Re-verification is a specification requirement, not an implementation.** Implementation of the re-verification workflow is deferred to `/to-tickets`.

## Section 23 — Field-Level Validation Tracking

23.1 **Per REC-000 RULE 0, item 5:** Track validation per record. Persist `validated_field_count`, `validation_counts`, and `field_evidence` (value + snippet + source_url per field) so any row is auditable field-by-field, word-by-word, number-by-number.
23.2 **`field_evidence` structure:** `{ value: <verbatim>, snippet: <source snippet>, source_url: <traceable URL> }`.
23.3 **`validated_field_count`:** Integer count of fields that passed validation.
23.4 **`validation_counts`:** Counts by validation status (e.g., verified, stripped, unknown, missing, not_applicable).
23.5 **Auditability:** Any row must be auditable field-by-field. This is a non-negotiable requirement for legal product integrity.

## Section 24 — Minimal Provenance Model (Proposed)

24.1 **Principle:** Every field that enters the database MUST be verifiable. Verifiable = traces to a `source_url` AND appears verbatim in a stored evidence snippet.
24.2 **Proposed `field_evidence` model:**
    - Per field: `{ value: <verbatim>, snippet: <source snippet>, source_url: <traceable URL> }`.
    - Per record: `validated_field_count` (integer), `validation_counts` (object).
    - Per record: verification status tracking (e.g., `verified_at`, `gate_version`).
24.3 **Proposed source reference model:**
    - External/historical source document reference (e.g., `source_document_id`, `source_url`, `source_type`).
    - Must be traceable to the external/historical source.
24.4 **PROVE existing schema cannot represent before adding.** Reuse-first (RULE 3).

## Section 25 — Analytics Eligibility Criteria (Final)

25.1 **Eligible records must meet ALL criteria:**
    - `VALUE_VERIFIED` — passed both gates.
    - `VALUE_ANALYTICS_ELIGIBLE` — meets additional analytics-eligibility criteria.
    - `field_evidence` present for every field.
    - `validated_field_count` and `validation_counts` present.
    - No unverifiable fields persisted.
    - No fabricated fields, no default collapses, no placeholder conversions.
25.2 **Ineligible records:** Records with any `STRIPPED`, `UNKNOWN`, `MISSING`, or `NOT_APPLICABLE` fields that were collapsed, defaulted, or placeholder-converted.
25.3 **Preference:** Prefer the smallest useful trustworthy record over the largest possible form. Zero eligible records beats contaminated analytics.

## Section 26 — Existing Schema Reuse Proof Requirement

26.1 **Before any EXTEND is proposed, PROVE that the existing SETTLE schema/model cannot represent the requirement.**
26.2 **Proof must include:**
    - Existing table/column/enum/constraint/RLS policy that would be reused.
    - Why the existing schema is insufficient for the proposed extension.
    - What the proposed extension would add.
    - Migration + rollback + RLS/tenant-isolation + tests plan (if extension is approved).
26.3 **Do NOT add any table, column, enum, constraint, RLS policy, or migration unless the existing schema is proven insufficient.**
26.4 **No parallel database.** Do not create `settle_old_database`, `settle_v3_database`, `historical_contributions_database`, `analytics_database`, or any parallel data plane.

## Section 27 — Customer Portal Boundary

27.1 **Customer Portal owns attorney-facing UI.** SETTLE specifies backend capability only.
27.2 **This specification is backend-only.** No Customer Portal UI is designed, built, or authorized in this packet.
27.3 **Customer Portal follow-on is a separate, later work package.** It depends on this backend specification being reviewed and approved.
27.4 **Canonical SETTLE information stays in SETTLE's existing Supabase database.** The portal presents the UI and sends commands. It does not duplicate TRACE data or create a separate settlement database.

## Section 28 — Cross-Service Contract Boundary

28.1 **Frozen contracts SETTLE must comply with:**
    - WebhookSignature v1.0 — Sign + Verify.
    - EventEnvelope v1.0.1 — Validate on receive, emit on send.
    - MatterActivatedPayload v1.0 — Validate on receive.
    - ActivationEvidenceManifest v1.0 — Validate on receive.
28.2 **Do not edit, add, or remove canonical contracts.** Canonical contracts live in `app/shared/contracts.py`.
28.3 **Do not freeze new cross-service events or contracts.**
28.4 **Do not create new ontology IDs.**
28.5 **C2/C7/C12 out of scope.** Do not implement, fix, erase, write to, read from, drop, or repurpose them.

## Section 29 — Migration Tracking

29.1 **Auth source logged on every verification.**
29.2 **Legacy bearer auth deprecated after 2026-09-01.**
29.3 **Dual auth (HMAC OR legacy) during migration window.**
29.4 **Development, staging, and production must use different secrets.**
29.5 **Support primary/secondary key rotation via `TRUEVOW_WEBHOOK_SECONDARY_KEYS`.**
29.6 **Never log webhook secrets, complete signatures, or confidential request bodies.**
29.7 **Hash exact raw request bytes (no JSON re-serialization).**
29.8 **Validate signature hex format and buffer length before compare_digest.**
29.9 **Enforce event idempotency via event_id (not just timestamp window).**
29.10 **Resolve secrets strictly by key_id from env vars.**

## Section 30 — Artifact Convention

30.1 **Planning artifacts live under `docs/00-Planning/`.** Existing convention: `SETTLE-<NAME>.md`.
30.2 **This specification artifact title:** `SETTLE-CONTRIB-SPEC-001 External Historical Settlement Contribution Foundation`.
30.3 **Do not rename/mutate mislabelled planning files** (the two DOCX-with-.md-extension files). That is a separate repository-hygiene ticket.
30.4 **Implementation progress convention:** `docs/01-main/`.
30.5 **Architecture spec convention:** `docs/architecture/`.
30.6 **Do not create documentation files (*.md) unless explicitly requested by the user.** This specification artifact is explicitly requested by the user as part of this work package.

## Section 31 — Skill Reference

31.1 **Matt Pocock skills installed** in `.opencode/skills/engineering/` and `.opencode/skills/productivity/`.
31.2 **Skills used for this work package:** `truevow-plan` (for architecture/feature/refactor planning), `truevow-verify` (for verifying builds, tests, quality assurance), `truevow-build` (for coding features, fixing bugs, migrations — NOT authorized in this specification).
31.3 **Skill reference table:** Pocock fundamentals + TrueVow platform (committed in `9b83e1b`).

## Section 32 — Environment Reference

32.1 **Working directory:** `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\TrueVow_Tenant_SETTLE-Service`.
32.2 **Repository:** truevow-ai/TrueVow_Tenant_SETTLE_Service on master branch.
32.3 **HEAD:** `9b83e1b`.
32.4 **Platform:** win32.
32.5 **Today's date:** Sun Aug 30 2026.

## Section 33 — Writeback Protocol (TrueVow Orchestrator)

33.1 **Per AGENTS.md:** This service MUST write back learnings to the shared memory vault. Services without recent activity are flagged as STALE.
33.2 **Start of session:** `python ../TrueVow_Shared_Orchestration/orchestrator.py sync-memory`, `scan-services`, `agent-checkin start`.
33.3 **During work:** `python ../TrueVow_Shared_Orchestration/memory.py remember <category> "<title>" "<content>" --importance N`.
33.4 **End of session:** `python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin done`, `push-memory`.
33.5 **If blocked:** `python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin blocked`.
33.6 **Before any work:** `python ../TrueVow_Shared_Orchestration/orchestrator.py dispatch "<user's request>"`.

## Section 34 — Implementation Sequence (Per RULE 3)

34.1 **Required sequence:** Existing SETTLE Supabase → inspect existing schema → reuse existing entities → extend only where proven necessary → migration + rollback + RLS/tenant-isolation + tests → no duplicate database.
34.2 **Applies to:** External/historical settlement contribution launch requirement.
34.3 **Do not add an insert path that bypasses the verify-and-persist gates.**
34.4 **Do not create a parallel database.**
34.5 **Do not duplicate TRACE data in SETTLE.**

## Section 35 — Security Requirements (Non-Negotiable)

35.1 **Never log webhook secrets, complete signatures, or confidential request bodies.**
35.2 **Hash exact raw request bytes (no JSON re-serialization).**
35.3 **Validate signature hex format and buffer length before compare_digest.**
35.4 **Enforce event idempotency via event_id (not just timestamp window).**
35.5 **Resolve secrets strictly by key_id from env vars.**
35.6 **Development, staging, and production must use different secrets.**
35.7 **Support primary/secondary key rotation via `TRUEVOW_WEBHOOK_SECONDARY_KEYS`.**
35.8 **Legacy bearer auth accepted only during documented migration period (cutoff: 2026-09-01).**
35.9 **Record auth_source on every verification (hmac/legacy/bypass).**
35.10 **No-fabrication (RULE 0):** Every field entering the database MUST be verifiable. Zero records is preferable to one fabricated field.

## Section 36 — Test Strategy (Existing Convention)

36.1 **Existing test command:** `python -m pytest tests/` (Python, pytest + SQLAlchemy).
36.2 **Existing golden fixture tests:** `tests/test_golden_fixtures.py` (17 webhook tests). Do not modify.
36.3 **Proposed test categories (for /to-tickets):** See Section 13.
36.4 **Do not implement tests in this specification.** Test strategy is specified only.

## Section 37 — Implementation Frontier (Final)

37.1 **Authorized in this specification:** Frozen specification document for `/to-tickets` triage.
37.2 **NOT authorized:** Any implementation code, migration, schema change, new database, Customer Portal UI, TRACE handoff, C2/C7/C12 work, ontology registry edit, new canonical event/contract, test implementation.
37.3 **DOWNSTREAM_IMPLEMENTATION = NOT AUTHORIZED.**
37.4 **SETTLE-CONTRIB-SPEC-001 = REVIEW_REQUIRED.**

## Section 38 — Final Declaration

38.1 **AGENT_RESPONSE_LANGUAGE = ENGLISH**
38.2 **GENERATED_ARTIFACT_LANGUAGE = ENGLISH**
38.3 **REC_000_MODIFIED = NO**
38.4 **DATABASE_CREATED = NO**
38.5 **MIGRATION_CREATED = NO**
38.6 **SCHEMA_CHANGED = NO**
38.7 **DOWNSTREAM_IMPLEMENTATION = NOT AUTHORIZED**
38.8 **SETTLE-CONTRIB-SPEC-001 = REVIEW_REQUIRED**
38.9 **STOP**

## Section 39 — Bounded Governance Correction

39.1 **Scope of correction.** This section documents the bounded governance challenge applied to SETTLE-CONTRIB-SPEC-001. It does not reopen REC-000. It does not perform another broad repository audit. It does not implement anything, create migrations, or modify schema. It does not modify AGENTS.md.
39.2 **Overall architectural conclusion — ACCEPTED:** EXISTING ARCHITECTURE SUPPORTS LAUNCH AS-IS = NO. The primary proven gap is an external/historical pipeline-origin gap. Persistence/schema extension remains UNPROVEN.
39.3 **Correction 1 — CORRECT "SMALLEST PROVEN EXTENSION" (Section 11.3).** Physical field names (`source_url`, `field_evidence`, `validated_field_count`, `validation_counts`, analytics eligibility flags) were prematurely described as proven requirements, despite Section 8.3 stating the existing schema has not yet been proven insufficient. These have been demoted to **Candidate Persistence Representations — NON-CANONICAL / NOT PROVEN NECESSARY**. The smallest proven extension is now stated at the CAPABILITY level: external/historical intake, provenance, verification, analytics-eligibility, privacy acceptance hardening, and semantic preservation.
39.4 **Correction 2 — CORRECT `sanitize_text()` DISPOSITION (Section 8.2).** Changed from `REUSE-AS-IS / EXTEND` to `EXTEND / LAUNCH-CRITICAL PRIVACY HARDENING — existing utility may remain only outside prohibited acceptance semantics or behind explicit rejection/gating`. The specification must not imply that current silent-sanitization behavior is reusable as-is for historical contribution acceptance.
39.5 **Correction 3 — CHALLENGE `no_fabrication_gate.py` AND `verdict_validator.py` REUSE-AS-IS (Section 8.2).** Changed from `REUSE-AS-IS` to `EXTEND pending PHI-category coverage proof — existing mechanism may be retained only if tests/source inspection prove complete required launch coverage`. REUSE-AS-IS is allowed only if existing evidence proves the mechanisms already satisfy the launch requirement. Do not replace either mechanism.
39.6 **Correction 4 — CHALLENGE WEBHOOK SIGNING RELEVANCE (Section 8.2).** Changed from `REUSE-AS-IS` to `OUT-OF-SCOPE / NOT REQUIRED FOR CURRENT SPEC — do not include `app/core/service_auth.py` in the minimal historical-contribution architecture merely because it exists`. Determine only from already-inspected evidence whether the Customer Portal→SETTLE contribution path legitimately requires that existing mechanism. If no direct evidence establishes relevance, classify as OUT-OF-SCOPE. Do not invent a webhook/event contract. Do not modify C2/C7.
39.7 **Correction 5 — PRESERVE DATABASE DECISION.** PERSISTENCE CHANGE REQUIRED = MAYBE / UNRESOLVED. Do NOT convert to YES. Existing SETTLE Supabase remains the only permitted SETTLE database. Any future persistence extension requires proof that existing entities and relationships cannot safely represent the required capability.
39.8 **Correction 6 — PRESERVE ACCEPTED BOUNDARIES.** No changes to: External/Historical Contribution = LAUNCH REQUIRED, Customer Portal owns attorney-facing UI, SETTLE owns backend contribution/verification/eligibility authority, no fake TRACE lifecycle for historical cases, no TRACE domain duplication, C2/C7/C12 untouched, REC-000 frozen, no new ontology IDs, no new canonical events/contracts, no migration/schema change, no implementation.
39.9 **Delta result.** See the status declarations in the final section for the correction-applied state.

## Section 40 — Final Declaration (Post-Correction)

40.1 **SPECIFICATION_CORRECTION_APPLIED = YES**
40.2 **PHYSICAL_FIELDS_DEMOTED_TO_CANDIDATE = YES**
40.3 **SANITIZE_TEXT = EXTEND_LAUNCH_CRITICAL**
40.4 **NO_FABRICATION_GATE = EXTEND_PENDING_PHI_CATEGORY_COVERAGE_PROOF**
40.5 **VERDICT_VALIDATOR = EXTEND_PENDING_PHI_CATEGORY_COVERAGE_PROOF**
40.6 **WEBHOOK_SIGNING_FOR_CONTRIBUTION = OUT_OF_SCOPE**
40.7 **PERSISTENCE_CHANGE_REQUIRED = MAYBE_UNRESOLVED**
40.8 **EXISTING_SETTLE_SUPABASE_ONLY = YES**
40.9 **REC_000_MODIFIED = NO**
40.10 **DATABASE_CREATED = NO**
40.11 **MIGRATION_CREATED = NO**
40.12 **SCHEMA_CHANGED = NO**
40.13 **DOWNSTREAM_IMPLEMENTATION = NOT AUTHORIZED**
40.14 **SETTLE-CONTRIB-SPEC-001 = REVIEW_REQUIRED**
40.15 **STOP
