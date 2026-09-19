# SETTLE-REC-000 — Repository Truth & Ontology Reconciliation

**Status:** AUTHORIZED NOW  
**Mode:** READ-ONLY RECONCILIATION  
**Implementation authority:** NONE  
**Language:** English only

## Mission

Reconcile the approved **TrueVow SETTLE Final Plan v2 — For Repo Agent** against the actual current SETTLE repository before any implementation tickets are created.

The purpose is to determine:

```text
what already exists and should be protected
what exists but needs extension
what belongs in TRACE instead of SETTLE
what should be shed
what is genuinely missing
what conflicts with the approved cross-product architecture
```

Do **not** treat the plan as proof that something is unbuilt.

Do **not** treat existing repository prose as architecture authority merely because it exists.

Repository code, accepted canonical contracts, accepted ontology, current database structures, tests, and frozen decisions must be reconciled together.

---

# 1. Required classification

Every relevant capability, model, service, route, event, contract, table, UI concept, integration, and analytical feature must receive exactly one primary classification:

```text
KEEP
EXTEND
MOVE-TO-TRACE
SHED
TRUE-GAP
CONTRACT-CONFLICT
```

Definitions:

### KEEP

Already exists and correctly implements the accepted SETTLE architecture.

Action:

```text
protect
do not rebuild
do not rename without cause
```

### EXTEND

A correct canonical capability already exists but requires bounded enhancement.

Action:

```text
preserve existing entity/contract
identify exact delta only
```

### MOVE-TO-TRACE

The capability belongs to TRACE's Matter-development/readiness ownership rather than SETTLE.

Examples may include pre-resolution evidence development, source collection, treatment-development readiness, or duplicate Matter-readiness behavior.

Action:

```text
do not implement in SETTLE
record TRACE ownership dependency
```

### SHED

The capability is redundant, architecturally harmful, duplicative, low-value, obsolete, or contrary to the approved product boundary.

Action:

```text
candidate for retirement
do not delete during REC-000
document rationale and dependencies
```

### TRUE-GAP

The approved SETTLE architecture requires the capability and no adequate implementation currently exists.

Action:

```text
candidate future implementation unit
do not implement during REC-000
```

### CONTRACT-CONFLICT

Actual repository behavior, schema, event, endpoint, documentation, or contract conflicts with the approved platform boundary or with another accepted source of authority.

Action:

```text
report explicitly
do not silently choose a winner
do not repair during REC-000
```

---

# 2. Hard prohibition — no implementation during REC-000

During `SETTLE-REC-000`, do NOT:

```text
create migrations
modify database schemas
mint ENT identifiers
mint canonical event names
freeze payload schemas
create new API contracts
remove tables
remove endpoints
rewrite historical data
rename canonical entities
change settlement algorithms
change scoring
change contribution logic
change pricing/billing logic
modify TRACE
implement TRACE → SETTLE handoff
make destructive changes
```

Do not turn reconciliation into opportunistic cleanup.

---

# 3. Cross-product boundary that controls this review

Canonical lifecycle:

```text
Matter activation
        ↓
TRACE begins Matter development
        ↓
TRACE develops evidence/readiness
        ↓
Unified Matter Readiness
        ↓
Attorney approval
        ↓
Governed settlement-context handoff
        ↓
SETTLE begins substantive resolution work
```

Therefore:

```text
matter.activated
```

must **not automatically be treated as the mature TRACE → SETTLE settlement-context boundary**.

Any current SETTLE artifact that says otherwise must be classified based on actual implementation and accepted contract history.

It may be:

```text
legacy bootstrap behavior
historical integration
stale documentation
currently functioning compatibility behavior
or a genuine contract conflict
```

Determine which through evidence.

Do not assume.

---

# 4. Bilateral contract rule

Neither repository may independently invent the future TRACE → SETTLE contract.

SETTLE must not dictate what TRACE stores.

TRACE must not independently dictate what SETTLE consumes.

The canonical contract will be frozen later during:

```text
TRACE-STL-001
```

after both repositories and the platform ontology have been reconciled.

The proposed event:

```text
trace.settlement_context_ready
```

is **PROVISIONAL ONLY**.

Do not register it as canonical during REC-000.

---

# 5. Architecture authority order

When evidence conflicts, use this discipline:

```text
accepted canonical platform contracts / ontology
        ↓
current accepted code + database behavior
        ↓
accepted test/gate evidence
        ↓
current approved product decisions
        ↓
active plans/specifications
        ↓
README / integration prose / comments
        ↓
historical or archived artifacts
```

Do not allow stale prose to override accepted architecture.

Do not allow current code that demonstrably violates a frozen contract to redefine the contract either.

A contradiction between two legitimate authority sources is:

```text
CONTRACT-CONFLICT
```

and must be reported.

---

# 6. Repository areas that must be inspected

Inspect actual current SETTLE repository truth, including at minimum:

```text
AGENTS.md

README.md

app/shared/contracts.py

app/core/service_auth.py

webhook routes

API routers/endpoints

settlement query services

estimator / analytical services

report generation

contribution workflow

anonymization / de-identification

validation / no-fabrication gates

case-bank models

settlement/contribution models

offer models if present

timeline models if present

readiness models if present

lien-related models/services

liability/comparative-fault fields

coverage/limits fields

database migrations

database schema

event registries

authority/transition registries if present

outbox/event delivery patterns

tests and golden fixtures

current frontend/admin/customer surfaces if contained in repo

accepted architecture docs

active planning docs

historical integration docs only where needed to explain drift
```

Do not use historical documents as a build checklist.

---

# 7. Ontology reconciliation

For every meaningful SETTLE concept, identify:

```text
canonical entity
aggregate
product owner
source vs derived
authoritative vs projection
state machine
commands
events
authority
required evidence
provenance
privacy class
staleness semantics
review semantics
cross-product dependency
```

The review must specifically detect duplicate ontology.

Examples:

```text
two offer models
two negotiation timelines
two readiness systems
duplicate liability truth
duplicate lien truth
duplicate settlement result models
duplicate contribution models
duplicate case classification systems
```

If duplicates exist, classify them rather than normalizing them silently.

---

# 8. TRACE ownership filter

Explicitly test every proposed SETTLE capability against the TRACE boundary.

Potential TRACE-owned concepts include:

```text
source-document development
evidence collection
fact normalization
contradiction development
treatment-development tracking
records/bills completeness
pre-resolution lien discovery/documentation
coverage evidence development
liability evidence development
comparative-fault evidence development
Matter readiness
readiness blockers
development limitations
source provenance
```

SETTLE should consume only the smallest useful governed projection needed for resolution work.

Do not make SETTLE duplicate TRACE's evidence system.

---

# 9. SETTLE ownership filter

Determine what genuinely belongs to SETTLE after the handoff.

Likely categories include:

```text
settlement context
comparable outcome analysis
settlement valuation/ranges where approved
resolution economics
offer analysis
negotiation/resolution workflow
net-recovery context
lien negotiation/resolution/payment
settlement reporting
resolution outcomes
approved contribution workflow
SETTLE-owned confidence/limitations
```

These are categories to reconcile, not automatic instructions to create new models.

---

# 10. Pruning tests

Apply the following product tests.

## Law-firm value test

For every proposed capability ask:

> Does this materially help a plaintiff law firm evaluate, negotiate, understand, document, or resolve a settlement?

If no:

```text
candidate SHED
```

## Duplication test

Ask:

> Does TRACE already own the underlying development truth?

If yes:

```text
MOVE-TO-TRACE
or
consume projection instead
```

## Black-box test

Avoid features whose only value is:

```text
opaque score
opaque ranking
unexplainable recommendation
```

Prefer:

```text
source-backed factors
comparables
confidence
limitations
explainable context
```

## Automation boundary

Do not introduce:

```text
automatic accept settlement
automatic reject settlement
automatic negotiation authority
```

unless separately and explicitly approved.

---

# 11. Privacy / PHI reconciliation

Determine what SETTLE actually stores today.

Classify:

```text
direct PII
PHI
de-identified Matter context
settlement contribution data
public-source data
attorney-entered data
derived analytical data
```

The future TRACE → SETTLE default contract should not require raw PHI merely because SETTLE could technically accept it.

Identify any current SETTLE model that would force unnecessary TRACE duplication or raw-PHI transfer.

Classify it.

Do not repair it yet.

---

# 12. No-fabrication requirement

Preserve SETTLE's no-fabrication discipline.

Unknown values must remain unknown.

Do not convert:

```text
UNKNOWN → default enum
MISSING → zero
NOT_APPLICABLE → missing
CONTRADICTED → chosen winner
STALE → current
```

without an authoritative rule.

Identify any existing code that violates this and classify it.

---

# 13. Legacy `matter.activated` investigation

Investigate the actual current status of:

```text
POST /settle/webhooks/matter-activated
```

and related:

```text
MatterActivatedPayload
ActivationEvidenceManifest
WebhookSignature
golden fixtures
callers
producers
consumers
database writes
side effects
deployment usage
tests
documentation
```

Answer:

```text
1. Does the endpoint actually exist?
2. Is it executable production code?
3. Who currently calls it?
4. What state does it create or mutate?
5. Does SETTLE currently depend on it?
6. Is it bootstrap-only, settlement-start, or something else?
7. Is its behavior covered by accepted tests?
8. Is the TRACE-as-producer statement true in production code?
9. Is the contract consistent with current platform ontology?
10. Can it coexist with the future mature handoff?
11. Would it need migration, retirement, repurposing, or no change?
```

Do not decide final migration during REC-000 unless current evidence makes the classification unambiguous.

---

# 14. Required output — capability matrix

Return a table with at least:

| Capability / artifact | Current evidence | Current owner | Proposed owner | Classification | Reason | Dependency | Recommended later action |
|---|---|---|---|---|---|---|---|

Allowed classification values only:

```text
KEEP
EXTEND
MOVE-TO-TRACE
SHED
TRUE-GAP
CONTRACT-CONFLICT
```

---

# 15. Required output — ontology map

Produce:

```text
SETTLE CANONICAL ONTOLOGY MAP
```

including current:

```text
Matter/case reference
settlement analysis
comparable
offer
negotiation/resolution timeline
lien resolution
net recovery
settlement result
contribution
report
authority
events
projections
```

Mark duplicate or conflicting entities explicitly.

---

# 16. Required output — contract inventory

Produce:

```text
CURRENT CROSS-PRODUCT CONTRACT INVENTORY
```

For each contract:

```text
name
version
producer
consumer
endpoint/event
authentication
payload
authority
idempotency
actual callers
tests
status
conflict notes
```

Include `matter.activated`.

---

# 17. Required output — plan reconciliation

For every major section of SETTLE Final Plan v2 state:

```text
ALREADY BUILT
PARTIALLY BUILT
TRUE GAP
MOVE TO TRACE
SHED
CONTRACT CONFLICT
```

Do not merely summarize the plan.

Compare it to repository truth.

---

# 18. Required output — recommended implementation frontier

At the end, recommend only the **next bounded units** that genuinely require work.

Do not generate full implementation tickets yet.

Output:

```text
Recommended first future unit:
<name>

Why:
<evidence>

Dependencies:
<dependencies>

Maturity:
A / B / C / D / E

Correct lifecycle entry:
protect / verify / repair / to-spec / wayfinder
```

Repeat only for genuinely necessary units.

---

# 19. Stop conditions

Stop and escalate if you find:

```text
a canonical ontology contradiction
a TRACE/SETTLE ownership conflict
two accepted contracts that disagree
a production behavior that contradicts frozen architecture
a privacy boundary conflict
a destructive migration apparently required
an unresolved event authority problem
```

Do not silently choose an answer.

Report:

```text
CONTRACT-CONFLICT
```

with exact evidence.

---

# 20. Completion criteria

`SETTLE-REC-000` is complete only when:

```text
1. Current repo truth is inventoried.
2. Existing SETTLE ontology is mapped.
3. Duplicate ontology is identified.
4. TRACE-owned concepts are separated.
5. SETTLE-owned concepts are separated.
6. Legacy matter.activated behavior is proven from code/callers.
7. Cross-product contracts are inventoried.
8. Privacy/PHI boundaries are documented.
9. Final Plan v2 is reconciled line-by-line at capability level.
10. Every relevant item has one allowed classification.
11. True gaps are separated from already-built functionality.
12. Contract conflicts are explicitly surfaced.
13. No migrations or implementation changes were made.
14. No canonical event or ENT identifier was invented.
15. A bounded future implementation frontier is recommended.
```

---

# Final instruction

**Do not implement SETTLE Final Plan v2. Reconcile it.**

Return the evidence-backed:

```text
KEEP
EXTEND
MOVE-TO-TRACE
SHED
TRUE-GAP
CONTRACT-CONFLICT
```

map first.

Only after owner/TrueVow review of `SETTLE-REC-000` may implementation specifications or tickets be frozen.