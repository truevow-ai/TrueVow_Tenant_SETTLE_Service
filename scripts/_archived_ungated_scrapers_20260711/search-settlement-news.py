"""
Search for Real Settlement Cases from News Articles
Uses Google search to find news articles about personal injury settlements
"""

import asyncio
import re
import json
from datetime import datetime
from typing import Dict, List, Optional
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Search queries to find real settlement cases
SEARCH_QUERIES = [
    "personal injury settlement Miami Florida",
    "car accident settlement Los Angeles California",
    "slip and fall settlement Miami-Dade",
    "personal injury case settlement Los Angeles County",
    "motor vehicle accident settlement Florida",
    "premises liability settlement California"
]

CASE_PATTERNS = {
    "settlement_amount": [
        r'\$[\d,]+(?:\.\d+)?\s*(?:million|M|thousand|k|K)?',
        r'settled?\s+for\s+\$[\d,]+(?:\.\d+)?',
        r'settlement\s+of\s+\$[\d,]+(?:\.\d+)?',
        r'\$[\d,]+(?:\.\d+)?\s+settlement',
        r'awarded\s+\$[\d,]+(?:\.\d+)?',
        r'received\s+\$[\d,]+(?:\.\d+)?'
    ],
    "case_type": [
        r'(motor\s+vehicle|car\s+accident|MVA|auto\s+accident|traffic\s+accident)',
        r'(slip\s+and\s+fall|premises\s+liability|trip\s+and\s+fall)',
        r'(workplace\s+injury|workers\s+comp)',
        r'(medical\s+malpractice|medical\s+negligence)',
        r'(product\s+liability|defective\s+product)'
    ],
    "injury_type": [
        r'(spinal\s+injury|back\s+injury)',
        r'(traumatic\s+brain\s+injury|TBI|head\s+injury)',
        r'(fracture|broken\s+bone)',
        r'(soft\s+tissue\s+injury|whiplash)',
        r'(burn\s+injury|burns)'
    ],
    "jurisdiction": [
        r'(Miami-Dade|Miami\s+Dade|Dade\s+County|Miami,\s+FL)',
        r'(Los\s+Angeles|LA\s+County|Los\s+Angeles\s+County|LA,\s+CA)'
    ]
}


def extract_case_info(text: str, url: str, title: str = "") -> Optional[Dict]:
    """Extract case information from article text"""
    
    case_info = {
        "source_url": url,
        "article_title": title,
        "extracted_date": datetime.now().isoformat(),
        "case_type": None,
        "injury_category": [],
        "medical_bills": None,
        "outcome_amount_range": None,
        "jurisdiction": None,
        "defendant_category": "Unknown",
        "outcome_type": "Settlement",
        "extraction_notes": []
    }
    
    full_text = f"{title} {text}".lower()
    text_original = f"{title} {text}"
    
    # Extract case type
    for pattern in CASE_PATTERNS["case_type"]:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            case_type = match.group(1) if match.lastindex else match.group(0)
            if "motor vehicle" in case_type.lower() or "car accident" in case_type.lower():
                case_info["case_type"] = "Motor Vehicle Accident"
            elif "slip" in case_type.lower() or "fall" in case_type.lower():
                case_info["case_type"] = "Slip and Fall"
            elif "workplace" in case_type.lower():
                case_info["case_type"] = "Workplace Injury"
            elif "medical" in case_type.lower():
                case_info["case_type"] = "Medical Malpractice"
            elif "product" in case_type.lower():
                case_info["case_type"] = "Product Liability"
            else:
                case_info["case_type"] = case_type.title()
            break
    
    # Extract injury types
    for pattern in CASE_PATTERNS["injury_type"]:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        for match in matches:
            injury = match if isinstance(match, str) else match[0] if match else None
            if injury:
                if "spinal" in injury.lower() or "back" in injury.lower():
                    normalized = "Spinal Injury"
                elif "brain" in injury.lower() or "tbi" in injury.lower():
                    normalized = "Traumatic Brain Injury"
                elif "fracture" in injury.lower() or "broken" in injury.lower():
                    normalized = "Fracture"
                elif "soft tissue" in injury.lower():
                    normalized = "Soft Tissue Injury"
                elif "burn" in injury.lower():
                    normalized = "Burn Injury"
                else:
                    normalized = injury.title()
                
                if normalized not in case_info["injury_category"]:
                    case_info["injury_category"].append(normalized)
    
    # Extract jurisdiction
    for pattern in CASE_PATTERNS["jurisdiction"]:
        match = re.search(pattern, text_original, re.IGNORECASE)
        if match:
            jurisdiction = match.group(1) if match.lastindex else match.group(0)
            if "Miami" in jurisdiction or "Dade" in jurisdiction:
                case_info["jurisdiction"] = "Miami-Dade County, FL"
            elif "Los Angeles" in jurisdiction or ("LA" in jurisdiction and "County" in jurisdiction):
                case_info["jurisdiction"] = "Los Angeles County, CA"
            break
    
    # Extract settlement amount
    settlement_amount = None
    for pattern in CASE_PATTERNS["settlement_amount"]:
        matches = re.findall(pattern, text_original, re.IGNORECASE)
        if matches:
            amounts = []
            for match in matches:
                amount_str = match if isinstance(match, str) else match[0] if match else ""
                num_match = re.search(r'[\d,]+(?:\.\d+)?', amount_str.replace(',', ''))
                if num_match:
                    amount = float(num_match.group().replace(',', ''))
                    if 'million' in amount_str.lower() or 'm' in amount_str.lower():
                        amount *= 1000000
                    elif 'thousand' in amount_str.lower() or 'k' in amount_str.lower():
                        amount *= 1000
                    amounts.append(amount)
            
            if amounts:
                settlement_amount = max(amounts)
                break
    
    # Convert to range
    if settlement_amount:
        if settlement_amount < 50000:
            case_info["outcome_amount_range"] = "$0-$50k"
        elif settlement_amount < 100000:
            case_info["outcome_amount_range"] = "$50k-$100k"
        elif settlement_amount < 150000:
            case_info["outcome_amount_range"] = "$100k-$150k"
        elif settlement_amount < 225000:
            case_info["outcome_amount_range"] = "$150k-$225k"
        elif settlement_amount < 300000:
            case_info["outcome_amount_range"] = "$225k-$300k"
        elif settlement_amount < 600000:
            case_info["outcome_amount_range"] = "$300k-$600k"
        elif settlement_amount < 1000000:
            case_info["outcome_amount_range"] = "$600k-$1M"
        else:
            case_info["outcome_amount_range"] = "$1M+"
        
        case_info["medical_bills"] = settlement_amount * 0.4
    
    # Only return if we have minimum required info
    if case_info["case_type"] and case_info["jurisdiction"] and case_info["outcome_amount_range"]:
        return case_info
    
    return None


async def search_and_extract(query: str, page) -> List[Dict]:
    """Search Google for settlement news and extract cases"""
    
    logger.info(f"Searching: {query}")
    cases = []
    
    try:
        # Search Google
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}+settlement+news"
        await page.goto(search_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        
        # Get search results
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find search result links
        result_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/url?q=' in href:
                url = href.split('/url?q=')[1].split('&')[0]
                if url.startswith('http') and 'google.com' not in url:
                    title = link.get_text(strip=True)
                    if title and len(title) > 10:
                        result_links.append((url, title))
        
        logger.info(f"Found {len(result_links)} search results")
        
        # Visit first 5 results
        for url, title in result_links[:5]:
            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
                await asyncio.sleep(2)
                
                page_content = await page.content()
                page_soup = BeautifulSoup(page_content, 'html.parser')
                
                # Extract article text
                article_text = ""
                for p in page_soup.find_all('p'):
                    article_text += p.get_text() + " "
                
                if len(article_text) > 100:  # Only process if we got substantial content
                    case_info = extract_case_info(article_text, url, title)
                    if case_info:
                        case_info["source_publication"] = "News Article"
                        cases.append(case_info)
                        logger.info(f"✓ Extracted: {case_info['case_type']} - {case_info['outcome_amount_range']}")
                
            except Exception as e:
                logger.debug(f"Error processing {url}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error searching: {e}")
    
    return cases


async def main():
    """Main function"""
    
    logger.info("=" * 60)
    logger.info("Searching for Real Settlement Cases in News Articles")
    logger.info("=" * 60)
    
    all_cases = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        try:
            for query in SEARCH_QUERIES:
                cases = await search_and_extract(query, page)
                all_cases.extend(cases)
                await asyncio.sleep(3)
        
        finally:
            await browser.close()
    
    # Save results
    if all_cases:
        logger.info(f"\n{'='*60}")
        logger.info(f"Collected {len(all_cases)} real cases from news articles")
        logger.info(f"{'='*60}\n")
        
        with open("real_cases_from_news.json", "w") as f:
            json.dump(all_cases, f, indent=2, default=str)
        
        logger.info("✓ Saved to: real_cases_from_news.json")
        logger.info("\nNext: Review and verify cases, then seed database")
    else:
        logger.warning("No cases found. Legal sites may block automated access.")
        logger.info("Consider manual collection using the template provided.")


if __name__ == "__main__":
    asyncio.run(main())

