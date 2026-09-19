# SETTLE Coding Agent — Immediate Execution Packet

## Authorized unit
`SETTLE-REC-000 — Repository Truth & Ontology Reconciliation`

## Planning authority
- `TrueVow SETTLE Final Product & Implementation Plan v3`
- `SETTLE-PLAN-TRACE-HANDOFF-001`
- `SETTLE-SDLC-V3-001`

## Mode
READ-ONLY RECONCILIATION. No runtime implementation is authorized.

## Execute in order

```text
REC-001 Authority Baseline
REC-002 Repository Surface Inventory
REC-003 Canonical Contract Inventory
REC-004 SETTLE Ontology Map
REC-005 Model & Schema Reconciliation
REC-006 Service / Capability Reconciliation
REC-007 matter.activated E2E Audit
REC-008 Privacy + No-Fabrication Audit
REC-009 V3 Capability Matrix
REC-010 Maturity Ledger + Future Frontier
REC-011 Reconciliation Evidence Pack
```

## Allowed classifications

```text
KEEP
EXTEND
MOVE-TO-TRACE
SHED
TRUE-GAP
CONTRACT-CONFLICT
```

Every relevant V3 capability/artifact gets exactly one primary classification.

## Forbidden

Do not:
- create migrations;
- modify runtime schemas;
- mint ENT identifiers;
- mint canonical events;
- freeze new payloads;
- implement the future TRACE→SETTLE handoff;
- replace `matter.activated`;
- change algorithms;
- change billing;
- delete old paths;
- perform opportunistic refactors.

## `matter.activated`

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

**FROZEN CONTRACT EXISTS ≠ RECEIVER IMPLEMENTATION EXISTS.**

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
already assumes the old contract should be implemented, which REC-000 is
forbidden to decide.

## Pocock routing after REC-000

Do not run `/to-spec`, `/to-tickets`, `/implement`, or `/wayfinder` on downstream work yet.

After owner/TrueVow acceptance:

```text
KEEP → protect / verify
EXTEND → repair or /to-spec depending maturity
MOVE-TO-TRACE → no SETTLE build
SHED → retirement decision
TRUE-GAP → /to-spec → /to-tickets
CONTRACT-CONFLICT → /wayfinder only if genuinely unresolved
```

### `matter.activated` maturity routing (entered as provisional)

```text
matter.activated frozen contract
→ KEEP pending reconciliation

MatterActivatedPayload / ActivationEvidenceManifest / WebhookSignature
→ KEEP pending bilateral contract reconciliation

service_auth TRACE→SETTLE allowed-path declaration
→ CONTRACT-CONFLICT

matter.activated executable receiver
→ ABSENT — not TRUE-GAP yet

TRACE production caller
→ NONE FOUND / NOT PROVEN

overall frozen-contract-vs-runtime condition
→ CONTRACT-CONFLICT
→ REVIEW_REQUIRED
→ later TRACE-STL-001 disposition
```

Do not let the agent classify the missing receiver itself as `TRUE-GAP`. That
already assumes the old contract should be implemented, which REC-000 is
forbidden to decide.

## Required final response

Return:
1. repository SHA reviewed;
2. authority matrix;
3. six-way capability matrix;
4. canonical ontology map;
5. current cross-product contract inventory;
6. `matter.activated` E2E findings;
7. privacy/no-fabrication findings;
8. V3 reconciliation matrix;
9. maturity ledger;
10. bounded future frontier;
11. explicit contract conflicts;
12. confirmation that zero implementation/migration/canonical-contract changes were made.

End state:

```text
SETTLE-REC-000 = REVIEW_REQUIRED
```

Do not begin downstream implementation until owner/TrueVow accepts the REC-000 evidence package.
