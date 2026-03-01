"""
Scrape Real Cases from Legal Blogs and Magazines
Extracts actual case information from law-related publications
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

# Legal blog and magazine sources that discuss real cases
LEGAL_SOURCES = [
    {
        "name": "Law.com",
        "url": "https://www.law.com/search?q=personal+injury+settlement",
        "selectors": {
            "articles": "article, .article-item, .search-result",
            "title": "h1, h2, .title, .article-title",
            "content": ".article-content, .content, .post-content",
            "date": ".date, .published-date, time"
        }
    },
    {
        "name": "ABA Journal",
        "url": "https://www.abajournal.com/search?q=settlement+personal+injury",
        "selectors": {
            "articles": "article, .article, .post",
            "title": "h1, h2, .entry-title",
            "content": ".entry-content, .article-body",
            "date": ".published, time"
        }
    },
    {
        "name": "Legal News Sites",
        "url": "https://www.lexisnexis.com/legalnewsroom/litigation/b/litigation-blog/posts/search?q=settlement",
        "selectors": {
            "articles": ".article, .post, .blog-post",
            "title": "h1, h2, .title",
            "content": ".content, .post-content",
            "date": ".date, time"
        }
    }
]

# Patterns to extract case information
CASE_PATTERNS = {
    "settlement_amount": [
        r'\$[\d,]+(?:\.\d+)?\s*(?:million|M|thousand|k|K)?',
        r'settled?\s+for\s+\$[\d,]+',
        r'settlement\s+of\s+\$[\d,]+',
        r'\$[\d,]+(?:\.\d+)?\s+settlement'
    ],
    "case_type": [
        r'(motor\s+vehicle|car\s+accident|MVA|auto\s+accident)',
        r'(slip\s+and\s+fall|premises\s+liability)',
        r'(workplace\s+injury|workers\s+comp)',
        r'(medical\s+malpractice|medical\s+negligence)',
        r'(product\s+liability|defective\s+product)'
    ],
    "injury_type": [
        r'(spinal\s+injury|back\s+injury)',
        r'(traumatic\s+brain\s+injury|TBI|head\s+injury)',
        r'(fracture|broken\s+bone)',
        r'(soft\s+tissue\s+injury)',
        r'(burn\s+injury|burns)'
    ],
    "jurisdiction": [
        r'(Miami-Dade|Miami|Dade\s+County|Florida|FL)',
        r'(Los\s+Angeles|LA\s+County|California|CA)',
        r'([A-Z][a-z]+\s+County,\s+[A-Z]{2})'
    ],
    "medical_bills": [
        r'medical\s+bills?\s+(?:of|totaling|totaled?)\s+\$[\d,]+',
        r'\$[\d,]+\s+in\s+medical\s+expenses',
        r'medical\s+costs?\s+of\s+\$[\d,]+'
    ]
}


def extract_case_info(text: str, url: str) -> Optional[Dict]:
    """Extract case information from article text"""
    
    case_info = {
        "source_url": url,
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
    
    text_lower = text.lower()
    
    # Extract case type
    for pattern in CASE_PATTERNS["case_type"]:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            case_type = match.group(1) if match.lastindex else match.group(0)
            case_info["case_type"] = case_type.title()
            break
    
    # Extract injury types
    for pattern in CASE_PATTERNS["injury_type"]:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            injury = match if isinstance(match, str) else match[0] if match else None
            if injury and injury.title() not in case_info["injury_category"]:
                case_info["injury_category"].append(injury.title())
    
    # Extract jurisdiction
    for pattern in CASE_PATTERNS["jurisdiction"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            jurisdiction = match.group(1) if match.lastindex else match.group(0)
            # Normalize jurisdiction
            if "Miami" in jurisdiction or "Dade" in jurisdiction:
                case_info["jurisdiction"] = "Miami-Dade County, FL"
            elif "Los Angeles" in jurisdiction or "LA" in jurisdiction:
                case_info["jurisdiction"] = "Los Angeles County, CA"
            else:
                case_info["jurisdiction"] = jurisdiction
            break
    
    # Extract settlement amount
    settlement_amount = None
    for pattern in CASE_PATTERNS["settlement_amount"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Get the largest amount mentioned
            amounts = []
            for match in matches:
                amount_str = match if isinstance(match, str) else match[0] if match else ""
                # Extract numeric value
                num_match = re.search(r'[\d,]+(?:\.\d+)?', amount_str.replace(',', ''))
                if num_match:
                    amount = float(num_match.group().replace(',', ''))
                    # Handle million/thousand multipliers
                    if 'million' in amount_str.lower() or 'm' in amount_str.lower():
                        amount *= 1000000
                    elif 'thousand' in amount_str.lower() or 'k' in amount_str.lower():
                        amount *= 1000
                    amounts.append(amount)
            
            if amounts:
                settlement_amount = max(amounts)
                break
    
    # Convert settlement amount to range
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
        
        # Estimate medical bills (typically 30-50% of settlement)
        case_info["medical_bills"] = settlement_amount * 0.4
    
    # Extract medical bills if mentioned separately
    for pattern in CASE_PATTERNS["medical_bills"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num_match = re.search(r'[\d,]+(?:\.\d+)?', match.group(0).replace(',', ''))
            if num_match:
                case_info["medical_bills"] = float(num_match.group().replace(',', ''))
                break
    
    # Only return if we have minimum required info
    if case_info["case_type"] and case_info["jurisdiction"] and case_info["outcome_amount_range"]:
        return case_info
    
    return None


async def scrape_legal_source(source: Dict, page) -> List[Dict]:
    """Scrape a legal blog/magazine source"""
    
    logger.info(f"Scraping {source['name']}...")
    cases = []
    
    try:
        await page.goto(source['url'], wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        
        # Get page content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find articles
        articles = soup.select(source['selectors']['articles'])
        logger.info(f"Found {len(articles)} articles")
        
        for article in articles[:10]:  # Limit to first 10 articles
            try:
                # Extract article content
                title_elem = article.select_one(source['selectors']['title'])
                content_elem = article.select_one(source['selectors']['content'])
                
                if not title_elem or not content_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                content_text = content_elem.get_text(strip=True)
                
                # Get article URL
                link = article.find('a', href=True)
                article_url = link['href'] if link else source['url']
                if not article_url.startswith('http'):
                    article_url = source['url'].split('/')[0] + '//' + source['url'].split('/')[2] + article_url
                
                # Extract case information
                full_text = f"{title} {content_text}"
                case_info = extract_case_info(full_text, article_url)
                
                if case_info:
                    case_info["article_title"] = title
                    case_info["source_publication"] = source['name']
                    cases.append(case_info)
                    logger.info(f"Extracted case: {case_info['case_type']} - {case_info['outcome_amount_range']}")
                
            except Exception as e:
                logger.debug(f"Error processing article: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error scraping {source['name']}: {e}")
    
    return cases


async def main():
    """Main scraping function"""
    
    logger.info("=" * 60)
    logger.info("Scraping Real Cases from Legal Blogs & Magazines")
    logger.info("=" * 60)
    
    all_cases = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            for source in LEGAL_SOURCES:
                cases = await scrape_legal_source(source, page)
                all_cases.extend(cases)
                await asyncio.sleep(2)  # Be respectful with requests
        
        finally:
            await browser.close()
    
    # Save collected cases
    if all_cases:
        logger.info(f"\nCollected {len(all_cases)} real cases from legal publications")
        
        with open("real_cases_from_blogs.json", "w") as f:
            json.dump(all_cases, f, indent=2, default=str)
        
        logger.info("Saved to: real_cases_from_blogs.json")
        
        # Create verification report
        verification_report = {
            "collection_date": datetime.now().isoformat(),
            "total_cases": len(all_cases),
            "source": "Legal blogs and magazines",
            "verification_instructions": {
                "note": "These cases were extracted from legal publications discussing real cases",
                "verification": "Review source URLs to verify case authenticity",
                "status": "needs_manual_verification"
            },
            "cases": []
        }
        
        for idx, case in enumerate(all_cases, 1):
            verification_report["cases"].append({
                "case_number": idx,
                "source_publication": case.get("source_publication"),
                "article_title": case.get("article_title"),
                "source_url": case.get("source_url"),
                "jurisdiction": case.get("jurisdiction"),
                "case_type": case.get("case_type"),
                "outcome_amount_range": case.get("outcome_amount_range"),
                "extraction_date": case.get("extracted_date"),
                "verification_status": "needs_review",
                "verification_notes": "Extracted from legal publication - verify against source article"
            })
        
        with open("verification_report_blogs.json", "w") as f:
            json.dump(verification_report, f, indent=2, default=str)
        
        logger.info("Created verification report: verification_report_blogs.json")
        
        logger.info("\n" + "=" * 60)
        logger.info("Collection Complete!")
        logger.info("=" * 60)
        logger.info(f"Total cases: {len(all_cases)}")
        logger.info("\nNext steps:")
        logger.info("1. Review real_cases_from_blogs.json")
        logger.info("2. Verify cases against source articles")
        logger.info("3. Run: python prepare-for-seeding.py real_cases_from_blogs.json")
        logger.info("4. Run: python seed-via-supabase-client.py verified_cases.json")
    else:
        logger.warning("No cases extracted. Check source URLs and selectors.")


if __name__ == "__main__":
    asyncio.run(main())

