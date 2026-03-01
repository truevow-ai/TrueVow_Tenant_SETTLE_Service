"""
Improved script to extract all 500 case URLs from Casemine search results
Handles pagination and lazy loading better
"""
import asyncio
import json
import logging
from typing import List
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract-all-500-improved.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def extract_all_urls_improved(page, target_count: int = 500) -> List[str]:
    """Extract all case URLs with improved pagination handling"""
    logger.info(f"Extracting case URLs (target: {target_count})...")
    
    all_urls = set()  # Use set to avoid duplicates
    scroll_attempts = 0
    max_scrolls = 200
    no_change_count = 0
    last_url_count = 0
    
    # Strategy 1: Scroll and extract incrementally
    logger.info("Strategy 1: Scrolling to load content...")
    while scroll_attempts < max_scrolls and len(all_urls) < target_count:
        # Scroll down
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(4000)  # Longer wait for lazy loading
        
        # Extract URLs after each scroll
        js_extract = """
        () => {
            const urls = [];
            const baseUrl = 'https://www.casemine.com';
            const seen = new Set();
            
            document.querySelectorAll('a[href]').forEach(link => {
                const href = link.getAttribute('href');
                if (!href) return;
                
                const fullUrl = href.startsWith('http') ? href : baseUrl + href;
                
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
        
        new_urls = await page.evaluate(js_extract)
        all_urls.update(new_urls)
        
        current_count = len(all_urls)
        
        # Check if we got new URLs
        if current_count == last_url_count:
            no_change_count += 1
        else:
            no_change_count = 0
            logger.info(f"  Found {current_count} URLs so far...")
        
        last_url_count = current_count
        
        # Try to find and click pagination/load more buttons
        if no_change_count >= 3:
            logger.info("  Trying to find pagination/load more buttons...")
            pagination_selectors = [
                'a:has-text("Next")',
                'a:has-text(">")',
                'button:has-text("Load More")',
                'button:has-text("Show More")',
                '[aria-label*="next" i]',
                '[aria-label*="more" i]',
                '.pagination a:last-child',
                '[class*="next"]',
                '[class*="load-more"]'
            ]
            
            clicked = False
            for selector in pagination_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.count() > 0:
                        is_visible = await elem.is_visible()
                        if is_visible:
                            await elem.click()
                            await page.wait_for_timeout(5000)
                            logger.info(f"  Clicked: {selector}")
                            clicked = True
                            no_change_count = 0
                            break
                except:
                    continue
            
            if not clicked:
                # Try scrolling up and down to trigger lazy loading
                await page.evaluate('window.scrollTo(0, 0)')
                await page.wait_for_timeout(2000)
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(3000)
        
        # If no new URLs after multiple attempts, break
        if no_change_count >= 10:
            logger.warning(f"  No new URLs found after {no_change_count} attempts, stopping...")
            break
        
        scroll_attempts += 1
        
        if scroll_attempts % 20 == 0:
            logger.info(f"  Progress: {scroll_attempts} scrolls, {current_count} URLs found")
    
    # Strategy 2: Try to extract from all result containers
    logger.info("Strategy 2: Extracting from result containers...")
    try:
        container_urls = await page.evaluate("""
        () => {
            const urls = [];
            const baseUrl = 'https://www.casemine.com';
            const seen = new Set();
            
            // Try various container selectors
            const containers = document.querySelectorAll('[class*="result"], [class*="case"], [class*="judgment"], article, [role="article"]');
            
            containers.forEach(container => {
                const links = container.querySelectorAll('a[href]');
                links.forEach(link => {
                    const href = link.getAttribute('href');
                    if (!href) return;
                    
                    const fullUrl = href.startsWith('http') ? href : baseUrl + href;
                    
                    if (fullUrl.includes('casemine.com') && 
                        (fullUrl.includes('/judgment/') || fullUrl.includes('/judgements/') || fullUrl.includes('/judgement/')) &&
                        !seen.has(fullUrl)) {
                        seen.add(fullUrl);
                        urls.push(fullUrl);
                    }
                });
            });
            
            return urls;
        }
        """)
        all_urls.update(container_urls)
        logger.info(f"  Found {len(container_urls)} additional URLs from containers")
    except Exception as e:
        logger.warning(f"  Error extracting from containers: {e}")
    
    # Convert to list and return
    unique_urls = list(all_urls)
    logger.info(f"Total unique URLs extracted: {len(unique_urls)}")
    
    return unique_urls[:target_count]


async def main():
    """Main execution"""
    search_url = "https://www.casemine.com/search/us/car%20accident?narrowing=settlement&sort=&judge=&courtType=0&published=&motionType=&motionOutcome=&year=&customYearFilter=false&tabName=filter"
    target_count = 500
    output_file = "all_500_case_urls_complete.txt"
    
    logger.info("="*60)
    logger.info("Improved URL Extraction - All 500 Cases")
    logger.info("="*60)
    logger.info(f"Search URL: {search_url}")
    logger.info(f"Target: {target_count} URLs")
    logger.info("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        logger.info(f"Navigating to search results page...")
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(5000)
        
        # Extract all URLs
        all_urls = await extract_all_urls_improved(page, target_count)
        
        # Save URLs
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in all_urls:
                f.write(f"{url}\n")
        
        logger.info("\n" + "="*60)
        logger.info("Extraction Complete!")
        logger.info("="*60)
        logger.info(f"Total URLs extracted: {len(all_urls)}")
        logger.info(f"Saved to: {output_file}")
        logger.info("\nNext step:")
        logger.info("Run: python scrape-casemine.py --urls all_500_case_urls_complete.txt --max-cases 500 --headless --output settlement_cases_500.json")
        logger.info("="*60)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
