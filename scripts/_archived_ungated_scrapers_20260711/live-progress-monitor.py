"""
Live progress monitor - displays incremental count updates
Shows real-time progress so you know scraper is working
"""
import json
import time
import os
from pathlib import Path
from datetime import datetime

def get_case_count_from_log(log_file: str) -> int:
    """Extract case count from log file"""
    if not os.path.exists(log_file):
        return 0
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Count "SUCCESS! Case #" occurrences
            count = content.count("SUCCESS! Case #")
            return count
    except:
        return 0

def get_case_count_from_json(json_file: str) -> int:
    """Get case count from JSON file"""
    if not os.path.exists(json_file):
        return 0
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return len(data)
            return 0
    except:
        return 0

def get_valid_case_count(json_file: str) -> int:
    """Get count of valid cases (excluding Captcha)"""
    if not os.path.exists(json_file):
        return 0
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                valid = [c for c in data if c.get('case_name', '').strip().lower() not in ['captcha', '403', 'forbidden', 'error'] and len(c.get('case_name', '').strip()) > 3]
                return len(valid)
            return 0
    except:
        return 0

def main():
    """Main monitoring loop"""
    log_file = "casemine-stealth-scraper.log"
    json_file = "settlement_cases_stealth_126.json"
    cleaned_file = "settlement_cases_stealth_126_cleaned.json"
    
    script_dir = Path(__file__).parent
    log_path = script_dir / log_file
    json_path = script_dir / json_file
    cleaned_path = script_dir / cleaned_file
    
    last_log_count = 0
    last_json_count = 0
    last_valid_count = 0
    
    print("=" * 70)
    print("LIVE PROGRESS MONITOR - Stealth Scraper")
    print("=" * 70)
    print("Monitoring every 30 seconds...")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Get current counts
            log_count = get_case_count_from_log(str(log_path))
            json_count = get_case_count_from_json(str(json_path))
            valid_count = get_valid_case_count(str(json_path))
            
            # Check if counts increased
            if log_count > last_log_count:
                increase = log_count - last_log_count
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ COUNT INCREASED!")
                print(f"   Log count: {last_log_count} → {log_count} (+{increase})")
                if json_count > last_json_count:
                    print(f"   JSON count: {last_json_count} → {json_count} (+{json_count - last_json_count})")
                if valid_count > last_valid_count:
                    print(f"   Valid cases: {last_valid_count} → {valid_count} (+{valid_count - last_valid_count})")
                print(f"   Total collected: {log_count} cases")
                print()
                last_log_count = log_count
                last_json_count = json_count
                last_valid_count = valid_count
            elif log_count > 0:
                # Show current status
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Current: {log_count} cases (JSON: {json_count}, Valid: {valid_count}) - Still working...", end='\r')
            
            time.sleep(30)  # Check every 30 seconds
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        print(f"Final count: {log_count} cases collected")

if __name__ == "__main__":
    main()
