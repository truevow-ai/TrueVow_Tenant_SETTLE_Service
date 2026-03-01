"""
Extract all 500 case URLs from Casemine with proper pagination handling
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
        logging.FileHandler('extract-500-paginated.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def extract_urls_from_current_page(page) -> Set[str]:
    """Extract all case URLs from the current page"""
    js_code = """
    () => {
        const urls = [];
        const baseUrl = 'https://www.casemine.com';
        const seen = new Set();
        
        // Extract all judgment/case links
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


async def find_and_click_next_page(page) -> bool:
    """Find and click the next page button, return True if successful"""
    next_selectors = [
        'a:has-text("Next")',
        'a:has-text(">")',
        'button:has-text("Next")',
        '[aria-label*="next" i]',
        '[aria-label*="Next" i]',
        '.pagination a:last-child',
        '[class*="next"]',
        '[class*="pagination"] a:has-text("Next")',
        'a[href*="page"]:has-text("Next")',
        'a[href*="page"]:has-text(">")'
    ]
    
    for selector in next_selectors:
        try:
            elem = page.locator(selector).first
            if await elem.count() > 0:
                is_visible = await elem.is_visible()
                is_enabled = await elem.is_enabled()
                if is_visible and is_enabled:
                    # Check if it's actually a "next" button (not disabled)
                    text = await elem.inner_text()
                    if 'next' in text.lower() or '>' in text or '»' in text:
                        await elem.click()
                        await page.wait_for_timeout(5000)  # Wait for page load
                        logger.info(f"  Clicked next page button: {selector}")
                        return True
        except Exception as e:
            logger.debug(f"  Error with selector {selector}: {e}")
            continue
    
    return False


async def extract_all_500_urls_paginated(page, target_count: int = 500) -> List[str]:
    """Extract all URLs by handling pagination"""
    logger.info(f"Extracting {target_count} URLs with pagination handling...")
    
    all_urls: Set[str] = set()
    page_num = 1
    max_pages = 50  # Safety limit
    consecutive_no_new_urls = 0
    
    while len(all_urls) < target_count and page_num <= max_pages:
        logger.info(f"\n--- Page {page_num} ---")
        
        # Wait for page to load
        await page.wait_for_load_state('networkidle', timeout=20000)
        await page.wait_for_timeout(3000)
        
        # Scroll to trigger lazy loading
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(2000)
        await page.evaluate('window.scrollTo(0, 0)')
        await page.wait_for_timeout(1000)
        
        # Extract URLs from current page
        page_urls = await extract_urls_from_current_page(page)
        new_urls = page_urls - all_urls
        
        if new_urls:
            all_urls.update(new_urls)
            logger.info(f"  Found {len(new_urls)} new URLs (total: {len(all_urls)})")
            consecutive_no_new_urls = 0
        else:
            consecutive_no_new_urls += 1
            logger.warning(f"  No new URLs found on page {page_num}")
            if consecutive_no_new_urls >= 2:
                logger.warning("  No new URLs for 2 consecutive pages, stopping...")
                break
        
        # Check if we've reached target
        if len(all_urls) >= target_count:
            logger.info(f"  Reached target of {target_count} URLs!")
            break
        
        # Try to go to next page
        logger.info(f"  Attempting to navigate to next page...")
        next_clicked = await find_and_click_next_page(page)
        
        if not next_clicked:
            # Try alternative: modify URL with page parameter
            current_url = page.url
            if 'page=' in current_url:
                # Extract current page number and increment
                import re
                match = re.search(r'page=(\d+)', current_url)
                if match:
                    current_page = int(match.group(1))
                    next_page = current_page + 1
                    new_url = re.sub(r'page=\d+', f'page={next_page}', current_url)
                else:
                    new_url = current_url + ('&' if '?' in current_url else '?') + f'page={page_num + 1}'
            else:
                new_url = current_url + ('&' if '?' in current_url else '?') + f'page={page_num + 1}'
            
            logger.info(f"  Trying direct URL navigation: {new_url}")
            try:
                await page.goto(new_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_load_state('networkidle', timeout=20000)
                await page.wait_for_timeout(3000)
                page_num += 1
                continue
            except:
                logger.warning("  Direct URL navigation failed, no more pages available")
                break
        
        page_num += 1
        
        # Rate limiting between pages
        await page.wait_for_timeout(3000)
    
    logger.info(f"\nExtraction complete: {len(all_urls)} URLs found across {page_num} pages")
    return list(all_urls)[:target_count]


async def main():
    """Main execution"""
    search_url = "https://www.casemine.com/search/us/car%20accident?narrowing=settlement&sort=&judge=&courtType=0&published=&motionType=&motionOutcome=&year=&customYearFilter=false&tabName=filter"
    target_count = 500
    output_file = "all_500_case_urls_paginated.txt"
    
    logger.info("="*60)
    logger.info("Extract All 500 URLs with Pagination")
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
        
        logger.info("Navigating to search results page...")
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(5000)
        
        # Extract all URLs with pagination
        all_urls = await extract_all_500_urls_paginated(page, target_count)
        
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
        logger.info("Run: python scrape-casemine.py --urls all_500_case_urls_paginated.txt --max-cases 500 --headless --output settlement_cases_500.json")
        logger.info("="*60)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
