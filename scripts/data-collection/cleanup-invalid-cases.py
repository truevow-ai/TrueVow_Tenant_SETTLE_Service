"""
Clean up invalid cases (Captcha entries) from collected data
"""
import json
import sys
from pathlib import Path

def cleanup_cases(input_file: str, output_file: str = None):
    """Remove invalid cases (Captcha, null, or too short names)"""
    if output_file is None:
        output_file = input_file.replace('.json', '_cleaned.json')
    
    print(f"Reading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    print(f"Total cases: {len(cases)}")
    
    # Filter out invalid cases
    valid_cases = []
    invalid_count = 0
    
    for case in cases:
        case_name = case.get('case_name', '').strip()
        
        # Skip invalid cases
        if not case_name or \
           case_name.lower() == 'captcha' or \
           len(case_name) < 3 or \
           case_name.lower() in ['403', 'forbidden', 'error']:
            invalid_count += 1
            continue
        
        valid_cases.append(case)
    
    print(f"Valid cases: {len(valid_cases)}")
    print(f"Invalid cases removed: {invalid_count}")
    
    # Save cleaned data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(valid_cases, f, indent=2, ensure_ascii=False)
    
    print(f"Saved cleaned data to: {output_file}")
    return len(valid_cases), invalid_count

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "settlement_cases_stealth_126.json"
    
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    valid, invalid = cleanup_cases(input_file)
    print(f"\nCleanup complete: {valid} valid cases, {invalid} invalid cases removed")
