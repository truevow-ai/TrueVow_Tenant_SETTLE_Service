"""Deterministic rule library for injury classification.

v1.0.0 — DO NOT modify keyword sets without bumping CLASSIFIER_VERSION per
the semver discipline in version.py.

Architecture:
    Each InjuryTag has a TagRule with:
    - strong_patterns: regex patterns that, if matched, GUARANTEE the tag
      with confidence ≥0.95 (single match) or 0.99 (multiple matches)
    - contextual_patterns: weaker signals; need 2+ matches for 0.70+ confidence
    - exclusion_patterns: regex that DISQUALIFIES the tag (negation handling)
    - co_occurrence_required: if this tag is applied, one of these MUST also be present
    - co_occurrence_forbidden: if this tag is applied, NONE of these may be present
    - notes: human-readable rationale for the rule design

Confidence schedule (deterministic, no probabilistic interpretation):
    2+ strong matches            → 0.99 (rule_engine_explicit)
    1 strong match               → 0.95 (rule_engine_explicit)
    3+ contextual matches        → 0.80 (rule_engine_contextual)
    2 contextual matches         → 0.70 (rule_engine_contextual)
    1 contextual match           → 0.60 (rule_engine_weak — requires human review)
    Any exclusion match          → 0.00 (disqualified)
    Zero matches                 → 0.00 (no tag emitted)

All regex patterns use re.IGNORECASE. Patterns use word boundaries (\\b) where
appropriate to avoid false positives on partial matches.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Pattern

from .schema import InjuryTag


# ============================================================================
# RULE DATA STRUCTURE
# ============================================================================

@dataclass(frozen=True)
class TagRule:
    """Complete rule definition for a single injury tag."""

    tag: InjuryTag
    strong_patterns: tuple[Pattern[str], ...]
    contextual_patterns: tuple[Pattern[str], ...]
    exclusion_patterns: tuple[Pattern[str], ...] = ()
    co_occurrence_required: frozenset[InjuryTag] = field(default_factory=frozenset)
    co_occurrence_forbidden: frozenset[InjuryTag] = field(default_factory=frozenset)
    notes: str = ""


def _re(pattern: str) -> Pattern[str]:
    """Helper to compile case-insensitive regex with multiline support."""
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE)


# ============================================================================
# TAG RULES (17 closed-set tags)
# ============================================================================

SOFT_TISSUE_RULE = TagRule(
    tag=InjuryTag.SOFT_TISSUE,
    strong_patterns=(
        _re(r"\b(whiplash|whiplash[\s\-]?associated[\s\-]?disorder|WAD)\b"),
        _re(r"\b(cervical|lumbar|thoracic)\s+(sprain|strain)\b"),
        _re(r"\b(rotator\s+cuff)\s+(tear|tendinitis|impingement|injury)\b"),
        _re(r"\bsoft\s+tissue\s+(injury|injuries|damage|trauma)\b"),
        _re(r"\b(muscle|ligament|tendon)\s+(tear|rupture|sprain|strain)\b"),
        _re(r"\bcontusion(s)?\b"),
        _re(r"\b(meniscus|labral|labrum)\s+tear\b"),
        _re(r"\bhematoma\b(?!\s+(?:subdural|epidural|intracranial))"),  # exclude brain hematoma
    ),
    contextual_patterns=(
        _re(r"\b(bruising|bruised|bruise)\b"),
        _re(r"\bstiffness\b"),  # standalone — "complained of stiffness" is a valid soft-tissue signal
        _re(r"\b(stiff|range[\s\-]of[\s\-]motion)\s+(limit|reduced|loss)"),  # compound forms
        _re(r"\bphysical\s+therapy\b"),
        _re(r"\b(soreness|sore|aches?)\b"),
        _re(r"\bmuscle\s+spasm(s)?\b"),
    ),
    exclusion_patterns=(
        _re(r"\b(no|denied|without|free\s+of|ruled\s+out)\s+(?:any\s+|all\s+|further\s+)?(soft\s+tissue|whiplash|sprain)"),
    ),
    notes="Strong patterns include explicit medical terms. Contextual patterns are physical-therapy adjacent. Negation handled via exclusion. WAD is the formal acronym used in plaintiff briefs. v1.0.1: exclusion now allows optional 'any/all/further' between negation verb and target ('Denied any soft tissue' now correctly disqualifies).",
)


FRACTURE_RULE = TagRule(
    tag=InjuryTag.FRACTURE,
    strong_patterns=(
        _re(r"\bfracture(s|d)?\b"),
        _re(r"\bbroken\s+(bone|leg|arm|hip|wrist|ankle|rib|jaw|nose|finger|toe|clavicle|collarbone|pelvis|femur|tibia|fibula|humerus|radius|ulna|vertebra)\b"),
        _re(r"\bcomminuted\b"),
        _re(r"\b(hairline|displaced|compound|greenstick|stress|spiral|transverse|oblique)\s+fracture\b"),
        _re(r"\b(open|closed)\s+fracture\b"),
        _re(r"\bfractured\s+(skull|rib|pelvis|hip|spine|vertebra|femur|tibia|fibula)\b"),
        _re(r"\b(total|partial)\s+(hip|knee|shoulder)\s+(replacement|arthroplasty)\b"),  # implies fracture
    ),
    contextual_patterns=(
        _re(r"\b(cast|casted|splint|immobilization|orthopedic\s+surgery)\b"),
        _re(r"\bbone\s+(graft|healing|density)\b"),
        _re(r"\b(callus\s+formation|mal[\s\-]?union|non[\s\-]?union)\b"),
        _re(r"\b(ORIF|open\s+reduction)\b"),  # surgical fixation of fracture
    ),
    exclusion_patterns=(
        _re(r"\b(no|ruled\s+out|denied)\s+fractures?\b"),
        _re(r"\bfractures?\s+(ruled\s+out|excluded|negative)\b"),
    ),
    notes="Strong patterns cover anatomical fractures explicitly. ORIF (Open Reduction Internal Fixation) is the surgical-fixation acronym — implies fracture occurred. Joint replacements (hip/knee/shoulder) typically follow fractures. Exclusion handles both 'no fracture' (singular) and 'no fractures' (plural).",
)


TRAUMATIC_BRAIN_INJURY_RULE = TagRule(
    tag=InjuryTag.TRAUMATIC_BRAIN_INJURY,
    strong_patterns=(
        _re(r"\b(TBI|MTBI|traumatic\s+brain\s+injury|mild\s+traumatic\s+brain\s+injury)\b"),
        _re(r"\bconcussion(s|al)?\b"),
        _re(r"\bpost[\s\-]?concussive\s+(syndrome|symptoms|disorder)\b"),
        _re(r"\b(subdural|epidural|intracranial|subarachnoid)\s+(hemorrhage|hematoma|bleed)\b"),
        _re(r"\bdiffuse\s+axonal\s+injury\b"),
        _re(r"\b(brain|cerebral)\s+(damage|injury|trauma|contusion)\b"),
        _re(r"\bskull\s+fracture\b"),  # typically implies brain injury
        _re(r"\bGlasgow\s+Coma\s+Scale\b"),  # diagnostic of TBI severity
    ),
    contextual_patterns=(
        _re(r"\b(cognitive|memory)\s+(impairment|deficit|loss|problems|issues)\b"),
        _re(r"\b(persistent|chronic|post[\s\-]?traumatic)\s+(headache|migraine)\b"),
        _re(r"\b(dizziness|vertigo)\s+(post[\s\-]?trauma|persistent|chronic)\b"),
        _re(r"\b(loss\s+of\s+consciousness|LOC|unconscious)\b"),
    ),
    exclusion_patterns=(
        _re(r"\b(no|ruled\s+out|negative\s+for|denied)\s+(TBI|concussion|brain\s+injury)"),
        _re(r"\b(TBI|concussion|brain\s+injury)\s+(ruled\s+out|excluded|negative)\b"),
    ),
    notes="GCS reference indicates clinical TBI assessment. Loss of consciousness is diagnostic. Hematoma patterns scoped to brain anatomy here (general hematoma is excluded from SOFT_TISSUE rule to avoid double-count).",
)


SPINAL_INJURY_RULE = TagRule(
    tag=InjuryTag.SPINAL_INJURY,
    strong_patterns=(
        _re(r"\bherniated\s+disc(s)?\b"),
        _re(r"\bdisc\s+(herniation|bulge|protrusion|extrusion)\b"),
        _re(r"\b(lumbar|cervical|thoracic)\s+(fusion|discectomy|laminectomy)\b"),
        _re(r"\bspinal\s+(cord|stenosis|fusion)\b"),
        _re(r"\bvertebra(l|e)?\s+(fracture|injury|compression)\b"),
        _re(r"\b[LCT][1-9]\d?[\s\-][LCT][1-9]\d?\b"),  # e.g., L4-L5, C5-C6
        _re(r"\b(cauda\s+equina|compression\s+fracture)\b"),
    ),
    contextual_patterns=(
        _re(r"\b(radiating|radicular)\s+pain\b"),
        _re(r"\bsciatica\b"),
        _re(r"\bnerve\s+(impingement|root\s+compression)\b"),
        _re(r"\bback\s+surgery\b"),
        _re(r"\b(foraminal|spinal)\s+stenosis\b"),
    ),
    exclusion_patterns=(
        _re(r"\b(no|ruled\s+out|denied)\s+(disc\s+herniation|spinal\s+injury)\b"),
    ),
    notes="Vertebral level notation (L4-L5, C5-C6, T8-T9) is a strong signal — used universally in MRI reports and surgical records. Cauda equina syndrome is a specific spinal emergency.",
)


PARALYSIS_RULE = TagRule(
    tag=InjuryTag.PARALYSIS,
    strong_patterns=(
        _re(r"\bparapleg(ia|ic)\b"),
        _re(r"\b(quadr|tetra)pleg(ia|ic)\b"),
        _re(r"\bhemipleg(ia|ic)\b"),
        _re(r"\bparalyz(ed|is)\b"),
        _re(r"\bparalysis\b"),
        _re(r"\bcomplete\s+(motor|sensory)\s+loss\b"),
    ),
    contextual_patterns=(
        _re(r"\bwheelchair[\s\-](dependent|bound|required)\b"),
        _re(r"\b(loss\s+of\s+motor|motor\s+function\s+loss)\b"),
        _re(r"\bASIA\s+(A|B|C|D)\b"),  # American Spinal Injury Association impairment scale
    ),
    co_occurrence_required=frozenset({InjuryTag.SPINAL_INJURY}),
    notes="Paralysis typically (but not exclusively) results from spinal cord injury. Co-occurrence required: if PARALYSIS is tagged, SPINAL_INJURY should also be present. ASIA scale is the clinical paralysis classification.",
)


INTERNAL_ORGAN_INJURY_RULE = TagRule(
    tag=InjuryTag.INTERNAL_ORGAN_INJURY,
    strong_patterns=(
        _re(r"\bperforated\s+(bowel|intestine|colon|stomach|small\s+bowel)\b"),
        _re(r"\b(splenectomy|ruptured\s+spleen|spleen\s+removal)\b"),
        _re(r"\b(kidney|renal)\s+(damage|injury|laceration|trauma|failure)\b"),
        _re(r"\b(liver|hepatic)\s+(laceration|damage|injury|trauma|rupture)\b"),
        _re(r"\b(collapsed\s+lung|pneumothorax|hemothorax)\b"),
        _re(r"\borgan\s+(damage|injury|trauma|failure)\b"),
        _re(r"\b(exploratory\s+laparotomy|abdominal\s+surgery\s+for\s+trauma)\b"),
        _re(r"\b(bowel|intestinal)\s+(resection|rupture)\b"),
        _re(r"\binternal\s+bleeding\s+requiring\s+surgery\b"),
    ),
    contextual_patterns=(
        _re(r"\binternal\s+(injury|injuries|bleeding|trauma)\b"),
        _re(r"\b(hemorrhage|hemorrhagic)\s+(shock|abdominal)\b"),
        _re(r"\b(intra[\s\-]?abdominal|retroperitoneal)\s+(bleed|hemorrhage)\b"),
    ),
    exclusion_patterns=(
        _re(r"\b(no|ruled\s+out|denied)\s+(internal\s+injury|organ\s+damage)"),
    ),
    notes="Internal organ injury is typically associated with high-energy trauma (MVA, fall from height). Exploratory laparotomy and emergency surgery are strong indicators.",
)


AMPUTATION_RULE = TagRule(
    tag=InjuryTag.AMPUTATION,
    strong_patterns=(
        _re(r"\bamputat(ion|ed)\b"),
        _re(r"\btraumatic\s+(limb\s+loss|dismemberment)\b"),
        _re(r"\b(above|below)[\s\-]?(knee|elbow)\s+amputation\b"),
        _re(r"\b(transfemoral|transtibial|transhumeral|transradial)\s+amputation\b"),
        _re(r"\b(prosthet(ic|ics))\s+(limb|leg|arm|foot|hand)\b"),
        _re(r"\b(digit|finger|toe)\s+(amputation|loss)\b"),
    ),
    contextual_patterns=(
        _re(r"\bprosthet(ic|ics)\b"),
        _re(r"\b(partial|complete)\s+limb\s+loss\b"),
        _re(r"\bphantom\s+(limb|pain)\b"),  # almost exclusively in amputees
    ),
    notes="Amputation is highly specific in language. Phantom pain is a near-exclusive amputee phenomenon. Prosthetic mentions without 'limb/leg/arm' are weaker (could be dental).",
)


BURNS_RULE = TagRule(
    tag=InjuryTag.BURNS,
    strong_patterns=(
        _re(r"\b(first|second|third|fourth)[\s\-]?degree\s+burn(s)?\b"),
        _re(r"\b\d+%\s+(of\s+)?(body|TBSA|total\s+body\s+surface\s+area)\s+burn(s|ed)?\b"),
        _re(r"\b(thermal|chemical|electrical|scald(ing)?)\s+burn(s)?\b"),
        _re(r"\bburn(s|ed)\s+(over|on)\s+(face|chest|arms|legs|back|hands|feet|body)\b"),
        _re(r"\b(skin\s+graft|debridement)\b"),
        _re(r"\b(eschar|escharotomy)\b"),
        _re(r"\b(inhalation\s+injury|smoke\s+inhalation)\b"),  # often accompanies burns
    ),
    contextual_patterns=(
        _re(r"\bblistering\b"),
        _re(r"\b(erythema|redness)\s+from\s+burn\b"),
        _re(r"\bburn\s+(unit|center|ICU)\b"),
        _re(r"\bcontracture(s)?\b"),  # post-burn scarring
    ),
    exclusion_patterns=(
        _re(r"\b(rope\s+burn|freezer\s+burn|carpet\s+burn)\b"),  # not the burns we mean
        _re(r"\b(no|ruled\s+out|denied)\s+burn(s)?\b"),
    ),
    notes="TBSA (Total Body Surface Area) percentage is a clinical burn-severity indicator. Burn unit/center admission is highly specific. Excludes friction-type 'burns' (rope, carpet, freezer).",
)


SCARRING_DISFIGUREMENT_RULE = TagRule(
    tag=InjuryTag.SCARRING_DISFIGUREMENT,
    strong_patterns=(
        _re(r"\bpermanent\s+scar(ring|s)?\b"),
        _re(r"\bdisfigure(ment|d|ing)\b"),
        _re(r"\b(keloid|hypertrophic)\s+scar(ring|s)?\b"),
        _re(r"\b(facial|visible)\s+(scar|scarring|disfigurement)\b"),
        _re(r"\bcosmetic\s+(deformity|impairment)\b"),
        _re(r"\bdegloving\s+injury\b"),
        _re(r"\b(reconstruction|reconstructive)\s+(surgery|procedure)\b"),
    ),
    contextual_patterns=(
        _re(r"\b(scar|scarring)\b"),
        _re(r"\b(visible|noticeable)\s+(damage|injury)\b"),
        _re(r"\bcosmetic\s+(surgery|repair)\b"),
        _re(r"\bskin\s+graft\b"),  # also a burns signal — co-occurrence is fine
    ),
    notes="Strong patterns require 'permanent' or anatomical specificity. Cosmetic surgery without trauma context is weak. Skin graft co-occurs naturally with BURNS.",
)


VISION_LOSS_RULE = TagRule(
    tag=InjuryTag.VISION_LOSS,
    strong_patterns=(
        _re(r"\b(total|complete|permanent)\s+blindness\b"),
        _re(r"\bblind(ness)?\s+in\s+(one|left|right|both)\s+eye(s)?\b"),
        _re(r"\b(vision|sight)\s+loss\b"),
        _re(r"\b(retinal\s+detachment|optic\s+nerve\s+damage)\b"),
        _re(r"\bocular\s+(trauma|injury|damage)\b"),
        _re(r"\b(enucleation|eye\s+removal)\b"),  # surgical eye removal
        _re(r"\b(corneal\s+abrasion|hyphema|globe\s+rupture)\b"),
    ),
    contextual_patterns=(
        _re(r"\b(visual\s+impairment|reduced\s+visual\s+acuity)\b"),
        _re(r"\b(diplopia|double\s+vision)\s+(persistent|chronic)\b"),
        _re(r"\bvisual\s+field\s+(defect|loss|reduction)\b"),
    ),
    notes="Eye injuries are highly specific in legal pleadings. Globe rupture and enucleation are catastrophic; corneal injuries are common but require persistence for legal damages.",
)


HEARING_LOSS_RULE = TagRule(
    tag=InjuryTag.HEARING_LOSS,
    strong_patterns=(
        _re(r"\b(deaf(ness)?|hearing\s+loss)\b"),
        _re(r"\b(permanent|partial|total)\s+hearing\s+(loss|impairment)\b"),
        _re(r"\b(sensorineural|conductive|mixed)\s+hearing\s+loss\b"),
        _re(r"\bcochlear\s+(damage|implant)\b"),
        _re(r"\b(ruptured|perforated)\s+(eardrum|tympanic\s+membrane)\b"),
    ),
    contextual_patterns=(
        _re(r"\b(tinnitus)\s+(chronic|persistent|permanent)\b"),
        _re(r"\bhearing\s+aid(s)?\s+required\b"),
        _re(r"\b(auditory\s+damage|vestibular\s+damage)\b"),
    ),
    notes="Tinnitus alone is weak — must be persistent/chronic to qualify as compensable. Cochlear implant signals severe hearing loss.",
)


NERVE_DAMAGE_RULE = TagRule(
    tag=InjuryTag.NERVE_DAMAGE,
    strong_patterns=(
        _re(r"\bnerve\s+(damage|injury|impingement|severance)\b"),
        _re(r"\b(RSD|CRPS|complex\s+regional\s+pain\s+syndrome|reflex\s+sympathetic\s+dystrophy)\b"),
        _re(r"\bperipheral\s+neuropathy\b"),
        _re(r"\b(brachial\s+plexus|sciatic\s+nerve|ulnar\s+nerve|radial\s+nerve|median\s+nerve)\s+(injury|damage|palsy)\b"),
        _re(r"\b(Erb's\s+palsy|Klumpke's\s+palsy)\b"),
    ),
    contextual_patterns=(
        _re(r"\b(tingling|numbness|paresthesia)\s+(persistent|chronic|permanent)\b"),
        _re(r"\bneuropath(y|ic)\b"),
        _re(r"\b(loss\s+of\s+sensation|sensory\s+loss)\b"),
    ),
    notes="RSD/CRPS is a specific chronic-pain nerve disorder. Erb's and Klumpke's are brachial plexus injuries common in birth trauma. Tingling/numbness alone needs persistence to count.",
)


PSYCHOLOGICAL_INJURY_RULE = TagRule(
    tag=InjuryTag.PSYCHOLOGICAL_INJURY,
    strong_patterns=(
        _re(r"\b(PTSD|post[\s\-]?traumatic\s+stress\s+disorder)\b"),
        _re(r"\b(severe|major|clinical)\s+depression\b"),
        _re(r"\b(generalized\s+anxiety\s+disorder|GAD|panic\s+disorder)\b"),
        _re(r"\badjustment\s+disorder\b"),
        _re(r"\bdiagnosed\s+with\s+(PTSD|depression|anxiety)\b"),
        _re(r"\b(psychiatric|psychological)\s+(treatment|diagnosis|hospitalization)\b"),
    ),
    contextual_patterns=(
        _re(r"\b(emotional\s+distress|mental\s+anguish)\b"),
        _re(r"\b(antidepressant|SSRI|anxiolytic)\s+(prescribed|treatment)\b"),
        _re(r"\b(therapist|counselor|psychiatrist)\s+(referral|treatment)\b"),
        _re(r"\bsleep\s+disturbance(s)?\b"),
    ),
    exclusion_patterns=(
        _re(r"\b(no|denied|ruled\s+out)\s+(PTSD|psychological\s+symptoms|psychiatric)"),
    ),
    notes="Strong patterns require formal diagnosis or DSM-coded disorders. Emotional distress and mental anguish are common-law pleading language — contextual only, must accompany clinical signals.",
)


CHRONIC_PAIN_RULE = TagRule(
    tag=InjuryTag.CHRONIC_PAIN,
    strong_patterns=(
        _re(r"\bchronic\s+(?:[a-z]+\s+)?pain\b"),  # "chronic pain", "chronic neck pain", "chronic back pain"
        _re(r"\bchronic\s+pain\s+(syndrome|disorder)\b"),
        _re(r"\b(fibromyalgia)\s+(post[\s\-]?trauma|trauma[\s\-]?induced)\b"),
        _re(r"\b(persistent|intractable|refractory)\s+pain\b"),
        _re(r"\bpain\s+(lasting|persisting|continuing)\s+(?:more\s+than\s+)?\d+\s+(months?|years?)\b"),
        _re(r"\b(?:pain\s+)?lasting\s+(?:more\s+than\s+)?(?:1[2-9]|[2-9]\d|\d{3,})\s+months?\b"),  # explicit ≥12 months
        _re(r"\b(?:pain\s+)?lasting\s+\d+\s+years?\b"),  # any years count as chronic
    ),
    contextual_patterns=(
        _re(r"\b(pain\s+management|chronic\s+pain\s+clinic)\s+(referral|treatment)\b"),
        _re(r"\blong[\s\-]?term\s+(opioid|narcotic|analgesic)\s+(prescription|use)\b"),
        _re(r"\bnerve\s+block\s+(injection|treatment)\b"),
        _re(r"\b(spinal\s+cord\s+stimulator|intrathecal\s+pump)\b"),
    ),
    notes="Chronic pain requires duration evidence OR explicit chronic/persistent language. Allows 'chronic [body part] pain' form (e.g., 'chronic neck pain'). Duration patterns: ≥12 months explicit, or any year-count.",
)


REPRODUCTIVE_INJURY_RULE = TagRule(
    tag=InjuryTag.REPRODUCTIVE_INJURY,
    strong_patterns=(
        _re(r"\breproductive\s+(organ|system)\s+(damage|injury|trauma)\b"),
        _re(r"\b(sterility|infertility)\s+(traumatic|post[\s\-]?trauma|caused\s+by)\b"),
        _re(r"\btraumatic\s+(miscarriage|stillbirth)\b"),
        _re(r"\b(emergency\s+)?hysterectomy\b"),
        _re(r"\b(testicular|ovarian|uterine)\s+(rupture|trauma|injury|damage)\b"),
        _re(r"\bsexual\s+dysfunction\s+(post[\s\-]?trauma|caused\s+by|following)\b"),
    ),
    contextual_patterns=(
        _re(r"\bfertility\s+(impact|loss)\b"),
        _re(r"\bgynecological\s+(surgery|trauma)\b"),
    ),
    notes="Highly sensitive category. Strong patterns require explicit causation language linking to trauma. Sexual dysfunction must be tied to the incident.",
)


DENTAL_INJURY_RULE = TagRule(
    tag=InjuryTag.DENTAL_INJURY,
    strong_patterns=(
        _re(r"\b(tooth|teeth)\s+(loss|knocked\s+out|avulsion|fracture|chipped|broken)\b"),
        _re(r"\blost\s+(?:\w+\s+){0,2}(tooth|teeth)\b"),  # "lost teeth", "lost three teeth"
        _re(r"\bdental\s+(trauma|injury|surgery|implants?)(?:\s+(required|needed))?\b"),
        _re(r"\b(fractured|broken)\s+(tooth|teeth|jaw|mandible|maxilla)\b"),
        _re(r"\b(mandibular|maxillary)\s+fracture\b"),
        _re(r"\bdental\s+implant(s)?(?:\s+(required|placement))?\b"),
        _re(r"\brequired\s+dental\s+implant(s)?\b"),  # "required dental implants"
    ),
    contextual_patterns=(
        _re(r"\bTMJ\s+(disorder|dysfunction)\b"),
        _re(r"\b(jaw\s+surgery|maxillofacial\s+surgery)\b"),
        _re(r"\b(crown|bridge|denture)\s+(required|needed|placement)\b"),
    ),
    notes="Dental injuries are often understated in legal pleadings. Mandibular/maxillary fractures are also FRACTURE-tagged (co-occurrence is fine). TMJ disorder often persists post-trauma. v1.0.1: handles 'lost teeth' form and decoupled 'required/needed' from 'dental implants' (was mandatory trailing space, now optional whole group).",
)


DEATH_RULE = TagRule(
    tag=InjuryTag.DEATH,
    strong_patterns=(
        _re(r"\bwrongful\s+death\b"),
        _re(r"\b(plaintiff|decedent|victim)\s+died\b"),
        _re(r"\b(decedent|deceased)\b"),
        _re(r"\bsurvivors\s+(awarded|received|granted)\b"),
        _re(r"\b(fatal\s+injury|fatality|killed\s+in)\b"),
        _re(r"\bestate\s+of\s+(?:the\s+)?(plaintiff|decedent|deceased)\b"),
        _re(r"\b(passed\s+away|succumbed\s+to\s+injuries)\b"),
    ),
    contextual_patterns=(
        _re(r"\b(end[\s\-]of[\s\-]life|terminal\s+injury)\b"),
        _re(r"\b(coroner|autopsy|medical\s+examiner)\b"),
    ),
    exclusion_patterns=(
        _re(r"\b(near[\s\-]death|almost\s+died|nearly\s+died|brush\s+with\s+death)\b"),
        _re(r"\bdied\s+(later|years\s+later)\s+from\s+(unrelated|other)\s+causes\b"),
    ),
    co_occurrence_forbidden=frozenset({InjuryTag.UNCLASSIFIED}),
    notes="Death triggers wrongful-death legal pathway. Strong patterns are highly specific. Near-death and unrelated-later-death are excluded. Co-occurrence with non-fatal-mechanism injuries alone triggers LOGICAL_CONTRADICTION review.",
)


UNCLASSIFIED_RULE = TagRule(
    tag=InjuryTag.UNCLASSIFIED,
    strong_patterns=(),  # Never auto-applied
    contextual_patterns=(),
    notes="Reserved tag for narratives that match zero rules. Only applied via human review after queue triage.",
)


# ============================================================================
# RULE REGISTRY (canonical lookup)
# ============================================================================

TAG_RULES: dict[InjuryTag, TagRule] = {
    InjuryTag.SOFT_TISSUE: SOFT_TISSUE_RULE,
    InjuryTag.FRACTURE: FRACTURE_RULE,
    InjuryTag.TRAUMATIC_BRAIN_INJURY: TRAUMATIC_BRAIN_INJURY_RULE,
    InjuryTag.SPINAL_INJURY: SPINAL_INJURY_RULE,
    InjuryTag.PARALYSIS: PARALYSIS_RULE,
    InjuryTag.INTERNAL_ORGAN_INJURY: INTERNAL_ORGAN_INJURY_RULE,
    InjuryTag.AMPUTATION: AMPUTATION_RULE,
    InjuryTag.BURNS: BURNS_RULE,
    InjuryTag.SCARRING_DISFIGUREMENT: SCARRING_DISFIGUREMENT_RULE,
    InjuryTag.VISION_LOSS: VISION_LOSS_RULE,
    InjuryTag.HEARING_LOSS: HEARING_LOSS_RULE,
    InjuryTag.NERVE_DAMAGE: NERVE_DAMAGE_RULE,
    InjuryTag.PSYCHOLOGICAL_INJURY: PSYCHOLOGICAL_INJURY_RULE,
    InjuryTag.CHRONIC_PAIN: CHRONIC_PAIN_RULE,
    InjuryTag.REPRODUCTIVE_INJURY: REPRODUCTIVE_INJURY_RULE,
    InjuryTag.DENTAL_INJURY: DENTAL_INJURY_RULE,
    InjuryTag.DEATH: DEATH_RULE,
    InjuryTag.UNCLASSIFIED: UNCLASSIFIED_RULE,
}


# ============================================================================
# FATAL PATHWAY TAGS (for LOGICAL_CONTRADICTION trigger)
# ============================================================================
# Death without one of these as a co-occurring tag is suspicious — death
# usually has a proximate cause that maps to an injury we can classify.

FATAL_PATHWAY_TAGS: frozenset[InjuryTag] = frozenset({
    InjuryTag.INTERNAL_ORGAN_INJURY,
    InjuryTag.TRAUMATIC_BRAIN_INJURY,
    InjuryTag.BURNS,
    InjuryTag.AMPUTATION,
    InjuryTag.SPINAL_INJURY,  # high cervical SCI can be fatal
})


# ============================================================================
# SEVERE INJURY TAGS (for VERDICT_AMOUNT_MISMATCH trigger)
# ============================================================================
# Severe injuries with sub-$50k verdicts are mathematically suspicious and
# warrant human review (likely wrong tagging or unusual case posture).

SEVERE_INJURY_TAGS: frozenset[InjuryTag] = frozenset({
    InjuryTag.AMPUTATION,
    InjuryTag.PARALYSIS,
    InjuryTag.TRAUMATIC_BRAIN_INJURY,
    InjuryTag.DEATH,
    InjuryTag.VISION_LOSS,  # if total/permanent
    InjuryTag.REPRODUCTIVE_INJURY,
})
