# TrueVow_Tenant_SETTLE-Service — Agent Rules

# Agent Onboarding Preamble
# Drop this into any service's AGENTS.md to wire it into the ecosystem.
# The agent reads this on startup and becomes ecosystem-aware.

## WRITEBACK PROTOCOL (MANDATORY)

**You report to the TrueVow CTO Orchestrator.** Every session you work on this service, you MUST write back your learnings to the shared memory vault. Services without recent activity are flagged as STALE. Do not let this service go stale.

**Format for all writebacks:** "<service>: <specific action taken> | <result/outcome> | <what you learned> | <next step or blocker>"

### Start of Session — Activate Service
```
python ../TrueVow_Shared_Orchestration/orchestrator.py sync-memory
python ../TrueVow_Shared_Orchestration/orchestrator.py scan-services
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin start "SETTLE: <specific task> | resuming from <previous state> | goal: <what success looks like>"
```

### During Work — Log Learnings
```
python ../TrueVow_Shared_Orchestration/memory.py remember <category> "<title>" "<content>" --importance N
```
Categories: architecture, pattern, decision, dependency, convention, bug, context, todo, relationship
Importance: 10 = critical blocker, 8 = important decision, 5 = observation

### End of Session — Writeback Results
```
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin done "SETTLE: <what was accomplished> | outcome: <result> | learned: <key insight> | next: <what remains>" --status DONE
python ../TrueVow_Shared_Orchestration/orchestrator.py push-memory
```

### If Blocked — Alert Immediately
```
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin blocked "SETTLE: <specific blocker> | attempted: <what you tried> | need: <what will unblock>"
```

### Before Any Work — Route the Task
```
python ../TrueVow_Shared_Orchestration/orchestrator.py dispatch "<user's request>"
```

### Security & Research
- Scan new skills: `skillspector scan <path> --no-llm`
- Web research: `agent-reach doctor` for status

### Skill Reference
Two families via `orchestrator.py dispatch` or `/truevow-ask`:
| Task | Skill |
|------|-------|
| Review code | `/code-review` (Pocock) |
| Write tests | `/tdd` (Pocock) |
| Security | `/security-and-hardening` (TrueVow — bar-compliant anonymization) |
| Deploy | `/shipping-and-launch` (TrueVow) |

**Reminder:** 12 of 13 services are currently STALE (>24h without agent activity). Write back to prove this one is alive. The CTO dashboard refreshes every scan.


---

## Service-Specific Rules

> Add service-specific rules below. The ecosystem preamble above is auto-generated
> and wires this agent into the TrueVow Agent Ecosystem.

## WebhookSignature v1.0 — SETTLE Responsibilities (frozen contract)

SETTLE is primarily a **verifier** of incoming webhooks and a **signer** of outbound
cross-service calls.

### Canonical paths SETTLE verifies:
- `POST /settle/webhooks/matter-activated` — receives matter.activated from TRACE

### Canonical paths SETTLE signs:
- `POST /settle/webhooks/resolution-update` — notifies COMMAND of resolution status changes

### Authoritative contract location:
- Contract: `app/shared/contracts.py` (CONTRACT_VERSIONS, golden fixtures)
- Signing/verification: `app/core/service_auth.py` (WebhookSigner, WebhookVerifier)
- Golden tests: `tests/test_golden_fixtures.py` (17 webhook tests)

### Frozen contracts SETTLE must comply with:
| Contract | Version | SETTLE Role |
|---|---|---|
| WebhookSignature | v1.0 | Sign + Verify |
| EventEnvelope | v1.0.1 | Validate on receive, emit on send |
| MatterActivatedPayload | v1.0 | Validate on receive |
| ActivationEvidenceManifest | v1.0 | Validate on receive |

### Security requirements (non-negotiable):
- Never log webhook secrets, complete signatures, or confidential request bodies
- Hash exact raw request bytes (no JSON re-serialization)
- Validate signature hex format and buffer length before compare_digest
- Enforce event idempotency via event_id (not just timestamp window)
- Resolve secrets strictly by key_id from env vars
- Development, staging, and production must use different secrets
- Support primary/secondary key rotation via TRUEVOW_WEBHOOK_SECONDARY_KEYS
- Legacy bearer auth accepted only during documented migration period (cutoff: 2026-09-01)
- Record auth_source on every verification (hmac/legacy/bypass)

### Migration tracking:
- Auth source logged on every verification
- Legacy bearer auth deprecated after 2026-09-01
- Dual auth (HMAC OR legacy) during migration window

## RULE 0 — NO-FABRICATION PRIME DIRECTIVE (NON-NEGOTIABLE, NEVER COMPROMISE)

**SETTLE is a legal product. Fabricated data will kill it. This rule overrides
every other consideration — speed, record counts, stakeholder optics, deadlines.
There is no circumstance under which it is relaxed.**

1. **Every field that enters the database MUST be verifiable** — it must trace to
   a `source_url` AND appear verbatim in a stored evidence snippet:
   numbers by their digits, strings by substring, ages by an in-range number in
   the snippet, enums by a justifying keyword, dates by their parts, lists
   element-by-element. If it cannot be verified, it is **stripped** — never kept,
   never guessed.

2. **NEVER guess, infer, hallucinate, or "salt" ANY value.** This explicitly
   includes: injury types, medical bills, damages (economic / non-economic /
   punitive), settlement/verdict amounts, insurance carriers, courts, judges,
   dates, expert-witness counts, case types, plaintiff age, liability tier,
   comparative negligence, defendant category, source URLs — and anything else.
   No fallback buckets (e.g. a default `personal_injury_general` case_type). No
   splitting a total in half. No default enum when the real one is unknown.

3. **Zero records is preferable to one fabricated field.** Do NOT grow the record
   count to please stakeholders. A smaller, fully-verifiable database beats a
   large contaminated one, always.

4. **The gate runs on EVERY scrape outcome — past and future.** Re-verification
   of already-loaded data is mandatory whenever the gate changes. Rejected,
   purged, and quarantined records are preserved (never destroyed) so they can be
   re-verified against their sources later and recovered if they legitimately
   pass.

5. **Track validation per record.** Persist `validated_field_count`,
   `validation_counts`, and `field_evidence` (value + snippet + source_url per
   field) so any row is auditable field-by-field, word-by-word, number-by-number.

### How this is enforced in code (keep it this way)
- `settle_data_scraping_factory/court_dockets_records/no_fabrication_gate.py`
  (`verify_record`) — the universal evidence gate. Run it FIRST.
- `settle_data_scraping_factory/court_dockets_records/verdict_validator.py`
  (`normalize_and_validate`) — enum/format/bounds gate. Run it SECOND.
- Both loaders (`cds_cap_loader.py`, `load_direct_supabase.py`) run BOTH gates
  before any insert. Never add an insert path that bypasses them.
- `_common/enrich.py` captures a source snippet for EVERY field it extracts.
- Every new source pipeline (carriers, govdata, etc.) MUST route through the
  same two gates before touching the DB.
- All gate/enricher changes must keep their `--selftest` green.

**If you are ever tempted to loosen this to make numbers look better: don't.
Re-read this rule. The answer is no.**

---

## RULE 1 — AGENT OUTPUT LANGUAGE (NON-NEGOTIABLE)

**All human-readable communication produced by any SETTLE coding agent MUST be in English.**

This requirement applies to every user-visible message, including:
- reasoning summaries and progress reports
- task status and terminal summaries
- findings, explanations, recommendations, and questions
- error reports and diagnostics
- evidence-pack prose, Markdown documentation, ticket reports, and review reports

Repository source material may contain other languages and may be quoted when
necessary as evidence, but the agent's **explanation** of that evidence MUST be in
English.

### Two independent checks — BOTH must pass

1. **ARTIFACT LANGUAGE** — are files created or modified by the task written in English?
2. **AGENT RESPONSE LANGUAGE** — is every human-readable message emitted by the
   coding agent itself written in English?

Checking whether repository files contain non-ASCII or Chinese characters does
NOT satisfy this requirement. Those are different questions.

### Final gate before emitting any user-visible response

```
OUTPUT_LANGUAGE_GATE
required_language = English
```

If the proposed response contains Chinese-language explanatory prose, translate
or rewrite the entire response into English BEFORE emitting it.

Do not report that the output is English unless the actual response being
delivered to the user is itself in English.

### Do not switch languages based on

- detected repository content
- terminal locale
- operating-system locale
- file encoding
- source-language detection
- previous tool output
- model-generated intermediate reasoning

The user's working language for this repository is English.

### Failure condition

Any agent-authored Chinese prose in a user-visible response is an output contract
failure.

### When reporting completion, include

```
AGENT_RESPONSE_LANGUAGE = ENGLISH
GENERATED_ARTIFACT_LANGUAGE = ENGLISH
```

These statements must describe the actual emitted response and artifacts, not
merely a character scan of repository files.

---

## RULE 2 — REPOSITORY HYGIENE: DO NOT RENAME MISLABELED FILES

`docs/00-Planning/TrueVow_SETTLE_Final_Boundary_Corrected_Plan.md` and
`docs/00-Planning/TrueVow_SETTLE_Final_Product_Implementation_Plan_v3_RERENDERED.md`
are **DOCX/ZIP files with a `.md` extension**, not Markdown.

A `.md` file that actually contains binary OOXML data breaks glob, grep, and any
document scan that trusts the extension. The correct `.docx` files exist beside
them.

**Do not rename them during a reconciliation run.** Renaming is a repository
modification and must be done deliberately, as its own change, with owner review —
not mixed into read-only work.

---

## RULE 3 — DATABASE GOVERNANCE (NON-NEGOTIABLE)

**All SETTLE database changes go through the EXISTING SETTLE Supabase database and
its existing migration/governance system. Do not create another database for new
settlement capabilities.**

### Intended architecture

```text
Customer Portal
     │
     │ attorney UI / external case entry
     ▼
SETTLE APIs
     │
     │ validation + business rules
     ▼
EXISTING SETTLE SUPABASE DATABASE
     │
     ├── existing settlement domain
     ├── existing case bank
     ├── existing contributions
     ├── existing offers / negotiations
     ├── existing liens / resolution
     └── necessary governed extensions
```

### 1. REUSE BEFORE ADDING

Before creating any table or column, the coding agent must PROVE that the existing
SETTLE schema/model cannot represent the requirement. REC-000 has already shown why
this matters — capabilities that existed were initially mistaken for gaps. Do not
repeat that mistake.

### 2. EXTEND THE EXISTING SETTLE DATABASE WHEN GENUINELY NECESSARY

Launch-grade historical contributions may eventually require additional provenance,
verification, analytics-eligibility or evidence relationships. If reconciliation
proves those are missing, add them through normal SETTLE Supabase migrations —
migration + rollback + RLS/tenant-isolation + tests.

### 3. NO PARALLEL "V3 DATABASE"

Do not create:

```text
settle_old_database
settle_v3_database
historical_contributions_database
analytics_database
```

Unnecessary complexity for the current product. A separately governed data plane
is permitted only if a genuine scale/security reason arises someday.

### 4. DO NOT DUPLICATE TRACE DATA IN SETTLE

SETTLE may persist the smallest governed settlement-context projection it legitimately
needs. It must NOT copy TRACE's medical chronology, raw PHI, evidence documents,
treatment records, liability evidence, etc. into its database simply because the
Customer Portal needs to display something.

### 5. CUSTOMER PORTAL IS NOT ANOTHER SETTLEMENT DATABASE

The portal presents the UI and sends commands. Canonical SETTLE information stays
in SETTLE's existing Supabase database.

### 6. C12's `settle_events` TABLE IS NOT PERMISSION TO START USING IT

We still do not know its intended authority. Leave it alone until reconciliation
establishes what it was supposed to do. No writer. No drop. No reads from application
code until disposition is established.

### Required implementation sequence

> Existing SETTLE Supabase → inspect existing schema → reuse existing entities →
> extend only where proven necessary → migration + rollback + RLS/tenant-isolation
> + tests → no duplicate database.

That applies particularly to the new launch requirement for external/historical
settlement contributions. If database changes are genuinely required to make those
contributions evidence-backed and trustworthy, make those changes properly within
the existing SETTLE Supabase architecture.
