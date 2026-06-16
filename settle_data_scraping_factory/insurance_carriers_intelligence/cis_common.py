"""
cis_common.py — Shared adapter infrastructure for the insurance_carriers_intelligence module.

Thin bridge between:
  - The insurance-carrier scraping skill at scripts/scraping-factory/insurance-carrier/
  - The SETTLE carrier intelligence database

Provides:
  - CarrierSourceDoc: canonical carrier intelligence record format
  - write_facts_jsonl / read_facts_jsonl: standardized I/O for carrier fact pipelines
  - Carrier fact type → source registry
  - Dynamic module loading for per-source scraping modules
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Iterable

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True, filename=".env.local"))

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_CARRIER_SKILL_DIR = os.path.normpath(
    os.path.join(_THIS_DIR, "..", "..", "..", "scripts", "scraping-factory", "insurance-carrier")
)

CARRIER_FACT_TO_SOURCE_TYPE: dict[str, str] = {
    "naic_complaint_index": "regulator_filing",
    "sec_filing": "sec_filing",
    "sec_loss_reserve": "sec_filing",
    "fl_oir_report": "regulator_filing",
    "bad_faith_opinion_count": "court_opinion",
    "carrier_crosscheck": "metadata_record",
}

CARRIER_FACT_TO_VALIDATION_ROLE: dict[str, str] = {
    "naic_complaint_index": "state_regulator_snapshot",
    "sec_filing": "carrier_financial_disclosure",
    "sec_loss_reserve": "carrier_reserves_evidence",
    "fl_oir_report": "state_regulator_snapshot",
    "bad_faith_opinion_count": "carrier_litigation_signal",
    "carrier_crosscheck": "identity_reconciliation",
}


@dataclass
class CarrierSourceDoc:
    kind: str
    entity_id: str
    entity_name: str
    value_text: str
    observed_at: str
    source_url: str
    source_dataset: str
    source_sha256: str
    fetch_timestamp: str
    cache_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CarrierFact = Any


def import_carrier_skill(name: str):
    if _CARRIER_SKILL_DIR not in sys.path:
        sys.path.insert(0, _CARRIER_SKILL_DIR)
    try:
        return __import__(name)
    except ImportError:
        return None


def carrier_fact_to_source_doc(fact: CarrierFact, fallback_publication_name: str | None = None) -> CarrierSourceDoc:
    entity_id = fact.get("entity_id", "")
    entity_name = fact.get("entity_name", fallback_publication_name or "")

    return CarrierSourceDoc(
        kind=fact.get("kind", "metadata_record"),
        entity_id=str(entity_id),
        entity_name=str(entity_name),
        value_text=json.dumps(fact, default=str),
        observed_at=fact.get("observed_at", datetime.utcnow().isoformat()),
        source_url=fact.get("source_url", ""),
        source_dataset=fact.get("source_dataset", ""),
        source_sha256=hashlib.sha256(json.dumps(fact, sort_keys=True, default=str).encode()).hexdigest(),
        fetch_timestamp=datetime.utcnow().isoformat(),
        cache_status=fact.get("cache_status", "miss"),
    )


def write_facts_jsonl(facts: Iterable[Any], out_path: str) -> int:
    count = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for f_item in facts:
            if isinstance(f_item, CarrierSourceDoc):
                doc = f_item.to_dict()
            elif isinstance(f_item, dict):
                doc = carrier_fact_to_source_doc(f_item).to_dict()
            else:
                doc = {"raw": str(f_item)}
            f.write(json.dumps(doc, default=str) + "\n")
            count += 1
    return count


def read_facts_jsonl(path: str) -> list[dict[str, Any]]:
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def storage_bucket() -> str:
    return os.getenv("SETTLE_CARRIER_GCS_BUCKET", "settle-carrier-data")


def db_connection_url() -> str | None:
    return os.getenv("SETTLE_DATABASE_URL") or os.getenv("DATABASE_URL")


if __name__ == "__main__":
    skills = {
        "naic_complaints": import_carrier_skill("naic_complaints"),
        "sec_edgar_filings": import_carrier_skill("sec_edgar_filings"),
        "sec_edgar_reserves": import_carrier_skill("sec_edgar_reserves"),
        "fl_oir_filings": import_carrier_skill("fl_oir_filings"),
        "courtlistener_bad_faith": import_carrier_skill("courtlistener_bad_faith"),
        "carrier_crosscheck": import_carrier_skill("carrier_crosscheck"),
        "carrier_profile": import_carrier_skill("carrier_profile"),
    }

    print("carrier-skill modules loaded from:", _CARRIER_SKILL_DIR)
    for name, skill in skills.items():
        print(f"  .{name:30s}: {'OK' if skill else 'NOT FOUND'}")
    print(f"  storage_bucket()        : {storage_bucket()}")
    print(f"  db_connection_url() set?: {'Yes' if db_connection_url() else 'No'}")
