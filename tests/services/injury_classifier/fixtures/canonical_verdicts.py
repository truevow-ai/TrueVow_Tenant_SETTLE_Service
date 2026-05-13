"""Canonical verdict fixtures for ground-truth testing.

15 synthetic verdict narratives covering the major case types + edge cases
that the deterministic classifier must handle correctly. These are the
first-tier regression suite — every rule change must keep these green.

Format:
    Each fixture is a dict with:
    - id: stable identifier for traceability
    - narrative: the verdict text (as it might appear from a scraper)
    - verdict_amount: the verdict dollar figure (USD)
    - expected_tags: the set of tags the classifier MUST produce
    - expected_review_required: whether the classifier MUST flag for review
    - notes: rationale for why these are the expected outputs

When expanding to test against REAL Florida verdict data, this fixture
file is the starting point. Real-data tests should be added in a separate
fixtures/real_verdicts.py file (loaded from the database or a frozen
snapshot).
"""
from __future__ import annotations

from app.services.injury_classifier.schema import InjuryTag, ReviewTrigger


CANONICAL_VERDICTS: list[dict] = [
    # ========================================================================
    # Example 1: MVA + multi-injury (TBI + spine + soft tissue + chronic pain)
    # ========================================================================
    {
        "id": "fixture_01_mva_multi_injury",
        "narrative": (
            "Plaintiff, 34-year-old delivery driver, rear-ended by commercial "
            "vehicle on I-95. Suffered concussion with persistent post-concussive "
            "symptoms, herniated disc at L4-L5 requiring lumbar fusion surgery, "
            "and chronic neck pain (whiplash-associated disorder) lasting 18 "
            "months. Verdict: $2.4M."
        ),
        "verdict_amount": 2_400_000,
        "expected_tags": {
            InjuryTag.TRAUMATIC_BRAIN_INJURY,
            InjuryTag.SPINAL_INJURY,
            InjuryTag.SOFT_TISSUE,
            InjuryTag.CHRONIC_PAIN,
        },
        "expected_review_required": False,
        "notes": "Canonical complex case. All four tags have strong-pattern matches.",
    },

    # ========================================================================
    # Example 2: Premises liability slip + fracture + soft tissue
    # (The Orange County FL scenario)
    # ========================================================================
    {
        "id": "fixture_02_premises_fall_fracture_soft_tissue",
        "narrative": (
            "Elderly plaintiff (72) slipped on accumulated grease in defendant's "
            "grocery store. Suffered a comminuted left hip fracture requiring "
            "total hip replacement, plus rotator cuff tear from breaking the fall, "
            "and prolonged soft tissue injuries to lower back. Verdict: $1.8M."
        ),
        "verdict_amount": 1_800_000,
        "expected_tags": {
            InjuryTag.FRACTURE,
            InjuryTag.SOFT_TISSUE,
        },
        "expected_review_required": False,
        "notes": "Demonstrates multi-tag where single-tag pipeline would only capture FRACTURE.",
    },

    # ========================================================================
    # Example 3: Med-mal wrongful death + internal organ injury
    # ========================================================================
    {
        "id": "fixture_03_medmal_death_internal",
        "narrative": (
            "Plaintiff's wife died from sepsis following undiagnosed perforated "
            "bowel after a routine appendectomy. Defendant surgeon failed to "
            "recognize post-op symptoms over 48 hours. Decedent was 47 years old "
            "at time of death. Survivors awarded $4.2M for wrongful death."
        ),
        "verdict_amount": 4_200_000,
        "expected_tags": {
            InjuryTag.DEATH,
            InjuryTag.INTERNAL_ORGAN_INJURY,
        },
        "expected_review_required": False,
        "notes": "Death with clear fatal-pathway (internal organ). Should NOT trigger LOGICAL_CONTRADICTION.",
    },

    # ========================================================================
    # Example 4: Product liability burns + scarring
    # ========================================================================
    {
        "id": "fixture_04_product_burns_scarring",
        "narrative": (
            "Plaintiff suffered second and third-degree burns over 22% of her "
            "body when a defective pressure cooker exploded. Required multiple "
            "skin grafts; permanent scarring on face and arms. Hospitalization "
            "in burn ICU for 6 weeks. Verdict: $3.6M."
        ),
        "verdict_amount": 3_600_000,
        "expected_tags": {
            InjuryTag.BURNS,
            InjuryTag.SCARRING_DISFIGUREMENT,
        },
        "expected_review_required": False,
        "notes": "Burns + permanent scarring is a canonical co-occurrence. TBSA percentage is a strong burn signal.",
    },

    # ========================================================================
    # Example 5: Single-injury control — soft tissue only
    # ========================================================================
    {
        "id": "fixture_05_soft_tissue_only_control",
        "narrative": (
            "Rear-end collision at low speed (under 15 mph). Plaintiff suffered "
            "cervical sprain/strain (whiplash). Underwent 8 weeks of physical "
            "therapy with full recovery documented. No fractures, no neurological "
            "deficits. Verdict: $42,000 for past medical expenses and pain and "
            "suffering."
        ),
        "verdict_amount": 42_000,
        "expected_tags": {InjuryTag.SOFT_TISSUE},
        "expected_review_required": False,
        "notes": "Critical control: single-injury cases must NOT be inflated to multi-tag. "
                 "The 'no fractures, no neurological deficits' exclusion language is honored.",
    },

    # ========================================================================
    # Example 6: Amputation + nerve damage (phantom limb)
    # ========================================================================
    {
        "id": "fixture_06_amputation_nerve",
        "narrative": (
            "Motorcyclist plaintiff struck by intoxicated driver. Required "
            "below-knee amputation of left leg due to crush injury. Subsequently "
            "developed phantom limb pain and CRPS in the residual limb. PTSD "
            "diagnosed by treating psychiatrist 3 months post-incident. "
            "Verdict: $5.2M."
        ),
        "verdict_amount": 5_200_000,
        "expected_tags": {
            InjuryTag.AMPUTATION,
            InjuryTag.NERVE_DAMAGE,
            InjuryTag.PSYCHOLOGICAL_INJURY,
        },
        "expected_review_required": False,
        "notes": "Amputation with phantom pain (nerve damage) and post-traumatic PTSD diagnosis.",
    },

    # ========================================================================
    # Example 7: Paralysis + spinal (co-occurrence enforcement test)
    # ========================================================================
    {
        "id": "fixture_07_paralysis_spinal",
        "narrative": (
            "Construction worker fell from improperly maintained scaffold at "
            "construction site. Suffered T6 spinal cord injury resulting in "
            "complete paraplegia. Wheelchair-dependent for life. ASIA A "
            "classification at trial. Verdict: $8.5M."
        ),
        "verdict_amount": 8_500_000,
        "expected_tags": {
            InjuryTag.SPINAL_INJURY,
            InjuryTag.PARALYSIS,
        },
        "expected_review_required": False,
        "notes": "PARALYSIS co-occurrence with SPINAL_INJURY satisfied. ASIA scale + vertebral level both detected.",
    },

    # ========================================================================
    # Example 8: NEGATION HANDLING — exclusion patterns
    # ========================================================================
    {
        "id": "fixture_08_negation_exclusion",
        "narrative": (
            "Slip and fall in grocery store aisle. Plaintiff was evaluated in "
            "ER. CT scan ruled out fracture; MRI showed no spinal injury. "
            "Discharged same day with diagnosis of contusion to right hip and "
            "mild bruising. Verdict: $18,000."
        ),
        "verdict_amount": 18_000,
        "expected_tags": {InjuryTag.SOFT_TISSUE},
        "expected_review_required": False,
        "notes": "Exclusion patterns must suppress FRACTURE and SPINAL_INJURY despite their keywords appearing.",
    },

    # ========================================================================
    # Example 9: VERDICT MISMATCH — severe injury with small verdict (REVIEW)
    # ========================================================================
    {
        "id": "fixture_09_verdict_mismatch_review",
        "narrative": (
            "Plaintiff suffered traumatic brain injury with loss of consciousness "
            "lasting 4 minutes following struck-by-falling-object incident on "
            "defendant's property. Diagnosed with mild traumatic brain injury "
            "(MTBI). Comparative negligence found 90% on plaintiff. Net verdict: "
            "$8,000 after reduction."
        ),
        "verdict_amount": 8_000,
        "expected_tags": {InjuryTag.TRAUMATIC_BRAIN_INJURY},
        "expected_review_required": True,
        "notes": "Severe injury (TBI) + sub-$50k verdict must trigger VERDICT_AMOUNT_MISMATCH review.",
    },

    # ========================================================================
    # Example 10: INSUFFICIENT NARRATIVE — too short (REVIEW)
    # ========================================================================
    {
        "id": "fixture_10_insufficient_narrative",
        "narrative": "MVA. Whiplash. $25k.",
        "verdict_amount": 25_000,
        "expected_tags": {InjuryTag.SOFT_TISSUE},
        "expected_review_required": True,
        "notes": "Whiplash is detected, but narrative under 200 chars must trigger INSUFFICIENT_NARRATIVE review.",
    },

    # ========================================================================
    # Example 11: UNCLASSIFIED — no rules match (REVIEW)
    # ========================================================================
    {
        "id": "fixture_11_unclassified",
        "narrative": (
            "Plaintiff was injured during defendant's premises operations. "
            "Specific injuries were not enumerated in the case summary available "
            "from the docket. Settlement reached for nuisance value to avoid "
            "trial. Documents under protective order."
        ),
        "verdict_amount": 75_000,
        "expected_tags": set(),
        "expected_review_required": True,
        "notes": "No injury keywords present. Must result in UNCLASSIFIED_NARRATIVE trigger.",
    },

    # ========================================================================
    # Example 12: Internal organ injury — splenectomy
    # ========================================================================
    {
        "id": "fixture_12_internal_organ_splenectomy",
        "narrative": (
            "Plaintiff hit broadside by red-light-runner at intersection. "
            "Ruptured spleen requiring emergency splenectomy. Multiple rib "
            "fractures on left side from impact. 14-day ICU stay. Verdict: $1.2M."
        ),
        "verdict_amount": 1_200_000,
        "expected_tags": {
            InjuryTag.INTERNAL_ORGAN_INJURY,
            InjuryTag.FRACTURE,
        },
        "expected_review_required": False,
        "notes": "Splenectomy + rib fractures from high-energy MVA. Two strong-pattern tags.",
    },

    # ========================================================================
    # Example 13: Vision loss + facial scarring
    # ========================================================================
    {
        "id": "fixture_13_vision_scarring",
        "narrative": (
            "Plaintiff struck in face by malfunctioning power tool during "
            "construction work. Left eye sustained globe rupture, resulting in "
            "permanent blindness in left eye. Facial scarring from lacerations; "
            "two reconstructive surgeries performed with limited cosmetic recovery. "
            "Verdict: $2.8M."
        ),
        "verdict_amount": 2_800_000,
        "expected_tags": {
            InjuryTag.VISION_LOSS,
            InjuryTag.SCARRING_DISFIGUREMENT,
        },
        "expected_review_required": False,
        "notes": "Globe rupture + permanent blindness, plus facial reconstruction.",
    },

    # ========================================================================
    # Example 14: Dental injury + soft tissue
    # ========================================================================
    {
        "id": "fixture_14_dental_softtissue",
        "narrative": (
            "Plaintiff was assaulted at defendant's bar. Lost three teeth, suffered "
            "mandibular fracture, and required dental implants for reconstruction. "
            "Cervical sprain documented from defensive movement. TMJ disorder "
            "developed over the following 6 months. Verdict: $185,000."
        ),
        "verdict_amount": 185_000,
        "expected_tags": {
            InjuryTag.DENTAL_INJURY,
            InjuryTag.FRACTURE,  # mandibular fracture
            InjuryTag.SOFT_TISSUE,
        },
        "expected_review_required": False,
        "notes": "Dental injury co-occurs naturally with FRACTURE (mandibular). TMJ is contextual.",
    },

    # ========================================================================
    # Example 15: Death without fatal pathway (REVIEW — LOGICAL_CONTRADICTION)
    # ========================================================================
    {
        "id": "fixture_15_death_no_pathway",
        "narrative": (
            "Decedent died at home several weeks after defendant's negligent "
            "conduct caused her to experience emotional distress from witnessing "
            "the underlying incident. Survivors brought wrongful death claim "
            "alleging stress-induced cardiac arrest as the cause of death. "
            "Defendant disputed causation. Verdict: $500,000."
        ),
        "verdict_amount": 500_000,
        "expected_tags": {
            InjuryTag.DEATH,
            InjuryTag.PSYCHOLOGICAL_INJURY,
        },
        "expected_review_required": True,
        "notes": "Death with no fatal-pathway tag (psychological injury is NOT in FATAL_PATHWAY_TAGS). "
                 "Must trigger LOGICAL_CONTRADICTION for human review of causation chain.",
    },
]


def get_fixture(fixture_id: str) -> dict:
    """Look up a fixture by ID."""
    for fixture in CANONICAL_VERDICTS:
        if fixture["id"] == fixture_id:
            return fixture
    raise KeyError(f"No canonical fixture found with id: {fixture_id}")
