"""
Verdict News Enrichment Scraper
Enriches existing verdict records with data from news articles via Exa AI Search API.
Extracts medical specials, lost wages, verdict/settlement amounts, and other fields
from news coverage of jury verdicts.

Data source: Exa AI Search API (exa.ai)
Env vars required: EXA_API_KEY

Usage:
    python cds_enrich_via_news.py --input verdicts.csv --output verdicts_enriched.csv
"""

import csv
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional, Tuple, List, Dict

EXA_API_URL = "https://api.exa.ai/search"
PER_REQUEST_DELAY = 0.4
INPUT_CSV = "verdicts_fl_sample.csv"
OUTPUT_CSV = "verdicts_fl_news_enriched.csv"
LOG_CSV = "enrichment_attempt_log.csv"
ATTEMPT_LOG = "news_enrichment_attempt_log.csv"

ALL_SETTLE_FIELDS = [
    "jurisdiction", "court_level", "case_type", "injury_category",
    "injury_severity", "medical_specials", "lost_wages", "verdict_amount",
    "settlement_amount", "comparative_negligence_pct", "trial_duration_days",
    "plaintiff_age_range", "defendant_category", "insurance_carrier",
    "expert_witnesses_plaintiff", "expert_witnesses_defense",
]

FL_COUNTIES = [
    "Alachua", "Baker", "Bay", "Bradford", "Brevard", "Broward",
    "Calhoun", "Charlotte", "Citrus", "Clay", "Collier", "Columbia",
    "DeSoto", "Dixie", "Duval", "Escambia", "Flagler", "Franklin",
    "Gadsden", "Gilchrist", "Glades", "Gulf", "Hamilton", "Hardee",
    "Hendry", "Hernando", "Highlands", "Hillsborough", "Holmes",
    "Indian River", "Jackson", "Jefferson", "Lafayette", "Lake",
    "Lee", "Leon", "Levy", "Liberty", "Madison", "Manatee", "Marion",
    "Martin", "Miami-Dade", "Monroe", "Nassau", "Okaloosa", "Okeechobee",
    "Orange", "Osceola", "Palm Beach", "Pasco", "Pinellas", "Polk",
    "Putnam", "St. Johns", "St. Lucie", "Santa Rosa", "Sarasota",
    "Seminole", "Sumter", "Suwannee", "Taylor", "Union", "Volusia",
    "Wakulla", "Walton", "Washington",
]


def parse_dollars(s: str) -> Optional[float]:
    """Convert '$141.5 million' -> 141500000"""
    if not s:
        return None
    s = s.replace("$", "").replace(",", "").strip()
    match = re.search(r"([\d.]+)\s*(million|billion|M|B)?", s, re.IGNORECASE)
    if not match:
        return None
    try:
        val = float(match.group(1))
        unit = (match.group(2) or "").lower()
        if unit in ("billion", "b"):
            val *= 1_000_000_000
        elif unit in ("million", "m"):
            val *= 1_000_000
        return val
    except ValueError:
        return None


def build_query(row: Dict[str, str]) -> str:
    """Build an Exa search query for a Verdix row."""
    parts = []
    if row.get("case_name"):
        parts.append(row["case_name"])
    if row.get("jurisdiction"):
        parts.append(row["jurisdiction"])
    parts.extend(["jury verdict", "settlement", "damages awarded"])
    return " ".join(parts)


def call_exa(query: str, num_results: int = 5, timeout: int = 30) -> Tuple[List[Dict], Optional[str]]:
    """Call Exa Search API. Returns (results, error_str)."""
    api_key = os.getenv("EXA_API_KEY", "")
    if not api_key:
        return [], "EXA_API_KEY not set"

    payload = json.dumps({
        "query": query,
        "numResults": num_results,
        "useAutoprompt": True,
        "type": "neural",
    }).encode("utf-8")

    req = urllib.request.Request(
        EXA_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return data.get("results", []), None
    except Exception as e:
        return [], str(e)


def extract_fields(
    results: List[Dict],
    expected_amount: Optional[float] = None,
    year: Optional[int] = None,
) -> Dict[str, Optional[str]]:
    """Aggregate top-N result summaries + highlights, regex-extract fields."""
    fields: Dict[str, Optional[str]] = {}

    all_text = ""
    for r in results:
        all_text += (r.get("text", "") or "") + " "
        for h in r.get("highlights", []) or []:
            all_text += h + " "

    amt_match = re.search(r"\$[\d,.]+(?:\s*(?:million|billion|M|B))?", all_text, re.IGNORECASE)
    if amt_match:
        fields["verdict_amount"] = str(parse_dollars(amt_match.group()))

    med_match = re.search(r"(?:medical|hospital)\s*(?:bills?|expenses?|specials?|costs?)[:\s]*\$?[\d,.]+", all_text, re.IGNORECASE)
    if med_match:
        fields["medical_specials"] = med_match.group()

    wage_match = re.search(r"(?:lost|lost\s+past)\s*(?:wages?|earnings?|income)[:\s]*\$?[\d,.]+", all_text, re.IGNORECASE)
    if wage_match:
        fields["lost_wages"] = wage_match.group()

    carrier_match = re.search(r"(?:insured\s+by|insurance\s+carrier|coverage\s+by)\s+([A-Z][A-Za-z\s&.]+?)(?:\.|,|\s+$)", all_text)
    if carrier_match:
        fields["insurance_carrier"] = carrier_match.group(1).strip()

    age_match = re.search(r"(?:plaintiff|claimant|decedent)[^.]*?(?:age[d\s]*|was\s+)(\d{1,3})", all_text, re.IGNORECASE)
    if age_match:
        fields["plaintiff_age_range"] = age_match.group(1)

    return fields


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Enrich verdicts with news data via Exa AI")
    parser.add_argument("--input", "-i", default=INPUT_CSV, help="Input CSV with verdict records")
    parser.add_argument("--output", "-o", default=OUTPUT_CSV, help="Output enriched CSV")
    parser.add_argument("--limit", type=int, default=50, help="Max records to process")
    parser.add_argument("--delay", type=float, default=PER_REQUEST_DELAY, help="Delay between API calls")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)[:args.limit]
        fieldnames = reader.fieldnames or []

    enriched_fieldnames = list(dict.fromkeys(fieldnames + ALL_SETTLE_FIELDS))
    enriched_rows = []

    for i, row in enumerate(rows):
        query = build_query(row)
        print(f"[{i + 1}/{len(rows)}] {query[:100]}...")

        results, error = call_exa(query)
        if error:
            print(f"  Error: {error}")
        else:
            extracted = extract_fields(results)
            row.update({k: v for k, v in extracted.items() if v})
            print(f"  Extracted: {list(extracted.keys())}")

        enriched_rows.append(row)
        time.sleep(args.delay)

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=enriched_fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(enriched_rows)

    print(f"Done. {len(enriched_rows)} rows written to {args.output}")


if __name__ == "__main__":
    main()
