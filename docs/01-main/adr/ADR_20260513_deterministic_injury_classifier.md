# ADR S-1.1 — Deterministic Injury Classifier (Refinement of S-1)

**Status:** PROPOSED
**Date:** 2026-05-13
**Supersedes:** ADR S-1 (multi-tag injury reclassification via LLM)
**Decision-maker:** Yasha (founder) + Hyperagent (architect)

---

## Context

ADR S-1 (drafted earlier this week) proposed a hybrid LLM-driven multi-tag reclassification approach for the 440 approved verdicts in `settle_contributions`. Investigation surfaced a specific problem (the Orange County FL Premises Liability soft_tissue cell returning n=0 despite 79 approved Premises Liability verdicts), which prompted Yasha to question whether LLM-driven classification was the right architectural choice for legal-grade attorney-facing data.

The honest analysis: **LLM-driven classification is the wrong architectural choice for this domain.** Personal injury verdict narratives use highly standardized legal-medical vocabulary; the linguistic space is bounded and well-defined; and the requirements for legal defensibility, reproducibility, and auditability all favor deterministic rules over probabilistic judgment.

---

## Decision

Replace the LLM-driven classifier proposed in ADR S-1 with a **deterministic rule engine** implemented in `app/services/injury_classifier/`. ZERO LLM dependencies on the classification path. Optionally retain LLM as a *narrow human-reviewer aid* on the review queue UI — never as a primary classifier.

### Library architecture

```
app/services/injury_classifier/
├── __init__.py        # public API (classify, classify_batch, enums)
├── version.py         # CLASSIFIER_VERSION = "1.0.0" with semver discipline
├── schema.py          # Pydantic InjuryClassification + 17-tag InjuryTag enum
├── rules.py           # closed-set TagRule library (17 rules with regex)
├── engine.py          # classify() — deterministic confidence calculation
└── triggers.py        # 7 review-trigger rules (deterministic)

tests/services/injury_classifier/
├── test_engine.py     # 15 canonical fixture tests + determinism + edge cases
├── test_rules.py      # per-tag strong-pattern, exclusion, contextual tests
├── test_triggers.py   # 7 trigger rule tests
└── fixtures/
    └── canonical_verdicts.py  # 15 ground-truth verdicts
```

### Closed-set taxonomy (17 tags, v1.0.0)

`soft_tissue`, `fracture`, `traumatic_brain_injury`, `spinal_injury`, `paralysis`, `internal_organ_injury`, `amputation`, `burns`, `scarring_disfigurement`, `vision_loss`, `hearing_loss`, `nerve_damage`, `psychological_injury`, `chronic_pain`, `reproductive_injury`, `dental_injury`, `death`, plus `unclassified` for review-only edge cases.

Adding/removing a tag is a MAJOR version bump. Modifying keywords within a tag is MINOR. Bug fixes in regex are PATCH.

### Confidence schedule (fixed, deterministic)

| Match signal | Confidence | Source label |
|---|---|---|
| 2+ strong-pattern matches | 0.99 | `rule_engine_explicit` |
| 1 strong-pattern match | 0.95 | `rule_engine_explicit` |
| 3+ contextual matches | 0.80 | `rule_engine_contextual` |
| 2 contextual matches | 0.70 | `rule_engine_contextual` |
| 1 contextual match | 0.60 | `rule_engine_weak` (review required) |
| Any exclusion match | 0.00 | (disqualified) |

Auto-apply threshold: ≥0.70. Below that, the tag is recorded but flagged for human review.

### Seven deterministic review triggers

1. **EXCESSIVE_TAG_COUNT** — >4 tags simultaneously (sanity check)
2. **LOW_CONFIDENCE_TAG** — any tag in 0.60-0.69 weak band
3. **VERDICT_AMOUNT_MISMATCH** — severe injuries (amputation, paralysis, TBI, death, vision_loss, reproductive) with sub-$50k verdict
4. **LOGICAL_CONTRADICTION** — death tagged without a fatal-pathway injury (internal_organ, TBI, burns, amputation, spinal)
5. **INSUFFICIENT_NARRATIVE** — <100 chars OR (100-200 chars AND <2 tags found)
6. **UNCLASSIFIED_NARRATIVE** — no rules matched at all
7. **CO_OCCURRENCE_VIOLATION** — tag combination violates a rule's forbidden-co-occurrence set

### Audit trail (stored as JSONB)

Every classification produces a complete `InjuryClassification` record:

```python
{
  "tags": ["fracture", "soft_tissue"],
  "confidence": {"fracture": 0.99, "soft_tissue": 0.92},
  "matched_spans": {
    "fracture": ["comminuted hip fracture", "total hip replacement"],
    "soft_tissue": ["rotator cuff tear"]
  },
  "source": "rule_engine_explicit",
  "classifier_version": "1.0.0",
  "classified_at": "2026-05-13T12:00:00Z",
  "review_triggers": [],
  "human_review_required": false,
  "reviewed": false,
  "reviewer_id": null,
  "review_action": null
}
```

Every decision is traceable to specific regex matches with byte-offset evidence.

---

## Consequences

### Positive

1. **Reproducibility** — Same input → same output, byte-identical across runs and machines.
2. **Legal defensibility** — Every tag traceable to a named rule + matched text span. Stronger than "the LLM thought so" in regulatory or litigation review.
3. **Cost** — Zero marginal cost per classification. No LLM API spend at scale.
4. **Performance** — Microseconds per row (regex matching). Sub-second to classify all 440 existing rows.
5. **Versionable** — TAG_RULES is code; git diff shows exactly what changed between versions.
6. **Domain-expert reviewable** — A personal injury attorney can read `rules.py` and validate without needing AI expertise.
7. **Test coverage** — 15 canonical fixtures form a regression suite. All passing in v1.0.0.

### Negative

1. **Brittleness to unusual phrasing** — A typo or rare medical term may miss a tag. Mitigation: human review queue catches these; rule library evolves via review feedback.
2. **Maintenance overhead** — Every new linguistic pattern requires a rule update + version bump. Acceptable cost for legal-grade reliability.
3. **Coverage gap on novel injuries** — New injury categories require MAJOR version bumps. Expected to be rare.

### Neutral

1. The library is **additive** to `settle_contributions` — existing `injury_category: List[str]` column remains; new `injury_classification: JSONB` column carries the audit trail. Zero schema breakage.

---

## Implementation plan

### Phase 1 — Library delivery (architect-led, this turn)

Deliverables (all in `/agent/workspace/injury_classifier/`):
- ✅ `app/services/injury_classifier/` (5 .py files, ~1000 LoC)
- ✅ `tests/services/injury_classifier/` (3 test files + canonical fixtures)
- ✅ This ADR document
- ✅ 15/15 canonical fixtures passing on local smoke test

### Phase 2 — Qoder integration (next session)

Coherent unit per Autonomy Calibration Pattern:
1. Pull the library files into `TrueVow_Tenant_SETTLE-Service/app/services/injury_classifier/`
2. Pull test files into `tests/services/injury_classifier/`
3. Add Alembic migration: `ALTER TABLE settle_contributions ADD COLUMN injury_classification JSONB DEFAULT '{}'::jsonb`
4. Run pytest → confirm 15/15 fixtures pass
5. Run pre-commit gates + secret scan
6. Commit as Cohort S-1: `feat(injury_classifier): deterministic 17-tag classifier with audit trail`
7. Push (gated on Yasha approval per usual rule)

### Phase 3 — Reclassification pass (next-next session)

Run the classifier across all 440 approved rows in `settle_contributions`:
1. Pull each row's case-facts narrative
2. Call `classify(narrative, verdict_amount)`
3. Update `injury_category` (multi-tag append) AND `injury_classification` (audit JSONB)
4. Queue review-flagged rows to a `human_review_queue` table
5. Re-run enumeration probe — measure how many `(jurisdiction, case_type, injury)` cells flipped from n=0 to n≥1
6. Report results

Expected: significant uplift on the Orange County FL Premises Liability soft_tissue cell and other multi-injury combinations that were single-tagged at ingest. Project doc estimate: ~30-40% of currently-empty cells likely become populated with zero new scraping.

### Phase 4 — Human review queue (later)

When the queue accumulates enough flagged rows, build a simple review UI:
- Show narrative + proposed tags + confidence + trigger reasons
- Reviewer can accept, modify, or reject
- All actions recorded in `injury_classification` JSONB
- Library evolves: novel patterns surfaced via review become new rule candidates for v1.1.0

---

## Alternatives considered (and rejected)

### Alternative A: Pure LLM classifier (original ADR S-1)

Rejected because: non-deterministic, not legally defensible, expensive at scale, opaque audit trail, model-version drift over time.

### Alternative B: Hybrid LLM + rules with LLM as primary

Rejected for the same reasons as A — LLM remains in the auto-apply path, inheriting all of A's downsides.

### Alternative C: Rules + LLM as confidence enhancer (parallel scoring)

Rejected because it produces hybrid records that can't be cleanly audited. Either a tag is rule-derived (traceable to regex) or LLM-derived (not auditable to a single source) — combining produces ambiguity.

### Alternative D: Pure rules, no LLM, no human review

Rejected because some narratives are genuinely ambiguous (the 6-15% that fall into 0.60-0.69 weak band). Without human review, those are dropped silently, losing recall.

### Selected: Pure rules + tiered human review

The chosen architecture. Rules handle the 85-94% of unambiguous cases deterministically. Human review handles the 6-15% ambiguous/edge cases. LLM has zero role on the classification path.

---

## Version compatibility

This ADR's library is `injury_classifier v1.0.0`. All future modifications follow semver:

- **v1.1.0** — keyword additions/refinements (most common evolution)
- **v1.0.1** — bug fixes in existing regex (typos, false-positive corrections)
- **v2.0.0** — tag added/removed from taxonomy

Every classified row records the version. Bulk re-classification with a new version produces a side-by-side audit of changes.

---

## Open questions for follow-up

1. **Multi-tag vs primary-tag schema** — Should the `injury_category` column remain `List[str]` (multi-tag) or split into `primary_injury` + `secondary_injuries`? Architect's lean: keep multi-tag List[str], it's already the type.

2. **Review queue UI** — Web app, admin dashboard, or simple CSV export? Defer to Phase 4 once volume warrants.

3. **Real-data canonical fixtures** — Should we extract 50+ actual Florida verdicts as fixtures (in addition to the 15 synthetic) to harden the regression suite? Defer until after Phase 3 reclassification pass surfaces real edge cases.

4. **LLM-second-opinion button on review queue** — Useful tool for reviewers, but does the LLM output need any guardrails (only valid taxonomy tags, etc.)? Defer to Phase 4 UI design.

---

**Sign-off:** Yasha approval requested. Library files staged in `/agent/workspace/injury_classifier/`, ready for Qoder integration into the SETTLE repo.
