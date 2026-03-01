#!/usr/bin/env python3
"""Extract case details from known Casemine URLs"""

import asyncio
import json
import sys
import importlib.util

# Import the scraper module
spec = importlib.util.spec_from_file_location("scrape_casemine", "scrape-casemine.py")
scrape_casemine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scrape_casemine)
CasemineScraper = scrape_casemine.CasemineScraper

async def main():
    # Known valid case URLs from earlier successful runs
    known_urls = [
        "https://www.casemine.com/judgement/us/6960ea2241a75857bc299b4e",
        "https://www.casemine.com/judgement/us/6960edd341a75857bc299c4d",
        "https://www.casemine.com/judgement/us/695fc8d2f7a3416bb34da0f6",
        "https://www.casemine.com/judgement/us/695fdad7f7a3416bb34da259",
        "https://www.casemine.com/judgement/us/695e5dfaf7a3416bb34d9e86",
        "https://www.casemine.com/judgement/us/695e5d36f7a3416bb34d9e60",
        "https://www.casemine.com/judgement/us/695e5389827d4c0685d55f5c",
        "https://www.casemine.com/judgement/us/695e46b7f7a3416bb34d9bc5",
        "https://www.casemine.com/judgement/us/695e5150827d4c0685d55e51",
        "https://www.casemine.com/judgement/us/695e51d4827d4c0685d55e93"
    ]
    
    output_file = sys.argv[1] if len(sys.argv) > 1 else "casemine_cases_from_urls.json"
    
    print(f"Extracting from {len(known_urls)} known case URLs...")
    
    scraper = CasemineScraper(max_cases=len(known_urls), headless=True)
    cases = await scraper.scrape_from_urls(known_urls)
    
    # Filter out captcha/invalid cases
    valid_cases = [c for c in cases if c and c.get('case_name') and 
                   'captcha' not in c.get('case_name', '').lower() and
                   'caseiq' not in c.get('case_name', '').lower()]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(valid_cases, f, indent=2, ensure_ascii=False)
    
    print(f"\nCollected {len(valid_cases)} valid cases")
    print(f"Saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
