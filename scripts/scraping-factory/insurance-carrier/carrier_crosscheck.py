"""
carrier_crosscheck.py — Cross-reference carrier identities across NAIC, SEC,
and other data sources. Uses token-based name matching (Jaccard) to reconcile
carrier entities across datasets.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Any

from carrier_common import utc_now_iso, sha256_hex

INSURANCE_SIC_BAND = range(6300, 6500)
_STOPWORDS = frozenset({
    "the", "and", "of", "in", "a", "an", "for", "to", "by",
    "inc", "corp", "co", "llc", "ltd", "company", "corporation",
    "insurance", "group", "mutual", "casualty", "property",
    "life", "health", "fire", "marine", "assurance",
})


def _tokenize(name: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class CrossCheckResult:
    crosscheck_id: str
    source_a: str
    source_b: str
    entity_id_a: str
    entity_id_b: str
    entity_name_a: str
    entity_name_b: str
    jaccard_score: float
    confidence: str


def cross_check(
    entities_a: list[dict[str, Any]],
    entities_b: list[dict[str, Any]],
    source_a: str,
    source_b: str,
    min_jaccard: float = 0.3,
    min_confidence: float = 0.6,
) -> list[CrossCheckResult]:
    results: list[CrossCheckResult] = []
    tokens_b = [(_tokenize(e.get("entity_name", "")), e) for e in entities_b]

    for ea in entities_a:
        name_a = ea.get("entity_name", "")
        tokens_a = _tokenize(name_a)
        id_a = ea.get("entity_id", "")

        for tokens_b_set, eb in tokens_b:
            score = _jaccard(tokens_a, tokens_b_set)
            if score >= min_jaccard:
                id_b = eb.get("entity_id", "")
                confidence = "high" if score >= 0.7 else "medium"
                if score < min_confidence:
                    confidence = "low"

                results.append(CrossCheckResult(
                    crosscheck_id=sha256_hex(f"{source_a}:{id_a}|{source_b}:{id_b}")[:16],
                    source_a=source_a,
                    source_b=source_b,
                    entity_id_a=id_a,
                    entity_id_b=id_b,
                    entity_name_a=name_a,
                    entity_name_b=eb.get("entity_name", ""),
                    jaccard_score=round(score, 4),
                    confidence=confidence,
                ))

    return sorted(results, key=lambda r: r.jaccard_score, reverse=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Carrier identity cross-reference")
    ap.add_argument("--input-a", required=True, help="JSONL file for source A")
    ap.add_argument("--input-b", required=True, help="JSONL file for source B")
    ap.add_argument("--label-a", default="naic", help="Label for source A")
    ap.add_argument("--label-b", default="sec", help="Label for source B")
    ap.add_argument("--output", default=None, help="JSONL output path")
    ap.add_argument("--min-jaccard", type=float, default=0.3)
    args = ap.parse_args()

    def read_jsonl(path: str) -> list[dict[str, Any]]:
        rows = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    entities_a = read_jsonl(args.input_a)
    entities_b = read_jsonl(args.input_b)
    results = cross_check(entities_a, entities_b, args.label_a, args.label_b, min_jaccard=args.min_jaccard)

    output = [asdict(r) for r in results]
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            for row in output:
                f.write(json.dumps(row, default=str) + "\n")
        print(f"Wrote {len(output)} cross-matches to {args.output}")
    else:
        print(json.dumps(output, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
