# SETTLE — Coding Agent Operating Instructions
## Read This Before Writing a Single Line of Code

**Version:** 1.0
**Date:** July 2026
**Classification:** Engineering — Required Reading
**Service:** TrueVow SETTLE™ (Settlement Database & Range Estimator) — attorney-owned settlement intelligence
**Trust domain:** TENANTS (Clerk App 3 "TrueVow-Tenants") — external, tenant-scoped, plus public API-key access
**Prerequisite:** SETTLE PRD, `SETTLE_FEATURE_ROADMAP.md`, the platform AGENTS.md, ADR-000 (Clerk over Auth0)

> This document is the operating standard for every line of code in SETTLE. It is not a set of guidelines. Any deviation requires explicit justification in the PR description and sign-off from the product owner.

---

## The One Thing That Matters Most

The person SETTLE serves is **a solo PI attorney preparing a demand letter or mediation brief.** They are sitting across from an insurance adjuster — or staring at an offer that is tens of thousands of dollars too low — and they need to say "here is what cases like this actually settle for in this county" with a straight face and a data-backed number. If your estimator returns a range that is catastrophically wrong — low enough to make them lowball their own client, or unsupported enough to collapse under cross-examination — you have cost an injured person tens of thousands of dollars they deserved. You have also cost the attorney their credibility, possibly their case, and certainly their trust in TrueVow.

This attorney needs three things from SETTLE and needs them instantly: (1) a settlement-range estimate they can bet their reputation on, (2) county-specific comparables that hold up to scrutiny, and (3) a blockchain-verified PDF report they can hand to opposing counsel knowing it is unassailable.

The second person SETTLE serves is **the injured client who never sees this product but whose financial future depends on its output.** If the estimator anchors too low, that client walks away with a fraction of what they should have received. If anonymization fails and their identity leaks through a contributed case, they are exposed in violation of bar ethics rules and possibly HIPAA.

The third person SETTLE serves is **the founding member attorney contributing settlements.** They entrusted TrueVow with sensitive financial outcome data (anonymized by design, but still competitively valuable). A leak of their contribution patterns or any client identifier attached to their data betrays that trust irreparably.

Everything below exists because breaking it eventually hurts one of those three people.

---

## Part 0 — What SETTLE Is (So You Don't Break It)

SETTLE is a **Python FastAPI service with a PostgreSQL database** that provides a shared, attorney-owned settlement database and instant (<1s) settlement-range estimates. It is the ethical, plaintiff-side alternative to Colossus — insurance industry tools that have historically been used to suppress payouts.

The defining architectural fact: **SETTLE is a shared service, not tenant-isolated at the database level.** All settlement data lives in one centralized `settle_db`. Tenant isolation is enforced by API-key authentication and query-level scoping, not by separate databases. The estimator operates on anonymized aggregate data. The blockchain verification path (OpenTimestamps → Bitcoin) produces reports that are independently verifiable by anyone with the `.ots` proof file.

Five constraints are non-negotiable:
1. **Anonymization is absolute.** No client name, no case caption, no party identifier, no attorney name (beyond the contributing firm's API key, stored separately from contribution data), no narrative text — ever — in a contributed settlement or a query result.
2. **Estimator correctness is life-or-death for a case.** A wrong range is worse than no range. The estimator must be deterministic, versioned, and tested per jurisdiction against known benchmarks.
3. **Estimate latency < 1 second.** An attorney waiting for a number during a mediation is losing leverage with every second. Algorithmic complexity must be budgeted against this hard target.
4. **Blockchain proofs must anchor and remain verifiable.** An OpenTimestamps proof that fails to anchor is not a proof at all. An expired or corrupted `.ots` file makes a report legally unverifiable.
5. **Data freshness is monitored.** A silently-stale scraping pipeline serves increasingly-wrong data. The estimator must surface data-age warnings when the underlying data pool is outdated.

---

## Part 1 — Build Philosophy

### 1.1 Boring is a Feature
Do not adopt a new estimation algorithm because the paper was published last month. Use documented statistical methods (numpy-based percentiles, jurisdictional weighting, confidence intervals from established formulas). **The test:** can you point to a statistics textbook, an established Python library, or a published legal-data methodology that supports this approach? If no, do not implement it.

### 1.2 Simple is Not Simplistic
Simple code means: one endpoint does one thing, one service function computes one estimate, names say what they contain, functions fit on one screen, no nested comprehensions deeper than two levels. **Junior developer test:** can a developer who has never seen this codebase understand the estimator's `compute_range()` function in 30 seconds? If not, rewrite it.

### 1.3 No Premature Abstractions
The estimator, anonymizer, and blockchain verifier are separate modules because they serve separate concerns. Everything else: build the simplest thing that works today. Do not build a "generic filter engine" when you have three query endpoints. Write the code twice before you abstract it.

### 1.4 The Attorney is Always Right About Their Trust
If a real attorney would hesitate before trusting a number, contributing their data, or handing a report to opposing counsel — the behavior is wrong, even if technically correct. When unsure, ask: *what would a PI attorney who has been burned by biased data before need to see to trust this?* Build that (confidence scores, data freshness, provenance, methodology transparency).

---

## Part 2 — Code Quality Rules (Non-Negotiable)

### 2.1 Every Function Does One Thing
`compute_range()` estimates. `resolve_comparables()` queries the database. `generate_report()` formats a PDF. These are three functions, not one. Max length is what fits on one screen (~40–50 lines including docstring).

### 2.2 Name Everything Like a Sentence
`estimate_settlement_range(case_params: CaseEstimationParams) -> SettlementRange` — not `est(ps)`. Never single-letter names outside loop counters. Never `data`, `result`, `info`, `obj`, `thing`, or `stuff`. An estimator variable named `result` is a bug waiting for the next developer to misunderstand.

### 2.3 Explicit Over Implicit
Keyword arguments, not positional. No `*args`/`**kwargs` in business logic. The estimator takes a typed `CaseEstimationParams` — never a raw dict. A mis-ordered positional argument in settlement math silently produces the wrong dollar figure.

### 2.4 Type Everything
Every function signature, every Pydantic model, every return value is typed. Run `mypy` on every commit and fail CI on errors. Type hints are part of the code, not optional documentation.

### 2.5 Handle Every Error Path — Especially in Live Queries
No bare `except:`, no swallowed exceptions, no silent fallback to a "default range." A timeout in the database query is a failure the attorney must see, not a silently-returned empty result set.

### 2.6 DRY — But Not at the Cost of Clarity
Do not share validation logic between the estimation endpoint and the contribution endpoint unless the validation is truly identical. If extracting a shared helper forces the reader to jump files to understand what an endpoint accepts, the duplication is better.

### 2.7 Comments Explain Why, Not What

```python
# Wrong — restates the code
# compute the 25th and 75th percentiles
p25 = np.percentile(amounts, 25)

# Right — explains the legal/methodological reason
# We report the 25th–75th percentile range, not the full min-max, because
# full-range ranges are misleading in front of a mediator — opposing counsel
# will cherry-pick the min, and the attorney needs defensible central tendency.
p25 = np.percentile(amounts, 25)
```

### 2.8 Write the Test Before You Think You're Done
Every piece of business logic has a test before the PR opens. The pyramid: unit tests for estimator math (percentile, confidence-interval, jurisdictional-weight calculation); integration tests for query endpoints against a seeded database; contract tests for API schemas. Coverage floor is 80%; the **estimator, anonymizer, and blockchain proof generation must be at 95%+** and must have tests proving they reject/alert on invalid inputs.

---

## Part 3 — Architecture Rules (Non-Negotiable)

### 3.1 One File Per Resource
Follow the repo layout exactly. Each API resource gets one router file. Each service gets one file. Do not put two endpoints' logic in one file because they "share a pattern."

### 3.2 The Estimator Owns Estimation — Nothing Else
The estimator module receives typed parameters and returns a typed range with confidence metadata. It does not query the database. It does not format PDFs. It does not log. It computes. A pure function you cannot unit-test with known inputs and expected outputs is an estimator you cannot trust.

### 3.3 No Business Logic in Routers
FastAPI routers parse, authorize, validate, route, and format. Business logic lives in service classes. No SQL in routers, no estimation `if/else` in routers.

### 3.4 The Service Layer Owns Business Logic
Every service takes its dependencies via constructor injection and is testable without a live database, a live Bitcoin node, or a live Stripe account. An estimator service you cannot unit-test is an estimator you cannot ship.

### 3.5 Database Access is Explicit — and Always Scoped
Use async SQLAlchemy with explicit loads (`selectinload`/`joinedload`); no lazy loading, no N+1. **Every query that returns settlement data includes anonymization filters before serialization.** Never return raw contribution rows to an API consumer; always pass through the anonymizer first.

### 3.6 Migrations Are Permanent (Alembic)
Every schema change is an Alembic migration with a working `downgrade()`. Never edit an applied migration; write a new one to correct it. Never run raw SQL against production. Test the downgrade in dev before merge.

### 3.7 Environment Variables Are the Only Configuration
No hardcoded URLs, keys, thresholds, model names, or API endpoints. Every value that differs between environments is an env var. Keep `env.template` current in the **same PR** that adds a variable. Never commit a real `.env`.

### 3.8 Explicit Disabled State — Never Infer Capability from Absence
Every optional capability (Stripe, SendGrid, scraping pipeline, OpenTimestamps) has an explicit `disabled` state via env var. An absent env var is a misconfiguration, not an "off" switch. A job that reads a disabled backend raises immediately with a message that tells the developer exactly what to set and why.

### 3.9 Auth — Consume `@truevow/auth-client`, Never Import Clerk Directly
Clerk (App 3 "TrueVow-Tenants") is the platform-wide auth standard. The SETTLE frontend consumes the shared `@truevow/auth-client`. The FastAPI backend verifies JWT tokens (Clerk-issued or API-key) in its auth middleware and normalizes claims into `AuthContext(userId, firmId, role, permissions)`. **Every endpoint consumes `AuthContext`, never a raw token or Clerk object.** Public API-key access is a separate auth path with explicit scope limitations. Why: services stay testable, intent stays readable, and any auth claim change is isolated to one adapter.

### 3.10 Observability Is Part of the Feature
SETTLE ships OpenTelemetry + Prometheus + Sentry. Every estimation query, every contribution, every blockchain anchoring attempt, and every data-freshness check emits a span/metric. Metrics must carry `firm_id`, `jurisdiction`, and `case_type` — never any contribution content or identifying metadata. Errors go to Sentry with `firm_id` and `endpoint` tags.

### 3.11 Schema First — Add Fields Before You Need Them
If the roadmap's data model shows a field a future phase will populate, add it now as a nullable column. One migration line today beats a production migration touching tens of thousands of rows later.

---

## Part 4 — Anonymization, Estimate Integrity & Legal Admissibility

### 4.1 Anonymization Is Absolute — Zero Client Identifiers, Always
Every contributed settlement is stripped of client identifiers **before it touches the database.** No client name, case caption, party identifier, attorney name, narrative description, or free-text field may appear in a stored contribution. The anonymizer runs at the API boundary — before the INSERT — and rejects any contribution that contains identifiable text. **Verification:** regular automated scans of the contributions table must confirm zero PII/PHI patterns exist.

### 4.2 Settlement Math Must Be Deterministic, Versioned, and Battle-Tested
The estimator's percentile calculations, jurisdictional-weight formulas, and confidence-interval methods must be: (1) **deterministic** — same inputs always produce the same outputs; (2) **versioned** — any algorithm change increments a version that appears in report metadata so an attorney can prove which version produced their estimate; (3) **tested against known benchmarks** — known datasets with known distributions must produce expected ranges. A wrong low estimate costs a real client real money.

### 4.3 Data Integrity: Never Serve Stale Data Without Warning
The estimator must carry a `data_freshness` field on every response indicating the newest contribution date in the relevant pool. If the pool is older than a configured threshold, the response includes a warning: "The settlement data used for this estimate may be out of date. Estimates based on data older than [threshold] are less reliable." The scraping pipeline must emit a health metric; if the pipeline fails to update within a configured window, the estimator must surface degraded-data warnings automatically.

### 4.4 OpenTimestamps Anchoring Must Be Verified Before the Report Is Downloadable
A report is not "generated" until the `.ots` proof has been submitted to the Bitcoin calendar server and a pending confirmation is received. If anchoring fails (timeout, calendar unreachable), the generation endpoint returns an error — it never returns a report with a broken proof. The system must retry anchoring with exponential backoff before failing. A `pending_anchor` status is acceptable for a bounded window (minutes, not hours). After that window, the certificate transitions to a failure state and the attorney is notified.

### 4.5 API-Key Security — Never Expose Keys in Logs, URLs, or Responses
SETTLE API keys (for public/programmatic access) are stored hashed in the database. The plaintext key is returned once at creation and never again. Key validation is constant-time. Keys never appear in logs, URL paths, query strings, or response bodies — only in the `Authorization` header.

### 4.6 Blockchain Proof Integrity — `.ots` Files Are Immutable Post-Generation
Once a `.ots` proof file is generated and stored, it must never be modified, regenerated, or replaced. The file path in S3/CDN must be content-addressed or otherwise immutable. A modified proof file breaks the chain of trust and makes the certificate unverifiable — or worse, verifiably wrong with no detectable error.

### 4.7 Secrets Never Touch Git
`fly secrets set` for production, `.env.local` for dev, `env.template` (placeholders only) in git. If a secret is ever committed: rotate it first, then scrub history, then notify the team.

---

## Part 5 — The Attorney Experience (This Is the Product)

### 5.1 Latency Is a Feature — Under 1 Second Is a Requirement
The attorney at a mediation needs an estimate right now, not in 3 seconds. Budget every query, every computation, every serialization against the 1-second hard target. Profile the estimator. Cache jurisdiction-level aggregate statistics. A slow estimate is an estimate the attorney cannot use when it matters most.

### 5.2 Every Report Must Be Self-Contained and Courtroom-Ready
A generated PDF report must contain: the estimate range, confidence interval, county comparables, methodology summary, data-freshness date, blockchain proof reference, and a verification URL. A report that requires the recipient to "log in to see the data" is not a report — it is a link to a login wall. The report must stand alone as a document the attorney can attach to a demand or hand to a mediator.

### 5.3 Confidence Scores Must Be Honest — Not Marketed
A confidence score that rounds 0.62 to "High Confidence — Green" when the underlying data pool is shallow and stale is dishonest and dangerous. The score must accurately reflect: data pool size, freshness, jurisdictional match quality, and variance. A low-confidence estimate with an honest "Use with caution — limited data in this jurisdiction" warning is more valuable than a green-badged wrong number.

### 5.4 Errors the Attorney Sees Are Written for a Non-Technical Person
Error and empty states are plain English with a next action and a support contact — never HTTP codes, stack traces, "null", "undefined", "timeout", or JSON. Every empty state explains why it is empty and what to do next. An estimation failure says "We could not calculate an estimate right now. Please try again or contact support@truevow.law." — not "EstimatorError: percentile() requires at least 5 data points."

### 5.5 The Contribution Experience Must Feel Safe
The contribution page must explicitly confirm: "Your contribution is anonymous. No client names, case identifiers, or personally identifying information will be stored. Only the case type, jurisdiction, and financial figures are recorded." Before submission, a preview confirms exactly what data will be (and will not be) shared.

---

## Part 6 — Code Review Standards

### 6.1 The PR Description Is Part of the Code
Every PR states: what changed (plain English), why (link to spec/issue), how to test it manually (step by step), and any risks. "Fixed the estimator" is not mergeable.

### 6.2 Four-Eyes Rule for High-Stakes Code
Explicit second-reviewer sign-off — a comment confirming the specific concern was checked — is required for any change that:
- modifies the **estimator algorithm** or its confidence-interval math,
- modifies the **anonymizer** or its rejection rules,
- modifies **OpenTimestamps anchoring** or `.ots` proof handling,
- changes how **contribution data** is stored, serialized, or queried,
- changes **API-key authentication or scope**,
- modifies the **data-freshness monitoring** or scraping pipeline health checks.

### 6.3 Migrations Require Extra Care
Before merge: `alembic upgrade head` and `alembic downgrade -1` both succeed on a fresh DB and on a DB with existing data; the schema matches the spec data model. No migration merges on a Friday.

### 6.4 No Dead Code
No commented-out code, no unused imports, no TODOs older than a sprint. The only allowed marker is `# AGENT CHOICE: [description] — flagged for review`, to be resolved next sprint.

---

## Part 7 — Deployment Rules

### 7.1 Production Is Sacred
Production is where real attorneys query real settlement data to negotiate real cases. Pipeline: merge to `main` → auto-deploy to staging → full test suite → manual, signed-off production deploy, logged (who/when/what). No production deploys on Friday afternoon. No production deploy that has not run in staging — **including a live estimation query against the staging database.**

### 7.2 Secrets Never Touch Git
See §4.7. `fly secrets set` is the only path for production credentials.

### 7.3 Rollback Must Be Possible in Under 5 Minutes
Every deploy is rollback-able and tested in staging first. An estimator regression in production is wrong estimates going to real mediations.

---

## Part 8 — The Simplicity Test

Before marking any work complete, run it through these:

1. **Would a Python backend developer joining today understand the estimator, anonymizer, and blockchain verifier in 30 minutes without asking anyone?** If no: simplify or comment until yes.
2. **Could a real attorney trust this settlement-range estimate in front of a mediator?** If no: fix the math, the confidence score, or the data freshness — and add the test that proves it.
3. **Could any client identifier or PII appear in a contributed settlement, a query result, a log, or a report?** If yes: harden the anonymizer before merging.
4. **Could the `.ots` proof fail to anchor or verify, rendering the report legally worthless?** If yes: add explicit anchor verification, retry logic, and a failure-mode alert.
5. **If this estimator breaks at 2am before a morning mediation, does the attorney get a clear error — not a silent wrong number?** If they get a wrong number: add observable failure modes with honest error messages.

---

## Report to the Orchestrator — Mandatory Session Protocol

You are not working alone. This service reports to the TrueVow CTO Orchestrator, whose **only** real-time visibility into your work comes from two channels: your **git state** and your **check-ins**. If you never check in, the orchestrator dashboard shows this service as `NEGLECTED`, the CTO is flying blind, and stalled or half-finished work stays invisible.

A task is not "done" until the check-in is posted. **Intent is not completion.**

**Start of every session:**
```
python ../TrueVow_Shared_Orchestration/orchestrator.py sync-memory
python ../TrueVow_Shared_Orchestration/orchestrator.py scan-services
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin start "SETTLE: <task> | resuming from <state> | goal: <what success looks like>"
```

**During work — record decisions as they happen:**
```
python ../TrueVow_Shared_Orchestration/memory.py remember <category> "<title>" "<content>" --importance N
```

**End of session — write back, then push:**
```
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin done "SETTLE: <accomplished> | outcome: <result> | learned: <insight> | next: <remaining>" --status DONE
python ../TrueVow_Shared_Orchestration/orchestrator.py push-memory
```

**If blocked — raise it immediately, never go silent:**
```
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin blocked "SETTLE: <blocker> | attempted: <what you tried> | need: <what unblocks you>"
```

**RULE 0 — No fabrication.** Never report a build, a test count, or a metric you did not actually produce. If a command did not run green in front of you, it is not green. A stub result is not a real result. Binding platform-wide.

---

## The Final Instruction

You are not building a settlement database. You are building the data foundation that lets a solo PI attorney walk into a mediation room and say "the data says this case is worth $X" — and be right. That number will be the difference between a client who can afford their spinal surgery and a client who goes bankrupt waiting. Whether the attorney trusts that number, and whether it holds up when an adjuster or a judge scrutinizes it, depends on whether your estimator used the right percentiles, whether your anonymizer truly stripped every identifier, and whether your blockchain proof anchors to a block that will still verify in five years.

The code you write is the difference between an attorney with data-driven leverage and an attorney who gets lowballed because they had nothing but instinct.

Write code like it matters. Because it does.

---

*These instructions apply to every line of code written for SETTLE. They are the operating standard, not guidelines. Any deviation requires explicit justification in the PR description and product-owner sign-off.*

*Last updated: July 2026*
