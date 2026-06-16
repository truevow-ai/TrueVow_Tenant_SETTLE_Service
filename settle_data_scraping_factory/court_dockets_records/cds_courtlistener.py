"""
CourtListener Verdict Scraper
Fetches jury verdicts and settlement decisions from CourtListener API (free tier)
and feeds them into the SETTLE internal verdict database via bulk-insert endpoint.

Rate limits: 100 req/hr (anonymous), 500 req/hr (authenticated with API key)

Usage:
    python cds_courtlistener.py --jurisdiction "california" --max-verdicts 50
    python cds_courtlistener.py --search "personal injury settlement" --dry-run
    python cds_courtlistener.py --start-date 2023-01-01 --end-date 2024-12-31

Env vars required:
    COURTLISTENER_API_KEY - CourtListener API token (free at courtlistener.com/help/api/rest/)
    SETTLE_API_URL         - SETTLE service base URL (default: http://localhost:8002)
    SETTLE_ADMIN_API_KEY   - Admin API key for bulk-insert auth
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env.local")
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent / "cds_courtlistener.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

COURTLISTENER_BASE = "https://www.courtlistener.com/api/rest/v4"
SETTLE_API_URL = os.getenv("SETTLE_API_URL", "http://localhost:8002")
SETTLE_ADMIN_KEY = os.getenv("SETTLE_ADMIN_API_KEY", "billing_admin_dev_key_12345")
COURTLISTENER_KEY = os.getenv("COURTLISTENER_API_KEY", "")


INJURY_KEYWORDS = {
    "neck": ["neck", "cervical spine", "whiplash"],
    "back": ["back", "lumbar", "spine", "disc herniation", "spinal"],
    "head": ["head", "concussion", "traumatic brain", "tbi", "brain injury"],
    "shoulder": ["shoulder", "rotator cuff", "clavicle"],
    "knee": ["knee", "acl", "meniscus", "patella"],
    "hip": ["hip", "pelvis", "femur"],
    "wrist_hand": ["wrist", "hand", "finger", "carpal"],
    "ankle_foot": ["ankle", "foot", "toe", "achilles"],
    "multiple": ["multiple injuries", "polytrauma", "catastrophic"],
    "fatality": ["death", "fatal", "wrongful death", "fatality", "decedent"],
    "psychological": ["ptsd", "emotional distress", "psychological", "anxiety", "depression", "pain and suffering"],
    "soft_tissue": ["soft tissue", "sprain", "strain", "contusion", "bruise"],
    "burn": ["burn", "scarring", "disfigurement"],
    "fracture": ["fracture", "broken bone"],
    "amputation": ["amputation", "loss of limb"],
    "paralysis": ["paralysis", "quadriplegia", "paraplegia", "spinal cord"],
    "other": [],
}

CASE_TYPE_MAP = {
    "motor vehicle": "motor_vehicle_accident",
    "car accident": "motor_vehicle_accident",
    "auto accident": "motor_vehicle_accident",
    "slip and fall": "premises_liability",
    "premises liability": "premises_liability",
    "medical malpractice": "medical_malpractice",
    "product liability": "product_liability",
    "workplace": "workplace_accident",
    "wrongful death": "wrongful_death",
    "dog bite": "dog_bite",
    "assault": "assault_battery",
}


def classify_injury_types(text: str) -> List[str]:
    text_lower = text.lower() if text else ""
    matched = []
    for injury_type, keywords in INJURY_KEYWORDS.items():
        if injury_type == "other":
            continue
        if any(kw in text_lower for kw in keywords):
            matched.append(injury_type)
    return matched if matched else ["other"]


def classify_case_type(text: str) -> str:
    text_lower = text.lower() if text else ""
    for keyword, case_type in CASE_TYPE_MAP.items():
        if keyword in text_lower:
            return case_type
    return "personal_injury_general"


def parse_amount(text: str) -> Optional[float]:
    if not text:
        return None
    text = text.replace("$", "").replace(",", "").strip()
    match = re.search(r"[\d.]+", text)
    if match:
        try:
            val = float(match.group())
            if "million" in text.lower() or "M" in text:
                val *= 1_000_000
            return val
        except ValueError:
            return None
    return None


def parse_date(text: str) -> Optional[str]:
    if not text:
        return None
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


class CourtListenerVerdictScraper:
    def __init__(self, max_verdicts: int = 100, dry_run: bool = False):
        self.max_verdicts = max_verdicts
        self.dry_run = dry_run
        self.collected: List[Dict] = []
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Token {COURTLISTENER_KEY}"} if COURTLISTENER_KEY else {},
        )

    async def close(self):
        await self.client.aclose()

    async def search_opinions(
        self,
        query: str = "jury verdict personal injury",
        jurisdiction: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict]:
        params = {
            "q": query,
            "type": "o",  # opinions only
            "order_by": "dateFiled desc",
        }
        if start_date:
            params["filed_after"] = start_date
        if end_date:
            params["filed_before"] = end_date

        url = f"{COURTLISTENER_BASE}/search/?{urlencode(params)}"
        logger.info(f"Searching CourtListener: {url}")

        resp = await self.client.get(url)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("results", [])[:self.max_verdicts]:
            opinion_url = item.get("absolute_url", "")
            opinion_id = item.get("id")
            if opinion_url and opinion_id:
                detail = await self._fetch_opinion_detail(opinion_id)
                if detail:
                    results.append({**item, "detail": detail})
        return results

    async def _fetch_opinion_detail(self, opinion_id: int) -> Optional[Dict]:
        try:
            url = f"{COURTLISTENER_BASE}/opinions/{opinion_id}/"
            resp = await self.client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch opinion {opinion_id}: {e}")
            return None

    def extract_verdict(self, opinion: Dict) -> Optional[Dict]:
        detail = opinion.get("detail", {})
        plain_text = (detail.get("plain_text") or detail.get("html_with_citations") or "").lower()
        case_name = detail.get("caseName") or detail.get("case_name") or opinion.get("caseName", "")

        if not plain_text:
            return None

        has_verdict = any(word in plain_text for word in ["verdict", "jury", "settlement", "damages", "awarded"])
        if not has_verdict:
            return None

        jurisdiction = opinion.get("court", "")
        court_name = detail.get("court") or opinion.get("court", "")
        date_filed = detail.get("dateFiled") or opinion.get("dateFiled", "")

        injury_types = classify_injury_types(plain_text)
        case_type = classify_case_type(plain_text)

        total_verdict = None
        amt_match = re.search(r"\$[\d,]+(?:\.\d+)?\s*(?:million|M)?", detail.get("html_with_citations") or "", re.IGNORECASE)
        if amt_match:
            total_verdict = parse_amount(amt_match.group())

        settlement_amount = None
        if "settlement" in plain_text or "settle" in plain_text:
            settlement_amount = total_verdict

        outcome_type = "verdict_plaintiff"
        if "settlement" in plain_text:
            outcome_type = "settlement"
        elif "defense verdict" in plain_text or "judgment for defendant" in plain_text:
            outcome_type = "verdict_defense"
        elif "dismiss" in plain_text:
            outcome_type = "dismissed"

        record = {
            "case_name": case_name[:255] if case_name else f"CourtListener-{opinion.get('id')}",
            "jurisdiction": jurisdiction[:255] if jurisdiction else "Unknown",
            "court": court_name[:255] if court_name else None,
            "case_type": case_type,
            "injury_type": injury_types,
            "outcome_type": outcome_type,
            "liability_tier": "unknown",
            "defendant_category": "Unknown",
            "verdict_date": parse_date(date_filed) or str(date.today()),
            "total_verdict": total_verdict,
            "settlement_amount": settlement_amount,
            "source": "courtlistener",
            "source_url": detail.get("absolute_url") or opinion.get("absolute_url", ""),
            "plain_text_snippet": (detail.get("plain_text") or "")[:5000] if not self.dry_run else None,
        }
        return record

    async def bulk_insert(self, records: List[Dict]) -> Dict[str, int]:
        if self.dry_run or not records:
            return {"inserted": 0, "skipped": 0, "failed": 0}

        job_payload = {
            "source_name": "courtlistener_api",
            "source_config": {
                "max_results": len(records),
                "query": "jury verdict personal injury",
            },
            "records_count": len(records),
        }

        try:
            job_resp = await self.client.post(
                f"{SETTLE_API_URL}/api/v1/internal/verdicts/scrape/jobs",
                json=job_payload,
                headers={"X-Admin-Key": SETTLE_ADMIN_KEY},
            )
            job_data = job_resp.json() if job_resp.status_code == 200 else {}
            job_id = job_data.get("id")
        except Exception as e:
            logger.warning(f"Failed to create scrape job: {e}")
            job_id = None

        try:
            insert_resp = await self.client.post(
                f"{SETTLE_API_URL}/api/v1/internal/verdicts/scrape/bulk-insert",
                json=records,
                headers={"X-Admin-Key": SETTLE_ADMIN_KEY},
            )
            result = insert_resp.json()

            if job_id:
                await self.client.patch(
                    f"{SETTLE_API_URL}/api/v1/internal/verdicts/scrape/jobs/{job_id}",
                    json={"status": "completed", "inserted": result.get("inserted", 0), "skipped": result.get("skipped", 0), "failed": result.get("failed", 0)},
                    headers={"X-Admin-Key": SETTLE_ADMIN_KEY},
                )

            return result
        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")

            if job_id:
                await self.client.patch(
                    f"{SETTLE_API_URL}/api/v1/internal/verdicts/scrape/jobs/{job_id}",
                    json={"status": "failed", "error_log": str(e)[:1000]},
                    headers={"X-Admin-Key": SETTLE_ADMIN_KEY},
                )
            return {"inserted": 0, "skipped": 0, "failed": len(records)}

    async def run(
        self,
        query: str = "jury verdict personal injury damages awarded",
        jurisdiction: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(f"Starting CourtListener scrape: query='{query}', max={self.max_verdicts}, dry_run={self.dry_run}")

        opinions = await self.search_opinions(query=query, jurisdiction=jurisdiction, start_date=start_date, end_date=end_date)
        logger.info(f"Found {len(opinions)} opinions")

        verdicts = []
        for op in opinions:
            record = self.extract_verdict(op)
            if record:
                verdicts.append(record)

        logger.info(f"Extracted {len(verdicts)} verdict records from {len(opinions)} opinions")

        if self.dry_run:
            for i, v in enumerate(verdicts[:5]):
                safe = {k: str(v.get(k))[:100] for k in sorted(v.keys()) if k != "plain_text_snippet"}
                logger.info(f"  [{i}] {json.dumps(safe)}")
            return {"opinions_found": len(opinions), "verdicts_extracted": len(verdicts), "dry_run": True}

        result = await self.bulk_insert(verdicts)
        logger.info(f"Bulk insert: {result}")

        return {
            "opinions_found": len(opinions),
            "verdicts_extracted": len(verdicts),
            "bulk_insert": result,
        }


async def main():
    parser = argparse.ArgumentParser(description="CourtListener Verdict Scraper for SETTLE")
    parser.add_argument("--query", "-q", default=os.getenv("CDS_QUERY", "jury verdict personal injury damages"), help="Search query for CourtListener")
    parser.add_argument("--jurisdiction", "-j", default=os.getenv("CDS_JURISDICTION"), help="Jurisdiction filter")
    parser.add_argument("--start-date", default=os.getenv("CDS_START_DATE"), help="Start date YYYY-MM-DD")
    parser.add_argument("--end-date", default=os.getenv("CDS_END_DATE"), help="End date YYYY-MM-DD")
    parser.add_argument("--max-verdicts", "-m", type=int, default=int(os.getenv("CDS_MAX_VERDICTS", "100")), help="Max verdicts to scrape")
    parser.add_argument("--dry-run", "-d", action="store_true", default=os.getenv("CDS_DRY_RUN", "0") == "1", help="Preview without inserting")
    args = parser.parse_args()

    scraper = CourtListenerVerdictScraper(max_verdicts=args.max_verdicts, dry_run=args.dry_run)
    try:
        result = await scraper.run(
            query=args.query,
            jurisdiction=args.jurisdiction,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        print(json.dumps(result, indent=2, default=str))
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
