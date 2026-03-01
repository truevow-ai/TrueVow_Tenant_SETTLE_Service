"""
Extract case URLs from current Casemine search results page and scrape details
"""
import asyncio
import json
import logging
from typing import List
import importlib.util
import sys
import os

# Import the scraper module
spec = importlib.util.spec_from_file_location("scrape_casemine", os.path.join(os.path.dirname(__file__), "scrape-casemine.py"))
scrape_casemine = importlib.util.module_from_spec(spec)
sys.modules["scrape_casemine"] = scrape_casemine
spec.loader.exec_module(scrape_casemine)
CasemineScraper = scrape_casemine.CasemineScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract-current-page.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def extract_urls_from_search_page(search_url: str, max_cases: int = 50) -> List[str]:
    """Extract case URLs from a Casemine search results page"""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        logger.info(f"Navigating to: {search_url}")
        await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_load_state('networkidle', timeout=20000)
        await page.wait_for_timeout(5000)  # Wait for dynamic content
        
        # Scroll to load more content
        for i in range(3):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(1000)
        
        # Extract URLs using JavaScript
        js_extract = """
        () => {
            const urls = [];
            const baseUrl = 'https://www.casemine.com';
            
            // Method 1: Find all links with /judgment/ or /judgements/ in href
            document.querySelectorAll('a[href]').forEach(link => {
                const href = link.getAttribute('href');
                if (href && (href.includes('/judgment/') || href.includes('/judgements/') || href.includes('/judgement/'))) {
                    const fullUrl = href.startsWith('http') ? href : baseUrl + href;
                    if (fullUrl.includes('casemine.com') && !urls.includes(fullUrl)) {
                        urls.push(fullUrl);
                    }
                }
            });
            
            // Method 2: Find links that contain case name patterns (v., vs., etc.)
            document.querySelectorAll('a').forEach(link => {
                const text = link.textContent || link.innerText || '';
                const href = link.getAttribute('href');
                // Check if link text looks like a case name (contains " v. " or " vs. ")
                if (text && (text.includes(' v. ') || text.includes(' vs. ') || text.includes(' v ')) && 
                    href && href.length > 10) {
                    const fullUrl = href.startsWith('http') ? href : baseUrl + href;
                    if (fullUrl.includes('casemine.com') && !urls.includes(fullUrl) && 
                        (fullUrl.includes('/judgment/') || fullUrl.includes('/judgements/') || fullUrl.includes('/judgement/') || fullUrl.includes('/case/'))) {
                        urls.push(fullUrl);
                    }
                }
            });
            
            return [...new Set(urls)];
        }
        """
        
        case_urls = await page.evaluate(js_extract)
        await browser.close()
        
        logger.info(f"Extracted {len(case_urls)} case URLs from search results")
        return case_urls[:max_cases]


async def main():
    """Main execution"""
    import sys
    
    # Default to the search URL from the browser
    search_url = "https://www.casemine.com/search/us/car%20accident"
    max_cases = 50
    output_file = "casemine_cases_from_search.json"
    
    if len(sys.argv) > 1:
        search_url = sys.argv[1]
    if len(sys.argv) > 2:
        max_cases = int(sys.argv[2])
    if len(sys.argv) > 3:
        output_file = sys.argv[3]
    
    logger.info("="*60)
    logger.info("Extracting Case URLs from Search Results")
    logger.info("="*60)
    logger.info(f"Search URL: {search_url}")
    logger.info(f"Max cases: {max_cases}")
    logger.info(f"Output file: {output_file}")
    logger.info("="*60)
    
    # Extract URLs from search page
    case_urls = await extract_urls_from_search_page(search_url, max_cases)
    
    if not case_urls:
        logger.error("No case URLs found on the search results page")
        return
    
    logger.info(f"\nFound {len(case_urls)} case URLs:")
    for i, url in enumerate(case_urls, 1):
        logger.info(f"  {i}. {url}")
    
    # Save URLs to file
    urls_file = "extracted_case_urls.txt"
    with open(urls_file, 'w', encoding='utf-8') as f:
        for url in case_urls:
            f.write(f"{url}\n")
    logger.info(f"\nSaved URLs to: {urls_file}")
    
    # Extract case details using scraper
    logger.info("\n" + "="*60)
    logger.info("Extracting Case Details")
    logger.info("="*60)
    
    scraper = CasemineScraper(max_cases=max_cases, headless=True)
    cases = await scraper.scrape_from_urls(case_urls)
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    
    logger.info("\n" + "="*60)
    logger.info("Extraction Complete!")
    logger.info("="*60)
    logger.info(f"Total cases collected: {len(cases)}")
    logger.info(f"Saved to: {output_file}")
    logger.info("\nNext steps:")
    logger.info("1. Review collected cases in the JSON file")
    logger.info("2. Run: python prepare-for-seeding.py casemine_cases_from_search.json verified_cases.json")
    logger.info("3. Run: python seed-via-supabase-client.py verified_cases.json")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())
