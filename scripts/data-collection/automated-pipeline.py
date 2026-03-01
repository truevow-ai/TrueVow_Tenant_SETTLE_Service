"""
Fully automated pipeline: Extract → Process → Prepare for Seeding
Runs continuously until all 500 URLs are extracted and processed
"""
import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automated-pipeline.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutomatedPipeline:
    def __init__(self, target_urls: int = 500):
        self.target_urls = target_urls
        self.script_dir = Path(__file__).parent
        
    async def wait_for_extraction(self, url_file: str, timeout: int = 3600) -> bool:
        """Wait for URL extraction to complete"""
        logger.info(f"Waiting for URL extraction to complete ({url_file})...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if os.path.exists(url_file):
                with open(url_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                if len(urls) >= self.target_urls:
                    logger.info(f"✅ Target reached: {len(urls)} URLs extracted")
                    return True
                elif len(urls) > 0:
                    logger.info(f"  Progress: {len(urls)}/{self.target_urls} URLs")
            
            await asyncio.sleep(30)  # Check every 30 seconds
        
        logger.warning(f"Timeout waiting for extraction (found {len(urls) if 'urls' in locals() else 0} URLs)")
        return False
    
    async def process_urls(self, url_file: str, output_file: str):
        """Process URLs with settlement filter - streams output in real-time"""
        logger.info(f"Processing URLs from {url_file}...")
        print(f"\n{'='*70}")
        print(f"🚀 STARTING CASE PROCESSING")
        print(f"   Input: {url_file}")
        print(f"   Output: {output_file}")
        print(f"{'='*70}\n")
        
        cmd = [
            'python', 'scrape-casemine.py',
            '--urls', url_file,
            '--max-cases', '500',
            '--headless',
            '--output', output_file
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.script_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT  # Merge stderr to stdout
        )
        
        # Stream output in real-time
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            output = line.decode('utf-8', errors='replace').rstrip()
            if output:
                print(output)  # Print to console immediately
                logger.info(output)  # Also log it
        
        await process.wait()
        
        if process.returncode == 0:
            logger.info(f"✅ Processing complete: {output_file}")
            print(f"\n{'='*70}")
            print(f"✅ PROCESSING COMPLETE: {output_file}")
            print(f"{'='*70}\n")
            return True
        else:
            logger.error(f"Processing failed with return code: {process.returncode}")
            print(f"\n❌ Processing failed with return code: {process.returncode}\n")
            return False
    
    async def check_extraction_status(self) -> tuple:
        """Check status of all extraction attempts"""
        url_files = [
            'all_500_case_urls.txt',
            'all_500_case_urls_paginated.txt',
            'all_500_case_urls_infinite_scroll.txt',
            'all_500_case_urls_slow_scroll.txt',
            'all_500_case_urls_aggressive.txt'
        ]
        
        best_file = None
        best_count = 0
        
        for url_file in url_files:
            file_path = self.script_dir / url_file
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                if len(urls) > best_count:
                    best_count = len(urls)
                    best_file = url_file
        
        return best_file, best_count
    
    async def run_pipeline(self):
        """Run the complete automated pipeline"""
        logger.info("="*60)
        logger.info("Automated Pipeline - Extract & Process All URLs")
        logger.info("="*60)
        
        # Step 1: Check current extraction status
        logger.info("\nStep 1: Checking extraction status...")
        best_file, best_count = await self.check_extraction_status()
        
        if best_file:
            logger.info(f"  Found {best_count} URLs in {best_file}")
        else:
            logger.info("  No URL files found yet")
        
        # Step 2: Wait for extraction to reach target (or best available)
        if best_count < self.target_urls:
            logger.info(f"\nStep 2: Waiting for extraction to reach {self.target_urls} URLs...")
            # Wait for aggressive extraction
            await self.wait_for_extraction('all_500_case_urls_aggressive.txt', timeout=1800)
        
        # Step 3: Use best available URL file
        best_file, best_count = await self.check_extraction_status()
        
        if not best_file or best_count == 0:
            logger.error("No URLs found! Cannot proceed.")
            return
        
        logger.info(f"\nStep 3: Using {best_file} with {best_count} URLs")
        
        # Step 4: Process URLs
        output_file = f"settlement_cases_{best_count}.json"
        success = await self.process_urls(best_file, output_file)
        
        if success:
            logger.info("\n" + "="*60)
            logger.info("Pipeline Complete!")
            logger.info("="*60)
            logger.info(f"URLs extracted: {best_count}")
            logger.info(f"Cases processed: {output_file}")
            logger.info("\nNext steps:")
            logger.info(f"1. Review: {output_file}")
            logger.info("2. Run: python prepare-for-seeding.py <output_file> verified_cases.json")
            logger.info("3. Run: python seed-via-supabase-client.py verified_cases.json")
            logger.info("="*60)
        else:
            logger.error("Pipeline failed at processing step")


async def main():
    """Main execution"""
    pipeline = AutomatedPipeline(target_urls=500)
    await pipeline.run_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
