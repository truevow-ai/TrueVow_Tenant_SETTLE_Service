"""
Extract all 500 case URLs using aggressive infinite scroll detection
Handles lazy loading and dynamic content loading
"""
import asyncio
import json
import logging
import time
from typing import List, Set
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract-500-infinite-scroll.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def extract_urls_from_page(page) -> Set[str]:
    """Extract all case URLs currently visible on the page"""
    js_code = """
    () => {
        const urls = [];
        const baseUrl = 'https://www.casemine.com';
        const seen = new Set();
        
        // Method 1: Extract all judgment/case links
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
        
        return [...new Set(urls)];
    }
    """
    urls = await page.evaluate(js_code)
    return set(urls)


async def scroll_and_wait_for_content(page, scroll_delay: int = 2000, max_wait: int = 10000):
    """Scroll down and wait for new content to load"""
    # Get current URL count
    urls_before = await extract_urls_from_page(page)
    count_before = len(urls_before)
    
    # Scroll to bottom
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    
    # Wait for content to load (check multiple times)
    wait_interval = 500  # Check every 500ms
    waited = 0
    
    while waited < max_wait:
        await page.wait_for_timeout(wait_interval)
        waited += wait_interval
        
        # Check if new content loaded
        urls_after = await extract_urls_from_page(page)
        count_after = len(urls_after)
        
        if count_after > count_before:
            # New content loaded, wait a bit more for it to stabilize
            await page.wait_for_timeout(scroll_delay)
            return True
        
        # Also check if page height changed
        current_height = await page.evaluate('document.body.scrollHeight')
        initial_height = await page.evaluate('window.innerHeight')
        
        if current_height > initial_height * 1.5:  # Significant content
            await page.wait_for_timeout(scroll_delay)
            return True
    
    return False


async def extract_all_500_infinite_scroll(page, target_count: int = 500) -> List[str]:
    """Extract all URLs using aggressive infinite scroll"""
    logger.info(f"Extracting {target_count} URLs using infinite scroll...")
    
    all_urls: Set[str] = set()
    scroll_attempts = 0
    max_scrolls = 200
    consecutive_no_new_urls = 0
    max_consecutive_no_new = 5
    
    # Initial wait for page to load
    await page.wait_for_load_state('networkidle', timeout=30000)
    await page.wait_for_timeout(5000)
    
    # Initial extraction
    initial_urls = await extract_urls_from_page(page)
    all_urls.update(initial_urls)
    logger.info(f"Initial extraction: {len(initial_urls)} URLs found")
    
    while len(all_urls) < target_count and scroll_attempts < max_scrolls:
        scroll_attempts += 1
        logger.info(f"\n--- Scroll attempt {scroll_attempts} ---")
        logger.info(f"Current URL count: {len(all_urls)}")
        
        # Scroll and wait for content
        new_content_loaded = await scroll_and_wait_for_content(page, scroll_delay=3000, max_wait=10000)
        
        # Extract URLs after scroll
        current_urls = await extract_urls_from_page(page)
        new_urls = current_urls - all_urls
        
        if new_urls:
            all_urls.update(new_urls)
            logger.info(f"  ✓ Found {len(new_urls)} new URLs (total: {len(all_urls)})")
            consecutive_no_new_urls = 0
        else:
            consecutive_no_new_urls += 1
            logger.info(f"  ⚠ No new URLs (consecutive: {consecutive_no_new_urls}/{max_consecutive_no_new})")
            
            if consecutive_no_new_urls >= max_consecutive_no_new:
                logger.warning(f"  No new URLs for {max_consecutive_no_new} consecutive scrolls, stopping...")
                break
        
        # Check if we've reached target
        if len(all_urls) >= target_count:
            logger.info(f"  ✓ Reached target of {target_count} URLs!")
            break
        
        # Try scrolling in smaller increments to trigger lazy loading
        if not new_content_loaded:
            logger.info("  Trying incremental scrolling...")
            for i in range(3):
                scroll_position = await page.evaluate('window.pageYOffset || window.scrollY')
                viewport_height = await page.evaluate('window.innerHeight')
                new_position = scroll_position + (viewport_height * 0.8)
                
                await page.evaluate(f'window.scrollTo(0, {new_position})')
                await page.wait_for_timeout(2000)
                
                # Check for new URLs
                current_urls = await extract_urls_from_page(page)
                new_urls = current_urls - all_urls
                if new_urls:
                    all_urls.update(new_urls)
                    logger.info(f"    Found {len(new_urls)} URLs with incremental scroll")
                    consecutive_no_new_urls = 0
                    break
        
        # Small delay between scroll attempts
        await page.wait_for_timeout(1000)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Extraction complete: {len(all_urls)} URLs found after {scroll_attempts} scroll attempts")
    logger.info(f"{'='*60}")
    
    return list(all_urls)[:target_count]


async def main():
    """Main execution"""
    search_url = "https://www.casemine.com/search/us/car%20accident?narrowing=settlement&sort=&judge=&courtType=0&published=&motionType=&motionOutcome=&year=&customYearFilter=false&tabName=filter"
    target_count = 500
    output_file = "all_500_case_urls_infinite_scroll.txt"
    
    logger.info("="*60)
    logger.info("Extract All 500 URLs - Infinite Scroll Method")
    logger.info("="*60)
    logger.info(f"Search URL: {search_url}")
    logger.info(f"Target: {target_count} URLs")
    logger.info("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        logger.info("Navigating to search results page...")
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(5000)
        
        # Extract all URLs with infinite scroll
        all_urls = await extract_all_500_infinite_scroll(page, target_count)
        
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
        logger.info("Run: python scrape-casemine.py --urls all_500_case_urls_infinite_scroll.txt --max-cases 500 --headless --output settlement_cases_500.json")
        logger.info("="*60)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
