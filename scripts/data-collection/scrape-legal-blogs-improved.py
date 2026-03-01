"""
Improved Scraper for Real Cases from Legal Blogs and Magazines
Uses more accessible sources and better extraction methods
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

# More accessible legal sources that discuss real cases
LEGAL_SOURCES = [
    {
        "name": "Legal Newsline",
        "url": "https://legalnewsline.com/stories/tag/personal-injury",
        "selectors": {
            "articles": "article, .post, .story-item",
            "title": "h1, h2, h3, .title, .headline",
            "content": ".content, .article-body, .post-content, p",
            "link": "a"
        }
    },
    {
        "name": "Law360 Personal Injury",
        "url": "https://www.law360.com/personal-injury-news",
        "selectors": {
            "articles": "article, .article-item, .news-item",
            "title": "h1, h2, .title, .headline",
            "content": ".content, .article-body, .summary, p",
            "link": "a"
        }
    },
    {
        "name": "FindLaw Legal Blogs",
        "url": "https://blogs.findlaw.com/injured/",
        "selectors": {
            "articles": "article, .post, .blog-post",
            "title": "h1, h2, .entry-title, .post-title",
            "content": ".entry-content, .post-content, .content",
            "link": "a"
        }
    },
    {
        "name": "Justia Legal Blogs",
        "url": "https://www.justia.com/blogs/personal-injury/",
        "selectors": {
            "articles": "article, .post, .blog-entry",
            "title": "h1, h2, .title",
            "content": ".content, .post-content, .excerpt",
            "link": "a"
        }
    }
]

# Enhanced patterns to extract case information
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
        r'(workplace\s+injury|workers\s+comp|work\s+injury)',
        r'(medical\s+malpractice|medical\s+negligence|doctor\s+error)',
        r'(product\s+liability|defective\s+product|unsafe\s+product)',
        r'(wrongful\s+death)',
        r'(dog\s+bite|animal\s+attack)'
    ],
    "injury_type": [
        r'(spinal\s+injury|back\s+injury|spinal\s+cord)',
        r'(traumatic\s+brain\s+injury|TBI|head\s+injury|brain\s+injury)',
        r'(fracture|broken\s+bone|broken\s+arm|broken\s+leg)',
        r'(soft\s+tissue\s+injury|whiplash)',
        r'(burn\s+injury|burns|thermal\s+injury)',
        r'(amputation|loss\s+of\s+limb)',
        r'(paralysis|paralyzed)'
    ],
    "jurisdiction": [
        r'(Miami-Dade|Miami\s+Dade|Dade\s+County|Miami,\s+FL)',
        r'(Los\s+Angeles|LA\s+County|Los\s+Angeles\s+County|LA,\s+CA)',
        r'([A-Z][a-z]+\s+County,\s+[A-Z]{2})',
        r'([A-Z][a-z]+,\s+[A-Z]{2})'
    ],
    "medical_bills": [
        r'medical\s+bills?\s+(?:of|totaling|totaled?)\s+\$[\d,]+',
        r'\$[\d,]+\s+in\s+medical\s+expenses',
        r'medical\s+costs?\s+of\s+\$[\d,]+',
        r'\$[\d,]+\s+in\s+medical\s+bills'
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
            # Normalize case type
            if "motor vehicle" in case_type.lower() or "car accident" in case_type.lower() or "mva" in case_type.lower():
                case_info["case_type"] = "Motor Vehicle Accident"
            elif "slip" in case_type.lower() or "fall" in case_type.lower():
                case_info["case_type"] = "Slip and Fall"
            elif "workplace" in case_type.lower() or "work" in case_type.lower():
                case_info["case_type"] = "Workplace Injury"
            elif "medical" in case_type.lower():
                case_info["case_type"] = "Medical Malpractice"
            elif "product" in case_type.lower():
                case_info["case_type"] = "Product Liability"
            elif "wrongful death" in case_type.lower():
                case_info["case_type"] = "Wrongful Death"
            else:
                case_info["case_type"] = case_type.title()
            break
    
    # Extract injury types
    for pattern in CASE_PATTERNS["injury_type"]:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        for match in matches:
            injury = match if isinstance(match, str) else match[0] if match else None
            if injury:
                # Normalize injury names
                if "spinal" in injury.lower() or "back" in injury.lower():
                    normalized = "Spinal Injury"
                elif "brain" in injury.lower() or "tbi" in injury.lower() or "head" in injury.lower():
                    normalized = "Traumatic Brain Injury"
                elif "fracture" in injury.lower() or "broken" in injury.lower():
                    normalized = "Fracture"
                elif "soft tissue" in injury.lower() or "whiplash" in injury.lower():
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
            # Normalize jurisdiction
            if "Miami" in jurisdiction or "Dade" in jurisdiction:
                case_info["jurisdiction"] = "Miami-Dade County, FL"
            elif "Los Angeles" in jurisdiction or ("LA" in jurisdiction and "County" in jurisdiction):
                case_info["jurisdiction"] = "Los Angeles County, CA"
            elif re.match(r'[A-Z][a-z]+\s+County,\s+[A-Z]{2}', jurisdiction):
                case_info["jurisdiction"] = jurisdiction
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
        match = re.search(pattern, text_original, re.IGNORECASE)
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
        
        # Find articles - try multiple selectors
        articles = []
        for selector in source['selectors']['articles'].split(', '):
            found = soup.select(selector.strip())
            if found:
                articles.extend(found)
                break
        
        if not articles:
            # Try to find any article-like elements
            articles = soup.find_all(['article', 'div'], class_=re.compile(r'article|post|story|news', re.I))
        
        logger.info(f"Found {len(articles)} articles")
        
        for article in articles[:15]:  # Limit to first 15 articles
            try:
                # Extract article content
                title_elem = None
                for selector in source['selectors']['title'].split(', '):
                    title_elem = article.select_one(selector.strip())
                    if title_elem:
                        break
                
                if not title_elem:
                    title_elem = article.find(['h1', 'h2', 'h3'])
                
                content_elem = None
                for selector in source['selectors']['content'].split(', '):
                    content_elem = article.select_one(selector.strip())
                    if content_elem:
                        break
                
                if not content_elem:
                    # Get all paragraph text
                    paragraphs = article.find_all('p')
                    if paragraphs:
                        content_elem = paragraphs[0]
                
                if not title_elem or not content_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                content_text = content_elem.get_text(strip=True)
                
                # Get article URL
                link = article.find('a', href=True)
                if link:
                    article_url = link['href']
                    if not article_url.startswith('http'):
                        base_url = '/'.join(source['url'].split('/')[:3])
                        article_url = base_url + article_url
                else:
                    article_url = source['url']
                
                # Extract case information
                full_text = f"{title} {content_text}"
                case_info = extract_case_info(content_text, article_url, title)
                
                if case_info:
                    case_info["source_publication"] = source['name']
                    cases.append(case_info)
                    logger.info(f"✓ Extracted: {case_info['case_type']} - {case_info['outcome_amount_range']} - {case_info['jurisdiction']}")
                
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
        
        # Set user agent to avoid blocking
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        try:
            for source in LEGAL_SOURCES:
                cases = await scrape_legal_source(source, page)
                all_cases.extend(cases)
                await asyncio.sleep(3)  # Be respectful with requests
        
        finally:
            await browser.close()
    
    # Save collected cases
    if all_cases:
        logger.info(f"\n{'='*60}")
        logger.info(f"Collected {len(all_cases)} real cases from legal publications")
        logger.info(f"{'='*60}\n")
        
        with open("real_cases_from_blogs.json", "w") as f:
            json.dump(all_cases, f, indent=2, default=str)
        
        logger.info("✓ Saved to: real_cases_from_blogs.json")
        
        # Show summary
        by_jurisdiction = {}
        by_case_type = {}
        by_range = {}
        
        for case in all_cases:
            jur = case.get("jurisdiction", "Unknown")
            by_jurisdiction[jur] = by_jurisdiction.get(jur, 0) + 1
            
            ct = case.get("case_type", "Unknown")
            by_case_type[ct] = by_case_type.get(ct, 0) + 1
            
            rng = case.get("outcome_amount_range", "Unknown")
            by_range[rng] = by_range.get(rng, 0) + 1
        
        logger.info("\nSummary:")
        logger.info(f"  By Jurisdiction: {dict(by_jurisdiction)}")
        logger.info(f"  By Case Type: {dict(by_case_type)}")
        logger.info(f"  By Settlement Range: {dict(by_range)}")
        
        logger.info("\n" + "=" * 60)
        logger.info("Next Steps:")
        logger.info("1. Review real_cases_from_blogs.json")
        logger.info("2. Verify cases against source articles")
        logger.info("3. Run: python prepare-for-seeding.py real_cases_from_blogs.json verified_cases.json")
        logger.info("4. Run: python seed-via-supabase-client.py verified_cases.json")
        logger.info("=" * 60)
    else:
        logger.warning("No cases extracted. This may be due to:")
        logger.warning("  - Website structure changes")
        logger.warning("  - Paywalls or login requirements")
        logger.warning("  - Rate limiting")
        logger.warning("\nTry manual collection or different sources.")


if __name__ == "__main__":
    asyncio.run(main())

