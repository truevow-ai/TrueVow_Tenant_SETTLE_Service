"""
Aggressive extraction with network monitoring and multiple strategies
Monitors API calls, tries all possible interactions
"""
import asyncio
import json
import logging
import re
from typing import List, Set
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract-500-aggressive.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AggressiveExtractor:
    def __init__(self, page, target_count: int = 500):
        self.page = page
        self.target_count = target_count
        self.all_urls: Set[str] = set()
        self.api_urls: Set[str] = set()
        
    async def extract_urls_from_dom(self) -> Set[str]:
        """Extract URLs from DOM"""
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
        urls = await self.page.evaluate(js_code)
        return set(urls)
    
    async def monitor_network_requests(self):
        """Monitor network requests for case URLs"""
        async def handle_response(response):
            url = response.url
            # Check if this looks like a case data API
            if any(keyword in url.lower() for keyword in ['judgment', 'judgement', 'case', 'search', 'result', 'api']):
                try:
                    if 'application/json' in response.headers.get('content-type', ''):
                        data = await response.json()
                        # Extract URLs from JSON response
                        self._extract_urls_from_json(data, self.api_urls)
                except:
                    pass
        
        self.page.on('response', handle_response)
    
    def _extract_urls_from_json(self, data, url_set: Set[str]):
        """Recursively extract URLs from JSON"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['url', 'href', 'link', 'judgment_url', 'case_url'] and isinstance(value, str):
                    if '/judgment' in value.lower() or '/judgement' in value.lower():
                        full_url = value if value.startswith('http') else f"https://www.casemine.com{value}"
                        url_set.add(full_url)
                elif isinstance(value, (dict, list)):
                    self._extract_urls_from_json(value, url_set)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._extract_urls_from_json(item, url_set)
    
    async def try_all_interactions(self):
        """Try clicking all possible load more / pagination elements"""
        interaction_selectors = [
            # Load more buttons
            'button:has-text("Load More")',
            'button:has-text("Show More")',
            'button:has-text("More Results")',
            'a:has-text("Load More")',
            'a:has-text("Show More")',
            '[class*="load-more"]',
            '[class*="show-more"]',
            '[id*="load-more"]',
            '[id*="show-more"]',
            
            # Pagination
            'a:has-text("Next")',
            'a:has-text(">")',
            'button:has-text("Next")',
            '[aria-label*="next" i]',
            '[class*="next"]',
            '[class*="pagination"] a:last-child',
            
            # Infinite scroll triggers
            '[class*="infinite"]',
            '[class*="scroll"]',
            '[data-load-more]',
            '[data-next-page]',
        ]
        
        for selector in interaction_selectors:
            try:
                elements = await self.page.locator(selector).all()
                for elem in elements:
                    if await elem.is_visible():
                        try:
                            await elem.click()
                            await self.page.wait_for_timeout(3000)
                            logger.info(f"  Clicked: {selector}")
                            # Extract URLs after click
                            new_urls = await self.extract_urls_from_dom()
                            self.all_urls.update(new_urls)
                            if len(new_urls) > len(self.all_urls) - len(new_urls):
                                return True
                        except:
                            continue
            except:
                continue
        
        return False
    
    async def aggressive_scroll(self):
        """Very aggressive scrolling with multiple strategies"""
        viewport_height = await self.page.evaluate('window.innerHeight')
        document_height = await self.page.evaluate('document.body.scrollHeight')
        
        logger.info(f"Starting aggressive scroll: viewport={viewport_height}px, document={document_height}px")
        
        # Strategy 1: Smooth scroll to bottom
        await self.page.evaluate('window.scrollTo({top: document.body.scrollHeight, behavior: "smooth"})')
        await self.page.wait_for_timeout(5000)
        
        # Strategy 2: Jump scroll (faster)
        for i in range(10):
            position = (i + 1) * (document_height / 10)
            await self.page.evaluate(f'window.scrollTo(0, {position})')
            await self.page.wait_for_timeout(2000)
            
            # Extract after each jump
            new_urls = await self.extract_urls_from_dom()
            self.all_urls.update(new_urls)
            
            # Check if document grew
            new_height = await self.page.evaluate('document.body.scrollHeight')
            if new_height > document_height:
                document_height = new_height
                logger.info(f"  Document grew to {document_height}px")
        
        # Strategy 3: Scroll to absolute bottom multiple times
        for _ in range(5):
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await self.page.wait_for_timeout(3000)
            
            new_urls = await self.extract_urls_from_dom()
            self.all_urls.update(new_urls)
            
            new_height = await self.page.evaluate('document.body.scrollHeight')
            if new_height > document_height:
                document_height = new_height
            else:
                break
    
    async def extract_all(self) -> List[str]:
        """Main extraction method with all strategies"""
        logger.info(f"Starting aggressive extraction (target: {self.target_count} URLs)...")
        
        # Set up network monitoring
        await self.monitor_network_requests()
        
        # Initial load and wait
        await self.page.wait_for_load_state('networkidle', timeout=30000)
        await self.page.wait_for_timeout(10000)  # Long initial wait
        
        # Initial extraction
        initial_urls = await self.extract_urls_from_dom()
        self.all_urls.update(initial_urls)
        logger.info(f"Initial: {len(initial_urls)} URLs from DOM")
        
        # Combine with API URLs
        self.all_urls.update(self.api_urls)
        logger.info(f"Total after network monitoring: {len(self.all_urls)} URLs")
        
        # Try interactions
        logger.info("Trying all possible interactions...")
        interaction_success = await self.try_all_interactions()
        if interaction_success:
            logger.info("  Interactions successful, new URLs found")
        
        # Aggressive scrolling
        logger.info("Starting aggressive scrolling...")
        await self.aggressive_scroll()
        
        # Final extraction
        final_urls = await self.extract_urls_from_dom()
        self.all_urls.update(final_urls)
        self.all_urls.update(self.api_urls)
        
        logger.info(f"Final count: {len(self.all_urls)} URLs")
        
        return list(self.all_urls)[:self.target_count]


async def main():
    """Main execution"""
    search_url = "https://www.casemine.com/search/us/car%20accident?narrowing=settlement&sort=&judge=&courtType=0&published=&motionType=&motionOutcome=&year=&customYearFilter=false&tabName=filter"
    target_count = 500
    output_file = "all_500_case_urls_aggressive.txt"
    
    logger.info("="*60)
    logger.info("Aggressive Extraction - All 500 URLs")
    logger.info("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        logger.info("Navigating to search results...")
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
        
        extractor = AggressiveExtractor(page, target_count)
        all_urls = await extractor.extract_all()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in all_urls:
                f.write(f"{url}\n")
        
        logger.info(f"\nSaved {len(all_urls)} URLs to {output_file}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
