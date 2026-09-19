# T1 — Existing-Model + Persistence Capability Proof

**Ticket:** T1 (SETTLE-CONTRIB-TO-TICKETS)
**Status:** PASS
**Verdict:** EXISTING_PERSISTENCE_SUFFICIENT
**Date:** 2026-08-31

---

## Method

Inspected existing repository files directly. No schema change, no migration, no code implementation. Read-only evidence gathering only.

## Verdict

EXISTING_PERSISTENCE_SUFFICIENT

## Per-Question Findings

### Q1 — Can existing persistence represent contribution provenance adequately?

**SUFFICIENT.** `settle_verdicts` (migration d5e6f7a8b9c0, table at alembic/versions/d5e6f7a8b9c0_add_settle_verdicts_tables.py) already carries:
- `source` (TEXT, default 'scraped')
- `source_url` (TEXT)
- `source_notes` (TEXT)

Model: `app/models/verdicts.py` VerdictRecord lines 127-129.

`settlement_records` (migration 33175e3b6200) has `contributor_tenant_id`, `case_fingerprint_hash`, `submitted_at`.

`settle_contributions` has `contributor_user_id` (migration c3d4e5f6a7b8) and `source_type` (migration a1b2c3d4e5f6).

### Q2 — Can existing persistence represent the required evidence relationship, including sufficiently granular support for analytics-relevant contributed facts?

**SUFFICIENT.** `settle_verdicts` has (migration e6f7a8b9c0d1):
- `validated_field_count` (INTEGER)
- `validation_counts` (JSONB)
- `field_evidence` (JSONB)

Model: `app/models/verdicts.py` lines 143-145, with docstring: "No-fabrication audit trail (evidence per field)."

Migration docstring: "every field that reaches the DB is verbatim-verified against source evidence. These columns record HOW MANY of a record's fields were independently validated and the evidence (value + snippet + source_url) for each, so any row can be audited field-by-field."

### Q3 — Can existing persistence represent verification and partial-verification semantics adequately?

**SUFFICIENT.** `settle_verdicts` has:
- `review_status` (TEXT, CHECK constraint: pending/reviewed/verified/rejected)
- `confidence_score` (numeric 0-1)
- `completeness_score` (numeric 0-1)
- `corroboration_count` (INTEGER, migration c0d1e2f3a4b5)
- `corroborating_sources` (JSONB)

`settlement_records` has `verification_status` enum (pending/verified/rejected/flagged, migration ec7e4c7db3be).

No-fabrication gate: `no_fabrication_gate.py` (verify_record).
Normalization gate: `verdict_validator.py` (normalize_and_validate).

### Q4 — Can existing persistence represent analytics eligibility adequately?

**SUFFICIENT.** `intelligence_gate.py` enforces MIN_AGGREGATE_N=50 with hierarchical tiers (county/state/none), suppressing aggregate widgets when insufficient. `case_bank.py` EstimateResponse has `own_case_only` and `suppressed_features`. `verdicts.py` has VALID_VERDICT_REVIEW_STATUSES.

`settle_contributions` has `status` (pending/approved/rejected/flagged), `is_outlier`, `confidence_score`.

### Q5 — Can existing persistence preserve UNKNOWN / MISSING / NOT_APPLICABLE semantics without fabricating zero/default values?

**SUFFICIENT.** All relevant fields are OPTIONAL (nullable=True). `verdict_validator.py` VALID_VERDICT_LIABILITY_TIERS includes "unknown". VALID_VERDICT_POLICY_LIMIT_INDICATORS includes "unknown". `settle_contributions` has `lost_wages: Optional[float]`, `policy_limits: Optional[str]`.

### Q6 — Can corrections, invalidations and re-verification be represented without leaving stale trusted values influencing analytics?

**SUFFICIENT.** Migration c0d1e2f3a4b5 docstring: "a verdict is promoted from review_status='pending' to 'verified' ONLY when the same case appears in >=2 INDEPENDENT sources that AGREE on the outcome amount." This is multi-source corroboration with a promotion gate. `audit_events` table (shared foundation, b2c3d4e5f6a7) is append-only, tenant-scoped, immutable. `audit_store.py` records all state transitions.

### Q7 — Can the required design preserve tenant isolation and existing RLS?

**PASS.** `tenants` table has `tenant_id` on all entities. `tenant_core.py` enforces `validate_tenant_access()`. `role_assignments` has `tenant_id` index. `audit_events` has `tenant_id` with `idx_audit_tenant_time`. `settlement_records` has `contributor_tenant_id` with index. `settle_contributions` has `contributor_api_key_id`. All shared foundation tables (b2c3d4e5f6a7) include `tenant_id`.

### Q8 — Can all of the above be achieved using existing entities/relationships plus application logic only?

**VIABLE.** Yes. All required capabilities already exist in existing entities (`settle_verdicts`, `settlement_records`, `settle_contributions`, `audit_events`, `intelligence_gate`, `no_fabrication_gate`, `verdict_validator`, `audit_store`) plus application logic. No new table, column, enum, constraint, or migration is needed.

## Evidence Table

| Sub-question | Verdict | Primary Evidence |
|---|---|---|
| Q1 Provenance | SUFFICIENT | settle_verdicts.source/source_url/source_notes; settlement_records.contributor_tenant_id; settle_contributions.contributor_user_id/source_type |
| Q2 Evidence relationship | SUFFICIENT | settle_verdicts.validated_field_count/validation_counts/field_evidence (migration e6f7a8b9c0d1) |
| Q3 Verification | SUFFICIENT | settle_verdicts.review_status/corroboration_count/corroborating_sources; settlement_records.verification_status |
| Q4 Analytics eligibility | SUFFICIENT | intelligence_gate.py MIN_AGGREGATE_N=50; case_bank.py own_case_only/suppressed_features |
| Q5 Semantic preservation | SUFFICIENT | All fields OPTIONAL; verdict_validator "unknown" tiers; Optional[float]/Optional[str] |
| Q6 Corrections/re-verification | SUFFICIENT | corroboration promotion gate (c0d1e2f3a4b5); audit_events append-only |
| Q7 Tenant isolation / RLS | PASS | tenant_id on all entities; tenant_core.validate_tenant_access(); RLS indexes |
| Q8 Application logic only | VIABLE | All capabilities in existing entities + app logic |

## Consequence

T-PERSIST = NOT_REQUIRED. No migration should be created for this contribution foundation. The historical/external contribution capability can be delivered by routing external/historical cases through the existing verify-and-persist gate sequence using existing entities, with the new intake path implemented as application logic only.

## Database Governance

DATABASE_CREATED = NO
MIGRATION_CREATED = NO
SCHEMA_CHANGED = NO
RLS_CHANGED = NO