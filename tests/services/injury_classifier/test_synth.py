"""Unit tests for app.services.injury_classifier.synth."""
from __future__ import annotations

from app.services.injury_classifier.synth import (
    synthesize_pseudo_narrative,
)


def test_empty_row_returns_empty_string():
    assert synthesize_pseudo_narrative({}) == ""


def test_only_unspecified_returns_empty():
    row = {"injury_category": ["Unspecified"], "primary_diagnosis": "Unknown"}
    assert synthesize_pseudo_narrative(row) == ""


def test_valid_injury_category_only():
    row = {"injury_category": ["soft_tissue", "fracture"]}
    out = synthesize_pseudo_narrative(row)
    assert "soft_tissue" in out and "fracture" in out
    assert out.startswith("Injury types:")


def test_full_row_synthesis():
    row = {
        "injury_category": ["soft_tissue"],
        "primary_diagnosis": "Concussion",
        "treatment_type": ["physical therapy", "MRI"],
        "imaging_findings": ["lumbar disc herniation"],
        "defendant_category": "commercial retail",
        "case_type": "Premises Liability",
    }
    out = synthesize_pseudo_narrative(row)
    for token in [
        "soft_tissue",
        "Concussion",
        "physical therapy",
        "MRI",
        "lumbar disc herniation",
        "commercial retail",
        "Premises Liability",
    ]:
        assert token in out, f"Token '{token}' missing from synthesized narrative"


def test_mixed_sentinels_dropped():
    row = {
        "injury_category": ["Unspecified", "soft_tissue"],
        "primary_diagnosis": "n/a",
        "treatment_type": ["physical therapy"],
    }
    out = synthesize_pseudo_narrative(row)
    assert "Unspecified" not in out
    assert "n/a" not in out
    assert "soft_tissue" in out
    assert "physical therapy" in out


def test_classifier_can_extract_from_pseudo_narrative():
    """Integration: synthesized narrative + classifier produces expected tags."""
    from app.services.injury_classifier import classify

    row = {
        "injury_category": ["Unspecified"],
        "primary_diagnosis": "Concussion",
        "treatment_type": ["physical therapy"],
        "case_type": "Premises Liability",
    }
    narrative = synthesize_pseudo_narrative(row)
    result = classify(narrative=narrative)
    tag_values = {
        t.value if hasattr(t, "value") else str(t) for t in result.tags
    }
    assert "traumatic_brain_injury" in tag_values, (
        f"TBI not found in {tag_values}; narrative was: {narrative}"
    )
