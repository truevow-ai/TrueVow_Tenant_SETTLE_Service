"""Deterministic review-trigger evaluator.

Triggers route a classification to the human review queue. The list of
triggers is exhaustive (one of seven kinds per ReviewTrigger enum) and
each trigger has a precise, testable condition. No probabilistic
judgment.
"""
from __future__ import annotations

from typing import Optional

from .rules import FATAL_PATHWAY_TAGS, SEVERE_INJURY_TAGS, TAG_RULES
from .schema import InjuryTag, ReviewTrigger


# ============================================================================
# CONFIGURATION CONSTANTS (versioned via CLASSIFIER_VERSION)
# ============================================================================

MAX_TAGS_BEFORE_REVIEW = 4
MIN_NARRATIVE_LENGTH = 100  # very-short narratives lack context for confident classification
MIN_NARRATIVE_LENGTH_FOR_MULTI_TAG = 200  # for narratives 100-200 chars, require ≥2 tags to skip review
WEAK_CONFIDENCE_LOWER = 0.60
WEAK_CONFIDENCE_UPPER = 0.70  # half-open: weak is [0.60, 0.70)
SEVERE_VERDICT_THRESHOLD = 50_000  # USD; below this, severe injuries warrant review


def evaluate_triggers(
    narrative: str,
    tags: list[InjuryTag],
    confidence_map: dict[InjuryTag, float],
    verdict_amount: Optional[int] = None,
) -> list[ReviewTrigger]:
    """Apply seven deterministic trigger rules.

    Returns the full list of triggers that fired (may be empty). Each trigger
    is a discrete signal — they are NOT combined into a single "needs review"
    boolean here. The caller decides what to do with the trigger list
    (typically: if non-empty, route to human review queue).
    """
    triggers: list[ReviewTrigger] = []

    # Trigger 1: Excessive tag count (sanity check — very few real verdicts
    # have 5+ simultaneous injuries)
    if len(tags) > MAX_TAGS_BEFORE_REVIEW:
        triggers.append(ReviewTrigger.EXCESSIVE_TAG_COUNT)

    # Trigger 2: Low-confidence tag in the weak band
    if any(
        WEAK_CONFIDENCE_LOWER <= conf < WEAK_CONFIDENCE_UPPER
        for conf in confidence_map.values()
    ):
        triggers.append(ReviewTrigger.LOW_CONFIDENCE_TAG)

    # Trigger 3: Insufficient narrative (not enough context for confident multi-tag)
    # Tiered: <100 chars always triggers; 100-200 chars triggers only when <2 tags found
    # (rationale: short narrative with multiple strong-pattern matches has enough signal)
    narrative_len = len(narrative.strip())
    if narrative_len < MIN_NARRATIVE_LENGTH:
        triggers.append(ReviewTrigger.INSUFFICIENT_NARRATIVE)
    elif narrative_len < MIN_NARRATIVE_LENGTH_FOR_MULTI_TAG and len(tags) < 2:
        triggers.append(ReviewTrigger.INSUFFICIENT_NARRATIVE)

    # Trigger 4: Unclassified — no rules matched at all
    if not tags:
        triggers.append(ReviewTrigger.UNCLASSIFIED_NARRATIVE)

    # Trigger 5: Verdict-amount mismatch — severe injuries with tiny verdicts
    # are mathematically suspicious (likely wrong tagging or unusual posture
    # like comparative-negligence reduction or settled-for-pennies-on-dollar)
    tag_set = set(tags)
    if (
        verdict_amount is not None
        and verdict_amount < SEVERE_VERDICT_THRESHOLD
        and (tag_set & SEVERE_INJURY_TAGS)
    ):
        triggers.append(ReviewTrigger.VERDICT_AMOUNT_MISMATCH)

    # Trigger 6: Logical contradiction — death without any fatal-pathway injury
    # (death normally has a proximate cause we can classify; bare death is
    # suspicious)
    if InjuryTag.DEATH in tag_set and not (tag_set & FATAL_PATHWAY_TAGS):
        # Allow death-only as a special case ONLY for very short narratives where
        # we can't infer the pathway. For longer narratives, require a pathway tag.
        if len(narrative.strip()) >= MIN_NARRATIVE_LENGTH:
            triggers.append(ReviewTrigger.LOGICAL_CONTRADICTION)

    # Trigger 7: Co-occurrence forbidden violation
    for tag in tags:
        rule = TAG_RULES.get(tag)
        if rule is None:
            continue
        if rule.co_occurrence_forbidden:
            if rule.co_occurrence_forbidden & tag_set:
                triggers.append(ReviewTrigger.CO_OCCURRENCE_VIOLATION)
                break  # one trigger per evaluation regardless of how many violations

    return triggers
