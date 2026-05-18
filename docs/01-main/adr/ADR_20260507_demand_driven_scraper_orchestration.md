# ADR S-3: Demand-Driven Scraper Orchestration with Source Stratification

- **Date:** 2026-05-07
- **Status:** PROPOSED (awaiting architect decision; depends on ADR S-2)
- **Authors:** Agent B (executor)
- **Related:** ADR S-1 (multi-tag reclassification), ADR S-2 (query demand
  log + gap classification), Cohort R empty-pool guard.

## Context

Today the TopVerdict / IRFS / court-docket scrapers crawl breadth-first against
their source catalogs. They have no awareness of:

- which cells attorneys actually query (captured by ADR S-2);
- which cells are physically impossible vs. coverage_gap vs. NDA-locked
  (classified by ADR S-2);
- which cells were created by mis-tagging and don't need new data (fixed by
  ADR S-1);
- **source bias**: if 80% of a cell's cases come from TopVerdict and TopVerdict
  only publishes verdicts >$100k, the cell's percentiles are systematically
  upward-biased.

Without orchestration, scraping continues to burn budget on cells that will
never be attorney-relevant, while high-demand gaps stay empty.

## Decision

Replace breadth-first scraping with a **demand-driven, source-stratified
orchestrator** that consumes the `coverage_gap_classification` table from
ADR S-2.

### 1. Scraper consumption contract

A new service `app/services/scraper_orchestrator.py`:

```python
def next_scrape_batch(budget: int) -> List[ScrapeTarget]:
    """
    Returns up to `budget` ScrapeTargets, pulled from
    coverage_gap_classification WHERE classification = 'coverage_gap',
    ordered by (demand_30d DESC, gap_delta DESC).
    Each target respects source-stratification caps.
    """
```

Scrapers become **pull-based consumers** of this queue. They no longer decide
what to scrape.

### 2. Source-stratification caps (anti-gate-gaming)

For any single cell, **no more than 60%** of approved contributions may
originate from any single source. Enforced at ingestion, not post-hoc.

If a cell is at 50/50 from TopVerdict/court-docket and the scraper brings a
new TopVerdict row, ingest is allowed. If the cell is already at 70%
TopVerdict, the row is **held in `settle_contributions_pending_stratification`
until an opposing-source contribution arrives or 90 days elapse** — then
auto-approved with a `stratification_waived=true` flag.

Rationale: Year-2 "never sell empty dashboards" invariant is violated not
only by empty dashboards but by **shallow dashboards built from cherry-picked
single-source cohorts**. A 50-case FL Premises Liability cell that is 100%
TopVerdict (=publication-biased, upward-skewed) is not a credible cohort; it
just looks like one to the gate.

### 3. Multi-tag NLP on ingest

Every newly scraped row runs through the same multi-tag classifier defined in
ADR S-1, on the way in. This prevents new data from inheriting the same
single-dominant-tag pathology that ADR S-1 exists to retro-fix.

### 4. Loopback: demand resolution event

When a `coverage_gap` cell reaches the credibility floor, the orchestrator
fires a `gap_resolved` event. The estimator surfaces this on the next query
hit as *"Data for this query tier is newly available — precision increased."*

## Alternatives Considered

| Option | Verdict |
|---|---|
| **A.** Keep breadth-first scraping. | Rejected. Wastes budget on physically-impossible and attorney-irrelevant cells. |
| **B.** Pure demand-driven scraping, no source stratification. | Rejected. Scraper will aggressively fill cells from whichever source is cheapest (usually TopVerdict), producing publication-biased cohorts that look statistically sufficient but are systematically skewed upward. Gate-gaming. |
| **C.** Demand-driven + source-stratified, with multi-tag NLP on ingest. | **Chosen.** Closes the loop, respects the credibility floor, preserves the "never sell empty dashboards" invariant under its full meaning. |
| **D.** Option C plus human-in-the-loop before every scrape target. | Rejected for v1. Reviewer throughput is too low for the scrape queue depth. Defer to v2 if automated quality falters. |

## Consequences

### Positive
- Scraper budget is spent on cells that matter to attorneys.
- Source-stratification caps prevent systematic percentile bias.
- Gap resolution is closed-loop: empty → scraped → classified → gate-eligible
  → attorney-visible.
- Auditability: every approved contribution carries source provenance and
  stratification status.

### Negative
- Ingestion-path complexity grows: two-phase admission
  (`settle_contributions_pending_stratification` → `settle_contributions`).
- Edge case: cells where only one source covers the market (certain NDA-bound
  segments). Mitigation: the 90-day auto-approval with `stratification_waived`
  flag; such cells ship with a UI caveat ("evidence base limited to one
  publication source").
- Scraper teams lose autonomy over what to scrape. This is intentional but
  requires org buy-in.

## Open Questions (for architect)

1. **Stratification cap number.** 60% is a starting point. Do we run a
   historical simulation to find the percentile-stability-optimizing cap?
2. **Single-source cells.** How do we message to attorneys that a cell is
   backed by only one source? UI treatment is Agent A's domain — **escalate
   to Razi before specifying copy**.
3. **Priority formula.** `demand_30d × gap_delta` is the minimum viable
   ranking. Should we weight by tenant tier (e.g., enterprise attorneys'
   demand weighted higher)?
4. **Orchestrator as-service.** Standalone service or library imported by
   each scraper? (Recommend: library first, extract to service when >3
   scrapers consume it.)

## Dependencies

- ADR S-2 **must ship first**. S-3 is meaningless without the demand log.
- ADR S-1 SHOULD ship first (or in parallel) so the `mis_tagged` gap type
  is populated and the orchestrator doesn't waste budget on cells that are
  actually re-classifiable.
- New Alembic migration: `settle_contributions_pending_stratification`
  table + provenance column on `settle_contributions`.
- No Agent A dependency for v1 backend; any attorney-facing messaging on
  single-source cells requires cross-domain escalation.

## Sequencing recommendation

1. Ship **S-1** (reclassification) first — highest leverage, lowest risk,
   likely closes ~30-40% of current empty-pool cells with zero new scraping.
2. Ship **S-2** (demand log + classification) second — no scraper dependency,
   creates the feedback loop.
3. Ship **S-3** (orchestrator + stratification) last — depends on both.

## References

- Cohort R commit: `7847c54`
- ADR S-1: `ADR_20260507_multi_tag_injury_reclassification.md`
- ADR S-2: `ADR_20260507_query_demand_log.md`
- Year-2 "Never Sell Empty Dashboards" invariant
- `scripts/data-collection/` — existing scraper landscape
