"""
_common/extract.py — Deterministic PI relevance + outcome($)/injury extraction.

Shared across sources (CAP opinions, CourtListener, MoreLaw, news). Deterministic
(regex/keyword) first so results are explainable and reproducible — an LLM layer can
be added later behind the same interface.

INTEGRITY (LOW_BLOCKER_DATA_SOURCES section 6a — zero fabrication):
  * Never invent a value. If a field isn't found in the text, it is None / [].
  * Every extracted amount carries the EXACT source snippet it came from.
  * Ambiguous/weak signals -> abstain (None), never guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# --- Personal-injury / tort relevance ---------------------------------------

PI_TERMS = [
    "personal injury", "negligence", "negligent", "bodily injury", "pain and suffering",
    "premises liability", "products liability", "product liability", "medical malpractice",
    "wrongful death", "motor vehicle", "automobile accident", "car accident", "slip and fall",
    "rear-end", "dog bite", "tort", "plaintiff was injured", "suffered injuries",
    "damages for", "comparative negligence", "duty of care", "proximate cause",
]
# Strong negative signals (helps abstain on non-PI cases)
NON_PI_TERMS = [
    "rule of criminal procedure", "habeas corpus", "death penalty", "post-conviction",
    "disbarment", "bar admission", "in re amendments", "tax assessment", "zoning",
]

INJURY_KEYWORDS = {
    "neck": ["neck", "cervical", "whiplash"],
    "back": ["back", "lumbar", "spine", "spinal", "disc herniation", "herniated disc"],
    "head_brain": ["concussion", "traumatic brain", "tbi", "brain injury", "head injury"],
    "shoulder": ["shoulder", "rotator cuff", "clavicle"],
    "knee": ["knee", "acl", "meniscus", "patella"],
    "fracture": ["fracture", "broken bone", "broken leg", "broken arm"],
    "burn": ["burn", "scarring", "disfigurement"],
    "amputation": ["amputation", "loss of limb"],
    "paralysis": ["paralysis", "quadriplegia", "paraplegia", "spinal cord injury"],
    "fatality": ["wrongful death", "decedent", "fatal injuries", "died as a result"],
    "psychological": ["ptsd", "emotional distress", "post-traumatic"],
    "soft_tissue": ["soft tissue", "sprain", "strain", "contusion"],
}

CASE_TYPE_MAP = {
    "motor_vehicle_accident": ["motor vehicle", "automobile accident", "car accident", "rear-end", "collision"],
    "premises_liability": ["slip and fall", "premises liability", "trip and fall"],
    "medical_malpractice": ["medical malpractice", "standard of care", "misdiagnosis"],
    "product_liability": ["product liability", "products liability", "defective product"],
    "wrongful_death": ["wrongful death"],
    "dog_bite": ["dog bite", "animal attack"],
    "workplace_accident": ["workplace", "workers' compensation", "industrial accident"],
}

# --- Money extraction --------------------------------------------------------

# $1,250,000 | $1.25 million | $750K | 1.5 million dollars
_MONEY_RE = re.compile(
    r"""
    (?:\$\s*)?
    (\d{1,3}(?:,\d{3})+(?:\.\d+)?      # 1,250,000(.00)
     |\d+(?:\.\d+)?)                    # or 1.25 / 750
    \s*
    (million|billion|thousand|m|k|b)?   # optional scale word
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)
_SCALE = {"thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6, "billion": 1e9, "b": 1e9}
_AWARD_CONTEXT = re.compile(
    r"(awarded|award|verdict|judgment|judgement|damages|settle(?:d|ment)?|recover(?:ed|y)?|"
    r"compensat\w+|jury found|in favor of)", re.IGNORECASE)


@dataclass
class MoneyHit:
    value: float
    raw: str
    snippet: str
    kind: str  # verdict | settlement | award | damages | unspecified


@dataclass
class Extraction:
    is_pi: bool
    pi_score: int
    pi_terms: list[str] = field(default_factory=list)
    case_type: Optional[str] = None
    injuries: list[str] = field(default_factory=list)
    outcome_type: Optional[str] = None
    amount: Optional[float] = None
    amount_snippet: Optional[str] = None
    money_hits: list[dict] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        return d


def _snippet(text: str, start: int, end: int, pad: int = 80) -> str:
    return re.sub(r"\s+", " ", text[max(0, start - pad): end + pad]).strip()


def find_amounts(text: str) -> list[MoneyHit]:
    if not text:
        return []
    hits: list[MoneyHit] = []
    for m in _MONEY_RE.finditer(text):
        num_str, scale = m.group(1), (m.group(2) or "").lower()
        # Skip bare small numbers with no $ and no scale (avoid page numbers, years).
        has_dollar = text[max(0, m.start() - 1): m.start() + 1].strip().startswith("$") or "$" in m.group(0)
        if not has_dollar and not scale:
            continue
        try:
            val = float(num_str.replace(",", ""))
        except ValueError:
            continue
        if scale in _SCALE:
            val *= _SCALE[scale]
        # Plausibility window for PI outcomes ($1k – $1B). Reject implausible.
        if val < 1000 or val > 1_000_000_000:
            continue
        snip = _snippet(text, m.start(), m.end())
        ctx = _AWARD_CONTEXT.search(snip)
        kind = "unspecified"
        low = snip.lower()
        if "settle" in low:
            kind = "settlement"
        elif "verdict" in low or "jury found" in low:
            kind = "verdict"
        elif "award" in low:
            kind = "award"
        elif "damages" in low or "judgment" in low or "judgement" in low:
            kind = "damages"
        if ctx or kind != "unspecified":
            hits.append(MoneyHit(value=val, raw=m.group(0).strip(), snippet=snip, kind=kind))
    return hits


def _matches(text_low: str, terms: list[str]) -> list[str]:
    return [t for t in terms if t in text_low]


def classify_case_type(text_low: str) -> Optional[str]:
    for ctype, terms in CASE_TYPE_MAP.items():
        if any(t in text_low for t in terms):
            return ctype
    return None


def extract_injuries(text_low: str) -> list[str]:
    found = []
    for tag, kws in INJURY_KEYWORDS.items():
        if any(kw in text_low for kw in kws):
            found.append(tag)
    return found


def extract(text: str) -> Extraction:
    """Main entry point. Returns an Extraction; abstains (None/[]) when unsure."""
    if not text:
        return Extraction(is_pi=False, pi_score=0)
    low = text.lower()

    pi_terms = _matches(low, PI_TERMS)
    non_pi = _matches(low, NON_PI_TERMS)
    pi_score = len(pi_terms) - 2 * len(non_pi)
    is_pi = pi_score >= 2  # require a couple of real PI signals

    injuries = extract_injuries(low) if is_pi else []
    case_type = classify_case_type(low) if is_pi else None

    money = find_amounts(text) if is_pi else []
    # Choose the outcome amount: prefer verdict > settlement > award > damages, then largest.
    best: Optional[MoneyHit] = None
    if money:
        priority = {"verdict": 3, "settlement": 3, "award": 2, "damages": 1, "unspecified": 0}
        best = sorted(money, key=lambda h: (priority.get(h.kind, 0), h.value), reverse=True)[0]

    # Confidence: combine PI strength, presence of injuries, and a contextual amount.
    conf = 0.0
    if is_pi:
        conf = min(1.0, 0.3 + 0.1 * len(pi_terms))
        if injuries:
            conf = min(1.0, conf + 0.15)
        if best and best.kind in ("verdict", "settlement", "award"):
            conf = min(1.0, conf + 0.25)

    return Extraction(
        is_pi=is_pi,
        pi_score=pi_score,
        pi_terms=pi_terms,
        case_type=case_type,
        injuries=injuries,
        outcome_type=(best.kind if best else None),
        amount=(best.value if best else None),
        amount_snippet=(best.snippet if best else None),
        money_hits=[h.__dict__ for h in money],
        confidence=round(conf, 2),
    )
