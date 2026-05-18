# ADR S-2: Query Demand Log + Gap Classification

- **Date:** 2026-05-07
- **Status:** PROPOSED (awaiting architect decision)
- **Authors:** Agent B (executor)
- **Related:** Cohort R empty-pool guard; ADR S-1 (multi-tag reclassification).

## Context

After Cohort R, every attorney query that hits an empty pool or an insufficient
cohort now returns a graceful `insufficient_data` response — but **the system
has no memory of what the attorney asked for**. The failure is invisible to
scraper prioritization, coverage reporting, and product analytics.

Naive enumeration of "all possible query combinations" to drive scraping is
infeasible: the cartesian product of jurisdiction × case_type × injury_category
× defendant_category × treatment_type alone is ~16M cells, and most are
physically impossible (e.g., Maritime Injury in landlocked counties) or
naturally sparse. A demand-driven approach is required.

## Decision

Introduce a **query demand log** plus a **nightly gap classification** pass.

### 1. `query_demand_log` table

```sql
CREATE TABLE query_demand_log (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id          UUID NOT NULL REFERENCES tenants(id),
  attorney_id_hash   TEXT NOT NULL,      -- HMAC-hashed, never raw
  jurisdiction       TEXT NOT NULL,
  case_type          TEXT NOT NULL,
  injury_category    TEXT[] NOT NULL,
  defendant_category TEXT,
  treatment_type     TEXT[],
  duration_of_treatment TEXT,
  policy_limits      TEXT,
  medical_bills_bucket TEXT,              -- band, NEVER raw (privacy)
  result_status      TEXT NOT NULL,       -- sufficient | insufficient_data | empty_pool
  aggregation_level  TEXT NOT NULL,       -- county | state | none
  n_county           INT NOT NULL,
  n_state            INT NOT NULL,
  n_cases_returned   INT NOT NULL,
  query_hash         TEXT NOT NULL,       -- stable hash of inputs for dedup
  queried_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_demand_log_cell ON query_demand_log
  (jurisdiction, case_type, queried_at DESC);
CREATE INDEX idx_demand_log_gaps ON query_demand_log (result_status, queried_at DESC)
  WHERE result_status IN ('insufficient_data', 'empty_pool');
```

Write path: hooked in `app/api/v1/endpoints/query.py::estimate_settlement_range`
after the `EstimateResponse` is constructed, fired asynchronously (no hot-path
latency).

### 2. `coverage_gap_classification` table (nightly aggregate)

```sql
CREATE TABLE coverage_gap_classification (
  id              UUID PRIMARY KEY,
  cell_key        TEXT NOT NULL UNIQUE,      -- e.g., "FL|Orange|Premises Liability|soft_tissue"
  jurisdiction    TEXT NOT NULL,
  case_type       TEXT NOT NULL,
  injury_category TEXT NOT NULL,
  demand_30d      INT NOT NULL,               -- # attorney queries in last 30d
  supply_n        INT NOT NULL,               -- current approved cases
  gap_delta       INT NOT NULL,               -- floor - supply_n (when positive)
  classification  TEXT NOT NULL,              -- physically_impossible | naturally_sparse
                                              -- | coverage_gap | nda_locked | mis_tagged
  classified_at   TIMESTAMPTZ,
  classified_by   TEXT,                       -- rule name or reviewer_id
  last_reviewed_at TIMESTAMPTZ
);
```

### 3. Classification rules (first pass, rule-based)

| Rule | Emits |
|---|---|
| `case_type=Maritime` AND state NOT IN coastal_states | `physically_impossible` |
| `national_n_for_(case_type, injury) < 5` | `naturally_sparse` |
| mis-tagged cells identified by ADR S-1 reclassification pass | `mis_tagged` |
| high-value segments with <10% publication rate vs. court docket filings | `nda_locked` |
| default | `coverage_gap` |

Low-confidence classifications flagged for human review in the same queue as
ADR S-1.

## Alternatives Considered

| Option | Verdict |
|---|---|
| **A.** Don't log queries at all. | Rejected. No feedback loop; scraping remains breadth-first and blind to actual demand. |
| **B.** Enumerate cartesian product of all possible queries a priori. | Rejected. ~16M cells, most physically impossible. Scraper budget would be wasted on impossible cells. |
| **C.** Log queries but no classification — scrape everything that returns empty. | Rejected. Would aggressively scrape physically-impossible and NDA-locked cells, wasting budget and never closing the gap. |
| **D.** Demand log + nightly classification with gap-type taxonomy. | **Chosen.** Real-world prioritization, budget-conscious, produces an investor-grade coverage report. |

## Consequences

### Positive
- Scraper backlog becomes finite and prioritized (`coverage_gap` cells
  ordered by `demand_30d × gap_delta`).
- Investor narrative: *"X% coverage against actual attorney demand in top N
  states, up from Y% last quarter"* — concrete, defensible.
- Product analytics: reveals which case types / jurisdictions are most
  valuable to attorneys.
- Signals when a gap is *impossible* so the UI can message correctly
  ("Maritime Injury cases do not exist in Arizona").

### Negative
- New schema surface: 2 tables + 1 async write path + 1 nightly job.
- Privacy: attorney query patterns are sensitive. Mitigation: `attorney_id`
  is HMAC-hashed; `medical_bills` is bucketed, never raw; tenant isolation
  enforced on all reads; no cross-tenant aggregation exposed to customers.
- Write-amplification on the estimate endpoint. Mitigation: async fire-and-
  forget, never blocks the response.

## Open Questions (for architect)

1. **Retention.** How long do we keep raw demand log rows? (Recommend: 365
   days raw, then aggregate into monthly rollups.)
2. **Cross-tenant aggregation.** Can Tenant A's demand pattern contribute to
   Tenant B's coverage classification? (Recommend: yes in aggregate only, with
   tenant-identifying fields stripped before aggregation.)
3. **Bills bucketing granularity.** `<$10k | $10k-$50k | $50k-$250k |
   $250k-$1M | $1M+` — or finer?
4. **Classification cadence.** Nightly batch, or real-time on demand log
   write? (Recommend: nightly for stability; real-time only for the
   "sufficient → insufficient" transition trigger.)

## Dependencies

- Alembic migration for the two new tables.
- Cohort S-1 (ADR S-1) enables the `mis_tagged` classification.
- Does not require Agent A work — pure backend.

## References

- Cohort R commit: `7847c54`
- `app/api/v1/endpoints/query.py::estimate_settlement_range` — hook point
- ADR S-1 (companion): `ADR_20260507_multi_tag_injury_reclassification.md`
