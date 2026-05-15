"""Deterministic injury classifier for SETTLE legal verdicts.

Public API:
    classify(narrative, verdict_amount=None) -> InjuryClassification
    classify_batch(narratives) -> list[InjuryClassification]

    InjuryTag, ClassificationSource, ReviewTrigger, ReviewAction — enums
    InjuryClassification — Pydantic model (audit trail schema)

    TAG_RULES — dict of all 17 tag rules (introspection / testing)
    CLASSIFIER_VERSION — current version string
"""
from .engine import classify, classify_batch
from .rules import TAG_RULES, FATAL_PATHWAY_TAGS, SEVERE_INJURY_TAGS
from .schema import (
    ClassificationSource,
    InjuryClassification,
    InjuryTag,
    ReviewAction,
    ReviewTrigger,
)
from .synth import synthesize_pseudo_narrative
from .triggers import evaluate_triggers
from .version import CLASSIFIER_VERSION, LEGACY_CLASSIFIER_VERSION

__all__ = [
    "classify",
    "classify_batch",
    "InjuryTag",
    "InjuryClassification",
    "ClassificationSource",
    "ReviewTrigger",
    "ReviewAction",
    "evaluate_triggers",
    "synthesize_pseudo_narrative",
    "TAG_RULES",
    "FATAL_PATHWAY_TAGS",
    "SEVERE_INJURY_TAGS",
    "CLASSIFIER_VERSION",
    "LEGACY_CLASSIFIER_VERSION",
]
