"""
Extract all 500 case URLs from Casemine search results page
Filter for settlement cases only and extract details
"""
import asyncio
import json
import logging
import random
from typing import List, Dict, Optional
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract-500-cases.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def extract_all_case_urls(page, max_urls: int = 500) -> List[str]:
    """Extract all case URLs from the current search results page"""
    logger.info("Extracting case URLs from search results page...")
    
    # Scroll to load all content (pagination or lazy loading)
    logger.info("Scrolling to load all cases...")
    last_height = 0
    scroll_attempts = 0
    max_scrolls = 50  # Prevent infinite scrolling
    
    while scroll_attempts < max_scrolls:
        # Scroll down
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(2000)  # Wait for content to load
        
        # Check if we've reached the bottom
        current_height = await page.evaluate('document.body.scrollHeight')
        if current_height == last_height:
            # Try clicking "Load More" or "Next" button if exists
            try:
                load_more = page.locator('text=/load more|show more|next/i').first
                if await load_more.count() > 0:
                    await load_more.click()
                    await page.wait_for_timeout(3000)
                    current_height = await page.evaluate('document.body.scrollHeight')
            except:
                pass
            
            if current_height == last_height:
                break  # No more content to load
        
        last_height = current_height
        scroll_attempts += 1
        logger.info(f"Scroll attempt {scroll_attempts}/{max_scrolls}, height: {current_height}")
    
    # Extract all case URLs
    js_code = """
    () => {
        const urls = [];
        const baseUrl = 'https://www.casemine.com';
        const seen = new Set();
        
        // Extract all judgment/case URLs
        document.querySelectorAll('a[href]').forEach(link => {
            const href = link.getAttribute('href');
            if (!href) return;
            
            const fullUrl = href.startsWith('http') ? href : baseUrl + href;
            
            // Check if it's a case/judgment URL
            if (fullUrl.includes('casemine.com') && 
                (fullUrl.includes('/judgment/') || fullUrl.includes('/judgements/') || fullUrl.includes('/judgement/')) &&
                !fullUrl.includes('/search') && !fullUrl.includes('/login') && !fullUrl.includes('/signup') &&
                !seen.has(fullUrl)) {
                seen.add(fullUrl);
                urls.push(fullUrl);
            }
        });
        
        return urls;
    }
    """
    
    urls = await page.evaluate(js_code)
    logger.info(f"Extracted {len(urls)} case URLs from page")
    
    # Remove duplicates and return
    unique_urls = list(dict.fromkeys(urls))  # Preserves order
    return unique_urls[:max_urls]


async def check_is_settlement_case(page, case_url: str) -> bool:
    """Check if a case is a settlement case (not just verdict)"""
    try:
        await page.goto(case_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_load_state('networkidle', timeout=15000)
        await page.wait_for_timeout(3000)
        
        # Get page content
        content = await page.content()
        page_text = await page.evaluate('document.body.innerText')
        
        # Check for settlement indicators
        content_lower = (content + " " + page_text).lower()
        
        # Strong settlement indicators
        settlement_keywords = [
            'settlement', 'settled', 'settling',
            'settlement agreement', 'settled for', 'settlement amount',
            'reached a settlement', 'agreed to settle', 'settlement reached'
        ]
        
        # Exclude verdict-only cases
        verdict_keywords = [
            'jury verdict', 'verdict for', 'verdict against',
            'awarded by jury', 'jury found', 'jury awarded'
        ]
        
        has_settlement = any(keyword in content_lower for keyword in settlement_keywords)
        has_verdict_only = any(keyword in content_lower for keyword in verdict_keywords) and not has_settlement
        
        # If it has verdict keywords but no settlement, it's not a settlement case
        if has_verdict_only:
            return False
        
        # If it has settlement keywords, it's a settlement case
        if has_settlement:
            return True
        
        # If URL or page title indicates settlement
        page_title = await page.title()
        if 'settlement' in page_title.lower() or 'settlement' in case_url.lower():
            return True
        
        return False
        
    except Exception as e:
        logger.warning(f"Error checking settlement status for {case_url}: {e}")
        return False  # Default to False if we can't determine


async def main():
    """Main execution"""
    import sys
    
    # Get current page URL from browser or use default
    search_url = "https://www.casemine.com/search/us/car%20accident?narrowing=settlement&sort=&judge=&courtType=0&published=&motionType=&motionOutcome=&year=&customYearFilter=false&tabName=filter"
    max_cases = 500
    output_file = "all_500_case_urls.txt"
    settlement_urls_file = "settlement_case_urls.txt"
    
    if len(sys.argv) > 1:
        search_url = sys.argv[1]
    if len(sys.argv) > 2:
        max_cases = int(sys.argv[2])
    
    logger.info("="*60)
    logger.info("Extracting All 500 Case URLs")
    logger.info("="*60)
    logger.info(f"Search URL: {search_url}")
    logger.info(f"Max cases: {max_cases}")
    logger.info("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # Navigate to search results page
        logger.info(f"Navigating to: {search_url}")
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(5000)
        
        # Extract all case URLs
        all_urls = await extract_all_case_urls(page, max_cases)
        
        # Save all URLs
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in all_urls:
                f.write(f"{url}\n")
        logger.info(f"Saved {len(all_urls)} URLs to {output_file}")
        
        # Filter for settlement cases only
        logger.info("\n" + "="*60)
        logger.info("Filtering for Settlement Cases Only")
        logger.info("="*60)
        
        settlement_urls = []
        for i, url in enumerate(all_urls, 1):
            logger.info(f"[{i}/{len(all_urls)}] Checking: {url[:80]}...")
            
            is_settlement = await check_is_settlement_case(page, url)
            
            if is_settlement:
                settlement_urls.append(url)
                logger.info(f"  ✓ Settlement case found! ({len(settlement_urls)} total)")
            else:
                logger.info(f"  ✗ Not a settlement case, skipping...")
            
            # Rate limiting
            delay = 5000 + random.randint(0, 3000)  # 5-8 seconds
            await page.wait_for_timeout(delay)
            
            # Every 10 cases, take a longer break
            if i % 10 == 0:
                extra_delay = 15000 + random.randint(0, 10000)  # 15-25 seconds
                logger.info(f"  Taking extended break: {extra_delay/1000:.1f} seconds...")
                await page.wait_for_timeout(extra_delay)
        
        # Save settlement URLs
        with open(settlement_urls_file, 'w', encoding='utf-8') as f:
            for url in settlement_urls:
                f.write(f"{url}\n")
        
        logger.info("\n" + "="*60)
        logger.info("Extraction Complete!")
        logger.info("="*60)
        logger.info(f"Total URLs extracted: {len(all_urls)}")
        logger.info(f"Settlement cases found: {len(settlement_urls)}")
        logger.info(f"Saved settlement URLs to: {settlement_urls_file}")
        logger.info("\nNext steps:")
        logger.info("1. Review settlement URLs")
        logger.info("2. Run: python scrape-casemine.py --urls settlement_case_urls.txt --max-cases 500 --headless --output settlement_cases.json")
        logger.info("="*60)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
