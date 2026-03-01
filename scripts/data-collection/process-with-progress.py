"""
Process URLs with real-time progress reporting
Shows success message and count after each case
"""
import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scrape_casemine import CasemineScraper

async def main():
    """Process URLs with enhanced progress reporting"""
    script_dir = Path(__file__).parent
    
    # Find best URL file
    url_files = [
        'all_500_case_urls_aggressive.txt',
        'all_500_case_urls_slow_scroll.txt',
        'all_500_case_urls_infinite_scroll.txt',
        'all_500_case_urls_paginated.txt',
        'all_500_case_urls.txt'
    ]
    
    best_file = None
    best_count = 0
    
    for url_file in url_files:
        file_path = script_dir / url_file
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            if len(urls) > best_count:
                best_count = len(urls)
                best_file = url_file
    
    if not best_file:
        print("❌ No URL files found!")
        return
    
    print(f"\n{'='*70}")
    print(f"🚀 STARTING CASE PROCESSING")
    print(f"   Source: {best_file}")
    print(f"   URLs: {best_count}")
    print(f"   Output: settlement_cases_{best_count}.json")
    print(f"{'='*70}\n")
    
    output_file = f"settlement_cases_{best_count}.json"
    scraper = CasemineScraper(max_cases=best_count, headless=True, output_file=output_file)
    
    # Read URLs
    with open(script_dir / best_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()][:best_count]
    
    # Process with settlement filter
    cases = await scraper.scrape_from_urls(urls, settlement_only=True)
    
    # Save final results
    import json
    with open(script_dir / output_file, 'w', encoding='utf-8') as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print(f"✅ FINAL SUMMARY")
    print(f"   Total cases collected: {len(cases)}")
    print(f"   Saved to: {output_file}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    asyncio.run(main())
