# ADR S-1: Multi-Tag Injury Reclassification of Existing Verdicts

- **Date:** 2026-05-07
- **Status:** PROPOSED (awaiting architect decision)
- **Authors:** Agent B (executor)
- **Related:** Cohort R empty-pool guard (commit `7847c54`), surfaced via
  `scripts/_cohort_q_attorney_examples.py` Scenario 4 (Orange County, FL ×
  Premises Liability × soft_tissue).

## Context

The Cohort R live probe surfaced that even when a state-tier cohort has **79
approved FL Premises Liability verdicts**, the injury-filtered pool for
`soft_tissue` came back empty. `injury_category` is already modeled as
`List[str]` in `SettleContribution` (supports multi-tag), but the ingestion
pipeline populates it with a **single dominant tag** per verdict. Slip-and-fall
narratives that contain language like *sprain, strain, contusion, whiplash*
alongside a primary `fracture` or `back_injury` are classified with the primary
tag only — so the soft-tissue secondary signal is lost.

The hypothesis: a significant fraction of "empty pool" gaps surfaced by the
Cohort R guard are **mis-tagging, not missing data**. Fixing tagging is cheaper
and lower-risk than scraping new cases.

## Decision

Run a one-shot **multi-tag reclassification pass** over existing approved
verdicts:

1. LLM + rule-based hybrid pass over `case_facts` / `injury_description` /
   `outcome_type` for every row in `settle_contributions` with
   `status='approved'`.
2. Emit `injury_category[]` as a **union** of existing tags plus any new tags
   inferred from the narrative, each carrying a confidence score.
3. Add a new column `injury_tag_provenance JSONB` on `settle_contributions`
   capturing per-tag origin and confidence: `{tag: {source, confidence,
   reviewer_id, reviewed_at}}` where `source ∈ {source_explicit, rule_match,
   nlp_inferred, human_reviewed}`.
4. **Gate writeback by confidence threshold.** Tags with
   `confidence >= 0.85` auto-merge. Tags with `0.60 <= confidence < 0.85`
   enter a human review queue. Tags below 0.60 are dropped.
5. **Non-destructive append-only.** Never overwrite existing tags; only add
   new ones. Preserves immutability claims on the tamper-evident contribution
   record.

## Alternatives Considered

| Option | Verdict |
|---|---|
| **A.** Leave tagging as-is; rely on new scraping to fill gaps. | Rejected. Scraping new data is 10-100x more expensive than re-classifying existing data, and the mis-tagged rows remain wrong forever. |
| **B.** Rule-based regex only (no LLM). | Rejected. High precision, low recall. Misses legal-narrative phrasings that don't use canonical injury terms. |
| **C.** LLM-only with no human review. | Rejected. Hallucination risk directly corrupts the percentile engine — a phantom `soft_tissue` tag on a fracture verdict skews cohort statistics. |
| **D.** Hybrid LLM + rule + confidence-gated human review. | **Chosen.** High recall + bounded hallucination risk + auditable provenance. |

## Consequences

### Positive
- **~30-40% of "empty pool" cells likely become populated with zero new
  scraping**, based on informal inspection of FL Premises Liability narratives.
- Explicit `injury_tag_provenance` column creates an audit trail for
  regulatory / IRB defense — any tag can be traced to origin and reviewer.
- Enables Cohort S-2 demand log to distinguish `coverage_gap` from
  `mis_tagged` gap types.
- Append-only preserves tamper-evidence claims on the contribution record.

### Negative
- One-time LLM inference cost (estimate: $0.005 × N rows; for ~5k FL rows
  ≈ $25, trivial).
- Human review queue introduces ops overhead for the mid-confidence band.
  Mitigation: batch review, 2-minute SLA per row, domain-expert reviewer
  (paralegal-tier).
- Phantom-tag risk for narratives that are genuinely ambiguous. Mitigation:
  audit trail + reversibility — any mis-classified tag can be reviewed and
  removed with `provenance` preserved.

## Open Questions (for architect)

1. **Confidence threshold calibration.** 0.85 / 0.60 are initial guesses.
   Do we run a gold-standard labeled set first to calibrate?
2. **Reviewer sourcing.** In-house (Razi), paralegal contractor, or
   crowdsourced with consensus rule?
3. **Versioning.** Do we version the LLM prompt + model so tag sets can be
   re-audited if the prompt changes? (Recommend yes — `tag_set_version`
   column.)
4. **Backfill ordering.** Run against all historical data at once, or
   stratify by jurisdiction/case_type and watch percentile stability?

## Dependencies

- New column migration: `alembic revision -m "add injury_tag_provenance column"`
- Reviewer UI (belongs to Agent A — cross-domain; **escalate to Razi before
  starting**).
- One-shot backfill script: `scripts/reclassify_injury_tags.py`.

## References

- Cohort R commit: `7847c54`
- Cohort R log: `logs/cohort_r_attorney_examples.log`
- `app/models/case_bank.py::SettleContribution.injury_category`
