"""
Extract all 500 case URLs from Casemine search results and process settlement cases only
"""
import asyncio
import json
import logging
import random
from typing import List
from playwright.async_api import async_playwright

# Import the scraper
import importlib.util
import sys
import os

spec = importlib.util.spec_from_file_location("scrape_casemine", os.path.join(os.path.dirname(__file__), "scrape-casemine.py"))
scrape_casemine = importlib.util.module_from_spec(spec)
sys.modules["scrape_casemine"] = scrape_casemine
spec.loader.exec_module(scrape_casemine)
CasemineScraper = scrape_casemine.CasemineScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract-500-settlement.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def extract_all_urls_from_page(page, max_urls: int = 500) -> List[str]:
    """Extract all case URLs from the current search results page"""
    logger.info("Extracting all case URLs from search results page...")
    
    # Scroll to load all content
    logger.info("Scrolling to load all cases (this may take a few minutes)...")
    last_height = 0
    scroll_attempts = 0
    max_scrolls = 100  # Allow more scrolls for 500 cases
    no_change_count = 0
    
    while scroll_attempts < max_scrolls:
        # Scroll down
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(3000)  # Wait for content to load
        
        # Check if we've reached the bottom
        current_height = await page.evaluate('document.body.scrollHeight')
        if current_height == last_height:
            no_change_count += 1
            if no_change_count >= 3:
                # Try clicking "Load More" or pagination if exists
                try:
                    load_more_selectors = [
                        'text=/load more/i',
                        'text=/show more/i',
                        'text=/next/i',
                        'button:has-text("Load More")',
                        'button:has-text("Show More")',
                        '[class*="load-more"]',
                        '[class*="pagination"] a'
                    ]
                    for selector in load_more_selectors:
                        try:
                            elem = page.locator(selector).first
                            if await elem.count() > 0:
                                await elem.click()
                                await page.wait_for_timeout(5000)
                                current_height = await page.evaluate('document.body.scrollHeight')
                                if current_height > last_height:
                                    no_change_count = 0
                                    break
                        except:
                            continue
                except:
                    pass
            
            if current_height == last_height and no_change_count >= 5:
                break  # No more content to load
        
        if current_height > last_height:
            no_change_count = 0
        
        last_height = current_height
        scroll_attempts += 1
        
        if scroll_attempts % 10 == 0:
            logger.info(f"Scroll {scroll_attempts}/{max_scrolls}, height: {current_height}")
    
    logger.info(f"Finished scrolling after {scroll_attempts} attempts")
    
    # Extract all case URLs using JavaScript
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
                !fullUrl.includes('/home') && !fullUrl.includes('/about') &&
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


async def main():
    """Main execution"""
    import sys
    
    # Use the search URL from the browser (with settlement filter)
    search_url = "https://www.casemine.com/search/us/car%20accident?narrowing=settlement&sort=&judge=&courtType=0&published=&motionType=&motionOutcome=&year=&customYearFilter=false&tabName=filter"
    max_cases = 500
    urls_file = "all_500_case_urls.txt"
    output_file = "settlement_cases_500.json"
    
    if len(sys.argv) > 1:
        search_url = sys.argv[1]
    if len(sys.argv) > 2:
        max_cases = int(sys.argv[2])
    if len(sys.argv) > 3:
        output_file = sys.argv[3]
    
    logger.info("="*60)
    logger.info("Extract 500 Settlement Cases from Casemine")
    logger.info("="*60)
    logger.info(f"Search URL: {search_url}")
    logger.info(f"Max cases: {max_cases}")
    logger.info(f"Output file: {output_file}")
    logger.info("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # Step 1: Navigate and extract all URLs
        logger.info(f"\nStep 1: Navigating to search results page...")
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(5000)
        
        logger.info(f"Step 2: Extracting all case URLs (this may take a few minutes)...")
        all_urls = await extract_all_urls_from_page(page, max_cases)
        
        # Save all URLs
        with open(urls_file, 'w', encoding='utf-8') as f:
            for url in all_urls:
                f.write(f"{url}\n")
        logger.info(f"✓ Saved {len(all_urls)} URLs to {urls_file}")
        
        await browser.close()
    
    # Step 2: Extract case details using the scraper (settlement-only)
    logger.info(f"\n{'='*60}")
    logger.info(f"Step 3: Extracting settlement case details")
    logger.info(f"{'='*60}")
    logger.info(f"Processing {len(all_urls)} URLs with SETTLEMENT-ONLY filter...")
    logger.info(f"This will take approximately {len(all_urls) * 20 / 60:.1f} minutes")
    logger.info(f"{'='*60}\n")
    
    scraper = CasemineScraper(max_cases=len(all_urls), headless=True)
    settlement_cases = await scraper.scrape_from_urls(all_urls, settlement_only=True)
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(settlement_cases, f, indent=2, ensure_ascii=False)
    
    logger.info("\n" + "="*60)
    logger.info("Extraction Complete!")
    logger.info("="*60)
    logger.info(f"Total URLs processed: {len(all_urls)}")
    logger.info(f"Settlement cases collected: {len(settlement_cases)}")
    logger.info(f"Saved to: {output_file}")
    logger.info("\nNext steps:")
    logger.info("1. Review collected settlement cases")
    logger.info("2. Run: python prepare-for-seeding.py settlement_cases_500.json verified_settlement_cases.json")
    logger.info("3. Run: python seed-via-supabase-client.py verified_settlement_cases.json")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())
