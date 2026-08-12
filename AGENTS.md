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
