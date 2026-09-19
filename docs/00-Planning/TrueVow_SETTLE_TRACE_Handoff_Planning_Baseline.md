# TRUEVOW SETTLE - TRACE HANDOFF PLANNING BASELINE

**Plan ID:** `SETTLE-PLAN-TRACE-HANDOFF-001`  
**Status:** ACCEPTED PLANNING DIRECTION / Class D - DEFINED FEATURE  
**Date:** 2026-08-30  
**Implementation authorization:** NONE until the controlling TRACE Gate 003 and post-Gate-003 sequence reaches `TRACE-STL-001`  
**Purpose:** Keep SETTLE aligned with the canonical TRACE -> SETTLE settlement-context boundary while preserving existing repository artifacts as evidence to reconcile rather than architecture truth.

---

## 1. Controlling product boundary

Canonical product model:

> **INTAKE Captures. TRACE Develops. SETTLE Resolves. COMMAND Measures.**

Matter activation begins TRACE development.

The mature TRACE -> SETTLE boundary occurs later, after the Matter has been sufficiently developed for settlement-context work and an attorney has approved a governed handoff.

The intended lifecycle is:

```text
Matter activation
    ↓
TRACE develops the Matter
    ↓
Unified Matter Readiness
    ↓
Attorney approval
    ↓
Governed settlement-context handoff
    ↓
SETTLE begins substantive resolution work
```

Matter activation must not be reused as the mature TRACE -> SETTLE settlement-context boundary.

---

## 2. Legacy SETTLE integration artifacts are evidence, not future architecture authority

The SETTLE repository contains historical/current integration documentation that predates the canonical TRACE -> SETTLE settlement-context boundary.

This includes current agent/documentation material describing:

```text
POST /settle/webhooks/matter-activated
receives matter.activated from TRACE
```

That artifact must not be promoted into future architecture truth merely because it exists.

For the future TRACE -> SETTLE boundary:

- legacy integration documentation is **reconciliation evidence**;
- it is **not controlling architecture authority**;
- do not delete or rewrite historical/as-built evidence merely to make the repository appear aligned;
- do not build new behavior from that historical contract before `TRACE-STL-001`;
- any retirement, compatibility period, migration, or reuse decision must be made explicitly during the two-sided reconciliation.

---

## 3. SETTLE ownership after the boundary

SETTLE owns settlement-context and resolution-support behavior, including the settlement-facing interpretation of governed inputs.

SETTLE may own, subject to its own canonical ontology:

- comparable settlement/outcome context;
- settlement valuation or ranges where allowed by the approved SETTLE architecture;
- settlement-facing economics;
- resolution strategy/support tools;
- lien negotiation, resolution and payment/disbursement lifecycle;
- settlement reports;
- SETTLE-specific confidence/limitation semantics;
- accepted SETTLE-domain records derived from a governed TRACE contract.

SETTLE does **not** acquire ownership of TRACE's source facts merely by consuming a handoff packet.

SETTLE must not directly mutate TRACE persistence.

TRACE must not directly mutate SETTLE persistence.

---

## 4. TRACE owns the development record

Before handoff, TRACE remains authoritative for the pre-litigation development layer, including:

- source-linked evidence;
- records and bills completeness;
- treatment development;
- evidence/contradiction state;
- documented economic-damages support;
- pre-resolution lien/reimbursement discovery and documentation;
- liability/comparative-fault evidence and attorney-reviewed development position;
- coverage/limits evidence and status;
- Matter Readiness blockers and limitations;
- source provenance;
- attorney approval of the handoff projection.

SETTLE must not require TRACE to duplicate SETTLE-domain resolution state merely to satisfy an integration.

---

## 5. TRACE-STL-001 is a mandatory two-sided reconciliation gate

`TRACE-STL-001` must reconcile **both repositories and both ontology sides before either agent invents or freezes the contract**.

TRACE must not independently define what SETTLE consumes.

SETTLE must not independently dictate what TRACE stores.

The goal of STL-001 is:

> **Define the smallest useful, governed, de-identified projection that lets SETTLE begin settlement-context work without transferring ownership of TRACE's underlying development records.**

STL-001 must inspect at minimum:

### TRACE side
- canonical Matter / TRACE Case identity;
- Unified Matter Readiness;
- source/evidence/provenance models;
- attorney approval authority;
- EventEnvelope;
- TransitionContract / StateMachine;
- current signed cross-product contract patterns;
- privacy/PHI boundaries;
- outbox/idempotency patterns.

### SETTLE side
- current webhook endpoints;
- `matter.activated` receiver artifacts;
- `AGENTS.md`;
- `app/shared/contracts.py`;
- `app/core/service_auth.py`;
- current event/payload registries;
- current API-key/service-auth integration model;
- settlement query/report/contribution schemas;
- SETTLE privacy and no-fabrication constraints;
- any accepted current ontology/contract documentation.

Conflicts are reconciliation findings, not invitations to choose whichever document is older or more convenient.

---

## 6. Contract may freeze only after STL-001

Only after the joint reconciliation may the cross-product contract freeze:

```text
canonical event/command name
producer
consumer
aggregate/entity identity
schema version
required fields
optional fields
authority
required evidence
transition
guards
privacy classification
PHI/PII policy
provenance semantics
correlation/causation semantics
idempotency key
signature/authentication contract
replay protection
acceptance semantics
failure semantics
retry semantics
compatibility/versioning policy
retirement/migration of legacy integration paths
```

No agent may freeze any of those independently before STL-001 completes.

---

## 7. Provisional event name

The candidate name:

```text
trace.settlement_context_ready
```

is **PROVISIONAL ONLY**.

It is not canonical.

Do not add it to a frozen event registry, contract schema, database migration, endpoint requirement, or production integration before STL-001 reconciliation.

The final name may remain this value, change, or be replaced by a different command/event pair depending on the ontology and transition analysis.

---

## 8. Handoff projection principles

The handoff should be the smallest useful projection.

Candidate categories, subject to STL-001 reconciliation, include:

- opaque tenant reference;
- canonical Matter reference;
- TRACE Case reference if required;
- jurisdiction / venue;
- incident and case classification;
- structured treatment/injury context;
- documented economic-damages inputs;
- liability/comparative-fault context;
- coverage/limits status;
- pre-resolution lien/reimbursement development status;
- completeness/blockers/limitations;
- governed source references;
- attorney review/approval metadata;
- schema version;
- correlation/causation identifiers.

The projection should not become a serialized copy of TRACE.

---

## 9. Privacy default

Default TRACE -> SETTLE handoff must exclude raw:

- client name;
- phone;
- email;
- street address;
- date of birth;
- claim number;
- medical-record number;
- raw PHI;
- unnecessary source-document bodies;
- unreviewed narrative.

If SETTLE later requires PHI-bound access, stop and create a separate governed privacy/security contract. Do not silently widen the handoff.

---

## 10. No-fabrication discipline survives the handoff

SETTLE's no-fabrication rule remains binding.

Receipt of a TRACE handoff packet does not authorize SETTLE to:

- infer missing values;
- create fallback classifications;
- manufacture liability tiers;
- guess comparative negligence;
- convert unknown coverage into defaults;
- invent medical/damages amounts;
- treat absent fields as zero;
- treat limitations as confirmed facts.

Unknown, missing, not-applicable, contradicted and stale conditions must remain semantically distinguishable where relevant to the SETTLE contract.

---

## 11. Controlling execution sequence

The cross-product plan remains gated by TRACE foundation completion.

Controlling sequence:

```text
Gate 003 PASS
    ↓
TRACE-DMG-000
    ↓
TRACE-DMG-001
    ↓
TRACE-DMG-002
    ↓
TRACE-DMG-003
    ↓
TRACE-DMG-004
    ↓
TRACE-DMG-005
    ↓
TRACE-STL-001  ← FIRST JOINT TRACE / SETTLE CONTRACT WORK
    ↓
TRACE-STL-002
    ↓
TRACE-STL-003
    ↓
TRACE-STL-004
```

SETTLE must not pre-build the new handoff contract while TRACE is still completing its foundation/readiness model.

SETTLE may perform read-only repository reconciliation preparation, but no new canonical contract is implementation-authorized before `TRACE-STL-001`.

---

## 12. STL-001 output

STL-001 must produce one joint contract decision package containing:

1. ontology ownership matrix;
2. current TRACE contract inventory;
3. current SETTLE contract inventory;
4. legacy/stale conflict list;
5. minimal handoff field matrix;
6. required/optional field semantics;
7. authority and transition definition;
8. evidence/provenance requirements;
9. privacy classification;
10. event/command decision;
11. schema version;
12. signed delivery/authentication mechanism;
13. idempotency/replay behavior;
14. receiver acceptance/rejection semantics;
15. compatibility/migration treatment for the legacy `matter.activated` path;
16. contract tests to be implemented by both repositories.

Only that package may authorize `TRACE-STL-002` and later implementation.

---

## 13. Definition of Done for the planning baseline

This planning baseline is satisfied when:

- both agents agree that Matter activation starts TRACE, not substantive SETTLE resolution;
- legacy SETTLE integration artifacts are treated as reconciliation evidence rather than future architecture authority;
- no new TRACE -> SETTLE contract is frozen before STL-001;
- the event name remains provisional;
- the smallest-useful-projection rule is preserved;
- no direct cross-database writes are introduced;
- privacy defaults remain de-identified;
- SETTLE no-fabrication rules remain intact;
- any legacy-path retirement/migration is explicit and tested;
- both repositories implement the same frozen contract only after the joint reconciliation.

---

## 14. Final rule for SETTLE agents

> **Do not derive the future TRACE -> SETTLE architecture from an old endpoint merely because the endpoint exists.**

> **Do not independently tell TRACE what to store.**

> **At STL-001, reconcile both sides and freeze the smallest useful settlement-context projection together.**

Until then, `trace.settlement_context_ready` is provisional and the existing `matter.activated`-from-TRACE artifact is historical/current implementation evidence to reconcile, not the final boundary contract.
