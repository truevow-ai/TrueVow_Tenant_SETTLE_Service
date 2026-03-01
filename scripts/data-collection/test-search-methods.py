"""
Test Search Methods - Interactive Testing
Tests actual search functionality on both court websites
"""

import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_los_angeles_calendar_search():
    """Test Los Angeles calendar search"""
    logger.info("=" * 60)
    logger.info("Testing Los Angeles Calendar Search")
    logger.info("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to access-a-case
            logger.info("Navigating to access-a-case page...")
            await page.goto("https://www.lacourt.ca.gov/pages/lp/access-a-case", wait_until="networkidle")
            await asyncio.sleep(3)
            
            # Look for "Search Court Calendars" link
            logger.info("Looking for 'Search Court Calendars'...")
            
            # Try multiple selectors
            selectors = [
                "text=Search Court Calendars",
                "a:has-text('Search Court Calendars')",
                "[href*='calendar']",
                "button:has-text('Calendar')"
            ]
            
            clicked = False
            for selector in selectors:
                try:
                    element = page.locator(selector).first()
                    if await element.count() > 0:
                        logger.info(f"Found element with selector: {selector}")
                        await element.click()
                        await asyncio.sleep(3)
                        clicked = True
                        break
                except:
                    continue
            
            if clicked:
                current_url = page.url
                logger.info(f"Current URL: {current_url}")
                
                # Take screenshot
                await page.screenshot(path="la_calendar_search_test.png")
                logger.info("Screenshot saved: la_calendar_search_test.png")
                
                # Look for search form
                logger.info("Looking for search form elements...")
                
                # Check for date inputs
                date_inputs = await page.locator("input[type='date']").count()
                logger.info(f"Date inputs found: {date_inputs}")
                
                # Check for text inputs
                text_inputs = await page.locator("input[type='text']").count()
                logger.info(f"Text inputs found: {text_inputs}")
                
                # Check for selects
                selects = await page.locator("select").count()
                logger.info(f"Select dropdowns found: {selects}")
                
                # Get page title
                title = await page.title()
                logger.info(f"Page title: {title}")
                
                # Save HTML snippet
                html = await page.content()
                with open("la_calendar_search.html", "w", encoding="utf-8") as f:
                    f.write(html[:20000])  # First 20k chars
                logger.info("HTML saved: la_calendar_search.html")
                
                logger.info("\n" + "=" * 60)
                logger.info("Manual Testing Instructions:")
                logger.info("1. Review the page that opened")
                logger.info("2. Look for date range inputs")
                logger.info("3. Try entering a date range")
                logger.info("4. See what results appear")
                logger.info("5. Note the URL and form structure")
                logger.info("=" * 60)
                
                # Keep browser open for manual testing
                logger.info("\nBrowser will stay open for 60 seconds for manual testing...")
                await asyncio.sleep(60)
            else:
                logger.warning("Could not find 'Search Court Calendars' link")
                logger.info("Please manually click the link and note the URL")
                await asyncio.sleep(30)
        
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await browser.close()

async def test_miami_civil_search():
    """Test Miami-Dade civil search"""
    logger.info("=" * 60)
    logger.info("Testing Miami-Dade Civil Search")
    logger.info("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to civil search
            logger.info("Navigating to civil search page...")
            await page.goto("https://www.miamidadeclerk.gov/clerk/civil/caseSearch.page", wait_until="networkidle")
            await asyncio.sleep(3)
            
            # Take screenshot
            await page.screenshot(path="miami_civil_search_test.png")
            logger.info("Screenshot saved: miami_civil_search_test.png")
            
            # Look for search form elements
            logger.info("Analyzing search form...")
            
            # Check for all input types
            inputs = await page.locator("input").count()
            logger.info(f"Total input fields: {inputs}")
            
            # Check for selects
            selects = await page.locator("select").count()
            logger.info(f"Select dropdowns: {selects}")
            
            # Check for buttons
            buttons = await page.locator("button, input[type='submit']").count()
            logger.info(f"Buttons: {buttons}")
            
            # Get all input names/types
            input_info = []
            for i in range(min(inputs, 20)):  # Check first 20 inputs
                try:
                    inp = page.locator("input").nth(i)
                    input_type = await inp.get_attribute("type") or "text"
                    input_name = await inp.get_attribute("name") or await inp.get_attribute("id") or "unnamed"
                    input_info.append(f"  Input {i+1}: type={input_type}, name={input_name}")
                except:
                    pass
            
            if input_info:
                logger.info("Input fields found:")
                for info in input_info:
                    logger.info(info)
            
            # Get all select options
            if selects > 0:
                logger.info("\nSelect dropdowns found:")
                for i in range(min(selects, 10)):
                    try:
                        sel = page.locator("select").nth(i)
                        select_name = await sel.get_attribute("name") or await sel.get_attribute("id") or "unnamed"
                        options = await sel.locator("option").count()
                        logger.info(f"  Select {i+1}: name={select_name}, options={options}")
                    except:
                        pass
            
            # Save HTML
            html = await page.content()
            with open("miami_civil_search.html", "w", encoding="utf-8") as f:
                f.write(html[:20000])
            logger.info("HTML saved: miami_civil_search.html")
            
            logger.info("\n" + "=" * 60)
            logger.info("Manual Testing Instructions:")
            logger.info("1. Review the search form")
            logger.info("2. Check if date range search is available")
            logger.info("3. Check if case type filters exist")
            logger.info("4. Try different search methods")
            logger.info("5. Note what works and what doesn't")
            logger.info("=" * 60)
            
            # Keep browser open
            logger.info("\nBrowser will stay open for 60 seconds for manual testing...")
            await asyncio.sleep(60)
        
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await browser.close()

async def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("Court Search Methods - Interactive Testing")
    print("=" * 60)
    print()
    print("This will open browsers to test search methods.")
    print("You can manually interact and explore.")
    print()
    
    choice = input("Test (1) Los Angeles, (2) Miami-Dade, or (3) Both: ").strip()
    
    if choice == "1":
        await test_los_angeles_calendar_search()
    elif choice == "2":
        await test_miami_civil_search()
    elif choice == "3":
        await test_los_angeles_calendar_search()
        print("\n" + "=" * 60)
        print("Moving to Miami-Dade test...")
        print("=" * 60 + "\n")
        await asyncio.sleep(2)
        await test_miami_civil_search()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())

