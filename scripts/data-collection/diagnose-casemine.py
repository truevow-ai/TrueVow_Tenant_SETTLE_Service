"""
Diagnostic script to understand Casemine.com page structure
"""

import asyncio
from playwright.async_api import async_playwright

async def diagnose():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for inspection
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        url = "https://www.casemine.com/search/us?stype=parallel&q=car+accident"
        print(f"Navigating to: {url}")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(5000)
        
        # Get all links and their hrefs
        print("\n=== All Links ===")
        links = await page.locator('a').all()
        print(f"Total links found: {len(links)}")
        
        judgment_links = []
        for i, link in enumerate(links[:50]):  # First 50 links
            try:
                href = await link.get_attribute('href')
                text = await link.inner_text()
                if href:
                    print(f"{i+1}. {href[:80]}... | Text: {text[:50]}")
                    if 'judgment' in href.lower() or 'case' in href.lower():
                        judgment_links.append((href, text))
            except:
                pass
        
        print(f"\n=== Judgment/Case Links Found: {len(judgment_links)} ===")
        for href, text in judgment_links[:10]:
            print(f"  {href} | {text[:50]}")
        
        # Check for data attributes
        print("\n=== Checking for data attributes ===")
        elements_with_data = await page.locator('[data-href], [data-url], [data-case-id], [data-judgment-id]').all()
        print(f"Elements with data attributes: {len(elements_with_data)}")
        for elem in elements_with_data[:10]:
            try:
                data_href = await elem.get_attribute('data-href')
                data_url = await elem.get_attribute('data-url')
                data_case = await elem.get_attribute('data-case-id')
                print(f"  data-href: {data_href}, data-url: {data_url}, data-case-id: {data_case}")
            except:
                pass
        
        # Check page title and URL
        print(f"\n=== Page Info ===")
        print(f"Title: {await page.title()}")
        print(f"URL: {page.url}")
        
        # Save HTML
        html = await page.content()
        with open('casemine_diagnostic.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("\nSaved HTML to: casemine_diagnostic.html")
        
        print("\n=== Waiting 30 seconds for manual inspection ===")
        print("Please inspect the browser window and the page structure")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(diagnose())

