"""
_common/enrich.py — Deep deterministic enrichment from opinion text.

Extracts fields that the base extract() skips: judge names, itemized damages
(economic / non-economic / punitive / medical), plaintiff age, trial duration,
expert witness counts, defendant categorisation, insurance carrier mentions,
and approximate dates.

Uses only regex + keyword matching — no LLM, fully deterministic and auditable.
Every extracted dollar amount carries its source snippet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from _common.extract import _snippet

_MONTHS = (
    r"January|February|March|April|May|June|July|August|"
    r"September|October|November|December"
)

# --- Judge name extraction -------------------------------------------------

_JUDGE_RE = re.compile(
    r"^([A-Z]{2,}(?:\s+[A-Z]{2,})*),?\s*(J\.|C?J\.|P?J\.|acting P\.J\.)",
    re.MULTILINE,
)

_JUDGE_TEXT_RE = re.compile(
    r"(?:[Jj]ustice|[Jj]udge|Honou?rable|Hon\.|[Mm]agistrate [Jj]udge|"
    r"[Cc]hief [Jj]ustice|"
    r"delivered by|opinion by|authored by)\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+(?:\s+(?:Jr|Sr|III|II|IV)\.?)?)+)",
)


_JUDGE_SITTING_RE = re.compile(
    r"Before:?\s*(?:the\s+)?(?:[Cc]ourt\s+)?(?:consists?\s+of\s+)?(?:Justices?|Judges?)?\s*"
    r"([A-Z, .'Jand]+(?:\s*[A-Z, .'Jand]+)*)",
)

def _parse_panel(raw: str) -> list[str]:
    """Parse 'SMITH, J., JONES, J., and BROWN, J.' -> ['SMITH, J.', 'JONES, J.', 'BROWN, J.']"""
    names: list[str] = []
    for name in re.findall(r"[A-Z]{2,}(?:,\s*J\.?)?", raw):
        name = name.strip()
        if name and name.lower() not in ("before", "justices", "judges"):
            names.append(name)
    return names

# --- Damages breakdown -------------------------------------------------------

_MEDICAL_BILLS_RE = re.compile(
    r"(?:past\s+)?medical\s+(?:bills?|expenses?|specials?|costs?)\s*"
    r"(?:of|in\s+the\s+amount\s+of|totalling|totaling|totalled|total|were|was)\s*"
    r"\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

_MEDICAL_FUTURE_RE = re.compile(
    r"future\s+medical\s+(?:bills?|expenses?|specials?|costs?|care)\s*"
    r"(?:of|in\s+the\s+amount\s+of|totalling|totaling)\s*"
    r"\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

_ECONOMIC_RE = re.compile(
    r"(?<!non[\s-])(?:past\s+)?(?:total\s+)?economic\s+damages?\s*(?:of|in\s+the\s+amount\s+of|awarded\s+at|:\s*)?\s*"
    r"\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

_SPECIAL_DAMAGES_RE = re.compile(
    r"special\s+damages?\s*(?:of|in\s+the\s+amount\s+of|totalling)?\s*"
    r"\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

_LOST_WAGES_RE = re.compile(
    r"(?:lost|lost\s+past|past\s+lost)\s*(?:wages?|earnings?|income)\s*"
    r"(?:of|in\s+the\s+amount\s+of|were|was|totalling|totaling|totalled)?\s*"
    r"\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

_LOST_FUTURE_WAGES_RE = re.compile(
    r"(?:lost\s+)?future\s+(?:wages?|earnings?|income|earning\s+capacity)\s*"
    r"(?:of|in\s+the\s+amount\s+of)?\s*"
    r"\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

_NONECONOMIC_RE = re.compile(
    r"non[\s-]economic\s+damages?\s*"
    r"(?:of|in\s+the\s+amount\s+of|awarded\s+at)?\s*"
    r"\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

_GENERAL_DAMAGES_RE = re.compile(
    r"general\s+damages?\s*(?:of|in\s+the\s+amount\s+of)?\s*"
    r"\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

_PAIN_SUFFERING_RE = re.compile(
    r"pain\s+and\s+suffering\s*(?:damages)?\s*"
    r"(?:of|in\s+the\s+amount\s+of|awarded\s+at)?\s*"
    r"\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

_PUNITIVE_RE = re.compile(
    r"punitive\s+damages?\s*(?:of|in\s+the\s+amount\s+of|awarded\s+at)?\s*"
    r"\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

_EXEMPLARY_RE = re.compile(
    r"exemplary\s+damages?\s*(?:of|in\s+the\s+amount\s+of)?\s*"
    r"\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

# --- Plaintiff age ----------------------------------------------------------

_PLAINTIFF_AGE_RE = re.compile(
    r"(?:plaintiff|claimant|decedent|victim)\s*(?:,\s*)?(?:was|is)?\s*"
    r"(?:aged?\s+)?(\d{1,3})(?:\s*(?:[\-]\s*|\s+)years?\s+old)?\s*[,\s]",
    re.IGNORECASE,
)

_AGE_YEARS_OLD_RE = re.compile(
    r"(\d{1,3})[\s-]year[\s-]old",
    re.IGNORECASE,
)

_AGE_OF_RE = re.compile(
    r"at\s+the\s+age\s+of\s+(\d{1,3})", re.IGNORECASE,
)

# --- Trial duration ---------------------------------------------------------

_TRIAL_DURATION_RE = re.compile(
    r"(\d+)[\s-]day\s+(?:trial|hearing|proceeding|jury\s+trial)",
    re.IGNORECASE,
)

_TRIAL_LASTED_RE = re.compile(
    r"trial\s+(?:lasted|lasting|that\s+lasted)\s+(\d+)\s+days?",
    re.IGNORECASE,
)

# --- Expert witnesses -------------------------------------------------------

_EXPERT_RE = re.compile(
    r"expert\s+(?:witness|testimony|opinion)",
    re.IGNORECASE,
)

_EXPERT_PLAINTIFF_RE = re.compile(
    r"(?:plaintiff|appellee|claimant|petitioner)(?:'s|\s+(?:called|retained|presented|offered))\s+"
    r"(?:an?\s+)?expert\s+(?:witness|testimony)",
    re.IGNORECASE,
)

_EXPERT_DEFENSE_RE = re.compile(
    r"(?:defendant|appellant|respondent)(?:'s|\s+(?:called|retained|presented|offered))\s+"
    r"(?:an?\s+)?expert\s+(?:witness|testimony)",
    re.IGNORECASE,
)

# --- Insurance carrier ------------------------------------------------------

# Major US auto/PI/liability carriers (and common trade names). Matched
# case-insensitively but the value is normalised back to canonical form.
_KNOWN_CARRIERS = {
    "state farm": "State Farm",
    "geico": "GEICO",
    "progressive": "Progressive",
    "allstate": "Allstate",
    "usaa": "USAA",
    "liberty mutual": "Liberty Mutual",
    "nationwide": "Nationwide",
    "farmers": "Farmers Insurance",
    "travelers": "Travelers",
    "american family": "American Family Insurance",
    "erie insurance": "Erie Insurance",
    "auto-owners": "Auto-Owners Insurance",
    "auto owners": "Auto-Owners Insurance",
    "the hartford": "The Hartford",
    "hartford": "The Hartford",
    "chubb": "Chubb",
    "metlife": "MetLife",
    "mercury insurance": "Mercury Insurance",
    "esurance": "Esurance",
    "national general": "National General",
    "safeco": "Safeco",
    "kemper": "Kemper",
    "the general": "The General",
    "root insurance": "Root Insurance",
    "amica": "Amica Mutual",
    "csaa": "CSAA Insurance",
    "aaa insurance": "AAA Insurance",
    "berkshire hathaway": "Berkshire Hathaway",
    "zurich": "Zurich",
    "aig": "AIG",
    "cna": "CNA",
    "sentry insurance": "Sentry Insurance",
    "westfield insurance": "Westfield Insurance",
    "cincinnati insurance": "Cincinnati Insurance",
}

# Carrier keys that are ordinary English words or place names ("the general
# rule", "travelers on the road", "nationwide practice", "Hartford,
# Connecticut", "progressive disease"). They only count as a carrier when an
# insurance indicator appears nearby, otherwise opinion prose produces
# hundreds of false positives.
_AMBIGUOUS_CARRIERS = {
    "progressive", "nationwide", "travelers", "farmers", "the general",
    "hartford", "the hartford", "chubb", "kemper", "zurich", "aig", "cna",
    "amica", "root insurance",
}

_KNOWN_CARRIERS_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(_KNOWN_CARRIERS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Insurance-context indicator used to gate ambiguous carrier matches.
_INSURANCE_CONTEXT_RE = re.compile(
    r"insur|carrier|policy|polic|coverage|underwrit|indemnit|casualty|"
    r"insured|assurance|reinsur|no-fault|no fault|uninsured|underinsured|"
    r"liability\s+(?:insurer|carrier|coverage)",
    re.IGNORECASE,
)
_CONTEXT_WINDOW = 60


def _carrier_in_context(text: str, start: int, end: int) -> bool:
    """True if an insurance indicator sits within the window around a match."""
    lo = max(0, start - _CONTEXT_WINDOW)
    hi = min(len(text), end + _CONTEXT_WINDOW)
    return bool(_INSURANCE_CONTEXT_RE.search(text[lo:hi]))


def _find_known_carrier(text: str) -> Optional[str]:
    """Return a canonical known carrier, gating ambiguous names on context."""
    for m in _KNOWN_CARRIERS_RE.finditer(text):
        key = m.group(1).lower()
        if key in _AMBIGUOUS_CARRIERS and not _carrier_in_context(text, m.start(), m.end()):
            continue
        return _KNOWN_CARRIERS[key]
    return None

# Contextual pattern: an introductory phrase followed by a *properly
# capitalised* company name that ends in an insurance-style suffix. The
# captured group is case-SENSITIVE (no IGNORECASE) so lowercase sentence
# fragments like "insured by the appellee" never match.
_INSURANCE_RE = re.compile(
    r"(?:[Ii]nsured\s+by|[Ii]nsurance\s+(?:carrier|company|provider)|"
    r"[Cc]overage\s+(?:through|by|from)|[Pp]olicy\s+(?:issued|written)\s+by|"
    r"[Ll]iability\s+(?:insurer|carrier))\s+"
    r"((?:[A-Z][A-Za-z&.'-]+\s+){0,4}"
    r"(?:Insurance|Ins\.|Indemnity|Casualty|Assurance|Mutual|Underwriters|"
    r"Group|Company|Co\.))\b",
)

_CARRIER_STOPWORDS = {"the", "a", "an", "and", "of", "his", "her", "its", "their"}


def extract_carrier(text: str) -> Optional[str]:
    """Return a validated insurance-carrier name, or None.

    Prefers an exact known-carrier match; otherwise falls back to a strict
    contextual proper-noun-with-suffix pattern. Rejects sentence fragments.
    """
    if not text:
        return None
    known = _find_known_carrier(text)
    if known:
        return known
    m = _INSURANCE_RE.search(text)
    if not m:
        return None
    candidate = m.group(1).strip().rstrip(".,;")
    words = candidate.split()
    if len(candidate) < 3 or candidate.lower() in _CARRIER_STOPWORDS:
        return None
    # First token must be a real proper noun (capitalised, not a stopword).
    if words and (words[0].lower() in _CARRIER_STOPWORDS or not words[0][:1].isupper()):
        words = words[1:]
    if not words:
        return None
    return " ".join(words)


def _extract_carrier_with_snippet(text: str) -> tuple[Optional[str], Optional[str]]:
    """Return (carrier, source_snippet). The snippet is the verbatim context in
    which the carrier was found, so the value is verifiable word-by-word."""
    if not text:
        return None, None
    for m in _KNOWN_CARRIERS_RE.finditer(text):
        key = m.group(1).lower()
        if key in _AMBIGUOUS_CARRIERS and not _carrier_in_context(text, m.start(), m.end()):
            continue
        return _KNOWN_CARRIERS[key], _snippet(text, m.start(), m.end())
    m = _INSURANCE_RE.search(text)
    if not m:
        return None, None
    candidate = m.group(1).strip().rstrip(".,;")
    words = candidate.split()
    if len(candidate) < 3 or candidate.lower() in _CARRIER_STOPWORDS:
        return None, None
    if words and (words[0].lower() in _CARRIER_STOPWORDS or not words[0][:1].isupper()):
        words = words[1:]
    if not words:
        return None, None
    return " ".join(words), _snippet(text, m.start(), m.end())


# Suffixes that make a standalone value credible as a company name.
_CARRIER_SUFFIX_RE = re.compile(
    r"\b(?:Insurance|Ins\.?|Indemnity|Casualty|Assurance|Mutual|Underwriters|"
    r"Assur\.?|Surety|Fire|Life|Group|Company|Co\.?|Corp\.?|Inc\.?|LLC|Ltd\.?)\b"
)


def is_valid_carrier(value: Optional[str]) -> bool:
    """Validate an already-extracted carrier value (not free text).

    Accepts a known carrier or a short, mostly-capitalised name carrying an
    insurance-style suffix. Rejects sentence fragments produced by the old
    greedy/IGNORECASE extractor.
    """
    if not value or not isinstance(value, str):
        return False
    v = value.strip()
    if len(v) < 3 or v.lower() in _CARRIER_STOPWORDS:
        return False
    if _KNOWN_CARRIERS_RE.search(v):
        return True
    words = v.split()
    # Too long to be a company name -> almost certainly a captured sentence.
    if len(words) > 6:
        return False
    lower_words = sum(1 for w in words if w[:1].islower())
    if lower_words > 1:
        return False
    return bool(_CARRIER_SUFFIX_RE.search(v))


def clean_carrier(value: Optional[str]) -> Optional[str]:
    """Normalise a valid carrier value (canonicalise known names), else None."""
    if not value or not isinstance(value, str):
        return None
    v = value.strip().rstrip(".,;")
    # Strip leading stopwords ("and Chicago Insurance Co" -> "Chicago Insurance Co").
    words = v.split()
    while words and words[0].lower() in _CARRIER_STOPWORDS:
        words = words[1:]
    v = " ".join(words)
    if not is_valid_carrier(v):
        return None
    km = _KNOWN_CARRIERS_RE.search(v)
    if km:
        return _KNOWN_CARRIERS[km.group(1).lower()]
    return v

# --- Defendant category -----------------------------------------------------

_DEFENDANT_CATEGORY_MAP = {
    "healthcare": [
        r"\bhospital\b", r"\bmedical\s+center\b", r"\bclinic\b",
        r"\bphysician\b", r"\bdoctor\b", r"\bsurgeon\b", r"\bnurse\b",
        r"\bnursing\s+home\b", r"\bassisted\s+living\b",
    ],
    "insurance_company": [
        r"\binsurance\s+company\b", r"\binsurer\b", r"\binsurance\s+carrier\b",
        r"\blife\s+insurance\b", r"\bauto\s+insurance\b", r"\bhealth\s+insurance\b",
    ],
    "corporation": [
        r"\bcorporation\b", r"\binc\.?\b", r"\bllc\b", r"\bcorp\.?\b",
        r"\bcompany\b", r"\benterprise\b", r"\bltd\.?\b",
    ],
    "manufacturer": [
        r"\bmanufacturer\b", r"\bmanufacturing\b", r"\bproduct\s+liability\b",
        r"\bdefective\s+product\b",
    ],
    "government": [
        r"\bcity\s+of\b", r"\bcounty\s+of\b", r"\bstate\s+of\b",
        r"\bmunicipality\b", r"\bgovernment\b", r"\bpublic\s+entity\b",
        r"\bschool\s+district\b", r"\bpolice\s+department\b",
    ],
    "individual": [
        r"\bdefendant\s+(?:driver|operator|owner|individual)\b",
        r"\bnegligent\s+driver\b",
    ],
    "landlord": [
        r"\blandlord\b", r"\bproperty\s+owner\b", r"\bproperty\s+management\b",
    ],
    "employer": [
        r"\bemployer\b", r"\bemployment\b", r"\bworkers.?\s+compensation\b",
    ],
}

# --- Dates ------------------------------------------------------------------

_DATE_RE = re.compile(
    rf"({_MONTHS})\s+(\d{{1,2}}),?\s+(\d{{4}})", re.IGNORECASE,
)

_FILED_DATE_CTX = re.compile(
    rf"(?:filed|commenced|initiated|brought|original\s+complaint|complaint\s+filed)"
    rf"\s+(?:on\s+)?(?:or\s+about\s+)?({_MONTHS})\s+(\d{{1,2}}),?\s+(\d{{4}})",
    re.IGNORECASE,
)

_VERDICT_DATE_CTX = re.compile(
    rf"(?:verdict|judg?ment|award)\s+(?:was\s+)?(?:entered|rendered|reached|returned|filed)"
    rf"\s+(?:on\s+)?(?:or\s+about\s+)?({_MONTHS})\s+(\d{{1,2}}),?\s+(\d{{4}})",
    re.IGNORECASE,
)

_VERDICT_RETURNED_RE = re.compile(
    rf"(?:returned|reached|delivered)\s+(?:its|a|the)\s+verdict\s+(?:on\s+)?(?:or\s+about\s+)?"
    rf"({_MONTHS})\s+(\d{{1,2}}),?\s+(\d{{4}})",
    re.IGNORECASE,
)

# --- Comparative negligence -------------------------------------------------

_COMP_NEG_RE = re.compile(
    r"(?:found|apportioned|allocated)\s+(?:to\s+be\s+)?(\d{1,3})\s*(?:%|percent)\s*"
    r"(?:at\s+fault|negligent|liable|responsible|comparative)",
    re.IGNORECASE,
)

_COMP_NEG_PLAINTIFF_RE = re.compile(
    r"(?:plaintiff|claimant)(?:'s|was\s+found|was|is|found)\s+"
    r"(?:to\s+be\s+)?(\d{1,3})\s*(?:%|percent)\s*(?:at\s+fault|negligent|responsible)",
    re.IGNORECASE,
)

# --- Liability determination -----------------------------------------------

_LIABILITY_CLEAR_RE = re.compile(
    r"(?:clear|undisputed|admitted|stipulated)\s+liability", re.IGNORECASE,
)

_LIABILITY_DISPUTED_RE = re.compile(
    r"(?:disputed|contested|denied)\s+liability", re.IGNORECASE,
)

# --- Policy limits ----------------------------------------------------------

_POLICY_LIMIT_RE = re.compile(
    r"policy\s+(?:limit|limits?)\s*(?:of|was|were|is|are)\s*\$?([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)


def _parse_amount(num_str: str) -> Optional[float]:
    try:
        return float(num_str.replace(",", ""))
    except ValueError:
        return None


def _best_amount(text: str, pattern: re.Pattern) -> tuple[Optional[float], Optional[str]]:
    """Find the best (largest plausible) amount matching pattern."""
    best_val = None
    best_snippet = None
    for m in pattern.finditer(text):
        val = _parse_amount(m.group(1))
        if val is None:
            continue
        if val < 100 or val > 1_000_000_000:
            continue
        snippet = _snippet(text, m.start(), m.end())
        if best_val is None or val > best_val:
            best_val = val
            best_snippet = snippet
    return best_val, best_snippet


@dataclass
class EnrichedFields:
    judge_name: Optional[str] = None
    judge_name_snippet: Optional[str] = None
    panel: list[str] = field(default_factory=list)
    medical_bills: Optional[float] = None
    medical_bills_snippet: Optional[str] = None
    future_medical: Optional[float] = None
    future_medical_snippet: Optional[str] = None
    economic_damages: Optional[float] = None
    economic_damages_snippet: Optional[str] = None
    non_economic_damages: Optional[float] = None
    non_economic_damages_snippet: Optional[str] = None
    punitive_damages: Optional[float] = None
    punitive_damages_snippet: Optional[str] = None
    lost_wages: Optional[float] = None
    lost_wages_snippet: Optional[str] = None
    plaintiff_age_range: Optional[str] = None
    plaintiff_age_range_snippet: Optional[str] = None
    trial_duration_days: Optional[int] = None
    trial_duration_days_snippet: Optional[str] = None
    expert_witnesses_plaintiff: Optional[int] = None
    expert_witnesses_plaintiff_snippet: Optional[str] = None
    expert_witnesses_defense: Optional[int] = None
    expert_witnesses_defense_snippet: Optional[str] = None
    total_expert_witnesses: Optional[int] = None
    defendant_category: Optional[str] = None
    defendant_category_snippet: Optional[str] = None
    defendant_industry: Optional[str] = None
    insurance_carrier: Optional[str] = None
    insurance_carrier_snippet: Optional[str] = None
    policy_limit_indicator: Optional[str] = None
    policy_limit_indicator_snippet: Optional[str] = None
    verdict_date: Optional[str] = None
    verdict_date_snippet: Optional[str] = None
    filing_date: Optional[str] = None
    filing_date_snippet: Optional[str] = None
    comparative_negligence_pct: Optional[float] = None
    comparative_negligence_pct_snippet: Optional[str] = None
    liability_tier: Optional[str] = None
    liability_tier_snippet: Optional[str] = None

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if v is not None and v != []:
                d[k] = v
        return d


def enrich(text: str, case_type: Optional[str] = None) -> EnrichedFields:
    if not text:
        return EnrichedFields()

    ef = EnrichedFields()

    m = _JUDGE_RE.search(text)
    if m:
        ef.judge_name = f"{m.group(1).strip()} {m.group(2)}"
        ef.judge_name_snippet = _snippet(text, m.start(), m.end())

    if ef.judge_name is None:
        m = _JUDGE_TEXT_RE.search(text)
        if m:
            ef.judge_name = m.group(1).strip()
            ef.judge_name_snippet = _snippet(text, m.start(), m.end())

    panel_m = _JUDGE_SITTING_RE.search(text[:600])
    if panel_m:
        ef.panel = _parse_panel(panel_m.group(1))

    med_val, med_snip = _best_amount(text, _MEDICAL_BILLS_RE)
    if med_val:
        ef.medical_bills = med_val
        ef.medical_bills_snippet = med_snip

    fut_val, fut_snip = _best_amount(text, _MEDICAL_FUTURE_RE)
    if fut_val:
        ef.future_medical = fut_val
        ef.future_medical_snippet = fut_snip

    econ_val, econ_snip = _best_amount(text, _ECONOMIC_RE)
    if econ_val is None:
        econ_val, econ_snip = _best_amount(text, _SPECIAL_DAMAGES_RE)
    if econ_val:
        ef.economic_damages = econ_val
        ef.economic_damages_snippet = econ_snip

    lw_val, lw_snip = _best_amount(text, _LOST_WAGES_RE)
    if lw_val is None:
        lw_val, lw_snip = _best_amount(text, _LOST_FUTURE_WAGES_RE)
    if lw_val:
        ef.lost_wages = lw_val
        ef.lost_wages_snippet = lw_snip

    ne_val, ne_snip = _best_amount(text, _NONECONOMIC_RE)
    if ne_val is None:
        ne_val, ne_snip = _best_amount(text, _GENERAL_DAMAGES_RE)
    if ne_val is None:
        ne_val, ne_snip = _best_amount(text, _PAIN_SUFFERING_RE)
    if ne_val:
        ef.non_economic_damages = ne_val
        ef.non_economic_damages_snippet = ne_snip

    pun_val, pun_snip = _best_amount(text, _PUNITIVE_RE)
    if pun_val is None:
        pun_val, pun_snip = _best_amount(text, _EXEMPLARY_RE)
    if pun_val:
        ef.punitive_damages = pun_val
        ef.punitive_damages_snippet = pun_snip

    age_m = _PLAINTIFF_AGE_RE.search(text)
    if age_m is None:
        age_m = _AGE_YEARS_OLD_RE.search(text)
    if age_m is None:
        age_m = _AGE_OF_RE.search(text)
    if age_m:
        age = int(age_m.group(1))
        if 0 < age < 120:
            if age < 18:
                ef.plaintiff_age_range = "0_17"
            elif age < 30:
                ef.plaintiff_age_range = "18_29"
            elif age < 45:
                ef.plaintiff_age_range = "30_44"
            elif age < 60:
                ef.plaintiff_age_range = "45_59"
            elif age < 75:
                ef.plaintiff_age_range = "60_74"
            else:
                ef.plaintiff_age_range = "75_plus"
            ef.plaintiff_age_range_snippet = _snippet(text, age_m.start(), age_m.end())

    td_m = _TRIAL_DURATION_RE.search(text)
    if td_m is None:
        td_m = _TRIAL_LASTED_RE.search(text)
    if td_m:
        days = int(td_m.group(1))
        if 0 < days < 1000:
            ef.trial_duration_days = days
            ef.trial_duration_days_snippet = _snippet(text, td_m.start(), td_m.end())

    # Expert witnesses: report ONLY counts explicitly attributable to a side,
    # each with a source snippet. NEVER guess or split a total (no-fabrication).
    pl_matches = list(_EXPERT_PLAINTIFF_RE.finditer(text))
    df_matches = list(_EXPERT_DEFENSE_RE.finditer(text))
    all_experts = len(_EXPERT_RE.findall(text))
    if all_experts > 0:
        ef.total_expert_witnesses = all_experts
    if pl_matches:
        ef.expert_witnesses_plaintiff = len(pl_matches)
        m0 = pl_matches[0]
        ef.expert_witnesses_plaintiff_snippet = _snippet(text, m0.start(), m0.end())
    if df_matches:
        ef.expert_witnesses_defense = len(df_matches)
        m0 = df_matches[0]
        ef.expert_witnesses_defense_snippet = _snippet(text, m0.start(), m0.end())

    carrier, carrier_snip = _extract_carrier_with_snippet(text)
    if carrier:
        ef.insurance_carrier = carrier
        ef.insurance_carrier_snippet = carrier_snip

    text_low = text.lower()
    for category, patterns in _DEFENDANT_CATEGORY_MAP.items():
        cat_match = None
        for p in patterns:
            cat_match = re.search(p, text_low)
            if cat_match:
                break
        if cat_match:
            if ef.defendant_category is None:
                ef.defendant_category = category
                ef.defendant_category_snippet = _snippet(text, cat_match.start(), cat_match.end())
            else:
                if case_type and category == "manufacturer" and case_type == "product_liability":
                    ef.defendant_category = category
                    ef.defendant_category_snippet = _snippet(text, cat_match.start(), cat_match.end())
                    ef.defendant_industry = "manufacturing"
                elif case_type and category == "insurance_company" and case_type in ("motor_vehicle_accident", "wrongful_death"):
                    ef.defendant_category = category
                    ef.defendant_category_snippet = _snippet(text, cat_match.start(), cat_match.end())
                    ef.defendant_industry = "insurance"
                elif category not in ("individual", "corporation"):
                    ef.defendant_category = category
                    ef.defendant_category_snippet = _snippet(text, cat_match.start(), cat_match.end())
                    ef.defendant_industry = category

    if ef.defendant_industry is None and ef.defendant_category:
        cat_to_ind = {
            "healthcare": "healthcare",
            "insurance_company": "insurance",
            "manufacturer": "manufacturing",
            "landlord": "real_estate",
            "employer": "employment",
            "government": "government",
        }
        ef.defendant_industry = cat_to_ind.get(ef.defendant_category)

    pol_m = _POLICY_LIMIT_RE.search(text)
    if pol_m:
        ef.policy_limit_indicator = f"mentioned: {pol_m.group(0)[:80]}"
        ef.policy_limit_indicator_snippet = _snippet(text, pol_m.start(), pol_m.end())

    filed_m = _FILED_DATE_CTX.search(text)
    if filed_m:
        ef.filing_date = f"{filed_m.group(1)} {filed_m.group(2)}, {filed_m.group(3)}"
        ef.filing_date_snippet = _snippet(text, filed_m.start(), filed_m.end())

    verdict_m = _VERDICT_DATE_CTX.search(text)
    if verdict_m is None:
        verdict_m = _VERDICT_RETURNED_RE.search(text)
    if verdict_m:
        ef.verdict_date = f"{verdict_m.group(1)} {verdict_m.group(2)}, {verdict_m.group(3)}"
        ef.verdict_date_snippet = _snippet(text, verdict_m.start(), verdict_m.end())

    cn_m = _COMP_NEG_PLAINTIFF_RE.search(text)
    if cn_m is None:
        cn_m = _COMP_NEG_RE.search(text)
    if cn_m:
        pct = float(cn_m.group(1))
        if 0 <= pct <= 100:
            ef.comparative_negligence_pct = pct
            ef.comparative_negligence_pct_snippet = _snippet(text, cn_m.start(), cn_m.end())

    liab_m = _LIABILITY_CLEAR_RE.search(text)
    if liab_m:
        ef.liability_tier = "clear_liability"
        ef.liability_tier_snippet = _snippet(text, liab_m.start(), liab_m.end())
    else:
        liab_m = _LIABILITY_DISPUTED_RE.search(text)
        if liab_m:
            ef.liability_tier = "disputed_liability"
            ef.liability_tier_snippet = _snippet(text, liab_m.start(), liab_m.end())
        elif cn_m and ef.comparative_negligence_pct is not None:
            # Derived from comparative-negligence %, so its evidence is the
            # comp-neg snippet (transparent about the derivation).
            if ef.comparative_negligence_pct <= 20:
                ef.liability_tier = "likely_liable"
            elif ef.comparative_negligence_pct <= 50:
                ef.liability_tier = "shared_liability"
            else:
                ef.liability_tier = "likely_not_liable"
            ef.liability_tier_snippet = _snippet(text, cn_m.start(), cn_m.end())

    return ef


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    print("Judge extraction:")
    text1 = "WERDEGAR, J.\n\nA person found not guilty..."
    e1 = enrich(text1)
    check("judge from cap-style header", e1.judge_name == "WERDEGAR J.")
    check("panel empty when no sitting line", e1.panel == [])

    text2 = "Justice Ruth Bader Ginsburg delivered the opinion of the Court."
    e2 = enrich(text2)
    check("judge from 'Justice Name' pattern", e2.judge_name == "Ruth Bader Ginsburg")

    text3 = "Before: Justices SMITH, J., JONES, J., and BROWN, J."
    e3 = enrich(text3)
    check("panel extracted from 'Before:' line", len(e3.panel) == 3)

    print("Medical bills:")
    text4 = "The plaintiff incurred medical bills of $245,000 for her treatment."
    e4 = enrich(text4)
    check("medical_bills extracted", e4.medical_bills == 245000.0)

    print("Economic damages:")
    text5 = "The jury awarded economic damages of $1,200,000 and non-economic damages in the amount of $2,500,000."
    e5 = enrich(text5)
    check("economic_damages extracted", e5.economic_damages == 1200000.0)
    check("non_economic_damages extracted", e5.non_economic_damages == 2500000.0)

    print("Punitive damages:")
    text6 = "The court also imposed punitive damages of $5,000,000."
    e6 = enrich(text6)
    check("punitive_damages extracted", e6.punitive_damages == 5000000.0)

    print("Plaintiff age:")
    text7 = "The plaintiff, aged 42 years, suffered permanent injuries."
    e7 = enrich(text7)
    check("plaintiff_age extracted", e7.plaintiff_age_range == "30_44")

    print("Trial duration:")
    text8 = "After a 14-day trial, the jury deliberated for three days."
    e8 = enrich(text8)
    check("trial_duration extracted", e8.trial_duration_days == 14)

    print("Expert witnesses:")
    text9 = "The plaintiff called an expert witness on accident reconstruction. The defense presented expert testimony from a biomechanical engineer."
    e9 = enrich(text9)
    check("expert witnesses detected", e9.total_expert_witnesses is not None and e9.total_expert_witnesses > 0)

    print("Insurance carrier:")
    text10 = "The defendant was insured by State Farm Mutual Automobile Insurance Company."
    e10 = enrich(text10)
    check("insurance_carrier extracted", e10.insurance_carrier is not None and "State Farm" in e10.insurance_carrier)

    print("Defendant category:")
    text11 = "The defendant hospital failed to meet the standard of care."
    e11 = enrich(text11)
    check("defendant_category healthcare", e11.defendant_category == "healthcare")

    print("Dates:")
    text12 = "The complaint was filed on June 15, 2019. The jury returned its verdict on March 3, 2022."
    e12 = enrich(text12)
    check("filing_date extracted", e12.filing_date == "June 15, 2019")
    check("verdict_date extracted", e12.verdict_date == "March 3, 2022")

    print("Comparative negligence:")
    text13 = "The plaintiff was found 15% at fault."
    e13 = enrich(text13)
    check("comparative_negligence extracted", e13.comparative_negligence_pct == 15.0)
    check("liability_tier likely_liable", e13.liability_tier == "likely_liable")

    print("Lost wages:")
    text14 = "The plaintiff claimed lost wages of $85,000."
    e14 = enrich(text14)
    check("lost_wages extracted", e14.lost_wages == 85000.0)

    print("Empty text -> no errors:")
    e0 = enrich("")
    check("empty text returns empty", e0.to_dict() == {})

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(selftest())
