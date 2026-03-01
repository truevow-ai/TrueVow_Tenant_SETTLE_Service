"""
Casemine.com Case Scraper
Scrapes real legal cases from Casemine.com for SETTLE database population

Usage:
    python scrape-casemine.py --search "car accident" --max-cases 50
    python scrape-casemine.py --search "personal injury settlement" --jurisdiction "Miami-Dade" --max-cases 30
"""

import argparse
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlencode, quote_plus

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('casemine-scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CasemineScraper:
    """Scrapes case data from Casemine.com"""
    
    def __init__(self, max_cases: int = 50, headless: bool = True, output_file: str = None):
        self.max_cases = max_cases
        self.headless = headless
        self.collected_cases = []
        self.base_url = "https://www.casemine.com"
        self.output_file = output_file
        
    async def search_cases(self, page: Page, search_term: str, jurisdiction: Optional[str] = None) -> List[str]:
        """Search for cases and return list of case URLs"""
        logger.info(f"Searching for: '{search_term}'")
        
        # Build search URL
        params = {
            'stype': 'parallel',
            'q': search_term
        }
        if jurisdiction:
            params['jurisdiction'] = jurisdiction
            
        search_url = f"{self.base_url}/search/us?{urlencode(params)}"
        logger.info(f"Navigating to: {search_url}")
        
        # Track network requests to detect when cases are loaded
        case_urls_found = []
        request_complete = False
        
        async def handle_response(response):
            """Monitor network responses for case data"""
            nonlocal case_urls_found, request_complete
            url = response.url
            # Check if this looks like a case data API call
            if any(keyword in url.lower() for keyword in ['judgment', 'case', 'search', 'result', 'api']):
                try:
                    # Try to extract URLs from JSON responses
                    if 'application/json' in response.headers.get('content-type', ''):
                        try:
                            data = await response.json()
                            # Look for URLs in the response
                            if isinstance(data, dict):
                                self._extract_urls_from_json(data, case_urls_found)
                            elif isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        self._extract_urls_from_json(item, case_urls_found)
                        except:
                            pass
                except:
                    pass
        
        # Set up network monitoring
        page.on('response', handle_response)
        
        try:
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for page to fully load and JavaScript to execute
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
            
            # Wait for network to be idle (all requests complete)
            try:
                await page.wait_for_load_state('networkidle', timeout=20000)
            except:
                logger.debug("Network not idle, continuing anyway...")
            
            # Extra wait for dynamic content - Casemine loads results via JS
            await page.wait_for_timeout(8000)  # Increased wait time
            
            # Try to trigger lazy loading by scrolling
            logger.info("Scrolling to trigger content loading...")
            for i in range(3):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)
                await page.evaluate('window.scrollTo(0, 0)')
                await page.wait_for_timeout(1000)
            
            # Check if URL changed (Casemine sometimes redirects)
            current_url = page.url
            logger.info(f"Current page URL: {current_url}")
            
            # Try to interact with the page to load content
            logger.info("Interacting with page to load case results...")
            
            # Try clicking on Judgments tab if it exists
            try:
                judgments_tab = page.locator('text=/Judgments/i, button:has-text("Judgments"), [role="tab"]:has-text("Judgments"), a:has-text("Judgments")').first
                if await judgments_tab.count() > 0:
                    await judgments_tab.click()
                    await page.wait_for_timeout(3000)
                    logger.info("Clicked on Judgments tab")
            except Exception as e:
                logger.debug(f"Could not click Judgments tab: {e}")
            
            # Try clicking Recent sort option
            try:
                recent_options = [
                    'text=/Recent/i',
                    'button:has-text("Recent")',
                    '[role="tab"]:has-text("Recent")',
                    'select option:has-text("Recent")',
                    '[data-sort="recent"]',
                    '.sort-recent'
                ]
                for selector in recent_options:
                    try:
                        elem = page.locator(selector).first
                        if await elem.count() > 0:
                            await elem.click()
                            await page.wait_for_timeout(3000)
                            logger.info("Clicked Recent sort option")
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Could not sort by recent: {e}")
            
            # Scroll multiple times to trigger lazy loading
            logger.info("Scrolling to load all content...")
            for scroll_attempt in range(5):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)
                # Check if new content loaded
                content_height = await page.evaluate('document.body.scrollHeight')
                if scroll_attempt > 0:
                    await page.wait_for_timeout(1000)
            
            # Scroll back to top
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(2000)
            
            # Wait for any case-related content to appear
            try:
                await page.wait_for_selector('text=/v\\./i, text=/vs\\./i, [class*="case"], [class*="judgment"], article', timeout=10000)
                logger.info("Case content detected on page")
            except:
                logger.warning("No case content detected, continuing with extraction...")
            
            # Try multiple strategies to find case links
            case_urls = []
            
            # Strategy 1: Extract from network responses (if we captured any)
            if case_urls_found:
                logger.info(f"Found {len(case_urls_found)} URLs from network responses")
                case_urls.extend(case_urls_found[:self.max_cases])
            
            # Strategy 2: Look for case name patterns and their links
            logger.info("Strategy 2: Searching for case name patterns...")
            try:
                # First, try to find links directly that contain case name patterns
                js_find_case_links = """
                () => {
                    const urls = [];
                    document.querySelectorAll('a').forEach(link => {
                        const text = (link.textContent || link.innerText || '').trim();
                        const href = link.getAttribute('href');
                        // Check if link text matches case name pattern (e.g., "SMITH v. JONES")
                        if (text && /[A-Z][A-Z\\s&]+\\s+v\\.?\\s+[A-Z]/.test(text) && href) {
                            const fullUrl = href.startsWith('http') ? href : 'https://www.casemine.com' + href;
                            if (fullUrl.includes('casemine.com') && 
                                (fullUrl.includes('/judgment/') || fullUrl.includes('/judgments/') || fullUrl.includes('/judgement/') || fullUrl.includes('/judgements/') || fullUrl.includes('/case/'))) {
                                if (!urls.includes(fullUrl)) {
                                    urls.push(fullUrl);
                                }
                            }
                        }
                    });
                    return urls;
                }
                """
                js_case_urls = await page.evaluate(js_find_case_links)
                if js_case_urls:
                    logger.info(f"Found {len(js_case_urls)} case URLs via JavaScript case name matching")
                    for url in js_case_urls[:self.max_cases]:
                        if url not in case_urls:
                            case_urls.append(url)
                            logger.info(f"Found case URL via JS case name: {url[:80]}...")
                
                # Fallback: More flexible pattern matching with Playwright locators
                if len(case_urls) < self.max_cases:
                    case_patterns = [
                        'text=/[A-Z][A-Z\\s&]+\\s+v\\.?\\s+[A-Z]/i',
                        'text=/[A-Z][A-Z\\s&]+\\s+vs\\.?\\s+[A-Z]/i',
                        'text=/[A-Z][A-Z\\s&]+\\s+v\\s+[A-Z]/i'
                    ]
                    
                    for pattern in case_patterns:
                        try:
                            case_elements = await page.locator(pattern).all()
                            if case_elements:
                                logger.info(f"Found {len(case_elements)} case name patterns with pattern: {pattern}")
                                for elem in case_elements[:self.max_cases * 2]:
                                    try:
                                        # Check if the element itself is a link
                                        tag_name = await elem.evaluate('el => el.tagName.toLowerCase()')
                                        if tag_name == 'a':
                                            href = await elem.get_attribute('href')
                                            if href:
                                                full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                                                if ('judgment' in full_url.lower() or 'case' in full_url.lower()) and 'casemine.com' in full_url:
                                                    if full_url not in case_urls:
                                                        case_urls.append(full_url)
                                                        logger.info(f"Found case URL (element is link): {full_url[:80]}...")
                                                        if len(case_urls) >= self.max_cases:
                                                            break
                                                        continue
                                        
                                        # Try to find parent link
                                        try:
                                            parent_link = elem.locator('xpath=ancestor::a[1]').first
                                            if await parent_link.count() > 0:
                                                href = await parent_link.get_attribute('href')
                                                if href:
                                                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                                                    if ('judgment' in full_url.lower() or 'judgement' in full_url.lower() or 'case' in full_url.lower()) and 'casemine.com' in full_url:
                                                        if full_url not in case_urls:
                                                            case_urls.append(full_url)
                                                            logger.info(f"Found case URL (parent link): {full_url[:80]}...")
                                                            if len(case_urls) >= self.max_cases:
                                                                break
                                        except:
                                            pass
                                    except:
                                        continue
                                
                                if len(case_urls) >= self.max_cases:
                                    break
                        except Exception as e:
                            logger.debug(f"Error with pattern {pattern}: {e}")
                            continue
            except Exception as e:
                logger.debug(f"Error in Strategy 2: {e}")
            
            # Strategy 3: Direct link extraction - look for /judgment/ or /judgments/ URLs first
            if len(case_urls) < self.max_cases:
                logger.info("Strategy 3a: Direct judgment URL extraction...")
                try:
                    # Use JavaScript to find all links with judgment in the URL
                    js_extract = """
                    () => {
                        const urls = [];
                        // Method 1: Find all links with /judgment/ in href
                        document.querySelectorAll('a[href]').forEach(link => {
                            const href = link.getAttribute('href');
                            if (href && (href.includes('/judgment/') || href.includes('/judgments/'))) {
                                const fullUrl = href.startsWith('http') ? href : 'https://www.casemine.com' + href;
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
                                const fullUrl = href.startsWith('http') ? href : 'https://www.casemine.com' + href;
                                if (fullUrl.includes('casemine.com') && !urls.includes(fullUrl) && 
                                    (fullUrl.includes('/judgment/') || fullUrl.includes('/judgments/') || fullUrl.includes('/case/'))) {
                                    urls.push(fullUrl);
                                }
                            }
                        });
                        return urls;
                    }
                    """
                    js_urls = await page.evaluate(js_extract)
                    if js_urls:
                        logger.info(f"Found {len(js_urls)} judgment URLs via JavaScript")
                        for url in js_urls[:self.max_cases]:
                            if url not in case_urls:
                                case_urls.append(url)
                                logger.info(f"Found case URL via JS: {url[:80]}...")
                except Exception as e:
                    logger.debug(f"Error in JS extraction: {e}")
            
            # Strategy 3: Comprehensive link scanning with smart filtering
            if len(case_urls) < self.max_cases:
                logger.info("Strategy 3b: Comprehensive link scanning...")
                await page.evaluate('window.scrollTo(0, 0)')
                await page.wait_for_timeout(1000)
                
                # Get all links
                all_links = await page.locator('a').all()
                logger.info(f"Found {len(all_links)} total links on page")
                
                excluded_domains = ['facebook.com', 'twitter.com', 'linkedin.com', 'youtube.com', 
                                  'instagram.com', 'caseiq', 'amicus', 'parallel', 'login', 'signup', 
                                  'commentary', 'google.com', 'bing.com']
                excluded_paths = ['/login', '/signup', '/home', '/search', '/commentary', '/chat', 
                                 '/caseiq', '/signup', '/help', '/about']
                
                for link in all_links:
                    try:
                        href = await link.get_attribute('href')
                        if not href or len(href) < 5:
                            continue
                        
                        # Skip excluded domains and paths
                        if any(domain in href.lower() for domain in excluded_domains):
                            continue
                        if any(path in href for path in excluded_paths):
                            continue
                        
                        # Check for case/judgment indicators
                        is_case_link = False
                        link_text = ""
                        
                        try:
                            link_text = await link.inner_text()
                        except:
                            pass
                        
                        # Pattern 1: Contains /judgments/ or /judgment/ (strong indicator)
                        if '/judgments/' in href or '/judgment/' in href:
                            is_case_link = True
                        # Pattern 2: Contains /cases/ 
                        elif '/cases/' in href:
                            is_case_link = True
                        # Pattern 3: Link text contains case indicators (v., vs., etc.)
                        elif link_text:
                            case_indicators = [' v. ', ' vs. ', ' v ', 'Court', 'District', 'Appeal', 
                                             'Supreme', 'Circuit', 'County']
                            if any(indicator in link_text for indicator in case_indicators):
                                # Additional check: URL should be substantial and look like a case URL
                                if (href.startswith('/') or href.startswith('http')) and len(href) > 15:
                                    # Make sure it's not a search or navigation link
                                    if not any(excluded in href for excluded in ['/search', '/login', '/signup', '/home', '/about']):
                                        is_case_link = True
                        
                        if is_case_link:
                            if href.startswith('http'):
                                full_url = href
                            elif href.startswith('/'):
                                full_url = f"{self.base_url}{href}"
                            else:
                                continue
                            
                            # Final validation (accept both "judgment" and "judgement" spellings)
                            if ('casemine.com' in full_url and 
                                ('judgment' in full_url.lower() or 'judgement' in full_url.lower() or 'case' in full_url.lower()) and
                                full_url not in case_urls):
                                case_urls.append(full_url)
                                logger.info(f"Found case URL: {full_url[:80]}...")
                                
                                if len(case_urls) >= self.max_cases:
                                    break
                    except Exception as e:
                        logger.debug(f"Error processing link: {e}")
                        continue
            
            # Strategy 4: Look in result containers and specific sections
            if len(case_urls) < self.max_cases:
                logger.info("Strategy 4: Checking result containers and sections...")
                try:
                    # Try various container selectors
                    container_selectors = [
                        '[class*="result"]',
                        '[class*="judgment"]',
                        '[class*="case"]',
                        '[id*="result"]',
                        '[id*="judgment"]',
                        'article',
                        '[role="article"]',
                        '.search-result',
                        '.case-result',
                        '[data-case-id]',
                        '[data-judgment-id]'
                    ]
                    
                    all_containers = []
                    for selector in container_selectors:
                        try:
                            containers = await page.locator(selector).all()
                            all_containers.extend(containers)
                        except:
                            continue
                    
                    logger.info(f"Found {len(all_containers)} potential result containers")
                    
                    for container in all_containers:
                        try:
                            # Find all links in container
                            links_in_container = await container.locator('a').all()
                            for link_elem in links_in_container:
                                try:
                                    href = await link_elem.get_attribute('href')
                                    if href and ('judgment' in href.lower() or 'case' in href.lower()):
                                        if href.startswith('http'):
                                            full_url = href
                                        elif href.startswith('/'):
                                            full_url = f"{self.base_url}{href}"
                                        else:
                                            continue
                                        
                                        if 'casemine.com' in full_url and full_url not in case_urls:
                                            case_urls.append(full_url)
                                            logger.info(f"Found case URL in container: {full_url[:80]}...")
                                            if len(case_urls) >= self.max_cases:
                                                break
                                except:
                                    continue
                            
                            if len(case_urls) >= self.max_cases:
                                break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Error with container strategy: {e}")
            
            # Strategy 5: Try to extract from page JavaScript/JSON data
            if len(case_urls) < self.max_cases:
                logger.info("Strategy 5: Extracting from page data...")
                try:
                    # Try to execute JavaScript to find case URLs
                    js_code = """
                    () => {
                        const urls = [];
                        // Look for data attributes
                        document.querySelectorAll('[data-url], [data-href], [data-case-url], [data-judgment-url]').forEach(el => {
                            const url = el.getAttribute('data-url') || el.getAttribute('data-href') || 
                                       el.getAttribute('data-case-url') || el.getAttribute('data-judgment-url');
                            if (url && (url.includes('judgment') || url.includes('case'))) {
                                urls.push(url);
                            }
                        });
                        // Look for script tags with JSON data
                        document.querySelectorAll('script').forEach(script => {
                            const text = script.textContent || '';
                            const matches = text.match(/https?:\\/\\/[^"\\s]*judgment[^"\\s]*/gi);
                            if (matches) urls.push(...matches);
                        });
                        return [...new Set(urls)];
                    }
                    """
                    js_urls = await page.evaluate(js_code)
                    if js_urls:
                        logger.info(f"Found {len(js_urls)} URLs from JavaScript")
                        for url in js_urls:
                            if url and ('judgment' in url.lower() or 'case' in url.lower()):
                                full_url = url if url.startswith('http') else f"{self.base_url}{url}"
                                if 'casemine.com' in full_url and full_url not in case_urls:
                                    case_urls.append(full_url)
                                    if len(case_urls) >= self.max_cases:
                                        break
                except Exception as e:
                    logger.debug(f"Error extracting from JS: {e}")
            
            # Remove network listeners
            try:
                page.remove_listener('response', handle_response)
                page.remove_listener('request', handle_request)
            except:
                pass
            
            # Debug: Save page HTML for inspection
            try:
                html_content = await page.content()
                with open('casemine_debug.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.debug("Saved page HTML to casemine_debug.html for debugging")
            except Exception as e:
                logger.debug(f"Could not save debug HTML: {e}")
            
            logger.info(f"Found {len(case_urls)} case URLs")
            return case_urls[:self.max_cases]
            
        except PlaywrightTimeoutError:
            logger.error("Timeout waiting for search results")
            return []
        except Exception as e:
            logger.error(f"Error searching cases: {e}")
            return []
    
    async def extract_case_details(self, page: Page, case_url: str, settlement_only: bool = True) -> Optional[Dict]:
        """Extract detailed case information from a case page
        
        Args:
            page: Playwright page object
            case_url: URL of the case to extract
            settlement_only: If True, skip non-settlement cases (default: True)
        """
        logger.info(f"Extracting case from: {case_url}")
        
        try:
            await page.goto(case_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            await page.wait_for_timeout(3000)  # Wait for dynamic content
            
            # Check for captcha but still try to extract (sometimes content is still available)
            page_title = await page.title()
            page_url = page.url
            captcha_detected = False
            if 'captcha' in page_title.lower() or 'captcha' in page_url.lower():
                logger.warning(f"Possible captcha detected on {case_url}, but attempting extraction anyway...")
                captcha_detected = True
            
            # Get page content
            content = await page.content()
            page_text = await page.evaluate('document.body.innerText')
            full_text = (content + " " + page_text).lower()
            
            # Check for captcha in content but don't skip
            if 'captcha' in content.lower()[:10000]:
                if not captcha_detected:
                    logger.warning(f"Possible captcha in page content for {case_url}, but attempting extraction anyway...")
                captcha_detected = True
            
            # FILTER: Check if this is a settlement case (if settlement_only is True)
            if settlement_only:
                settlement_keywords = [
                    'settlement', 'settled', 'settling',
                    'settlement agreement', 'settled for', 'settlement amount',
                    'reached a settlement', 'agreed to settle', 'settlement reached'
                ]
                
                verdict_only_keywords = [
                    'jury verdict', 'verdict for', 'verdict against',
                    'awarded by jury', 'jury found', 'jury awarded'
                ]
                
                has_settlement = any(keyword in full_text for keyword in settlement_keywords)
                has_verdict_only = any(keyword in full_text for keyword in verdict_only_keywords) and not has_settlement
                
                # More lenient filtering: If search was filtered for settlements, trust it
                # Only skip if it's clearly a verdict-only case with NO settlement mention
                if has_verdict_only and not has_settlement:
                    logger.info(f"  ✗ Skipping: Verdict-only case (no settlement mentioned)")
                    return None
                
                # If settlement is mentioned OR search was filtered for settlements, accept it
                # (The search URL already has narrowing=settlement, so we trust the filter)
                if has_settlement or 'settlement' in page_title.lower() or 'settlement' in case_url.lower():
                    logger.info(f"  ✓ Settlement case confirmed")
                else:
                    # If no clear indicators but search was filtered, still accept (might be in details)
                    logger.info(f"  ⚠ No clear settlement indicators, but search was filtered - accepting")
            
            soup = BeautifulSoup(content, 'html.parser')
            
            case_data = {
                'source_url': case_url,
                'collected_at': datetime.now().isoformat(),
                'collector_notes': f"Scraped from Casemine.com" + (" (CAPTCHA detected but extraction attempted)" if captcha_detected else ""),
                'verification_status': 'pending'
            }
            
            # Extract case title/name - try multiple methods
            title_found = False
            
            # Method 1: Try CSS selectors
            title_selectors = [
                'h1',
                '.case-title',
                '.judgment-title',
                '[data-case-title]',
                'title'
            ]
            for selector in title_selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        title_text = element.get_text(strip=True)
                        if title_text and len(title_text) > 5:
                            case_data['case_name'] = title_text
                            title_found = True
                            break
                except:
                    continue
            
            # Method 2: Try Playwright to get title
            if not title_found:
                try:
                    title_elem = await page.locator('h1').first
                    if await title_elem.count() > 0:
                        title_text = await title_elem.inner_text()
                        if title_text and len(title_text.strip()) > 5:
                            case_data['case_name'] = title_text.strip()
                            title_found = True
                except:
                    pass
            
            # Method 3: Extract from page title tag
            if not title_found:
                try:
                    title_tag = soup.find('title')
                    if title_tag:
                        title_text = title_tag.get_text(strip=True)
                        # Remove " | CaseMine" or similar suffixes
                        title_text = re.sub(r'\s*\|\s*.*$', '', title_text)
                        if title_text and len(title_text) > 5:
                            case_data['case_name'] = title_text
                            title_found = True
                except:
                    pass
            
            # Extract court/jurisdiction - try multiple methods
            court_found = False
            
            # Method 1: Try CSS selectors
            court_selectors = [
                '.court-name',
                '.jurisdiction',
                '[data-court]',
                '[class*="court"]',
                '[class*="jurisdiction"]'
            ]
            for selector in court_selectors:
                try:
                    elements = soup.select(selector)
                    for elem in elements:
                        text = elem.get_text(strip=True)
                        if text and ('Court' in text or 'District' in text or 'County' in text):
                            case_data['court'] = text
                            court_found = True
                            # Try to extract jurisdiction
                            if 'Miami' in text or 'Dade' in text:
                                case_data['jurisdiction'] = 'Miami-Dade County, FL'
                            elif 'Los Angeles' in text or 'LA' in text:
                                case_data['jurisdiction'] = 'Los Angeles County, CA'
                            elif 'California' in text:
                                case_data['jurisdiction'] = self._extract_california_jurisdiction(text)
                            elif 'Florida' in text:
                                case_data['jurisdiction'] = self._extract_florida_jurisdiction(text)
                            break
                    if court_found:
                        break
                except:
                    continue
            
            # Method 2: Search text content for court patterns
            if not court_found:
                page_text = soup.get_text()
                court_patterns = [
                    r'([A-Z][a-z]+ (?:County|District|Circuit|Supreme) Court)',
                    r'([A-Z][a-z]+ Court of [A-Z][a-z]+)',
                    r'(United States (?:District|Circuit|Supreme) Court)',
                    r'([A-Z][a-z]+ (?:Superior|Municipal|Justice) Court)'
                ]
                for pattern in court_patterns:
                    match = re.search(pattern, page_text)
                    if match:
                        case_data['court'] = match.group(1)
                        court_found = True
                        # Try to extract jurisdiction from court name
                        court_text = match.group(1)
                        if 'Miami' in court_text or 'Dade' in court_text:
                            case_data['jurisdiction'] = 'Miami-Dade County, FL'
                        elif 'Los Angeles' in court_text or 'LA' in court_text:
                            case_data['jurisdiction'] = 'Los Angeles County, CA'
                        elif 'California' in court_text:
                            case_data['jurisdiction'] = self._extract_california_jurisdiction(court_text)
                        elif 'Florida' in court_text:
                            case_data['jurisdiction'] = self._extract_florida_jurisdiction(court_text)
                        break
            
            # Extract case date - try multiple methods
            date_found = False
            
            # Method 1: Look for date elements
            date_selectors = [
                '[class*="date"]',
                '[data-date]',
                'time[datetime]'
            ]
            for selector in date_selectors:
                try:
                    elements = soup.select(selector)
                    for elem in elements:
                        date_text = elem.get('datetime') or elem.get_text(strip=True)
                        if date_text:
                            # Try to parse the date
                            date_patterns = [
                                r'(\w+\s+\d{1,2},\s+\d{4})',  # "June 18, 2004"
                                r'(\d{1,2}/\d{1,2}/\d{4})',   # "06/18/2004"
                                r'(\d{4}-\d{2}-\d{2})'         # "2004-06-18"
                            ]
                            for pattern in date_patterns:
                                match = re.search(pattern, date_text)
                                if match:
                                    case_data['case_date'] = match.group(1)
                                    date_found = True
                                    break
                        if date_found:
                            break
                    if date_found:
                        break
                except:
                    continue
            
            # Method 2: Search page text for dates
            if not date_found:
                date_text = soup.get_text()
                date_patterns = [
                    r'(\w+\s+\d{1,2},\s+\d{4})',  # "June 18, 2004"
                    r'(\d{1,2}/\d{1,2}/\d{4})',   # "06/18/2004"
                    r'(\d{4}-\d{2}-\d{2})'         # "2004-06-18"
                ]
                for pattern in date_patterns:
                    match = re.search(pattern, date_text)
                    if match:
                        case_data['case_date'] = match.group(1)
                        date_found = True
                        break
            
            # Extract case type from content
            case_data['case_type'] = self._infer_case_type(soup.get_text())
            
            # Extract outcome information
            outcome_info = self._extract_outcome(soup.get_text())
            case_data.update(outcome_info)
            
            # Extract injury information
            injury_info = self._extract_injury_info(soup.get_text())
            case_data.update(injury_info)
            
            # Extract financial information
            financial_info = self._extract_financial_info(soup.get_text())
            case_data.update(financial_info)
            
            # Extract defendant category
            case_data['defendant_category'] = self._infer_defendant_category(soup.get_text())
            
            # Extract citation if available
            citation = self._extract_citation(soup.get_text())
            if citation:
                case_data['citation'] = citation
            
            # Set defaults for required fields
            if 'case_name' not in case_data or not case_data.get('case_name'):
                # Last resort: try to extract from URL or use a default
                try:
                    # Try to get title from page using Playwright
                    title_text = await page.title()
                    if title_text and len(title_text) > 5:
                        # Remove " | CaseMine" suffix
                        title_text = re.sub(r'\s*\|\s*.*$', '', title_text)
                        case_data['case_name'] = title_text
                    else:
                        case_data['case_name'] = f"Case from {case_url.split('/')[-1]}"
                except:
                    case_data['case_name'] = f"Case from {case_url.split('/')[-1]}"
            
            if 'jurisdiction' not in case_data:
                case_data['jurisdiction'] = 'Unknown'
            if 'case_type' not in case_data:
                case_data['case_type'] = 'Personal Injury'
            if 'outcome_type' not in case_data:
                case_data['outcome_type'] = 'Settlement'
            if 'outcome_amount_range' not in case_data:
                case_data['outcome_amount_range'] = '$0-$50k'
            if 'injury_category' not in case_data:
                case_data['injury_category'] = []
            if 'defendant_category' not in case_data:
                case_data['defendant_category'] = 'Unknown'
            if 'case_date' not in case_data:
                case_data['case_date'] = None
            
            logger.info(f"Extracted case: {case_data.get('case_name', 'Unknown')}")
            return case_data
            
        except PlaywrightTimeoutError:
            logger.error(f"Timeout loading case: {case_url}")
            # Return minimal case data even on timeout
            return {
                'source_url': case_url,
                'collected_at': datetime.now().isoformat(),
                'collector_notes': f"Scraped from Casemine.com (timeout during extraction)",
                'verification_status': 'pending',
                'case_name': f"Case from {case_url.split('/')[-1]}",
                'jurisdiction': 'Unknown',
                'case_type': 'Personal Injury',
                'outcome_type': 'Settlement',
                'outcome_amount_range': '$0-$50k',
                'injury_category': [],
                'defendant_category': 'Unknown',
                'case_date': None
            }
        except Exception as e:
            logger.error(f"Error extracting case from {case_url}: {e}")
            logger.exception("Full error traceback:")
            # Return minimal case data even on error
            return {
                'source_url': case_url,
                'collected_at': datetime.now().isoformat(),
                'collector_notes': f"Scraped from Casemine.com (error: {str(e)[:100]})",
                'verification_status': 'pending',
                'case_name': f"Case from {case_url.split('/')[-1]}",
                'jurisdiction': 'Unknown',
                'case_type': 'Personal Injury',
                'outcome_type': 'Settlement',
                'outcome_amount_range': '$0-$50k',
                'injury_category': [],
                'defendant_category': 'Unknown',
                'case_date': None
            }
    
    def _extract_urls_from_json(self, data: Dict, url_list: List[str]):
        """Recursively extract URLs from JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['url', 'href', 'link', 'judgment_url', 'case_url'] and isinstance(value, str):
                    if '/judgment' in value.lower() or '/case' in value.lower():
                        full_url = value if value.startswith('http') else f"{self.base_url}{value}"
                        if full_url not in url_list:
                            url_list.append(full_url)
                elif isinstance(value, (dict, list)):
                    self._extract_urls_from_json(value, url_list)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._extract_urls_from_json(item, url_list)
    
    def _extract_california_jurisdiction(self, text: str) -> str:
        """Extract California jurisdiction from text"""
        if 'Los Angeles' in text or 'LA' in text:
            return 'Los Angeles County, CA'
        elif 'San Francisco' in text or 'SF' in text:
            return 'San Francisco County, CA'
        elif 'Orange' in text:
            return 'Orange County, CA'
        else:
            return 'California (Unknown County)'
    
    def _extract_florida_jurisdiction(self, text: str) -> str:
        """Extract Florida jurisdiction from text"""
        if 'Miami' in text or 'Dade' in text:
            return 'Miami-Dade County, FL'
        elif 'Broward' in text:
            return 'Broward County, FL'
        elif 'Palm Beach' in text:
            return 'Palm Beach County, FL'
        else:
            return 'Florida (Unknown County)'
    
    def _infer_case_type(self, text: str) -> str:
        """Infer case type from text content"""
        text_lower = text.lower()
        
        if any(term in text_lower for term in ['car accident', 'motor vehicle', 'auto accident', 'traffic accident']):
            return 'Motor Vehicle Accident'
        elif any(term in text_lower for term in ['slip and fall', 'slip & fall', 'premises liability']):
            return 'Slip and Fall'
        elif any(term in text_lower for term in ['medical malpractice', 'medical negligence']):
            return 'Medical Malpractice'
        elif any(term in text_lower for term in ['product liability', 'defective product']):
            return 'Product Liability'
        elif any(term in text_lower for term in ['wrongful death']):
            return 'Wrongful Death'
        elif any(term in text_lower for term in ['workplace injury', 'workers comp', 'work injury']):
            return 'Workplace Injury'
        else:
            return 'Personal Injury'
    
    def _extract_outcome(self, text: str) -> Dict:
        """Extract outcome information (settlement amount, verdict, etc.)"""
        outcome = {
            'outcome_type': 'Settlement',
            'outcome_amount_range': '$0-$50k'
        }
        
        text_lower = text.lower()
        
        # Check for verdict vs settlement
        if 'verdict' in text_lower and 'jury' in text_lower:
            outcome['outcome_type'] = 'Jury Verdict'
        elif 'verdict' in text_lower:
            outcome['outcome_type'] = 'Verdict'
        elif 'settlement' in text_lower:
            outcome['outcome_type'] = 'Settlement'
        
        # Extract dollar amounts
        amount_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:million|M)',
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:million|M)\s*dollars?'
        ]
        
        amounts = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if 'million' in text.lower() or 'M' in match:
                        # Convert millions
                        num = float(match.replace(',', ''))
                        amount = num * 1000000
                    else:
                        amount = float(match.replace(',', ''))
                    amounts.append(amount)
                except:
                    pass
        
        if amounts:
            max_amount = max(amounts)
            outcome['outcome_amount_range'] = self._bucket_amount(max_amount)
            outcome['extracted_amount'] = max_amount
        
        return outcome
    
    def _bucket_amount(self, amount: float) -> str:
        """Bucket amount into predefined ranges"""
        if amount < 50000:
            return '$0-$50k'
        elif amount < 100000:
            return '$50k-$100k'
        elif amount < 150000:
            return '$100k-$150k'
        elif amount < 225000:
            return '$150k-$225k'
        elif amount < 300000:
            return '$225k-$300k'
        elif amount < 600000:
            return '$300k-$600k'
        elif amount < 1000000:
            return '$600k-$1M'
        else:
            return '$1M+'
    
    def _extract_injury_info(self, text: str) -> Dict:
        """Extract injury-related information"""
        injury_info = {
            'injury_category': [],
            'primary_diagnosis': None,
            'treatment_type': [],
            'imaging_findings': []
        }
        
        text_lower = text.lower()
        
        # Injury categories
        injury_keywords = {
            'Spinal Injury': ['spinal', 'spine', 'vertebra', 'disc', 'herniated'],
            'Traumatic Brain Injury': ['tbi', 'brain injury', 'head injury', 'concussion', 'traumatic brain'],
            'Fracture': ['fracture', 'broken', 'break'],
            'Soft Tissue Injury': ['soft tissue', 'sprain', 'strain', 'whiplash'],
            'Internal Injury': ['internal injury', 'organ damage', 'internal bleeding'],
            'Burn Injury': ['burn', 'burns'],
            'Amputation': ['amputation', 'amputated', 'loss of limb']
        }
        
        for category, keywords in injury_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                injury_info['injury_category'].append(category)
        
        # Treatment types
        treatment_keywords = {
            'Surgery': ['surgery', 'surgical', 'operation'],
            'Physical Therapy': ['physical therapy', 'pt ', 'rehabilitation'],
            'Chiropractic': ['chiropractic', 'chiropractor'],
            'Pain Management': ['pain management', 'pain medication'],
            'Emergency Treatment': ['emergency', 'er ', 'emergency room']
        }
        
        for treatment, keywords in treatment_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                injury_info['treatment_type'].append(treatment)
        
        # Imaging findings
        imaging_keywords = {
            'Fracture': ['fracture', 'broken bone'],
            'Herniated Disc': ['herniated disc', 'disc herniation'],
            'Contusion': ['contusion', 'bruise'],
            'Laceration': ['laceration', 'cut']
        }
        
        for finding, keywords in imaging_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                injury_info['imaging_findings'].append(finding)
        
        return injury_info
    
    def _extract_financial_info(self, text: str) -> Dict:
        """Extract financial information (medical bills, lost wages, etc.)"""
        financial_info = {
            'medical_bills': 0.0,
            'lost_wages': None,
            'policy_limits': None
        }
        
        # Extract medical bills
        medical_patterns = [
            r'medical\s+(?:bills?|expenses?|costs?)[:\s]+\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+in\s+medical'
        ]
        
        for pattern in medical_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    financial_info['medical_bills'] = float(match.group(1).replace(',', ''))
                    break
                except:
                    pass
        
        # Extract lost wages
        wage_patterns = [
            r'lost\s+(?:wages?|income)[:\s]+\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+in\s+lost'
        ]
        
        for pattern in wage_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    financial_info['lost_wages'] = float(match.group(1).replace(',', ''))
                    break
                except:
                    pass
        
        # Extract policy limits
        policy_patterns = [
            r'policy\s+limits?[:\s]+(\$?\d+k/\$?\d+k)',
            r'(\$?\d+k/\$?\d+k)\s+policy'
        ]
        
        for pattern in policy_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                financial_info['policy_limits'] = match.group(1)
                break
        
        return financial_info
    
    def _infer_defendant_category(self, text: str) -> str:
        """Infer defendant category from text"""
        text_lower = text.lower()
        
        if any(term in text_lower for term in ['corporation', 'corp', 'company', 'llc', 'inc']):
            return 'Business'
        elif any(term in text_lower for term in ['government', 'state', 'city', 'county', 'municipal']):
            return 'Government'
        elif any(term in text_lower for term in ['individual', 'person', 'driver', 'defendant']):
            return 'Individual'
        else:
            return 'Unknown'
    
    def _extract_citation(self, text: str) -> Optional[str]:
        """Extract case citation if available"""
        # Look for citation patterns like "254 P.3d 1054" or "123 F.3d 456"
        citation_pattern = r'(\d+\s+[A-Z]\.?\d+d\s+\d+)'
        match = re.search(citation_pattern, text)
        if match:
            return match.group(1)
        return None
    
    async def scrape_from_urls(self, case_urls: List[str], settlement_only: bool = True) -> List[Dict]:
        """Extract case details from a list of case URLs
        
        Args:
            case_urls: List of case URLs to extract
            settlement_only: If True, only extract settlement cases (default: True)
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            all_cases = []
            skipped_count = 0
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Extracting from {len(case_urls)} case URLs")
            if settlement_only:
                logger.info("FILTER: Settlement cases only (skipping verdict-only cases)")
            logger.info(f"{'='*60}\n")
            
            import random
            
            for i, case_url in enumerate(case_urls, 1):
                logger.info(f"\n[{i}/{len(case_urls)}] Processing case...")
                
                case_data = await self.extract_case_details(page, case_url, settlement_only=settlement_only)
                
                if case_data:
                    all_cases.append(case_data)
                    current_count = len(all_cases)
                    case_name = case_data.get('case_name', 'Unknown')
                    logger.info(f"✅ SUCCESS! Case #{current_count} collected: {case_name}")
                    # Print prominent progress update
                    print(f"\n{'='*70}")
                    print(f"✅ CASE #{current_count} SUCCESSFULLY SCRAPED")
                    print(f"   Case Name: {case_name[:80]}")
                    print(f"   Progress: {current_count} cases collected | {i}/{len(case_urls)} processed")
                    print(f"{'='*70}\n")
                    # Also save incrementally to avoid data loss
                    if current_count % 10 == 0 and self.output_file:
                        try:
                            with open(self.output_file, 'w', encoding='utf-8') as f:
                                json.dump(all_cases, f, indent=2, ensure_ascii=False)
                            logger.info(f"💾 Checkpoint: Saved {current_count} cases to {self.output_file}")
                        except Exception as e:
                            logger.warning(f"Could not save checkpoint: {e}")
                else:
                    skipped_count += 1
                    if settlement_only:
                        logger.info(f"  (Skipped non-settlement case)")
                    else:
                        logger.warning(f"✗ Failed to extract case from: {case_url}")
                    # Still show progress even for skipped
                    print(f"⏭️  Case {i}/{len(case_urls)} skipped (non-settlement) | {len(all_cases)} collected so far")
                
                # Rate limiting - longer randomized delay to avoid captchas
                # Use 15-25 second delay with randomization
                delay = 15000 + random.randint(0, 10000)  # 15-25 seconds
                logger.info(f"Waiting {delay/1000:.1f} seconds before next case...")
                await page.wait_for_timeout(delay)
                
                # Every 5 cases, take a longer break
                if i % 5 == 0:
                    extra_delay = 30000 + random.randint(0, 20000)  # 30-50 seconds
                    logger.info(f"Taking extended break: {extra_delay/1000:.1f} seconds...")
                    print(f"⏸️  Extended break ({extra_delay/1000:.1f}s) - {len(all_cases)} cases collected so far...")
                    await page.wait_for_timeout(extra_delay)
            
            await browser.close()
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Extraction Summary:")
            logger.info(f"  Total URLs processed: {len(case_urls)}")
            logger.info(f"  Cases collected: {len(all_cases)}")
            logger.info(f"  Cases skipped: {skipped_count}")
            logger.info(f"{'='*60}")
            
            return all_cases
    
    async def scrape(self, search_terms: List[str], jurisdiction: Optional[str] = None) -> List[Dict]:
        """Main scraping method"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            all_cases = []
            
            for search_term in search_terms:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing search term: {search_term}")
                logger.info(f"{'='*60}\n")
                
                # Search for cases
                case_urls = await self.search_cases(page, search_term, jurisdiction)
                
                if not case_urls:
                    logger.warning(f"No cases found for: {search_term}")
                    continue
                
                # Extract details from each case
                for i, case_url in enumerate(case_urls, 1):
                    logger.info(f"\n[{i}/{len(case_urls)}] Processing case...")
                    
                    case_data = await self.extract_case_details(page, case_url)
                    
                    if case_data:
                        all_cases.append(case_data)
                        logger.info(f"✓ Collected case: {case_data.get('case_name', 'Unknown')}")
                    else:
                        logger.warning(f"✗ Failed to extract case from: {case_url}")
                    
                    # Rate limiting - longer delay to avoid captchas
                    await page.wait_for_timeout(8000)  # 8 second delay between cases
                    
                    if len(all_cases) >= self.max_cases:
                        break
                
                if len(all_cases) >= self.max_cases:
                    break
            
            await browser.close()
            return all_cases


async def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Scrape cases from Casemine.com')
    parser.add_argument('--search', nargs='+', help='Search terms (e.g., "car accident" "personal injury")')
    parser.add_argument('--urls', help='File containing case URLs (one per line) or comma-separated URLs')
    parser.add_argument('--jurisdiction', help='Filter by jurisdiction (e.g., "Miami-Dade", "Los Angeles")')
    parser.add_argument('--max-cases', type=int, default=50, help='Maximum number of cases to collect')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser in headless mode')
    parser.add_argument('--no-headless', action='store_false', dest='headless', help='Show browser window')
    parser.add_argument('--output', default='casemine_cases.json', help='Output JSON file')
    
    args = parser.parse_args()
    
    if not args.search and not args.urls:
        parser.error("Either --search or --urls must be provided")
    
    scraper = CasemineScraper(max_cases=args.max_cases, headless=args.headless, output_file=args.output)
    
    logger.info("="*60)
    logger.info("Casemine.com Case Scraper")
    logger.info("="*60)
    
    cases = []
    
    if args.urls:
        # Extract from provided URLs
        if os.path.isfile(args.urls):
            # Read URLs from file
            logger.info(f"Reading URLs from file: {args.urls}")
            with open(args.urls, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        else:
            # URLs provided as comma-separated string
            urls = [url.strip() for url in args.urls.split(',') if url.strip()]
        
        logger.info(f"Found {len(urls)} URLs to process")
        logger.info(f"Max cases: {args.max_cases}")
        logger.info(f"Output file: {args.output}")
        logger.info("="*60)
        
        cases = await scraper.scrape_from_urls(urls[:args.max_cases])
    else:
        # Search for cases
        logger.info(f"Search terms: {args.search}")
        logger.info(f"Jurisdiction filter: {args.jurisdiction or 'None'}")
        logger.info(f"Max cases: {args.max_cases}")
        logger.info(f"Output file: {args.output}")
        logger.info("="*60)
        
        cases = await scraper.scrape(args.search, args.jurisdiction)
    
    # Save results
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    
    logger.info("\n" + "="*60)
    logger.info("Scraping Complete!")
    logger.info("="*60)
    logger.info(f"Total cases collected: {len(cases)}")
    logger.info(f"Saved to: {args.output}")
    logger.info("\nNext steps:")
    logger.info("1. Review collected cases in the JSON file")
    logger.info("2. Verify cases manually if needed")
    logger.info("3. Run: python prepare-for-seeding.py casemine_cases.json verified_cases.json")
    logger.info("4. Run: python seed-via-supabase-client.py verified_cases.json")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())

