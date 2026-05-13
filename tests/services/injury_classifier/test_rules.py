"""Per-rule unit tests for the injury classifier.

For each TagRule, verify that:
- Strong patterns produce confidence ≥0.95
- Contextual patterns produce confidence in 0.60-0.84 band
- Exclusion patterns disqualify the tag
- The expected spans are captured for audit
"""
from __future__ import annotations

import pytest

from app.services.injury_classifier.engine import calculate_confidence
from app.services.injury_classifier.rules import TAG_RULES
from app.services.injury_classifier.schema import InjuryTag


# ============================================================================
# STRONG-PATTERN TESTS — must produce ≥0.95 confidence
# ============================================================================

class TestStrongPatterns:
    """Each tag must produce high confidence when its strong patterns match."""

    @pytest.mark.parametrize("narrative,expected_tag", [
        ("Cervical sprain documented at 4 weeks post-MVA.", InjuryTag.SOFT_TISSUE),
        ("Plaintiff suffered a comminuted left femur fracture.", InjuryTag.FRACTURE),
        ("Diagnosed with mild traumatic brain injury (MTBI).", InjuryTag.TRAUMATIC_BRAIN_INJURY),
        ("Herniated disc at L4-L5 required lumbar fusion.", InjuryTag.SPINAL_INJURY),
        ("Resulting in T6 paraplegia.", InjuryTag.PARALYSIS),
        ("Emergency splenectomy performed.", InjuryTag.INTERNAL_ORGAN_INJURY),
        ("Below-knee amputation of left leg.", InjuryTag.AMPUTATION),
        ("Second and third-degree burns over 22% of body.", InjuryTag.BURNS),
        ("Permanent scarring on face and arms.", InjuryTag.SCARRING_DISFIGUREMENT),
        ("Permanent blindness in left eye following globe rupture.", InjuryTag.VISION_LOSS),
        ("Permanent hearing loss diagnosed.", InjuryTag.HEARING_LOSS),
        ("Diagnosed with complex regional pain syndrome (CRPS).", InjuryTag.NERVE_DAMAGE),
        ("Diagnosed with PTSD by treating psychiatrist.", InjuryTag.PSYCHOLOGICAL_INJURY),
        ("Chronic pain syndrome developed over 18 months.", InjuryTag.CHRONIC_PAIN),
        ("Emergency hysterectomy following crush trauma.", InjuryTag.REPRODUCTIVE_INJURY),
        ("Lost three teeth and required dental implants.", InjuryTag.DENTAL_INJURY),
        ("Plaintiff died from injuries sustained.", InjuryTag.DEATH),
    ])
    def test_strong_pattern_produces_high_confidence(self, narrative: str, expected_tag: InjuryTag):
        rule = TAG_RULES[expected_tag]
        conf, spans = calculate_confidence(narrative, rule)
        assert conf >= 0.95, (
            f"Tag {expected_tag.value}: expected ≥0.95, got {conf}. "
            f"Narrative: {narrative}. Spans: {spans}"
        )
        assert len(spans) >= 1, f"Tag {expected_tag.value}: expected matched spans, got {spans}"


# ============================================================================
# EXCLUSION TESTS — negation must disqualify the tag
# ============================================================================

class TestExclusions:
    """Negation patterns must drive confidence to 0.0."""

    @pytest.mark.parametrize("narrative,blocked_tag", [
        ("CT scan ruled out fracture.", InjuryTag.FRACTURE),
        ("MRI showed no spinal injury.", InjuryTag.SPINAL_INJURY),
        ("Ruled out concussion and TBI.", InjuryTag.TRAUMATIC_BRAIN_INJURY),
        ("Denied any soft tissue injury.", InjuryTag.SOFT_TISSUE),
        ("No internal injury observed.", InjuryTag.INTERNAL_ORGAN_INJURY),
        ("No burns documented.", InjuryTag.BURNS),
        ("Brush with death only; no serious injury.", InjuryTag.DEATH),
        ("Near-death experience but full recovery.", InjuryTag.DEATH),
    ])
    def test_exclusion_disqualifies_tag(self, narrative: str, blocked_tag: InjuryTag):
        rule = TAG_RULES[blocked_tag]
        conf, _ = calculate_confidence(narrative, rule)
        assert conf == 0.0, (
            f"Tag {blocked_tag.value}: exclusion pattern should disqualify, but got conf={conf}. "
            f"Narrative: {narrative}"
        )


# ============================================================================
# CONTEXTUAL-CLUSTER TESTS — multiple weak signals → 0.70+
# ============================================================================

class TestContextualClusters:
    """Multiple contextual matches should sum to medium confidence."""

    def test_two_contextual_soft_tissue_signals(self):
        """Two soft_tissue contextual signals → confidence 0.70."""
        narrative = "Plaintiff complained of stiffness and underwent physical therapy."
        rule = TAG_RULES[InjuryTag.SOFT_TISSUE]
        conf, _ = calculate_confidence(narrative, rule)
        # 2 contextual matches: 'stiffness' and 'physical therapy'
        assert conf == 0.70, f"Expected 0.70 for 2 contextual matches, got {conf}"

    def test_single_contextual_is_weak(self):
        """One contextual match → confidence 0.60 (weak band)."""
        narrative = "Plaintiff was advised physical therapy."
        rule = TAG_RULES[InjuryTag.SOFT_TISSUE]
        conf, _ = calculate_confidence(narrative, rule)
        assert conf == 0.60, f"Expected 0.60 for 1 contextual match, got {conf}"


# ============================================================================
# DETERMINISM TEST — same regex, same result, always
# ============================================================================

class TestRuleDeterminism:
    """Each rule produces the same confidence for the same input every time."""

    @pytest.mark.parametrize("tag,narrative", [
        (InjuryTag.SOFT_TISSUE, "Cervical sprain documented."),
        (InjuryTag.FRACTURE, "Comminuted femur fracture."),
        (InjuryTag.DEATH, "Plaintiff died from his injuries."),
    ])
    def test_repeated_calculate_confidence_identical(self, tag: InjuryTag, narrative: str):
        rule = TAG_RULES[tag]
        results = [calculate_confidence(narrative, rule) for _ in range(20)]
        for conf, spans in results[1:]:
            assert conf == results[0][0]
            assert spans == results[0][1]
