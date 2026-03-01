"""
Extract all 500 URLs using very slow, deliberate scrolling
Waits longer for content and checks DOM more carefully
"""
import asyncio
import json
import logging
from typing import List, Set
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract-500-slow-scroll.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def extract_all_urls_comprehensive(page) -> Set[str]:
    """Comprehensive URL extraction from all possible sources"""
    js_code = """
    () => {
        const urls = new Set();
        const baseUrl = 'https://www.casemine.com';
        
        // Method 1: All links
        document.querySelectorAll('a[href]').forEach(link => {
            const href = link.getAttribute('href');
            if (!href) return;
            const fullUrl = href.startsWith('http') ? href : baseUrl + href;
            if (fullUrl.includes('casemine.com') && 
                (fullUrl.includes('/judgment/') || fullUrl.includes('/judgements/') || fullUrl.includes('/judgement/')) &&
                !fullUrl.includes('/search') && !fullUrl.includes('/login') && !fullUrl.includes('/signup')) {
                urls.add(fullUrl);
            }
        });
        
        // Method 2: Data attributes
        document.querySelectorAll('[data-url], [data-href], [data-case-url]').forEach(el => {
            const url = el.getAttribute('data-url') || el.getAttribute('data-href') || el.getAttribute('data-case-url');
            if (url && url.includes('judgment')) {
                const fullUrl = url.startsWith('http') ? url : baseUrl + url;
                urls.add(fullUrl);
            }
        });
        
        // Method 3: Result containers
        document.querySelectorAll('[class*="result"], [class*="case"], [class*="judgment"], article').forEach(container => {
            const links = container.querySelectorAll('a[href]');
            links.forEach(link => {
                const href = link.getAttribute('href');
                if (href && (href.includes('/judgment/') || href.includes('/judgements/'))) {
                    const fullUrl = href.startsWith('http') ? href : baseUrl + href;
                    urls.add(fullUrl);
                }
            });
        });
        
        return Array.from(urls);
    }
    """
    urls = await page.evaluate(js_code)
    return set(urls)


async def slow_scroll_extraction(page, target_count: int = 500) -> List[str]:
    """Very slow, deliberate scrolling with comprehensive extraction"""
    logger.info(f"Starting slow scroll extraction (target: {target_count} URLs)...")
    
    all_urls: Set[str] = set()
    scroll_position = 0
    max_scrolls = 500
    no_new_url_count = 0
    max_no_new = 10
    
    # Initial extraction
    await page.wait_for_load_state('networkidle', timeout=30000)
    await page.wait_for_timeout(5000)
    
    initial_urls = await extract_all_urls_comprehensive(page)
    all_urls.update(initial_urls)
    logger.info(f"Initial: {len(initial_urls)} URLs found")
    
    viewport_height = await page.evaluate('window.innerHeight')
    document_height = await page.evaluate('document.body.scrollHeight')
    
    logger.info(f"Viewport: {viewport_height}px, Document: {document_height}px")
    
    scroll_step = viewport_height * 0.5  # Scroll 50% of viewport at a time
    
    while len(all_urls) < target_count and scroll_position < document_height and no_new_url_count < max_no_new:
        # Scroll slowly
        scroll_position += scroll_step
        await page.evaluate(f'window.scrollTo({{top: {scroll_position}, behavior: "smooth"}})')
        
        # Wait for content to load (longer wait)
        await page.wait_for_timeout(4000)  # 4 second wait
        
        # Check if page height increased (new content loaded)
        new_document_height = await page.evaluate('document.body.scrollHeight')
        if new_document_height > document_height:
            logger.info(f"  New content detected: {document_height}px → {new_document_height}px")
            document_height = new_document_height
            # Wait extra time for new content to fully load
            await page.wait_for_timeout(3000)
        
        # Extract URLs
        current_urls = await extract_all_urls_comprehensive(page)
        new_urls = current_urls - all_urls
        
        if new_urls:
            all_urls.update(new_urls)
            logger.info(f"  Scroll {int(scroll_position/scroll_step)}: Found {len(new_urls)} new URLs (total: {len(all_urls)})")
            no_new_url_count = 0
        else:
            no_new_url_count += 1
            if no_new_url_count % 3 == 0:
                logger.info(f"  No new URLs for {no_new_url_count} scrolls...")
        
        # Update document height
        document_height = await page.evaluate('document.body.scrollHeight')
        
        # Check if we've reached the bottom
        if scroll_position >= document_height - viewport_height:
            logger.info("  Reached bottom of page")
            # Try scrolling to absolute bottom
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(5000)
            
            # Final extraction
            final_urls = await extract_all_urls_comprehensive(page)
            all_urls.update(final_urls)
            
            if len(final_urls - all_urls) == 0:
                no_new_url_count += 1
            else:
                no_new_url_count = 0
    
    logger.info(f"\nExtraction complete: {len(all_urls)} URLs found")
    return list(all_urls)[:target_count]


async def main():
    """Main execution"""
    search_url = "https://www.casemine.com/search/us/car%20accident?narrowing=settlement&sort=&judge=&courtType=0&published=&motionType=&motionOutcome=&year=&customYearFilter=false&tabName=filter"
    target_count = 500
    output_file = "all_500_case_urls_slow_scroll.txt"
    
    logger.info("="*60)
    logger.info("Slow Scroll Extraction - All 500 URLs")
    logger.info("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Non-headless to see what's happening
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        logger.info("Navigating to search results...")
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(10000)  # Extra long initial wait
        
        all_urls = await slow_scroll_extraction(page, target_count)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in all_urls:
                f.write(f"{url}\n")
        
        logger.info(f"\nSaved {len(all_urls)} URLs to {output_file}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
