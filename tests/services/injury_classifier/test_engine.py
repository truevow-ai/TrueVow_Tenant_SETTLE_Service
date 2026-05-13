"""End-to-end tests for the deterministic injury classifier engine.

Tests run against the 15 canonical fixtures in canonical_verdicts.py.
Each fixture has expected_tags and expected_review_required — these
form a regression suite that must stay green across rule changes.
"""
from __future__ import annotations

import pytest

from app.services.injury_classifier import (
    CLASSIFIER_VERSION,
    InjuryTag,
    ReviewTrigger,
    classify,
)
from tests.services.injury_classifier.fixtures.canonical_verdicts import (
    CANONICAL_VERDICTS,
)


# ============================================================================
# CORE TESTS — fixture-driven regression suite
# ============================================================================

class TestCanonicalFixtures:
    """Run the classifier against every canonical fixture and verify
    expected tags + review status match."""

    @pytest.mark.parametrize(
        "fixture",
        CANONICAL_VERDICTS,
        ids=lambda f: f["id"],
    )
    def test_expected_tags(self, fixture: dict):
        """Every fixture's expected_tags must be produced by the engine."""
        result = classify(
            narrative=fixture["narrative"],
            verdict_amount=fixture["verdict_amount"],
        )
        actual_tags = set(result.tags)
        expected_tags = fixture["expected_tags"]

        # Convert InjuryTag enum values to plain strings for comparison
        # (Pydantic with use_enum_values=True coerces to strings on serialization)
        actual_tag_values = {
            t.value if hasattr(t, "value") else str(t)
            for t in actual_tags
        }
        expected_tag_values = {
            t.value if hasattr(t, "value") else str(t)
            for t in expected_tags
        }

        assert actual_tag_values == expected_tag_values, (
            f"Fixture {fixture['id']}: expected {expected_tag_values}, "
            f"got {actual_tag_values}. Notes: {fixture['notes']}"
        )

    @pytest.mark.parametrize(
        "fixture",
        CANONICAL_VERDICTS,
        ids=lambda f: f["id"],
    )
    def test_review_required_flag(self, fixture: dict):
        """Every fixture's expected_review_required must match."""
        result = classify(
            narrative=fixture["narrative"],
            verdict_amount=fixture["verdict_amount"],
        )
        assert result.human_review_required == fixture["expected_review_required"], (
            f"Fixture {fixture['id']}: expected review_required="
            f"{fixture['expected_review_required']}, got {result.human_review_required}. "
            f"Triggers fired: {result.review_triggers}. Notes: {fixture['notes']}"
        )


# ============================================================================
# DETERMINISM TESTS — same input → same output
# ============================================================================

class TestDeterminism:
    """Verify the classifier is fully deterministic: identical input produces
    identical output across repeated calls."""

    def test_repeated_classify_produces_identical_tags(self):
        """Classify the same narrative 10 times; tags must be identical every time."""
        narrative = CANONICAL_VERDICTS[0]["narrative"]
        verdict_amount = CANONICAL_VERDICTS[0]["verdict_amount"]

        results = [
            classify(narrative=narrative, verdict_amount=verdict_amount)
            for _ in range(10)
        ]

        first_tags = set(results[0].tags)
        for i, result in enumerate(results[1:], start=1):
            assert set(result.tags) == first_tags, (
                f"Run {i} produced different tags: {set(result.tags)} vs {first_tags}"
            )

    def test_repeated_classify_produces_identical_confidence(self):
        """Confidence scores must be byte-identical across repeated calls."""
        narrative = CANONICAL_VERDICTS[0]["narrative"]
        verdict_amount = CANONICAL_VERDICTS[0]["verdict_amount"]

        results = [
            classify(narrative=narrative, verdict_amount=verdict_amount)
            for _ in range(10)
        ]

        first_conf = results[0].confidence
        for i, result in enumerate(results[1:], start=1):
            assert result.confidence == first_conf, (
                f"Run {i} produced different confidence: {result.confidence} vs {first_conf}"
            )


# ============================================================================
# EDGE CASES — empty input, malformed input
# ============================================================================

class TestEdgeCases:
    """Classifier must handle adversarial input without raising."""

    def test_empty_string(self):
        """Empty narrative produces UNCLASSIFIED with no tags."""
        result = classify(narrative="", verdict_amount=None)
        assert result.tags == []
        assert ReviewTrigger.UNCLASSIFIED_NARRATIVE in result.review_triggers

    def test_whitespace_only(self):
        """Whitespace-only narrative produces UNCLASSIFIED."""
        result = classify(narrative="   \n\t  ", verdict_amount=None)
        assert result.tags == []
        assert ReviewTrigger.UNCLASSIFIED_NARRATIVE in result.review_triggers

    def test_no_verdict_amount(self):
        """Missing verdict_amount must not crash; VERDICT_AMOUNT_MISMATCH trigger
        must not fire if amount is unknown."""
        result = classify(
            narrative=CANONICAL_VERDICTS[5]["narrative"],  # amputation case
            verdict_amount=None,
        )
        # Tags should still be detected
        assert any("amputation" in t.value for t in result.tags if hasattr(t, "value")) \
            or InjuryTag.AMPUTATION.value in [t.value if hasattr(t, "value") else t for t in result.tags]
        # Should NOT trigger VERDICT_AMOUNT_MISMATCH because amount unknown
        assert ReviewTrigger.VERDICT_AMOUNT_MISMATCH not in result.review_triggers

    def test_classifier_version_recorded(self):
        """Every classification records the classifier_version.

        Asserts equality with the imported CLASSIFIER_VERSION constant
        rather than a hardcoded string — robust against future version bumps.
        """
        result = classify(narrative="whiplash injury", verdict_amount=10_000)
        assert result.classifier_version == CLASSIFIER_VERSION

    def test_classified_at_recorded(self):
        """Every classification records classified_at timestamp."""
        result = classify(narrative="whiplash injury", verdict_amount=10_000)
        assert result.classified_at is not None
