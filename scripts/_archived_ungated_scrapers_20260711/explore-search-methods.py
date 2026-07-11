"""
Explore Court Search Methods
Helps identify how to search for cases without specific case numbers
"""

import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def explore_los_angeles_calendar_search():
    """Explore Los Angeles calendar search functionality"""
    logger.info("Exploring Los Angeles Calendar Search...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for exploration
        page = await browser.new_page()
        
        try:
            # Go to access-a-case page
            await page.goto("https://www.lacourt.ca.gov/pages/lp/access-a-case", wait_until="networkidle")
            await asyncio.sleep(2)
            
            # Look for "Search Court Calendars" link
            logger.info("Looking for 'Search Court Calendars' option...")
            
            # Try to find and click the calendar search
            calendar_link = page.locator("text=Search Court Calendars").first()
            if await calendar_link.count() > 0:
                logger.info("Found 'Search Court Calendars' link")
                await calendar_link.click()
                await asyncio.sleep(3)
                
                # Get current URL
                current_url = page.url
                logger.info(f"Calendar search URL: {current_url}")
                
                # Take screenshot for reference
                await page.screenshot(path="la_calendar_search.png")
                logger.info("Screenshot saved: la_calendar_search.png")
                
                # Look for search form elements
                logger.info("Looking for search form elements...")
                
                # Check for date inputs
                date_inputs = await page.locator("input[type='date']").count()
                logger.info(f"Found {date_inputs} date inputs")
                
                # Check for case type dropdowns
                selects = await page.locator("select").count()
                logger.info(f"Found {selects} select dropdowns")
                
                # Check for search buttons
                buttons = await page.locator("button, input[type='submit']").count()
                logger.info(f"Found {buttons} buttons")
                
                # Get page HTML structure (first 5000 chars)
                html = await page.content()
                logger.info(f"Page HTML length: {len(html)}")
                
                # Save HTML for analysis
                with open("la_calendar_search.html", "w", encoding="utf-8") as f:
                    f.write(html[:10000])  # First 10k chars
                logger.info("HTML saved: la_calendar_search.html (first 10k chars)")
                
            else:
                logger.warning("Could not find 'Search Court Calendars' link")
            
            # Keep browser open for manual exploration
            logger.info("Browser will stay open for 30 seconds for manual exploration...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error exploring LA calendar search: {e}")
        finally:
            await browser.close()

async def explore_miami_civil_search():
    """Explore Miami-Dade civil case search"""
    logger.info("Exploring Miami-Dade Civil Search...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        page = await browser.new_page()
        
        try:
            # Go to main clerk page
            await page.goto("https://www2.miamidadeclerk.gov/", wait_until="networkidle")
            await asyncio.sleep(2)
            
            # Look for Civil or Civil Cases in navigation
            logger.info("Looking for Civil case search...")
            
            # Try to find navigation menu
            nav_items = await page.locator("a, button").all_text_contents()
            logger.info(f"Found {len(nav_items)} navigation items")
            
            # Look for "Civil" in text
            civil_links = []
            for item in nav_items:
                if "civil" in item.lower() and "criminal" not in item.lower():
                    civil_links.append(item)
            
            logger.info(f"Found potential civil links: {civil_links}")
            
            # Try to find and click civil link
            if civil_links:
                try:
                    civil_link = page.locator(f"text={civil_links[0]}").first()
                    await civil_link.click()
                    await asyncio.sleep(3)
                    
                    current_url = page.url
                    logger.info(f"Civil search URL: {current_url}")
                    
                    await page.screenshot(path="miami_civil_search.png")
                    logger.info("Screenshot saved: miami_civil_search.png")
                except Exception as e:
                    logger.warning(f"Could not click civil link: {e}")
            
            # Take screenshot of main page
            await page.screenshot(path="miami_main_page.png")
            logger.info("Screenshot saved: miami_main_page.png")
            
            # Get page HTML
            html = await page.content()
            with open("miami_main_page.html", "w", encoding="utf-8") as f:
                f.write(html[:10000])
            logger.info("HTML saved: miami_main_page.html")
            
            # Keep browser open for manual exploration
            logger.info("Browser will stay open for 30 seconds for manual exploration...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error exploring Miami civil search: {e}")
        finally:
            await browser.close()

async def main():
    """Main exploration function"""
    print("=" * 60)
    print("Court Search Methods Exploration")
    print("=" * 60)
    print()
    print("This will open browsers to explore search methods.")
    print("You can manually navigate and explore.")
    print()
    
    choice = input("Explore (1) Los Angeles or (2) Miami-Dade or (3) Both: ").strip()
    
    if choice == "1":
        await explore_los_angeles_calendar_search()
    elif choice == "2":
        await explore_miami_civil_search()
    elif choice == "3":
        await explore_los_angeles_calendar_search()
        await asyncio.sleep(2)
        await explore_miami_civil_search()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())

