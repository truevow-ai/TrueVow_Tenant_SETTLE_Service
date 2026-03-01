"""
Enhanced Casemine.com Scraper with Anti-Blocking Strategies
Implements stealth mode, user agent rotation, smart delays, and retry logic
"""
import argparse
import asyncio
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlencode

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('casemine-stealth-scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StealthCasemineScraper:
    """Enhanced scraper with anti-blocking strategies"""
    
    # Rotating user agents
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    def __init__(self, max_cases: int = 50, headless: bool = True, output_file: str = None):
        self.max_cases = max_cases
        self.headless = headless
        self.collected_cases = []
        self.base_url = "https://www.casemine.com"
        self.output_file = output_file
        self.failed_urls = []
        self.retry_count = {}
        
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(self.USER_AGENTS)
    
    def get_random_delay(self, base: int = 20, variance: int = 15) -> int:
        """Get randomized delay in milliseconds"""
        return (base * 1000) + random.randint(0, variance * 1000)
    
    async def create_stealth_context(self, browser):
        """Create a browser context with stealth features"""
        user_agent = self.get_random_user_agent()
        
        # Random viewport sizes (common resolutions)
        viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
            {'width': 1280, 'height': 720},
        ]
        viewport = random.choice(viewports)
        
        context = await browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            locale='en-US',
            timezone_id='America/New_York',
            permissions=[],
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        )
        
        # Add stealth scripts to avoid detection
        await context.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override chrome
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        return context
    
    async def extract_case_details(self, page: Page, case_url: str, settlement_only: bool = True, retry: int = 0) -> Optional[Dict]:
        """Extract detailed case information with retry logic"""
        max_retries = 3
        
        try:
            # Navigate with timeout
            await page.goto(case_url, wait_until='domcontentloaded', timeout=45000)
            
            # Wait for page to stabilize
            await page.wait_for_load_state('networkidle', timeout=20000)
            await page.wait_for_timeout(random.randint(2000, 5000))  # Random wait
            
            # Check for blocking
            page_title = await page.title()
            page_url = page.url
            content = await page.content()
            
            # Check for 403, CAPTCHA, or blocking
            if '403' in page_title or 'forbidden' in page_title.lower() or '403' in content[:5000]:
                if retry < max_retries:
                    logger.warning(f"  403 detected, retrying ({retry + 1}/{max_retries})...")
                    await page.wait_for_timeout(self.get_random_delay(30, 20))
                    return await self.extract_case_details(page, case_url, settlement_only, retry + 1)
                else:
                    logger.error(f"  ✗ Blocked after {max_retries} retries: {case_url}")
                    self.failed_urls.append(case_url)
                    return None
            
            if 'captcha' in page_title.lower() or 'captcha' in page_url.lower() or 'captcha' in content[:10000].lower():
                logger.warning(f"  CAPTCHA detected, waiting longer...")
                await page.wait_for_timeout(self.get_random_delay(60, 30))
                if retry < max_retries:
                    return await self.extract_case_details(page, case_url, settlement_only, retry + 1)
            
            soup = BeautifulSoup(content, 'html.parser')
            full_text = soup.get_text().lower()
            
            case_data = {
                'source_url': case_url,
                'collected_at': datetime.now().isoformat(),
                'collector_notes': 'Scraped from Casemine.com (stealth mode)',
                'verification_status': 'pending'
            }
            
            # Settlement filtering
            if settlement_only:
                verdict_only_keywords = [
                    'jury verdict', 'verdict for', 'verdict against',
                    'awarded by jury', 'jury found', 'jury awarded'
                ]
                
                if any(keyword in full_text for keyword in verdict_only_keywords) and \
                   not any(keyword in full_text for keyword in ['settlement', 'settled']):
                    logger.info(f"  ✗ Skipping: Verdict-only case")
                    return None
            
            # Extract case name
            case_name = None
            title_elem = soup.find('title')
            if title_elem:
                case_name = title_elem.get_text().strip()
                if '|' in case_name:
                    case_name = case_name.split('|')[0].strip()
            
            if not case_name or len(case_name) < 3:
                h1 = soup.find('h1')
                if h1:
                    case_name = h1.get_text().strip()
            
            if not case_name or len(case_name) < 3:
                # Try to extract from URL or default
                case_name = f"Case from {case_url.split('/')[-1]}"
            
            case_data['case_name'] = case_name
            
            # Extract other fields (simplified for speed)
            # Court/Jurisdiction
            court_patterns = [
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Court|District|Circuit))',
                r'(Supreme Court of [A-Z][a-z]+)',
                r'([A-Z][a-z]+ County)',
            ]
            for pattern in court_patterns:
                match = re.search(pattern, soup.get_text())
                if match:
                    case_data['court'] = match.group(1)
                    break
            
            # Outcome type
            if 'settlement' in full_text or 'settled' in full_text:
                case_data['outcome_type'] = 'Settlement'
            elif 'verdict' in full_text:
                case_data['outcome_type'] = 'Jury Verdict'
            else:
                case_data['outcome_type'] = 'Settlement'  # Default for filtered results
            
            # Amount extraction (simplified)
            amount_patterns = [
                r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|M|thousand|K))?',
                r'(\d+)\s*(?:million|M)',
            ]
            for pattern in amount_patterns:
                matches = re.findall(pattern, soup.get_text(), re.IGNORECASE)
                if matches:
                    case_data['extracted_amount'] = matches[0]
                    break
            
            # Set default ranges if not found
            if 'outcome_amount_range' not in case_data:
                case_data['outcome_amount_range'] = '$0-$50k'
            
            if 'jurisdiction' not in case_data:
                case_data['jurisdiction'] = 'Unknown'
            
            if 'case_type' not in case_data:
                case_data['case_type'] = 'Personal Injury'
            
            logger.info(f"  ✓ Extracted: {case_name[:60]}")
            return case_data
            
        except PlaywrightTimeoutError:
            if retry < max_retries:
                logger.warning(f"  Timeout, retrying ({retry + 1}/{max_retries})...")
                await page.wait_for_timeout(self.get_random_delay(20, 10))
                return await self.extract_case_details(page, case_url, settlement_only, retry + 1)
            else:
                logger.error(f"  ✗ Timeout after {max_retries} retries: {case_url}")
                self.failed_urls.append(case_url)
                return None
        except Exception as e:
            logger.error(f"  ✗ Error extracting {case_url}: {str(e)}")
            if retry < max_retries:
                await page.wait_for_timeout(self.get_random_delay(15, 10))
                return await self.extract_case_details(page, case_url, settlement_only, retry + 1)
            else:
                self.failed_urls.append(case_url)
                return None
    
    async def scrape_from_urls(self, case_urls: List[str], settlement_only: bool = True) -> List[Dict]:
        """Extract case details with enhanced anti-blocking"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            
            context = await self.create_stealth_context(browser)
            page = await context.new_page()
            
            all_cases = []
            skipped_count = 0
            blocked_count = 0
            
            logger.info(f"\n{'='*70}")
            logger.info(f"🚀 STEALTH MODE: Extracting from {len(case_urls)} case URLs")
            logger.info(f"   Anti-blocking: Enabled")
            logger.info(f"   Settlement filter: {'ON' if settlement_only else 'OFF'}")
            logger.info(f"{'='*70}\n")
            
            for i, case_url in enumerate(case_urls, 1):
                logger.info(f"\n[{i}/{len(case_urls)}] Processing case...")
                
                case_data = await self.extract_case_details(page, case_url, settlement_only=settlement_only)
                
                if case_data:
                    all_cases.append(case_data)
                    current_count = len(all_cases)
                    case_name = case_data.get('case_name', 'Unknown')
                    
                    logger.info(f"✅ SUCCESS! Case #{current_count} collected: {case_name}")
                    print(f"\n{'='*70}")
                    print(f"✅ CASE #{current_count} SUCCESSFULLY SCRAPED")
                    print(f"   Case Name: {case_name[:80]}")
                    print(f"   Progress: {current_count} cases collected | {i}/{len(case_urls)} processed")
                    print(f"{'='*70}\n")
                    
                    # Incremental save every 10 cases
                    if current_count % 10 == 0 and self.output_file:
                        try:
                            with open(self.output_file, 'w', encoding='utf-8') as f:
                                json.dump(all_cases, f, indent=2, ensure_ascii=False)
                            logger.info(f"💾 Checkpoint: Saved {current_count} cases")
                        except Exception as e:
                            logger.warning(f"Could not save checkpoint: {e}")
                else:
                    skipped_count += 1
                    if '403' in str(case_url) or case_url in self.failed_urls:
                        blocked_count += 1
                    if settlement_only:
                        logger.info(f"  (Skipped)")
                
                # Smart delay strategy
                if i % 5 == 0:
                    # Every 5 cases: longer break
                    delay = self.get_random_delay(45, 25)  # 45-70 seconds
                    logger.info(f"⏸️  Extended break: {delay/1000:.1f} seconds...")
                    print(f"⏸️  Extended break ({delay/1000:.1f}s) - {len(all_cases)} cases collected so far...")
                elif i % 10 == 0:
                    # Every 10 cases: very long break + context refresh
                    delay = self.get_random_delay(90, 30)  # 90-120 seconds
                    logger.info(f"🔄 Long break + context refresh: {delay/1000:.1f} seconds...")
                    await page.close()
                    await context.close()
                    context = await self.create_stealth_context(browser)
                    page = await context.new_page()
                else:
                    # Normal delay
                    delay = self.get_random_delay(25, 15)  # 25-40 seconds
                
                await page.wait_for_timeout(delay)
                
                # Stop if we hit max cases
                if len(all_cases) >= self.max_cases:
                    logger.info(f"Reached max cases limit: {self.max_cases}")
                    break
            
            await browser.close()
            
            logger.info(f"\n{'='*70}")
            logger.info(f"📊 EXTRACTION SUMMARY")
            logger.info(f"   Total URLs processed: {len(case_urls)}")
            logger.info(f"   Cases collected: {len(all_cases)}")
            logger.info(f"   Cases skipped: {skipped_count}")
            logger.info(f"   Blocked/Failed: {blocked_count}")
            logger.info(f"{'='*70}")
            
            if self.failed_urls:
                logger.warning(f"\n⚠️  {len(self.failed_urls)} URLs failed (saved to failed_urls.txt)")
                with open('failed_urls.txt', 'w', encoding='utf-8') as f:
                    for url in self.failed_urls:
                        f.write(f"{url}\n")
            
            return all_cases


async def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Stealth Casemine.com Scraper')
    parser.add_argument('--urls', required=True, help='File containing case URLs (one per line)')
    parser.add_argument('--max-cases', type=int, default=500, help='Maximum number of cases to collect')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser in headless mode')
    parser.add_argument('--no-headless', action='store_false', dest='headless', help='Show browser window')
    parser.add_argument('--output', default='settlement_cases_stealth.json', help='Output JSON file')
    
    args = parser.parse_args()
    
    scraper = StealthCasemineScraper(max_cases=args.max_cases, headless=args.headless, output_file=args.output)
    
    logger.info("="*70)
    logger.info("🚀 STEALTH CASEMINE SCRAPER")
    logger.info("   Anti-blocking strategies: ENABLED")
    logger.info("="*70)
    
    # Read URLs
    if os.path.isfile(args.urls):
        with open(args.urls, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    else:
        urls = [url.strip() for url in args.urls.split(',') if url.strip()]
    
    logger.info(f"Found {len(urls)} URLs to process")
    logger.info(f"Max cases: {args.max_cases}")
    logger.info(f"Output file: {args.output}")
    logger.info("="*70)
    
    # Process with stealth mode
    cases = await scraper.scrape_from_urls(urls[:args.max_cases], settlement_only=True)
    
    # Save final results
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    
    logger.info("\n" + "="*70)
    logger.info("✅ SCRAPING COMPLETE!")
    logger.info("="*70)
    logger.info(f"Total cases collected: {len(cases)}")
    logger.info(f"Saved to: {args.output}")
    logger.info("\nNext steps:")
    logger.info("1. Review collected cases in the JSON file")
    logger.info("2. Verify cases manually if needed")
    logger.info("3. Prepare for database seeding")


if __name__ == "__main__":
    asyncio.run(main())
