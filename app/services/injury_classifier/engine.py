"""Deterministic injury classifier engine.

ZERO LLM dependencies. ZERO non-determinism. Same input → same output, always.

Algorithm:
1. For each TagRule in the registry, scan the narrative
2. Apply exclusion patterns first (any match → score 0, tag disqualified)
3. Count strong-pattern matches → confidence schedule
4. Count contextual-pattern matches → confidence schedule
5. Collect matched spans for audit trail
6. Apply co-occurrence enforcement after all tags computed
7. Return InjuryClassification with full provenance

The confidence schedule is fixed in calculate_confidence(). To change it,
bump CLASSIFIER_VERSION (MINOR or MAJOR depending on impact).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .rules import TAG_RULES, TagRule
from .schema import (
    ClassificationSource,
    InjuryClassification,
    InjuryTag,
)
from .version import CLASSIFIER_VERSION


# ============================================================================
# CONFIDENCE SCHEDULE (deterministic)
# ============================================================================
# Documented thresholds — DO NOT modify without version bump.

CONFIDENCE_TWO_PLUS_STRONG = 0.99
CONFIDENCE_ONE_STRONG = 0.95
CONFIDENCE_THREE_PLUS_CONTEXTUAL = 0.80
CONFIDENCE_TWO_CONTEXTUAL = 0.70
CONFIDENCE_ONE_CONTEXTUAL = 0.60

AUTO_APPLY_THRESHOLD = 0.70  # ≥0.70 = auto-apply; <0.70 = weak/review/skip
WEAK_THRESHOLD = 0.60         # 0.60-0.69 = rule_engine_weak, requires review
DISQUALIFIED = 0.0


def calculate_confidence(
    narrative: str,
    rule: TagRule,
) -> tuple[float, list[str]]:
    """Score a single tag deterministically.

    Returns:
        (confidence_score, list_of_matched_spans)

    Confidence is one of: 0.99, 0.95, 0.80, 0.70, 0.60, or 0.00.
    No other values are possible. All thresholds are fixed in this function.
    """
    if not narrative or not narrative.strip():
        return DISQUALIFIED, []

    # Step 1: Exclusion patterns disqualify outright
    for excl in rule.exclusion_patterns:
        if excl.search(narrative):
            return DISQUALIFIED, []

    # Step 2: Collect strong-pattern matches with spans
    strong_spans: list[str] = []
    for pattern in rule.strong_patterns:
        for match in pattern.finditer(narrative):
            strong_spans.append(match.group(0))

    # Step 3: Collect contextual-pattern matches with spans
    contextual_spans: list[str] = []
    for pattern in rule.contextual_patterns:
        for match in pattern.finditer(narrative):
            contextual_spans.append(match.group(0))

    all_spans = strong_spans + contextual_spans

    # Step 4: Apply the fixed confidence schedule
    if len(strong_spans) >= 2:
        return CONFIDENCE_TWO_PLUS_STRONG, all_spans
    if len(strong_spans) == 1:
        return CONFIDENCE_ONE_STRONG, all_spans
    if len(contextual_spans) >= 3:
        return CONFIDENCE_THREE_PLUS_CONTEXTUAL, all_spans
    if len(contextual_spans) == 2:
        return CONFIDENCE_TWO_CONTEXTUAL, all_spans
    if len(contextual_spans) == 1:
        return CONFIDENCE_ONE_CONTEXTUAL, all_spans

    return DISQUALIFIED, []


def _determine_source(confidence_map: dict[InjuryTag, float]) -> ClassificationSource:
    """Choose the appropriate source label based on the lowest confidence among applied tags."""
    if not confidence_map:
        return ClassificationSource.UNCLASSIFIED

    min_conf = min(confidence_map.values())

    if min_conf >= 0.95:
        return ClassificationSource.RULE_ENGINE_EXPLICIT
    if min_conf >= 0.70:
        return ClassificationSource.RULE_ENGINE_CONTEXTUAL
    if min_conf >= 0.60:
        return ClassificationSource.RULE_ENGINE_WEAK
    return ClassificationSource.UNCLASSIFIED


def classify(
    narrative: str,
    verdict_amount: Optional[int] = None,
) -> InjuryClassification:
    """Classify an injury narrative deterministically.

    Args:
        narrative: The case-facts / injury-description text from the verdict.
                   Typically a sentence-to-paragraph length string.
        verdict_amount: Optional. Used by the trigger evaluator to detect
                        verdict-amount mismatches with tagged severity.

    Returns:
        InjuryClassification with full audit trail. Always returns a valid
        record — even an empty narrative produces an UNCLASSIFIED record
        with appropriate triggers. No exceptions are raised.
    """
    # Defer import to avoid circular dependency at module load
    from .triggers import evaluate_triggers

    # Step 1: Score every tag in the registry
    confidence_map: dict[InjuryTag, float] = {}
    span_map: dict[InjuryTag, list[str]] = {}

    for tag, rule in TAG_RULES.items():
        if tag == InjuryTag.UNCLASSIFIED:
            continue  # Never auto-apply
        score, spans = calculate_confidence(narrative, rule)
        if score > 0:
            confidence_map[tag] = score
            span_map[tag] = spans

    # Step 2: Filter to applied tags (auto-apply: ≥0.70; weak: 0.60-0.69 also recorded but flagged)
    applied_confidence: dict[InjuryTag, float] = {}
    weak_confidence: dict[InjuryTag, float] = {}

    for tag, score in confidence_map.items():
        if score >= AUTO_APPLY_THRESHOLD:
            applied_confidence[tag] = score
        elif score >= WEAK_THRESHOLD:
            weak_confidence[tag] = score
        # <0.60 are not recorded

    # Step 3: Apply co-occurrence requirements
    # If a tag has co_occurrence_required and none of the required tags are
    # also applied, the tag is downgraded to weak (review required).
    final_applied: dict[InjuryTag, float] = {}
    co_occurrence_downgrade: dict[InjuryTag, float] = {}

    for tag, score in applied_confidence.items():
        rule = TAG_RULES[tag]
        if rule.co_occurrence_required:
            required_set = rule.co_occurrence_required
            if not (required_set & set(applied_confidence.keys())):
                # Required co-occurrence not satisfied; downgrade
                co_occurrence_downgrade[tag] = score
                continue
        final_applied[tag] = score

    # Merge weak + co-occurrence-downgrade for the review queue
    review_candidates = {**weak_confidence, **co_occurrence_downgrade}

    # Step 4: Build the tags list (applied + weak both recorded; spans for both)
    all_tags_for_record = list(final_applied.keys()) + list(review_candidates.keys())
    full_confidence = {**final_applied, **review_candidates}
    full_spans = {tag: span_map.get(tag, []) for tag in all_tags_for_record}

    # Step 5: Determine source label
    if not all_tags_for_record:
        source = ClassificationSource.UNCLASSIFIED
    elif review_candidates:
        source = ClassificationSource.RULE_ENGINE_WEAK
    else:
        source = _determine_source(final_applied)

    # Step 6: Run trigger evaluator
    triggers = evaluate_triggers(
        narrative=narrative,
        tags=all_tags_for_record,
        confidence_map=full_confidence,
        verdict_amount=verdict_amount,
    )

    # Step 7: Determine review requirement
    human_review_required = bool(triggers) or bool(review_candidates)

    # Step 8: Assemble the final InjuryClassification
    return InjuryClassification(
        tags=all_tags_for_record,
        confidence={tag.value: round(conf, 2) for tag, conf in full_confidence.items()},
        matched_spans={
            tag.value: full_spans.get(tag, [])
            for tag in all_tags_for_record
        },
        source=source,
        classifier_version=CLASSIFIER_VERSION,
        classified_at=datetime.now(timezone.utc),
        review_triggers=triggers,
        human_review_required=human_review_required,
    )


def classify_batch(
    narratives: list[tuple[str, Optional[int]]],
) -> list[InjuryClassification]:
    """Classify a batch of narratives. Pure pass-through to classify() — kept as
    a separate function for clarity at the bulk-reclassification call site.

    Args:
        narratives: List of (narrative_text, verdict_amount) tuples.

    Returns:
        List of InjuryClassification records, same order as input.
    """
    return [classify(narrative, verdict_amount) for narrative, verdict_amount in narratives]
