"""
Stealth URL extraction from Casemine search results
Uses anti-blocking strategies to extract all case URLs
"""
import asyncio
import json
import logging
import random
from typing import List, Set
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract-urls-stealth.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]


async def create_stealth_context(browser):
    """Create stealth browser context"""
    user_agent = random.choice(USER_AGENTS)
    viewport = random.choice([
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1536, 'height': 864},
    ])
    
    context = await browser.new_context(
        user_agent=user_agent,
        viewport=viewport,
        extra_http_headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'DNT': '1',
        }
    )
    
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
    """)
    
    return context


async def extract_urls_stealth(search_url: str, target_count: int = 500) -> List[str]:
    """Extract URLs using stealth mode"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await create_stealth_context(browser)
        page = await context.new_page()
        
        logger.info(f"Loading search page: {search_url}")
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=30000)
        await page.wait_for_timeout(5000)
        
        all_urls: Set[str] = set()
        
        # Extract initial URLs
        js_code = """
        () => {
            const urls = new Set();
            const baseUrl = 'https://www.casemine.com';
            
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
            
            return Array.from(urls);
        }
        """
        
        # Initial extraction
        initial_urls = await page.evaluate(js_code)
        all_urls.update(initial_urls)
        logger.info(f"Initial URLs found: {len(initial_urls)}")
        
        # Aggressive scrolling with delays
        logger.info("Scrolling to load more content...")
        for i in range(20):  # More scroll attempts
            await page.evaluate(f'window.scrollTo(0, {i * 500})')
            await page.wait_for_timeout(1000 + random.randint(0, 1000))
            
            # Extract after each scroll
            new_urls = await page.evaluate(js_code)
            all_urls.update(new_urls)
            
            if len(all_urls) >= target_count:
                logger.info(f"Target reached: {len(all_urls)} URLs")
                break
        
        # Final scroll to bottom
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(5000)
        final_urls = await page.evaluate(js_code)
        all_urls.update(final_urls)
        
        await browser.close()
        
        unique_urls = list(all_urls)[:target_count]
        logger.info(f"Total unique URLs extracted: {len(unique_urls)}")
        
        return unique_urls


async def main():
    """Main execution"""
    search_url = "https://www.casemine.com/search/us/car%20accident?narrowing=settlement&sort=&judge=&courtType=0&published=&motionType=&motionOutcome=&year=&customYearFilter=false&tabName=filter"
    target_count = 500
    output_file = "all_500_case_urls_stealth.txt"
    
    logger.info("="*70)
    logger.info("🚀 STEALTH URL EXTRACTION")
    logger.info("="*70)
    
    urls = await extract_urls_stealth(search_url, target_count)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(f"{url}\n")
    
    logger.info(f"\n✅ Saved {len(urls)} URLs to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
