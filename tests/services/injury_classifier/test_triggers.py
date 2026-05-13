"""Tests for the deterministic review-trigger evaluator."""
from __future__ import annotations

import pytest

from app.services.injury_classifier.schema import InjuryTag, ReviewTrigger
from app.services.injury_classifier.triggers import evaluate_triggers


# Helper: long-enough narrative to avoid INSUFFICIENT_NARRATIVE trigger
LONG_NARRATIVE = (
    "Plaintiff sustained injuries in a motor vehicle accident on Interstate 95. "
    "The incident occurred during morning rush hour traffic. Multiple medical "
    "evaluations were performed to assess the extent of injuries sustained "
    "during the collision sequence and ongoing post-incident treatment."
)


class TestTriggerExcessiveTagCount:
    def test_five_tags_triggers_review(self):
        tags = [
            InjuryTag.SOFT_TISSUE, InjuryTag.FRACTURE,
            InjuryTag.TRAUMATIC_BRAIN_INJURY, InjuryTag.SPINAL_INJURY,
            InjuryTag.PSYCHOLOGICAL_INJURY,
        ]
        confidence = {t: 0.95 for t in tags}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, 1_000_000)
        assert ReviewTrigger.EXCESSIVE_TAG_COUNT in triggers

    def test_four_tags_no_trigger(self):
        tags = [
            InjuryTag.SOFT_TISSUE, InjuryTag.FRACTURE,
            InjuryTag.TRAUMATIC_BRAIN_INJURY, InjuryTag.SPINAL_INJURY,
        ]
        confidence = {t: 0.95 for t in tags}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, 1_000_000)
        assert ReviewTrigger.EXCESSIVE_TAG_COUNT not in triggers


class TestTriggerLowConfidence:
    def test_tag_with_weak_confidence_triggers_review(self):
        tags = [InjuryTag.SOFT_TISSUE]
        confidence = {InjuryTag.SOFT_TISSUE: 0.60}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, 50_000)
        assert ReviewTrigger.LOW_CONFIDENCE_TAG in triggers

    def test_tag_with_high_confidence_no_trigger(self):
        tags = [InjuryTag.SOFT_TISSUE]
        confidence = {InjuryTag.SOFT_TISSUE: 0.95}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, 50_000)
        assert ReviewTrigger.LOW_CONFIDENCE_TAG not in triggers


class TestTriggerVerdictAmountMismatch:
    def test_amputation_with_small_verdict_triggers_review(self):
        tags = [InjuryTag.AMPUTATION]
        confidence = {InjuryTag.AMPUTATION: 0.99}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, 25_000)
        assert ReviewTrigger.VERDICT_AMOUNT_MISMATCH in triggers

    def test_amputation_with_large_verdict_no_trigger(self):
        tags = [InjuryTag.AMPUTATION]
        confidence = {InjuryTag.AMPUTATION: 0.99}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, 2_500_000)
        assert ReviewTrigger.VERDICT_AMOUNT_MISMATCH not in triggers

    def test_unknown_verdict_no_trigger(self):
        """Missing verdict_amount must not trigger mismatch."""
        tags = [InjuryTag.AMPUTATION]
        confidence = {InjuryTag.AMPUTATION: 0.99}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, None)
        assert ReviewTrigger.VERDICT_AMOUNT_MISMATCH not in triggers


class TestTriggerLogicalContradiction:
    def test_death_without_pathway_triggers_review(self):
        tags = [InjuryTag.DEATH, InjuryTag.PSYCHOLOGICAL_INJURY]
        confidence = {InjuryTag.DEATH: 0.99, InjuryTag.PSYCHOLOGICAL_INJURY: 0.95}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, 500_000)
        assert ReviewTrigger.LOGICAL_CONTRADICTION in triggers

    def test_death_with_internal_organ_pathway_no_trigger(self):
        tags = [InjuryTag.DEATH, InjuryTag.INTERNAL_ORGAN_INJURY]
        confidence = {InjuryTag.DEATH: 0.99, InjuryTag.INTERNAL_ORGAN_INJURY: 0.95}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, 500_000)
        assert ReviewTrigger.LOGICAL_CONTRADICTION not in triggers

    def test_death_with_tbi_pathway_no_trigger(self):
        tags = [InjuryTag.DEATH, InjuryTag.TRAUMATIC_BRAIN_INJURY]
        confidence = {InjuryTag.DEATH: 0.99, InjuryTag.TRAUMATIC_BRAIN_INJURY: 0.95}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, 1_000_000)
        assert ReviewTrigger.LOGICAL_CONTRADICTION not in triggers


class TestTriggerInsufficientNarrative:
    def test_short_narrative_triggers_review(self):
        short = "MVA. Whiplash."
        tags = [InjuryTag.SOFT_TISSUE]
        confidence = {InjuryTag.SOFT_TISSUE: 0.95}
        triggers = evaluate_triggers(short, tags, confidence, 25_000)
        assert ReviewTrigger.INSUFFICIENT_NARRATIVE in triggers

    def test_long_narrative_no_trigger(self):
        tags = [InjuryTag.SOFT_TISSUE]
        confidence = {InjuryTag.SOFT_TISSUE: 0.95}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, 25_000)
        assert ReviewTrigger.INSUFFICIENT_NARRATIVE not in triggers


class TestTriggerUnclassified:
    def test_no_tags_triggers_review(self):
        triggers = evaluate_triggers(LONG_NARRATIVE, [], {}, 100_000)
        assert ReviewTrigger.UNCLASSIFIED_NARRATIVE in triggers

    def test_with_tags_no_trigger(self):
        tags = [InjuryTag.SOFT_TISSUE]
        confidence = {InjuryTag.SOFT_TISSUE: 0.95}
        triggers = evaluate_triggers(LONG_NARRATIVE, tags, confidence, 25_000)
        assert ReviewTrigger.UNCLASSIFIED_NARRATIVE not in triggers
