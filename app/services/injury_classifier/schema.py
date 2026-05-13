"""Output schema for the deterministic injury classifier.

Stored as JSONB on settle_contributions.injury_classification.

Design principle: backward-compatible. The existing injury_category column
(List[str]) remains the primary attorney-facing field. This new
injury_classification JSONB column carries the audit-trail provenance
(rules matched, confidence, review status). The estimator only needs
injury_category for filtering; injury_classification is for audit/review
tooling.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# CLOSED-SET INJURY TAXONOMY (v1.0.0)
# ============================================================================
#
# Adding or removing tags from this enum is a MAJOR version bump per
# version.py semver discipline. Modifying rules for an existing tag is MINOR.
#
# Naming convention: snake_case, descriptive, mapped to common legal/medical
# terminology. Tags are deliberately granular where queryability matters
# (PARALYSIS is separate from SPINAL_INJURY because attorneys often filter
# for catastrophic-injury cases specifically).
# ============================================================================

class InjuryTag(str, Enum):
    SOFT_TISSUE = "soft_tissue"
    FRACTURE = "fracture"
    TRAUMATIC_BRAIN_INJURY = "traumatic_brain_injury"
    SPINAL_INJURY = "spinal_injury"
    PARALYSIS = "paralysis"  # Separate from SPINAL_INJURY for queryability
    INTERNAL_ORGAN_INJURY = "internal_organ_injury"
    AMPUTATION = "amputation"
    BURNS = "burns"
    SCARRING_DISFIGUREMENT = "scarring_disfigurement"
    VISION_LOSS = "vision_loss"
    HEARING_LOSS = "hearing_loss"
    NERVE_DAMAGE = "nerve_damage"
    PSYCHOLOGICAL_INJURY = "psychological_injury"
    CHRONIC_PAIN = "chronic_pain"
    REPRODUCTIVE_INJURY = "reproductive_injury"
    DENTAL_INJURY = "dental_injury"
    DEATH = "death"
    UNCLASSIFIED = "unclassified"  # Special tag for narratives that match no rule


class ClassificationSource(str, Enum):
    """Origin and confidence tier of the classification."""
    RULE_ENGINE_EXPLICIT = "rule_engine_explicit"        # ≥0.95, strong keyword match
    RULE_ENGINE_CONTEXTUAL = "rule_engine_contextual"    # 0.70-0.94, contextual cluster
    RULE_ENGINE_WEAK = "rule_engine_weak"                # 0.60-0.69, requires review
    HUMAN_REVIEWED = "human_reviewed"                     # Human confirmed/corrected
    LEGACY_SINGLE_TAG = "legacy_single_tag"               # Pre-existing, not yet reclassified
    UNCLASSIFIED = "unclassified"                         # No rule matched


class ReviewTrigger(str, Enum):
    """Deterministic triggers that route a classification to the human review queue."""
    EXCESSIVE_TAG_COUNT = "excessive_tag_count"            # >4 tags simultaneously
    LOW_CONFIDENCE_TAG = "low_confidence_tag"              # Any tag in 0.60-0.69 band
    VERDICT_AMOUNT_MISMATCH = "verdict_amount_mismatch"    # Severe injuries + small verdict
    LOGICAL_CONTRADICTION = "logical_contradiction"        # Death without fatal-pathway
    INSUFFICIENT_NARRATIVE = "insufficient_narrative"      # <200 chars
    UNCLASSIFIED_NARRATIVE = "unclassified_narrative"      # No rules matched
    CO_OCCURRENCE_VIOLATION = "co_occurrence_violation"    # Tag combination violates rule


class ReviewAction(str, Enum):
    """Outcome of human review of a flagged classification."""
    ACCEPT = "accept"       # Reviewer confirms the engine's tags as-is
    MODIFY = "modify"       # Reviewer changes tags (records both before/after)
    REJECT = "reject"       # Reviewer marks classification as unrecoverable


# ============================================================================
# OUTPUT SCHEMAS
# ============================================================================

class InjuryClassification(BaseModel):
    """Complete audit-trail record stored as JSONB.

    Fields are deliberately verbose for legal defensibility — every
    classification decision is traceable to specific rule matches.
    """
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "tags": ["fracture", "soft_tissue"],
                "confidence": {"fracture": 0.99, "soft_tissue": 0.92},
                "matched_spans": {
                    "fracture": ["comminuted hip fracture", "total hip replacement"],
                    "soft_tissue": ["rotator cuff tear", "lower back soft tissue"],
                },
                "source": "rule_engine_explicit",
                "classifier_version": "1.0.0",
                "classified_at": "2026-05-13T12:00:00Z",
                "review_triggers": [],
                "human_review_required": False,
            }
        },
    )

    # Core classification output
    tags: list[InjuryTag] = Field(
        default_factory=list,
        description="Multi-tag list. Empty when narrative is unclassified."
    )
    confidence: dict[str, float] = Field(
        default_factory=dict,
        description="Per-tag confidence score. Keys are InjuryTag values."
    )
    matched_spans: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Text spans that triggered each tag, for audit. Keys are InjuryTag values."
    )

    # Provenance
    source: ClassificationSource
    classifier_version: str
    classified_at: datetime

    # Review pipeline
    review_triggers: list[ReviewTrigger] = Field(default_factory=list)
    human_review_required: bool = False

    # Human review record (populated only after review)
    reviewed: bool = False
    reviewer_id: Optional[str] = None
    review_action: Optional[ReviewAction] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    def tag_names(self) -> list[str]:
        """Return tag values as strings (for compatibility with injury_category column)."""
        return [t.value if hasattr(t, "value") else str(t) for t in self.tags]
