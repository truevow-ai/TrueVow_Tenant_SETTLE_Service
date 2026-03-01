"""
Simple script to extract case URLs from Casemine search results
"""
import asyncio
import json
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def extract_case_urls(search_url: str, max_urls: int = 50) -> list:
    """Extract case URLs from Casemine search results page"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        logger.info(f"Loading: {search_url}")
        await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_load_state('networkidle', timeout=20000)
        await page.wait_for_timeout(5000)
        
        # Scroll to load content
        for i in range(3):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(1000)
        
        # Extract URLs
        js_code = """
        () => {
            const urls = [];
            const baseUrl = 'https://www.casemine.com';
            const seen = new Set();
            
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
        await browser.close()
        
        logger.info(f"Found {len(urls)} case URLs")
        return urls[:max_urls]


async def main():
    search_url = "https://www.casemine.com/search/us/car%20accident"
    output_file = "extracted_case_urls.txt"
    
    logger.info("Extracting case URLs from search results...")
    urls = await extract_case_urls(search_url, max_urls=50)
    
    if urls:
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(f"{url}\n")
        logger.info(f"Saved {len(urls)} URLs to {output_file}")
        
        # Also save as JSON for easy reading
        with open("extracted_case_urls.json", 'w', encoding='utf-8') as f:
            json.dump(urls, f, indent=2)
        
        logger.info("\nExtracted URLs:")
        for i, url in enumerate(urls, 1):
            logger.info(f"  {i}. {url}")
    else:
        logger.warning("No URLs found")


if __name__ == "__main__":
    asyncio.run(main())
