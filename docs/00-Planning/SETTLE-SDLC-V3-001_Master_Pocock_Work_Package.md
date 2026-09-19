# TrueVow SETTLE — Revised Implementation SDLC Work Package

**Package ID:** `SETTLE-SDLC-V3-001`  
**Planning basis:** `TrueVow SETTLE Final Product & Implementation Plan v3`  
**Cross-product governance:** `SETTLE-PLAN-TRACE-HANDOFF-001`  
**Immediate unit:** `SETTLE-REC-000`  
**Status:** PLANNING PACKAGE / RECONCILIATION AUTHORIZED / IMPLEMENTATION NOT YET AUTHORIZED  
**Method:** Maturity-first Matt Pocock workflow adapted to TrueVow governance  
**Language:** English only

---

# 0. Why this package exists

This package converts the revised SETTLE V3 planning direction into an executable software-development control system without prematurely implementing assumptions.

The governing rule is:

```text
REPOSITORY TRUTH AUDIT
        ↓
MATURITY CLASSIFICATION
        ↓
APPROPRIATE SKILL
        ↓
SPEC / TICKETS IF REQUIRED
        ↓
IMPLEMENT
        ↓
CODE REVIEW
        ↓
INDEPENDENT TRUEVOW VERIFICATION
        ↓
PASS
        ↓
MERGE / FREEZE
        ↓
TRUTH + MATURITY WRITEBACK
```

`SETTLE-REC-000` must happen first.

No downstream schema, canonical event, ENT identifier, migration or implementation slice becomes authorized merely because it appears in this document.

---

# 1. Authority order

When sources disagree, use:

```text
accepted canonical platform ontology / frozen contracts
        ↓
current accepted code + database behavior
        ↓
accepted tests / gate evidence
        ↓
approved current product decisions
        ↓
SETTLE Final Product & Implementation Plan v3
        ↓
SETTLE-PLAN-TRACE-HANDOFF-001
        ↓
active specifications
        ↓
README / integration prose / comments
        ↓
historical / archived artifacts
```

Important:

- current code that violates a frozen accepted contract is a defect, not new architecture truth;
- stale prose never outranks accepted code/contracts;
- contradictions between legitimate authorities become `CONTRACT-CONFLICT`;
- do not silently resolve architecture disagreements through implementation.

---

# 2. TrueVow maturity-first routing

## Pre-step — Repository Truth Audit

`SETTLE-REC-000` is a pre-implementation truth audit.

It produces exactly one primary classification per relevant capability/artifact:

```text
KEEP
EXTEND
MOVE-TO-TRACE
SHED
TRUE-GAP
CONTRACT-CONFLICT
```

Then convert those classifications into maturity classes:

| REC classification | Default maturity | Correct next action |
|---|---|---|
| KEEP | A — BUILT_PROVEN or B — BUILT_AWAITING_PROOF | protect or verify |
| EXTEND | C if behavior violates settled intent; D if accepted new capability is missing | bounded repair or `/to-spec` |
| MOVE-TO-TRACE | ownership redirect | no SETTLE implementation |
| SHED | C/retirement or no-build | explicit retirement plan if code exists |
| TRUE-GAP | D — DEFINED FEATURE | thin `/to-spec` → `/to-tickets` |
| CONTRACT-CONFLICT | E if architecture genuinely unresolved; C if frozen contract clearly controls | `/wayfinder` only if truly unresolved, otherwise repair |

Complexity alone never triggers `/wayfinder`.

---

# 3. Matt Pocock skill routing

Use skills as tools, never as architecture authority.

## `/wayfinder`

Use only when `SETTLE-REC-000` proves a genuinely unresolved product/architecture decision.

Valid examples:
- two legitimate accepted authorities disagree and neither clearly controls;
- aggregate ownership between SETTLE and another service remains unresolved;
- future cross-product authority cannot be determined from accepted ontology.

Do NOT use for:
- already-built code needing verification;
- defects against a settled invariant;
- a feature that V3 already defines;
- implementation complexity;
- stale README contradictions when canonical truth is clear.

## `/to-spec`

Use for:
- `TRUE-GAP` Class D units;
- substantive `EXTEND` units whose behavior is decided but implementation contract needs definition;
- wide/security-sensitive Class C repairs.

Every `/to-spec` invocation gets exactly:

```text
1. current accepted SETTLE canonical truth / V3 planning authority
2. actual accepted repository SHA / DB state
3. one explicitly authorized unit from REC-000
```

Also include:
- `SETTLE-PLAN-TRACE-HANDOFF-001` when the unit touches TRACE;
- no historical document bundle unless specifically needed for a conflict.

## `/to-tickets`

Break one approved spec into independently verifiable tracer bullets.

Tickets must:
- have one purpose;
- identify exact files/models/contracts expected;
- state dependencies;
- state tests;
- state forbidden scope;
- define acceptance evidence;
- preserve green intermediate states.

## `/implement`

One ticket / branch / purpose.

Implementation must:
- follow accepted spec;
- preserve ontology ownership;
- preserve no-fabrication;
- preserve privacy boundary;
- avoid unrelated refactors;
- add tests before claiming completion.

## `/code-review`

Review against both:
1. engineering standards;
2. the approved spec/ontology boundary.

Builder fixes findings before independent TrueVow verification.

## Independent TrueVow verification

Builder green is not Gate PASS.

TrueVow independently checks:
- repo diff;
- DB/migrations where applicable;
- contracts;
- tests;
- privacy;
- ontology;
- callers;
- no fabricated values;
- no hidden cross-product coupling.

Only then:
`PASS → merge/freeze → truth/maturity writeback`.

---

# 4. Immediate authorized slice — SETTLE-REC-000

**Type:** reconciliation slice  
**Implementation changes:** forbidden  
**Canonical events/ENT IDs:** forbidden  
**Migrations:** forbidden  
**Future handoff contract:** forbidden to freeze

## Objective

Reconcile V3 and handoff governance against actual SETTLE repository truth and return an evidence-backed map:

```text
KEEP
EXTEND
MOVE-TO-TRACE
SHED
TRUE-GAP
CONTRACT-CONFLICT
```

---

# 5. REC-000 ticket package

These are the only tickets authorized now.

## REC-001 — Authority Baseline
**Goal:** freeze the evidence hierarchy used by reconciliation.

Inspect:
- V3;
- `SETTLE-PLAN-TRACE-HANDOFF-001`;
- `AGENTS.md`;
- accepted canonical contracts;
- current main SHA;
- accepted tests/golden fixtures.

Deliver:
- authority matrix;
- conflict-handling rule;
- repository SHA under review.

No code changes.

## REC-002 — Repository Surface Inventory
Inventory actual current surfaces:
`app/api/`, `app/core/`, `app/models/`, `app/services/`, `app/shared/`, database/migrations/tests/docs.

Classify runtime/tooling/archived/active/duplicate/unknown.
## REC-003 — Canonical Contract Inventory

Inspect:
`app/shared/contracts.py`, `app/core/service_auth.py`, webhook endpoints, golden fixtures, event/authority/ontology registries.

Record contract/version/producer/consumer/path/auth/payload/idempotency/callers/tests/deployment/status.

Special focus:
- `EventEnvelope v1.0.1`;
- `MatterActivatedPayload v1.0`;
- `ActivationEvidenceManifest v1.0`;
- `WebhookSignature v1.0`;
- current `trace_to_settle` contract surface.

**Known evidence entering REC-003 (provisional — verify independently):**

```text
Existing TRACE→SETTLE contract surface:
    frozen shared contract artifacts — EXISTS
    TRACE-authorized matter.activated path configuration — EXISTS

    executable SETTLE receiver — NOT IMPLEMENTED
    router registration — NOT IMPLEMENTED
    production caller — NONE FOUND
```

Preliminary evidence indicates the corresponding SETTLE receiver and production
invocation path are not implemented. REC-007 must independently verify and
classify this discrepancy before downstream work is authorized.

No replacement contract design.

## REC-004 — SETTLE Ontology Map
Map current:
case/matter reference, settlement analysis, comparable, offer, negotiation timeline, lien resolution, net recovery, settlement result, contribution, report, authority, events, projections.

For every entity:
source vs derived, authoritative vs projection, owner, state machine, evidence/provenance, privacy, duplicate candidates.

## REC-005 — Model & Schema Reconciliation
Inspect actual persistence, including current models such as:
`activation.py`, `case_bank.py`, `settlement.py`, `verdicts.py`, `reports.py`, `billing.py`, `api_keys.py`.

Compare V3 concepts to existing persistence.

For each proposed V3 entity:
reuse existing / extend / move to TRACE / shed / true gap / conflict.

Do NOT create migrations.

## REC-006 — Service / Capability Reconciliation
Inspect existing services including:
`estimator.py`, `confidence_score.py`, `outcome_distribution.py`, `anomaly_detector.py`, `intelligence_gate.py`, `carrier_patterns.py`, `contributor.py`, `anonymizer.py`, `billing/`, `integrations/`.

Apply:
- law-firm value test;
- duplication test;
- explainability test;
- professional-authority test.

## REC-007 — `matter.activated` E2E Audit
Prove current endpoint/producer/callers/production callers/tests/side effects/DB writes/state transitions/idempotency/deployment use/bootstrap-vs-settlement-start semantics.

### Known evidence entering REC-007 (provisional — verify independently)

```text
matter.activated CURRENT PROVEN BASELINE

Contract declaration:       EXISTS
Auth/path configuration:    EXISTS
Golden-fixture support:     EXISTS

Route handler:              DOES NOT EXIST
Router registration:        DOES NOT EXIST
Executable receiver:        DOES NOT EXIST
Production caller:          NONE FOUND
Observed runtime behavior:  NONE

TRACE-as-producer:
CONFIGURED BY CONTRACT/AUTH METADATA
NOT PROVEN BY AN EXECUTABLE CALL PATH
```

**FROZEN CONTRACT EXISTS ≠ RECEIVER IMPLEMENTED EXISTS.**

The repository contains frozen `matter.activated` contract artifacts and
service-auth configuration, but preliminary repository inspection found no
corresponding route handler, router registration, executable receiver, or
production caller.

Treat this as a provisional `CONTRACT-CONFLICT` that REC-007 must independently
verify and fully evidence.

Do NOT reinterpret the existence of `MatterActivatedPayload`,
`ActivationEvidenceManifest`, `WebhookSignature`, `make_golden_envelope()`, or
the `service_auth.py` allowed path as proof that the endpoint exists.

REC-007 must determine why the frozen contract exists without its receiver and
recommend later disposition — preserve/implement, supersede, repurpose,
compatibility bridge, or retire — **without implementing any option**.

Do not let the agent classify the missing receiver itself as `TRUE-GAP`. That
already assumes the old contract should be implemented, which this package is
forbidden to decide.

Allowed outcome: classify current artifact.

Forbidden: replacement event name/payload/endpoint/migration.

Future replacement belongs to bilateral `TRACE-STL-001`.

## REC-008 — Privacy + No-Fabrication Audit
Map PII/PHI/de-identified/public-source/attorney-entered/contribution/derived analytics.

Check whether existing or V3 behavior:
- invents defaults;
- treats unknown as zero;
- collapses missing/not-applicable;
- discards contradiction/staleness;
- requires unnecessary raw PHI;
- duplicates TRACE evidence.

## REC-009 — V3 Capability Matrix
For every major V3 section produce:
`ALREADY BUILT / PARTIALLY BUILT / TRUE GAP / MOVE TO TRACE / SHED / CONTRACT CONFLICT`
then map to the six primary classifications.

## REC-010 — Maturity Ledger + Future Frontier
Translate findings into:
`A BUILT_PROVEN / B BUILT_AWAITING_PROOF / C DEFECT/HARDENING / D DEFINED FEATURE / E UNRESOLVED FEATURE`.

Recommend only genuine next units. Do NOT generate implementation tickets yet.

## REC-011 — Reconciliation Evidence Pack
Compile all evidence and finish with:

```text
SETTLE-REC-000 = REVIEW_REQUIRED
```

Owner/TrueVow reviews before any spec is frozen.

---

# 6. REC-000 acceptance gate

Pass only if:

```text
0 implementation files changed
0 migrations created
0 canonical events minted
0 ENT IDs minted
0 replacement TRACE→SETTLE contract frozen
100% relevant V3 capabilities classified
current matter.activated path evidenced
ontology duplicates surfaced
privacy conflicts surfaced
TRUE-GAP separated from EXTEND/KEEP
future frontier bounded
```

---

# 7. Conditional downstream program

This is a routing skeleton, not implementation authorization.

Possible slice families after accepted REC-000:

- `SETTLE-FND-*` — contract/foundation repairs
- `SETTLE-RES-*` — SETTLE-owned resolution workflow
- `SETTLE-LIEN-*` — post-handoff lien negotiation/resolution/payment
- `SETTLE-INTEL-*` — explainable settlement intelligence
- `SETTLE-REPORT-*` — report extensions
- `SETTLE-CONTRIB-*` — contribution/outcome intake
- `TRACE-STL-001` — bilateral cross-product contract; not SETTLE-only

---

# 8. Prototype schema rules

Prototype schemas are allowed only as:

```text
PROTOTYPE
NON-CANONICAL
NOT FOR MIGRATION
NOT FOR CONTRACT REGISTRY
SUBJECT TO REC-000 / STL-001
```

Never use a production-like canonical event registry key or migration filename before approval.

---

# 9. Prototype — future settlement-context handoff envelope

**NON-CANONICAL — FOR STL-001 DESIGN DISCUSSION ONLY**

```json
{
  "prototype_type": "settlement_context_handoff",
  "prototype_version": "0",
  "tenant_ref": "opaque-uuid",
  "matter_ref": "opaque-uuid",
  "trace_case_ref": "opaque-uuid-or-null",
  "jurisdiction": {"state": "CA", "county": "Orange"},
  "classification": {
    "incident_type": "motor_vehicle",
    "injury_context": []
  },
  "development_context": {
    "treatment_summary_status": "complete|partial|unknown",
    "documented_economic_inputs": [],
    "liability_context_status": "reviewed|limited|unknown",
    "comparative_fault_context_status": "reviewed|limited|unknown",
    "coverage_limits_status": "known|partial|unknown",
    "lien_development_status": "complete|partial|unknown"
  },
  "readiness": {
    "status": "ready|ready_with_limitations",
    "blockers": [],
    "limitations": []
  },
  "source_refs": [],
  "approval": {
    "authority_class": "ATTY_AUTH",
    "authority_record_ref": "opaque-uuid",
    "approved_at": "RFC3339"
  },
  "correlation": {
    "correlation_id": "uuid",
    "causation_id": "uuid-or-null"
  }
}
```

This is not the canonical event payload and does not authorize `trace.settlement_context_ready`.

---

# 10. Prototype — SETTLE-owned resolution aggregate

**NON-CANONICAL — instantiate only if REC-000 proves a true gap**

```text
SettlementResolution
--------------------
resolution_id
tenant_ref / account_ref
matter_ref
source_handoff_ref
status
opened_at
opened_by
current_offer_ref
resolution_outcome_ref
created_at
updated_at
```

Candidate states for later specification only:

```text
CONTEXT_RECEIVED
UNDER_REVIEW
NEGOTIATION_ACTIVE
RESOLUTION_PENDING_APPROVAL
RESOLVED
CLOSED
```

Do not create if existing `settlement.py` already owns equivalent semantics.

---

# 11. Prototype — offer aggregate

**NON-CANONICAL**

```text
SettlementOffer
---------------
offer_id
resolution_id
direction
amount_cents
currency
received_or_sent_at
source_type
source_ref
status
attorney_review_state
notes_ref
created_at
```

Possible semantics:
`RECEIVED / COUNTERED / WITHDRAWN / EXPIRED / ACCEPTED / REJECTED`.

Before implementing:
- check existing offer/timeline models;
- avoid automated accept/reject;
- preserve attorney authority.

---

# 12. Prototype — lien resolution projection

**NON-CANONICAL**

```text
LienResolution
--------------
lien_resolution_id
matter_ref
source_lien_ref
claimant_type
asserted_amount_cents
verified_amount_cents
negotiated_amount_cents
resolution_status
payment_status
source_refs
reviewed_by
resolved_at
```

TRACE pre-resolution evidence remains TRACE-owned.

---

# 13. Prototype migration policy

No prototype SQL becomes a migration before:

```text
REC-000 accepted
→ maturity classified
→ /to-spec approved
→ /to-tickets approved
→ implementation ticket authorized
```

Future migrations must cover:
expand/migrate/contract; rollback/recovery; existing-data behavior; constraints; indexes; privacy; no-fabrication; tests; zero destructive loss unless explicitly approved.

---

# 14. Post-REC ticket template

```markdown
# <TICKET-ID> — <one purpose>
## Maturity
## Source of authority
## Goal: FROM / TO
## In scope
## Out of scope
## Ontology
- aggregate
- owner
- source vs derived
- authority
- evidence
- transition
- event
- projection
## Persistence
## Acceptance
## Review
builder self-test → /code-review → fixes → commit/push → independent TrueVow verification
```

---

# 15. Slice template

```markdown
# <SLICE-ID> — <business capability>
## Why
## Maturity
## Skill route
/to-spec → /to-tickets → implement → code-review
## Tickets
## Entry gate
## Exit gate
## Forbidden
```

---

# 16. Branch strategy

REC-000: prefer no runtime branch. If artifacts must be preserved, use docs/scratch only.

Implementation: one branch per accepted slice, e.g.
`settle/SETTLE-RES-001`, `settle/SETTLE-LIEN-001`, `settle/SETTLE-INTEL-001`.

Exact names only after REC-000.

---

# 17. Testing strategy

Future slices require:
- unit tests;
- contract tests;
- PostgreSQL/Supabase persistence tests;
- privacy tests;
- no-fabrication tests;
- cross-product tests only after STL-001.

No production SQLite shortcut.

---

# 18. Immediate execution order

```text
REC-001
→ REC-002
→ REC-003
→ REC-004
→ REC-005
→ REC-006
→ REC-007
→ REC-008
→ REC-009
→ REC-010
→ REC-011
→ owner / TrueVow review
→ only then instantiate downstream specs/tickets
```

---

# 19. Final control rule

> Do not implement V3 from prose. Convert repository truth into maturity-classified work first.

> Do not invent the future TRACE→SETTLE contract during SETTLE-REC-000.

> Prototype schemas are thinking tools, not architecture authority.

> Only accepted TRUE-GAP / EXTEND / actionable conflict findings become future SETTLE implementation work.
